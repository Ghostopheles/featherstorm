import asyncio
import inspect
import logging

from enum import StrEnum
from pathlib import Path
from typing import Callable, Optional, Any

from league import config
from league.api import LeagueClient
from league.lcu import LCUClient
from league.watcher import MatchWatcher
from league.models import GameEvent, AllGameData
from league.lcu.models import LCUGameflowPhase
from league.enums import GameEventType, LeagueClientStatus
from league.lcu.socket import LCUWebsocketEvent, LCUWebsocketEventType

log = logging.getLogger(__name__)

type BridgeCallback = Callable[..., Any]

LOBBY_ENDPOINT = "/lol-lobby/v2/lobby"
GAMEFLOW_PHASE_ENDPOINT = "/lol-gameflow/v1/gameflow-phase"


class LeagueEvent(StrEnum):
    # in-game events (Live Client API) - callbacks receive a GameEvent
    GameStart = "GameStart"
    GameEnd = "GameEnd"
    MinionsSpawning = "MinionsSpawning"
    FirstBlood = "FirstBlood"
    TurretKilled = "TurretKilled"
    InhibKilled = "InhibKilled"
    DragonKill = "DragonKill"
    HeraldKill = "HeraldKill"
    BaronKill = "BaronKill"
    ChampionKill = "ChampionKill"
    Multikill = "Multikill"
    Ace = "Ace"
    HordeKill = "HordeKill"
    FirstBrick = "FirstBrick"
    AtakahnKill = "AtakahnKill"
    InhibRespawned = "InhibRespawned"
    # out-of-game events (LCU websocket) - callbacks receive an LCUWebsocketEvent
    LobbyCreated = "LobbyCreated"
    LobbyUpdated = "LobbyUpdated"
    LobbyDeleted = "LobbyDeleted"
    # gameflow phase changes (LCU websocket) - callbacks receive an LCUGameflowPhase
    PhaseChanged = "PhaseChanged"
    # in-game session lifecycle (MatchWatcher) - callbacks receive no arguments
    SessionStart = "SessionStart"
    SessionEnd = "SessionEnd"


def _bridge_event_for(event_type: GameEventType) -> Optional[LeagueEvent]:
    try:
        return LeagueEvent(event_type.value)
    except ValueError:
        return None


class LeagueEventBridge:
    """Unified event hub bridging the Live Client API (in-game) and the LCU websocket (out-of-game).

    Register callbacks with `on(LeagueEvent.X, cb)` (sync or async), then `await run()`.
    Underlying clients exposed as `bridge.game` (LeagueClient) and `bridge.lcu` (LCUClient,
    None when the League client isn't running).
    """

    game: LeagueClient
    lcu: Optional[LCUClient]

    def __init__(self, game_client: Optional[LeagueClient] = None, lcu_client: Optional[LCUClient] = None):
        self.game = game_client or LeagueClient()
        self._watcher = MatchWatcher(self.game, exit_on_timeout=False)
        self._callbacks: dict[LeagueEvent, list[BridgeCallback]] = {}
        self._tasks: set[asyncio.Task] = set()

        # internal dispatchers registered up-front so user callbacks can be added any time,
        # sidestepping the LCU websocket's register-before-connect constraint
        for event_type in GameEventType:
            bridge_event = _bridge_event_for(event_type)
            if bridge_event is None:
                log.warning(f"No LeagueEvent member for game event '{event_type}' - it will not be dispatched")
                continue
            self.game.on(event_type, self._make_game_dispatcher(bridge_event))

        self._watcher.on_session_start(self._on_session_start)
        self._watcher.on_session_end(self._make_session_dispatcher(LeagueEvent.SessionEnd))

        self.lcu = lcu_client
        if self.lcu is None:
            try:
                client_path = Path(config.get("lcu.client_install_path"))
                self.lcu = LCUClient(client_install_path=client_path)
            except Exception:
                log.warning("League client not running - out-of-game events disabled")

        if self.lcu is not None:
            self._register_lcu_dispatchers()

    def on(self, event: LeagueEvent, callback: Optional[BridgeCallback] = None):
        if callback is None:

            def decorator(fn: BridgeCallback) -> BridgeCallback:
                self._callbacks.setdefault(event, []).append(fn)
                return fn

            return decorator
        self._callbacks.setdefault(event, []).append(callback)

    def _spawn(self, coro):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run_callback(self, event: LeagueEvent, callback: BridgeCallback, *args):
        try:
            await callback(*args)
        except Exception as e:
            log.exception(f"Error dispatching bridge callback for '{event}': {e}")

    async def _fire(self, event: LeagueEvent, *args):
        # async callbacks run as tasks so a slow handler can't stall the 250ms poll loop or the
        # websocket reader - they are concurrent with each other, not serialized
        for callback in self._callbacks.get(event, []):
            if inspect.iscoroutinefunction(callback):
                self._spawn(self._run_callback(event, callback, *args))
                continue
            try:
                callback(*args)
            except Exception as e:
                log.exception(f"Error dispatching bridge callback for '{event}': {e}")

    def _make_game_dispatcher(self, bridge_event: LeagueEvent):
        async def dispatch(event: GameEvent):
            await self._fire(bridge_event, event)

        return dispatch

    def _make_session_dispatcher(self, bridge_event: LeagueEvent):
        async def dispatch():
            await self._fire(bridge_event)

        return dispatch

    async def _on_session_start(self):
        # drop the previous match's event count/history, otherwise the next game silently
        # dispatches nothing until it passes the old count
        self.game.reset()
        await self._fire(LeagueEvent.SessionStart)

    def _make_lobby_dispatcher(self, bridge_event: LeagueEvent):
        async def dispatch(event: LCUWebsocketEvent):
            # the LCU sends a list payload for some lobby transitions - nothing downstream can use it
            if isinstance(event.data, list):
                return
            await self._fire(bridge_event, event)

        return dispatch

    async def _on_phase_event(self, event: LCUWebsocketEvent):
        try:
            phase = LCUGameflowPhase(event.data)
        except ValueError:
            log.warning(f"Unknown gameflow phase '{event.data}' - add it to LCUGameflowPhase")
            return
        await self._fire(LeagueEvent.PhaseChanged, phase)

    def _register_lcu_dispatchers(self):
        lobby_events = {
            LCUWebsocketEventType.Create: LeagueEvent.LobbyCreated,
            LCUWebsocketEventType.Update: LeagueEvent.LobbyUpdated,
            LCUWebsocketEventType.Delete: LeagueEvent.LobbyDeleted,
        }
        for ws_type, bridge_event in lobby_events.items():
            self.lcu.ws.on(LOBBY_ENDPOINT, self._make_lobby_dispatcher(bridge_event), ws_type)

        # phase pushes arrive as Create or Update depending on client state
        for ws_type in (LCUWebsocketEventType.Create, LCUWebsocketEventType.Update):
            self.lcu.ws.on(GAMEFLOW_PHASE_ENDPOINT, self._on_phase_event, ws_type)

    async def get_phase(self) -> Optional[LCUGameflowPhase]:
        if self.lcu is None:
            return None
        return await self.lcu.get_gameflow_phase()

    async def get_game_data(self) -> AllGameData:
        return await self.game.get_all_game_data()

    async def is_in_game(self) -> bool:
        return await self.game.get_client_status() == LeagueClientStatus.CONNECTED

    async def close(self):
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        if self.lcu is not None:
            await self.lcu.ws.disconnect()
            await self.lcu.close()
        await self.game.close()

    async def run(self):
        if self.lcu is not None:
            await self.lcu.start_websocket()
        try:
            await self._watcher.run()
        finally:
            await self.close()
