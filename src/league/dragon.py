import json
import httpx

from pathlib import Path
from typing import Optional

from league.http import BaseAPIClient

DRAGON_PATH = Path("./data/dragon")
DRAGON_PATH.mkdir(parents=True, exist_ok=True)

class CommunityDataDragon(BaseAPIClient):
    _champion_map: dict[int, str] # mapping of champ ID -> name

    def __init__(self):
        self.latest_version = self.get_latest_version()

        community_base_url = f"https://cdn.communitydragon.org/{self.latest_version}"
        self.client = httpx.AsyncClient(base_url=community_base_url)

        official_base_url = "https://ddragon.leagueoflegends.com"
        self.official_client = httpx.AsyncClient(base_url=official_base_url, http2=True)

    async def get_latest_version(self):
        endpoint = "/api/versions.json"
        res = await self.official_client.get(endpoint)
        res.raise_for_status()
        data = res.json()
        return data[0]

    def check_champion_cache(self, championID: int) -> Optional[dict]:
        path = DRAGON_PATH / "champion" / f"{championID}.json"
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

    async def get_champion(self, championID: int) -> dict:
        data = self.check_champion_cache(championID)
        if data is not None:
            return data

        data = await self.get(f"/champion/{championID}/data")
        self.write_to_champion_cache(championID, data)
        return data
