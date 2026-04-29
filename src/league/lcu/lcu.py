import httpx
import asyncio

from rich import print
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from league.http import BaseAPIClient
from league.dragon import CommunityDataDragon
from league.lcu.models import *

FALLBACK_LOCKFILE_PATH = Path("F:/Games/League of Legends/lockfile")

RIOT_USERNAME = "riot"

DEFAULT_QUEUE_ID = 430
PRACTICE_QUEUE_ID = 3140
SUMMONERS_RIFT_MAP_ID = 11


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
        self.client = httpx.AsyncClient(
            base_url=base_url,
            verify=False,
            auth=httpx.BasicAuth(
                username=RIOT_USERNAME,
                password=self._lockfile.Password,
            ),
        )

        self.dragon = CommunityDataDragon()

    def _read_lockfile(self, client_install_path: Path) -> LCULockfileData:
        lockfile_path = client_install_path / "lockfile"
        if not lockfile_path.exists():
            lockfile_path = FALLBACK_LOCKFILE_PATH

        if not lockfile_path.exists():
            raise FileNotFoundError("Client lockfile not found")

        with open(lockfile_path) as f:
            text = f.read()

        return LCULockfileData(*text.split(":"))

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
            "queueId": PRACTICE_QUEUE_ID,
            "customGameLobby": {
                "configuration": {
                    "gameMode": game_mode,
                    "gameMutator": "",
                    "mutators": {"id": 1},
                    "gameServerRegion": "",
                    "mapId": SUMMONERS_RIFT_MAP_ID,
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

    async def create_normal_game_lobby(self, queueID: Optional[int] = DEFAULT_QUEUE_ID, **kwargs):
        """Non-functional right now"""
        lobby_config = {
            "queueId": queueID,
            "customGameLobby": {
                "configuration": {
                    "gameMode": LobbyGameMode.Normal,
                    "mapId": SUMMONERS_RIFT_MAP_ID,
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

    async def get_match_history(self) -> LCUMatchHistory:
        res = await self.get("/lol-match-history/v1/products/lol/current-summoner/matches")
        return LCUMatchHistory(**res)

    async def get_recent_match_ids(self) -> list[int]:
        history = await self.get_match_history()
        return [g.gameId for g in history.games.games]

    async def get_last_match(self) -> LCUMatch:
        history = await self.get_match_history()
        return history.games.games[0]

    async def get_last_match_id(self) -> int:
        last_match = await self.get_last_match()
        return last_match.gameId

    async def get_match_timeline(self, matchID: int) -> LCUTimeline:
        res = await self.get(f"/lol-match-history/v1/game-timelines/{matchID}")
        return LCUTimeline(**res)

    async def get_raw_match_timeline(self, matchID: int) -> dict:
        res = await self.get(f"/lol-match-history/v1/game-timelines/{matchID}")
        return res

    async def get_player_participant_id(self, matchID: int) -> int:
        game = await self.get_match(matchID)
        return game.participantIdentities[0].participantId

    async def download_replay(self, matchID: int):
        res = await self.post(f"/lol-replays/v1/rofls/{matchID}/download/graceful", json={"gameId": matchID})
        return res

    async def launch_replay(self, matchID: int):
        metadata = await self.get_replay_metadata(matchID)
        if metadata.get("state") == "download":
            await self.download_replay(matchID)
            await asyncio.sleep(5)

        return await self.post(f"/lol-replays/v1/rofls/{matchID}/watch", json={"gameId": matchID})

    async def get_replay_metadata(self, matchID: int):
        return await self.get(f"/lol-replays/v1/metadata/{matchID}")
