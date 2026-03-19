import httpx

from rich import print
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from league.http import BaseAPIClient
from league.dragon import CommunityDataDragon
from league.lcu.models import MyChampSelection, Summoner, LobbyGameMode, LobbyType

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
        queueID: Optional[int] = 430
    ):
        match lobby_type:
            case LobbyType.Normal:
                return await self.create_normal_game_lobby(queueID=queueID)
            case LobbyType.Custom:
                return await self.create_custom_game_lobby(game_mode=game_mode)


    async def create_custom_game_lobby(self, game_mode: Optional[LobbyGameMode] = LobbyGameMode.Practice):
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
        res = await self.post("/lol-lobby/v2/lobby", json=lobby_config)
        return res

    async def create_normal_game_lobby(self, queueID: Optional[int] = DEFAULT_QUEUE_ID):
        """Non-functional right now"""
        lobby_config = {
            "queueId": queueID,
            "customGameLobby": {
                "configuration": {
                    "gameMode": LobbyGameMode.Normal,
                    "mapId": SUMMONERS_RIFT_MAP_ID,
                }
            }
        }
        res = await self.post("/lol-lobby/v2/lobby", json=lobby_config)
        return res

    async def get_lobby(self):
        return await self.get("/lol-lobby/v2/lobby")

    async def get_current_summoner(self) -> Summoner:
        res = await self.get("/lol-summoner/v1/current-summoner")
        return Summoner(**res)
