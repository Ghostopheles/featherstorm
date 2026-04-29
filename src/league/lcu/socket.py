import ssl
import json
import asyncio
import websockets

from rich import print
from enum import StrEnum
from dataclasses import dataclass
from typing import Callable, Any

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


class LCUWebsocketClient:
    _port: int
    _auth: str
    _callbacks: dict[str, list[LCUWebsocketEventCallback]] = dict()
    _task: asyncio.Task | None = None

    def __init__(self, port: int, auth: str):
        self._port = port
        self._auth = auth

    def on(self, event: str, callback: LCUWebsocketEventCallback):
        if self._task:
            raise Exception("Cannot register callbacks after websocket has connected")

        self._callbacks.setdefault(event, [])
        self._callbacks[event].append(callback)

    @staticmethod
    def _parse_event(message: str) -> LCUWebsocketEvent:
        rawEvent = json.loads(message)
        opcode = rawEvent[0]
        eventName = rawEvent[1]
        event = rawEvent[2]
        return LCUWebsocketEvent(opcode=opcode, eventName=eventName, uri=event.get("uri"), eventType=event.get("eventType"), data=event.get("data"))

    async def _on_message(self, message: str):
        event = self._parse_event(message)

        print(event)
        for handler in self._callbacks.get(event.eventName, []):
            asyncio.create_task(handler(event))

    async def _listen(self):
        async for socket in websockets.connect(
            f"{SOCKET_URL}:{self._port}", additional_headers=[("Authorization", self._auth)], max_size=WS_MAX_SIZE, ssl=ssl_context
        ):
            try:
                if len(self._callbacks) == 0:
                    print("No event subscriptions - subscribing to all.")
                    await socket.send('[5, "OnJsonApiEvent"]')
                else:
                    for eventName in self._callbacks:
                        await socket.send(f'[5, "{eventName}"]')
                        print(f"Subscribed to '{eventName}'")

                print("Connected to LCU websocket")

                async for message in socket:
                    if not message:
                        continue
                    await self._on_message(message)
            except websockets.ConnectionClosed:
                continue

    def _on_task_done(self, task: asyncio.Task) -> None:
        if not task.cancelled() and (exc := task.exception()):
            print("WebSocket listener crashed:\n" + str(exc))

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
