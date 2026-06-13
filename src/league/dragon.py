import json
import httpx
import shutil

from PIL import Image
from io import BytesIO
from pathlib import Path
from typing import Optional

from league.http import BaseAPIClient
from league.models import DragonItem
from league.config import get_str
from league.cache import DataCache

CACHE_DIR = Path(get_str("cache_dir", "meta", "./data"))
DRAGON_PATH = CACHE_DIR / "dragon"
DRAGON_PATH.mkdir(parents=True, exist_ok=True)

RAW_BASE_URL = "https://ddragon.leagueoflegends.com"
OFFICIAL_BASE_URL = RAW_BASE_URL + "/cdn/{version}"
COMMUNITY_BASE_URL = "https://cdn.communitydragon.org/{version}"

class DataDragon(BaseAPIClient):
    locale: str = "en_US"
    latest_version: str | None = None

    _official_url: str | None = None
    _community_url: str | None = None

    _champion_lookup_cache: DataCache | None = None
    _champion_cache: DataCache | None = None
    _item_cache: DataCache | None = None

    _champion_lookup: dict | None = None

    _initialized: bool = False

    def __init__(self, locale: str | None = None):
        self.client = httpx.AsyncClient(http2=True)

        if locale is not None:
            self.locale = locale

    async def initialize(self):
        if self._initialized:
            return

        self.latest_version = await self.get_latest_version()
        self._init_cache()
        self._official_url = OFFICIAL_BASE_URL.format(version=self.latest_version)
        self._community_url = OFFICIAL_BASE_URL.format(version=self.latest_version)
        self._initialized = True

    async def get(self, endpoint: str, *args, **kwargs):
        full_url = f"{self._official_url}/{endpoint}"
        return await super().get(full_url, *args, **kwargs)

    async def get_full_url(self, url: str, *args, **kwargs):
        return await super().get(url, *args, **kwargs)

    async def get_latest_version(self):
        url = f"{RAW_BASE_URL}/api/versions.json"
        res = await self.get_full_url(url)
        version = res[0]

        return version

    def _init_cache(self):
        version_cache = DRAGON_PATH / self.latest_version
        version_cache.mkdir(exist_ok=True)

        self._champion_lookup_cache = DataCache(version_cache, default_name="champion_lookup.json")
        self._item_cache = DataCache(version_cache / "item", default_name="item.json")
        self._champion_cache = DataCache(version_cache / "champion", default_name="champion.json")

    def _make_champion_lookup(self, data: dict) -> dict:
        lookup = {"by-id": {}, "by-name": {}}

        for name, entry in data.items():
            key = int(entry["key"])
            lookup["by-id"][key] = name
            lookup["by-name"][name] = key

        return lookup

    async def _get_champion_lookup(self) -> dict:
        if self._champion_lookup is None:
            data = self._champion_lookup_cache.read()
            if data is not None:
                self._champion_lookup = data
            else:
                data = await self.get(f"data/{self.locale}/champion.json")
                self._champion_lookup = self._make_champion_lookup(data.get("data"))
                self._champion_lookup_cache.write(self._champion_lookup)

        return self._champion_lookup

    async def get_item(self, itemID: int) -> Optional[DragonItem]:
        data = self._item_cache.read()
        if data is None:
            res = await self.get(f"data/{self.locale}/item.json")
            all_items: dict = res.get("data")

            for id_str, item in all_items.items():
                filename = f"{id_str}.json"
                self._item_cache.write_json(filename, item)

            data = all_items.get(str(itemID))

        if data is None:
            return None

        return DragonItem(
            builds_from=data.pop("from", []),
            builds_into=data.pop("into", []),
            **data,
        )

    async def get_champion(self, championID: int) -> dict:
        filename = f"{championID}.json"
        data = self._champion_cache.read_json(filename)
        if data:
            return data

        lookup = await self._get_champion_lookup()

        name = lookup["by-id"].get(str(championID))
        data = await self.get(f"data/{self.locale}/champion/{name}.json")
        data = data.get("data").get(name)
        self._champion_cache.write_json(filename, data)
        return data

    async def get_champion_name(self, championID: int) -> str:
        lookup = await self._get_champion_lookup()
        return lookup.get("by-id").get(championID)

    async def get_champion_id(self, champion_name: str) -> int:
        lookup = await self._get_champion_lookup()
        return int(lookup.get("by-name").get(champion_name))

    async def get_loading_screen_art_by_champion_name(self, champion_name: str, skin: int = 0):
        full_url = f"{RAW_BASE_URL}/cdn/img/champion/loading/{champion_name}_{skin}.jpg"
        from league.console import format_file_path, print
        print(format_file_path(full_url))
        res = await self.get_full_url(full_url, no_json=True)
        return Image.open(BytesIO(res.content))

    async def get_loading_screen_art_by_champion_id(self, championID: int, skin: int = 0):
        name = await self.get_champion_id(championID)
        return await self.get_loading_screen_art_by_champion_name(name, skin)
