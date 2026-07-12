import httpx
import inspect

from typing import Callable, Optional

from league.http import BaseAPIClient
from league.console import log_error
from league.enums import GameEventType, LeagueClientStatus
from league.models import ActivePlayer, AllGameData, GameEvent, GameTeam

DEFAULT_RIOT_API_REGION = "na1"


type GameEventCallback = Callable[[GameEvent], None]


class LeagueClient(BaseAPIClient):
    _callbacks: dict[GameEventType, list[GameEventCallback]]
    _history: list[GameEvent]

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url="https://127.0.0.1:2999/liveclientdata",
            http2=True,
            verify=False,
        )
        self.last_event_count = 0
        self._callbacks = {}
        self._history = []

    async def get_client_status(self) -> LeagueClientStatus:
        err = await self.get("/eventdata", _return_exception=True, _suppress_exception=True)
        if isinstance(err, httpx.HTTPStatusError):
            return LeagueClientStatus.LOADING
        if isinstance(err, httpx.RequestError):
            if isinstance(err, httpx.RemoteProtocolError):
                return LeagueClientStatus.BANISHED
            return LeagueClientStatus.DISCONNECTED
        return LeagueClientStatus.CONNECTED

    async def get_all_game_data(self) -> AllGameData:
        return AllGameData(**await self.get("/allgamedata"))

    async def get_active_player(self) -> Optional[ActivePlayer]:
        raw = await self.get("/activeplayer")
        if raw is None or "error" in raw:
            return None

        return ActivePlayer(**raw)

    async def get_active_player_team(self) -> Optional[GameTeam]:
        active = await self.get_active_player()
        if active is None:
            return None

        raw = await self.get("/allgamedata")
        for player in raw["allPlayers"]:
            if player["riotId"] == active.riotId:
                return GameTeam(player["team"])
        return None

    async def get_all_events(self):
        events = await self.get("/eventdata", _suppress_exception=True)
        if events is not None:
            return events.get("Events")

    async def get_last_event(self) -> Optional[GameEvent]:
        return self._history[-1]

    def reset(self):
        self.last_event_count = 0

    def on(self, event_type: GameEventType, callback: GameEventCallback):
        self._callbacks.setdefault(event_type, [])
        self._callbacks[event_type].append(callback)

    async def poll_events(self):
        events = await self.get_all_events()
        if events is None:
            return
        event_count = len(events)
        if event_count == self.last_event_count:
            return

        num_new_events = event_count - self.last_event_count
        if event_count > 0:
            new_events = events[-num_new_events:]
            if isinstance(new_events, list):
                for event in new_events:
                    await self.on_event(event)
            else:
                await self.on_event(new_events)

        self.last_event_count = event_count

    async def try_fire_callbacks_for_event(self, event: GameEvent):
        event_type = event.EventName
        for callback in self._callbacks.get(event_type, []):
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                log_error(f"[error]Encountered an error while dispatching callbacks for event '[heading]{event.EventName}[/heading]'[/]: {str(e)}")

    async def on_event(self, eventRaw: dict):
        event = GameEvent(**eventRaw)
        self._history.append(event)
        await self.try_fire_callbacks_for_event(event)
