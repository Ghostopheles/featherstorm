import json
import httpx
import shutil

from pathlib import Path
from typing import Optional

from league.http import BaseAPIClient
from league.models import DragonItem

DRAGON_PATH = Path("./data/dragon")
DRAGON_PATH.mkdir(parents=True, exist_ok=True)

VERSION_FILE = DRAGON_PATH / "version.txt"


class CommunityDataDragon(BaseAPIClient):
    _champion_map: dict[int, str]  # mapping of champ ID -> name

    def __init__(self):
        official_base_url = "https://ddragon.leagueoflegends.com"
        self.official_client = httpx.AsyncClient(base_url=official_base_url, http2=True)
        self.latest_version: Optional[str] = None
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        self.latest_version = await self.get_latest_version()
        community_base_url = f"https://cdn.communitydragon.org/{self.latest_version}"
        self.client = httpx.AsyncClient(base_url=community_base_url)

    async def get_latest_version(self):
        endpoint = "/api/versions.json"
        res = await self.official_client.get(endpoint)
        res.raise_for_status()
        version = res.json()[0]

        stored = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else None
        if stored != version:
            shutil.rmtree(DRAGON_PATH / "champion", ignore_errors=True)
            shutil.rmtree(DRAGON_PATH / "item", ignore_errors=True)
            VERSION_FILE.write_text(version)

        return version

    def _check_champion_cache(self, championID: int) -> Optional[dict]:
        path = DRAGON_PATH / "champion" / f"{championID}.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            return data
        else:
            return None

    def _write_to_champion_cache(self, championID: int, data: dict):
        path = DRAGON_PATH / "champion" / f"{championID}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    def _check_item_cache(self, itemID: int) -> Optional[dict]:
        path = DRAGON_PATH / "item" / f"{itemID}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _write_to_item_cache(self, itemID: int, data: dict):
        path = DRAGON_PATH / "item" / f"{itemID}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    async def get_item(self, itemID: int) -> Optional[DragonItem]:
        data = self._check_item_cache(itemID)
        if data is None:
            res = await self.client.get(f"/cdn/{self.latest_version}/data/en_US/item.json")
            res.raise_for_status()
            all_items: dict = res.json()["data"]

            for id_str, item in all_items.items():
                self._write_to_item_cache(int(id_str), item)

            data = all_items.get(str(itemID))

        if data is None:
            return None

        return DragonItem(
            builds_from=data.pop("from", []),
            builds_into=data.pop("into", []),
            **data,
        )

    async def get_champion(self, championID: int) -> dict:
        data = self._check_champion_cache(championID)
        if data is not None:
            return data

        data = await self.get(f"/champion/{championID}/data")
        self._write_to_champion_cache(championID, data)
        return data

DRAGON_URL = "https://ddragon.leagueoflegends.com"

class DataDragon(BaseAPIClient):
    lookup: dict | None = None

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=DRAGON_URL,
            http2=True,
        )
        self.latest_version: Optional[str] = None
        self._initialized: bool = False

    async def initialize(self):
        if self._initialized:
            return

        self.latest_version = await self.get_latest_version()
        self.client.base_url = DRAGON_URL + f"/cdn/{self.latest_version}"
        self._initialized = True

    async def get_latest_version(self):
        endpoint = "/api/versions.json"
        res = await self.client.get(endpoint)
        res.raise_for_status()
        version = res.json()[0]

        stored = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else None
        if stored != version:
            shutil.rmtree(DRAGON_PATH / "champion", ignore_errors=True)
            shutil.rmtree(DRAGON_PATH / "item", ignore_errors=True)
            VERSION_FILE.write_text(version)

        return version

    def _check_champion_lookup(self):
        if self.lookup:
            return self.lookup

        path = DRAGON_PATH / "champion" / "lookup.json"
        if path.exists():
            with open(path) as f:
                lookup = json.load(f)

            self.lookup = lookup
            return lookup
        else:
            return None

    def _write_champion_lookup(self, data: dict):
        lookup = {
            "by-id": {},
            "by-name": {}
        }

        for name, entry in data.items():
            key = entry["key"]
            lookup["by-id"][key] = name
            lookup["by-name"][name] = key

        path = DRAGON_PATH / "champion" / "lookup.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(lookup, indent=4))

        self.lookup = lookup
        return lookup

    def _check_champion_cache(self, championID: int) -> Optional[dict]:
        path = DRAGON_PATH / "champion" / f"{championID}.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            return data
        else:
            return None

    def _write_to_champion_cache(self, championID: int, data: dict):
        path = DRAGON_PATH / "champion" / f"{championID}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    def _check_item_cache(self, itemID: int) -> Optional[dict]:
        path = DRAGON_PATH / "item" / f"{itemID}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _write_to_item_cache(self, itemID: int, data: dict):
        path = DRAGON_PATH / "item" / f"{itemID}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    async def get_item(self, itemID: int) -> Optional[DragonItem]:
        data = self._check_item_cache(itemID)
        if data is None:
            res = await self.client.get(f"/cdn/{self.latest_version}/data/en_US/item.json")
            res.raise_for_status()
            all_items: dict = res.json()["data"]

            for id_str, item in all_items.items():
                self._write_to_item_cache(int(id_str), item)

            data = all_items.get(str(itemID))

        if data is None:
            return None

        return DragonItem(
            builds_from=data.pop("from", []),
            builds_into=data.pop("into", []),
            **data,
        )

    async def get_champion(self, championID: int) -> dict:
        championID = str(championID)
        data = self._check_champion_cache(championID)
        if data:
            return data

        lookup = self._check_champion_lookup()
        if not lookup:
            lookup = await self.get("/data/en_US/champion.json")
            lookup = self._write_champion_lookup(lookup.get("data"))

        name = lookup["by-id"][championID]
        data = await self.get(f"/data/en_US/champion/{name}.json")
        data = data.get("data").get(name)
        self._write_to_champion_cache(championID, data)
        return data
