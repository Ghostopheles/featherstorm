import json
import httpx
import shutil

from PIL import Image
from io import BytesIO
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
        lookup = {"by-id": {}, "by-name": {}}

        for name, entry in data.items():
            key = entry["key"]
            lookup["by-id"][key] = name
            lookup["by-name"][name] = key

        path = DRAGON_PATH / "champion" / "lookup.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(lookup, indent=4))

        self.lookup = lookup
        return lookup

    async def fetch_champion_lookup(self):
        lookup = self._check_champion_lookup()
        if lookup is None:
            lookup = await self.get("/data/en_US/champion.json")
            lookup = self._write_champion_lookup(lookup.get("data"))
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

        lookup = await self.fetch_champion_lookup()

        name = lookup["by-id"][championID]
        data = await self.get(f"/data/en_US/champion/{name}.json")
        data = data.get("data").get(name)
        self._write_to_champion_cache(championID, data)
        return data

    async def get_champion_name(self, championID: int) -> str:
        lookup = await self.fetch_champion_lookup()
        return lookup.get("by-id").get(championID)

    async def get_champion_id(self, champion_name: str) -> int:
        lookup = await self.fetch_champion_lookup()
        return int(lookup.get("by-name").get(champion_name))

    async def get_loading_screen_art_by_champion_name(self, champion_name: str, skin: int = 0):
        old_base_url = self.client.base_url.copy_with()
        self.client.base_url = DRAGON_URL
        res = await self.get(f"/cdn/img/champion/loading/{champion_name}_{skin}.jpg", no_json=True)
        self.client.base_url = old_base_url
        return Image.open(BytesIO(res.content))

    async def get_loading_screen_art_by_champion_id(self, championID: int, skin: int = 0):
        name = await self.get_champion_id(championID)
        return await self.get_loading_screen_art_by_champion_name(name, skin)
