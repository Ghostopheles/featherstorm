import ssl
import json
import asyncio
import inspect
import websockets

from enum import StrEnum
from dataclasses import dataclass
from typing import Callable, Any

from league.console import print, log, log_error, log_warning

SOCKET_URL = "wss://localhost"
WS_MAX_SIZE = 2**32
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class LCUWebsocketEventType(StrEnum):
    Create = "Create"
    Update = "Update"
    Delete = "Delete"


@dataclass
class LCUWebsocketEvent:
    opcode: int
    eventName: str
    uri: str
    eventType: str
    data: dict

    def __post_init__(self):
        self.eventType = LCUWebsocketEventType[self.eventType]


type LCUWebsocketEventCallback = Callable[[LCUWebsocketEvent], Any]


@dataclass(frozen=True, slots=True)
class LCUWebsocketEventCallbackRegistration:
    event_type: LCUWebsocketEventType
    callback: LCUWebsocketEventCallback


class LCUWebsocketClient:
    _port: int
    _auth: str
    _callbacks: dict[str, list[LCUWebsocketEventCallbackRegistration]]
    _task: asyncio.Task | None

    def __init__(self, port: int, auth: str):
        self._port = port
        self._auth = auth
        self._callbacks = {}
        self._task = None

    def on(self, event: str, callback: LCUWebsocketEventCallback, type: LCUWebsocketEventType | None = None):
        if self._task:
            raise Exception("Cannot register callbacks after websocket has connected")

        event = event.replace("/", "_")
        if not event.startswith("OnJsonApiEvent"):
            event = f"OnJsonApiEvent{event}"

        registration = LCUWebsocketEventCallbackRegistration(event_type=type, callback=callback)

        self._callbacks.setdefault(event, [])
        self._callbacks[event].append(registration)

    @staticmethod
    def _parse_event(message: str) -> LCUWebsocketEvent:
        rawEvent = json.loads(message)
        opcode = rawEvent[0]
        eventName = rawEvent[1]
        event = rawEvent[2]
        return LCUWebsocketEvent(
            opcode=opcode,
            eventName=eventName,
            uri=event.get("uri"),
            eventType=event.get("eventType"),
            data=event.get("data"),
        )

    async def _on_message(self, message: str):
        event = self._parse_event(message)
        for handler in self._callbacks.get(event.eventName, []):
            if handler.event_type == event.eventType:
                try:
                    if inspect.iscoroutinefunction(handler.callback):
                        asyncio.create_task(handler.callback(event))
                    else:
                        handler.callback(event)
                except Exception as e:
                    log_error(f"{str(e)} calling handler for WS event '{event.eventName}'")

    async def _listen(self):
        async for socket in websockets.connect(
            f"{SOCKET_URL}:{self._port}", additional_headers=[("Authorization", self._auth)], max_size=WS_MAX_SIZE, ssl=ssl_context
        ):
            try:
                if not self._callbacks:
                    await socket.send('[5, "OnJsonApiEvent"]')
                else:
                    for eventName in self._callbacks:
                        await socket.send(f'[5, "{eventName}"]')
                        log(f"Subscribed to websocket event '{eventName}'")

                log("Connected to LCU websocket")

                async for message in socket:
                    if not message:
                        continue
                    await self._on_message(message)
            except websockets.ConnectionClosed:
                continue

    def _on_task_done(self, task: asyncio.Task) -> None:
        if not task.cancelled():
            log_warning("Websocket listener closed")

    async def connect(self):
        if self._task and not self._task.done():
            return

        self._task = asyncio.create_task(self._listen())
        self._task.add_done_callback(self._on_task_done)

    async def disconnect(self):
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
