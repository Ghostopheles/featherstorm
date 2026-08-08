from enum import StrEnum
from pathlib import Path

import league.config as cfg
from league.lcu import LCUClient
from league.lcu.models import LCUGameflowPhase
from league.lcu.socket import LCUWebsocketEventCallback, LCUWebsocketEventType

default_client_path = Path(cfg.get("lcu.client_install_path"))


class LCUGameFlowEvent(StrEnum):
    LobbyCreated = "LobbyCreated"
    LobbyUpdated = "LobbyUpdated"
    LobbyDeleted = "LobbyDeleted"


GAMEFLOW_EVENT_TO_WS_ENDPOINT = {
    LCUGameFlowEvent.LobbyCreated: "/lol-lobby/v2/lobby",
    LCUGameFlowEvent.LobbyUpdated: "/lol-lobby/v2/lobby",
    LCUGameFlowEvent.LobbyDeleted: "/lol-lobby/v2/lobby",
}


def get_event_endpoint(event: LCUGameFlowEvent):
    return GAMEFLOW_EVENT_TO_WS_ENDPOINT.get(event)


def get_event_type(event: LCUGameFlowEvent) -> LCUWebsocketEventType:
    if "Created" in event:
        return LCUWebsocketEventType.Create
    elif "Updated" in event:
        return LCUWebsocketEventType.Update
    elif "Deleted" in event:
        return LCUWebsocketEventType.Delete
    else:
        raise TypeError("'event' must be a valid LCUGameFlowEvent")


class LCUGameFlow:
    lcu: LCUClient
    _callbacks: dict[str, LCUWebsocketEventCallback] = None

    def __init__(self, lcu_client: LCUClient | None = None):
        self.lcu = lcu_client or LCUClient(client_install_path=default_client_path)

    async def start(self):
        await self.lcu.start_websocket()

    async def is_available(self) -> bool:
        availability = await self.lcu.get_gameflow_availability()
        return availability.get("isAvailable")

    async def get_phase(self) -> LCUGameflowPhase:
        return await self.lcu.get_gameflow_phase()

    def add_raw_ws_event_callback(
        self,
        endpoint: str,
        callback: LCUWebsocketEventCallback,
        event_type: LCUWebsocketEventType | None = None,
    ):
        return self.lcu.ws.on(endpoint, callback, event_type)

    def add_callback(self, event: LCUGameFlowEvent, callback: LCUWebsocketEventCallback):
        event_type = get_event_type(event)
        endpoint = get_event_endpoint(event)
        return self.add_raw_ws_event_callback(endpoint, callback, event_type)
