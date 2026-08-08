import httpx
import asyncio

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from league.enums import Queue
from league.lcu.models import *
from league.console import print
from league.dragon import DataDragon
from league.http import BaseAPIClient

from league.lcu.socket import LCUWebsocketClient, LCUWebsocketEventCallback
from league.lcu.exceptions import LCUMissingReplayMetadataException, LCUIncompatibleReplayException

FALLBACK_LOCKFILE_PATH = Path("F:/Games/League of Legends/lockfile")

RIOT_USERNAME = "riot"

DEFAULT_MATCH_HISTORY_COUNT = 20


@dataclass(frozen=True, slots=True)
class LCULockfileData:
    ProcessName: str
    ProcessID: int
    Port: int
    Password: str
    Protocol: str


class LCUClient(BaseAPIClient):
    def __init__(self, client_install_path: Path):
        self._lockfile = self._read_lockfile(client_install_path)

        base_url = f"{self._lockfile.Protocol}://127.0.0.1:{self._lockfile.Port}"
        auth = httpx.BasicAuth(
            username=RIOT_USERNAME,
            password=self._lockfile.Password,
        )
        self.client = httpx.AsyncClient(
            base_url=base_url,
            verify=False,
            auth=auth,
        )

        self.dragon = DataDragon()

        self.ws = LCUWebsocketClient(self._lockfile.Port, auth._auth_header)

    def _read_lockfile(self, client_install_path: Path) -> LCULockfileData:
        lockfile_path = client_install_path / "lockfile"
        if not lockfile_path.exists():
            lockfile_path = FALLBACK_LOCKFILE_PATH

        if not lockfile_path.exists():
            raise FileNotFoundError("Client lockfile not found")

        with open(lockfile_path) as f:
            text = f.read()

        return LCULockfileData(*text.split(":"))

    def on(self, event: str, callback: LCUWebsocketEventCallback):
        return self.ws.on(event, callback)

    async def start_websocket(self):
        await self.ws.connect()
        await self.dragon.initialize()

    async def close_websocket(self):
        await self.ws.disconnect()

    async def __aenter__(self):
        await self.start_websocket()
        return self

    async def __aexit__(self, *_):
        await self.close_websocket()

    async def is_logged_in(self):
        return await self.get("/lol-platform-config/v1/initial-configuration-complete")

    async def get_help(self):
        return await self.get("/help")

    async def get_locked_champion(self) -> Optional[int]:
        champ_id = await self.get("/lol-champ-select/v1/current-champion")
        return champ_id

    async def get_hovered_champion(self) -> Optional[MyChampSelection]:
        raw_selection = await self.get("/lol-champ-select/v1/session/my-selection")
        selection = MyChampSelection(**raw_selection) if raw_selection is not None else None
        if selection is None:
            return None

        return selection

    async def create_game_lobby(
        self,
        lobby_type: Optional[LobbyType] = LobbyType.Custom,
        game_mode: Optional[LobbyGameMode] = LobbyGameMode.Practice,
        queueID: Optional[int] = 430,
        **kwargs,
    ):
        match lobby_type:
            case LobbyType.Normal:
                return await self.create_normal_game_lobby(queueID=queueID, **kwargs)
            case LobbyType.Custom:
                return await self.create_custom_game_lobby(game_mode=game_mode, **kwargs)

    async def create_custom_game_lobby(self, game_mode: Optional[LobbyGameMode] = LobbyGameMode.Practice, **kwargs):
        lobby_config = {
            "queueId": Queue.PRACTICE,
            "customGameLobby": {
                "configuration": {
                    "gameMode": game_mode,
                    "gameMutator": "",
                    "mutators": {"id": 1},
                    "gameServerRegion": "",
                    "mapId": Map.SUMMONER_S_RIFT_3,
                    "spectatorPolicy": "AllAllowed",
                    "teamSize": 5,
                    "maxPlayerCount": 10,
                    "hidePublicly": True,
                },
                "lobbyName": "Clever Lobby Name Here",
                "lobbyPassword": "corgi",
            },
            "isCustom": True,
        }
        if kwargs:
            lobby_config.update(kwargs)
        res = await self.post("/lol-lobby/v2/lobby", json=lobby_config)
        return res

    async def create_normal_game_lobby(self, queueID: Optional[Queue] = Queue.Q_5V5_DRAFT_PICK_GAMES_2, **kwargs):
        """Non-functional right now"""
        lobby_config = {
            "queueId": queueID,
            "customGameLobby": {
                "configuration": {
                    "gameMode": LobbyGameMode.Normal,
                    "mapId": Map.SUMMONER_S_RIFT_3,
                }
            },
        }
        if kwargs:
            lobby_config.update(kwargs)
        res = await self.post("/lol-lobby/v2/lobby", json=lobby_config)
        return res

    async def get_lobby(self):
        return await self.get("/lol-lobby/v2/lobby")

    async def get_current_summoner(self) -> Summoner:
        res = await self.get("/lol-summoner/v1/current-summoner")
        return Summoner(**res)

    async def get_match(self, matchID: int) -> LCUMatch:
        res = await self.get(f"/lol-match-history/v1/games/{matchID}")
        return LCUMatch(**res)

    async def get_match_history(
        self,
        start_index: int = 0,
        end_index: Optional[int] = None,
        count: Optional[int] = None,
        queue_type: Optional[Queue] = None,
    ) -> LCUMatchHistory:
        if end_index is None:
            end_index = start_index + (count if count is not None else DEFAULT_MATCH_HISTORY_COUNT)

        params = {"begIndex": start_index, "endIndex": end_index}
        res = await self.get("/lol-match-history/v1/products/lol/current-summoner/matches", params=params)

        history = LCUMatchHistory(**res)
        if queue_type is not None:
            filtered = history.get_matches_by_queue_type(queue_type)
            history.games.update_games(filtered)

        return history

    async def get_recent_match_ids(self) -> list[int]:
        history = await self.get_match_history()
        return [g.gameId for g in history.games.games]

    async def get_last_match(self, queue_type: Optional[Queue] = None) -> LCUMatch:
        history = await self.get_match_history(count=1, queue_type=queue_type)
        return history.games.games[0]

    async def get_last_match_id(self, queue_type: Optional[Queue] = None) -> int:
        last_match = await self.get_last_match(queue_type=queue_type)
        return last_match.gameId

    async def get_match_timeline(self, matchID: int) -> LCUTimeline:
        res = await self.get(f"/lol-match-history/v1/game-timelines/{matchID}")
        return LCUTimeline(**res)

    async def get_player_participant_id(self, matchID: int) -> int:
        game = await self.get_match(matchID)
        return game.participantIdentities[0].participantId

    async def download_replay(self, matchID: int):
        async def start_download(matchID: int):
            return await self.post(f"/lol-replays/v1/rofls/{matchID}/download/graceful", json={"gameId": matchID}, no_json=True)

        async def check_download(matchID: int) -> LCUReplayDownloadStatus:
            progress = await self.get_replay_metadata(matchID)
            state = progress.get("state")
            match state:
                case LCUReplayState.Watch:
                    return LCUReplayDownloadStatus.Success
                case LCUReplayState.Retry:
                    return LCUReplayDownloadStatus.Retry
                case _:
                    return LCUReplayDownloadStatus.Downloading

        download_state = LCUReplayDownloadStatus.NotStarted
        res = await start_download(matchID)
        print(f"replay download start status: {res.status_code}")
        for _ in range(10):
            download_state = await check_download(matchID)
            match download_state:
                case LCUReplayDownloadStatus.Success:
                    break
                case LCUReplayDownloadStatus.Failed:
                    raise LCUIncompatibleReplayException(matchID=matchID)
                case LCUReplayDownloadStatus.Downloading:
                    await asyncio.sleep(1)
                case LCUReplayDownloadStatus.NotStarted | LCUReplayDownloadStatus.Retry:
                    start_res = await start_download(matchID)
                    print(f"replay download retry status: {start_res.status_code}")
                case _:
                    print(f"status: {download_state}")
                    break

        return download_state

    async def launch_replay(self, matchID: int):
        metadata = await self.get_replay_metadata(matchID)

        if metadata is None:
            await self.create_replay_metadata(matchID)
            metadata = await self.get_replay_metadata(matchID)

        if metadata is None:
            raise LCUMissingReplayMetadataException(matchID=matchID)

        if metadata.get("state") != LCUReplayState.Watch:
            success = await self.download_replay(matchID)
            print(f"download success: {success}")

        return await self.post(f"/lol-replays/v1/rofls/{matchID}/watch", json={"gameId": matchID})

    async def create_replay_metadata(self, matchID: int):
        return await self.post(f"/lol-replays/v2/metadata/{matchID}/create")

    async def get_replay_metadata(self, matchID: int):
        return await self.get(f"/lol-replays/v1/metadata/{matchID}")

    def get_position_for_lane_and_role(self, lane: LCULane, role: LCURole) -> LCUPosition:
        try:
            return PlayerRoleMapping[(lane, role)]
        except KeyError:
            print(f"[warning]Unable to find position for lane={lane}, role={role}[/]")
            return LCUPosition.Unknown

    async def get_inventory(self):
        return await self.get("/lol-game-data-inventory/v1/items/contentIds")

    async def get_inventory_item(self, content_id: str):
        return await self.get(f"/lol-game-data-inventory/v1/items/contentIds/{content_id}")

    async def get_asset(self, endpoint: str):
        return await self.get(endpoint, no_json=True)

    async def get_gameflow_availability(self):
        return await self.get(f"/lol-gameflow/v1/availability")

    async def get_gameflow_phase(self):
        phase = await self.get(f"/lol-gameflow/v1/gameflow-phase")
        return LCUGameflowPhase(phase)

    async def get_gameflow_session(self):
        return await self.get(f"/lol-gameflow/v1/session")
