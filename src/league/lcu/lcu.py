import json
import httpx

from rich import print
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from league.lcu.models import MyChampSelection, Summoner

RIOT_USERNAME = "riot"

DRAGON_PATH = Path("./data/dragon")
DRAGON_PATH.mkdir(parents=True, exist_ok=True)


class APIClient:
    client: httpx.AsyncClient

    async def _make_request(self, method, *args, **kwargs):
        try:
            res = await self.client.request(method, *args, **kwargs)
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            print(e.response.json())
            raise e

    async def get(self, *args, **kwargs):
        return await self._make_request("GET", *args, **kwargs)

    async def post(self, *args, **kwargs):
        return await self._make_request("POST", *args, **kwargs)


class CommunityDataDragon(APIClient):
    def __init__(self):
        self.latest_version = self.get_latest_version()

        base_url = f"https://cdn.communitydragon.org/{self.latest_version}"
        self.client = httpx.AsyncClient(base_url=base_url)

    def get_latest_version(self):
        url = "https://ddragon.leagueoflegends.com/api/versions.json"
        res = httpx.get(url).json()
        return res[0]

    def check_champion_cache(self, championID: int) -> Optional[dict]:
        path = DRAGON_PATH / "champion" / f"{championID}.json"
        print(path.resolve())
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            return data
        else:
            return None

    def write_to_champion_cache(self, championID: int, data: dict):
        path = DRAGON_PATH / "champion" / f"{championID}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    async def get_champion(self, championID: int):
        data = self.check_champion_cache(championID)
        if data is not None:
            return data

        data = await self.get(f"/champion/{championID}/data")
        self.write_to_champion_cache(championID, data)
        return data


@dataclass(frozen=True, slots=True)
class LCULockfileData:
    ProcessName: str
    ProcessID: int
    Port: int
    Password: str
    Protocol: str


class LCUClient(APIClient):
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

    async def get_selected_champion(self) -> Optional[MyChampSelection]:
        raw_selection = await self.get("/lol-champ-select/v1/session/my-selection")
        selection = MyChampSelection(**raw_selection) if raw_selection is not None else None
        if selection is None:
            return None

        data = await self.dragon.get_champion(selection.championPickIntent)
        print(data.get("name"))
        return selection

    async def create_custom_game_lobby(self):
        lobby_config = {
            "customGameLobby": {
                "configuration": {
                    "gameMode": "PRACTICETOOL",
                    "gameMutator": "",
                    "mutators": {"id": 1},
                    "gameServerRegion": "",
                    "mapId": 11,
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

    async def create_normal_game_lobby(self, queueID: Optional[int] = 430):
        lobby_config = {"queueId": queueID}
        res = await self.post("/lol-lobby/v2/", json=lobby_config)
        return res

    async def get_lobby(self):
        return await self.get("/lol-lobby/v2/lobby")

    async def get_current_summoner(self) -> Summoner:
        res = await self.get("/lol-summoner/v1/current-summoner")
        return Summoner(**res)
