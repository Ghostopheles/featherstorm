import httpx
import asyncio

from pathlib import Path
from typing import Optional, Any, override

import league.config as cfg

from league.cache import DataCache
from league.http import BaseAPIClient, RiotRateLimiter
from league.enums import MatchType, Queue, RankedQueueType, RankedTier, RankedDivision
from league.models import Match, MatchTimeline, PlayerMatch, LeagueEntry, RiotAccount

LANGUAGE = "en_US"
RIOT_REGION = "americas"
LOL_REGION = "na1"

RIOT_API_BASE_URL = "https://{region}.api.riotgames.com"


def get_region_for_url(url: str):
    if url.startswith("/riot"):
        return RIOT_REGION
    elif "match/v5" in url:
        return RIOT_REGION
    elif url.startswith("/lol"):
        return LOL_REGION


class RiotAPIClient(BaseAPIClient):
    _cache_init: bool = False
    _account_cache: DataCache | None = None

    def __init__(self, api_key: str):
        headers = {"X-Riot-Token": api_key, "Content-Type": "application/json"}

        self.client = httpx.AsyncClient(http2=True, headers=headers)
        self._cache_init = False

    @override
    async def get(self, endpoint, *args, **kwargs):
        region = get_region_for_url(endpoint)
        url = RIOT_API_BASE_URL.format(region=region) + endpoint
        return await super().get(url, *args, **kwargs)

    async def _init_account_cache(self):
        if self._cache_init:
            return

        cache_dir = Path(cfg.get_str("cache_dir", "meta", "./data"))
        cache_path = cache_dir / "riot"
        cache_path.mkdir(parents=True, exist_ok=True)

        self._account_cache = DataCache(cache_path, default_name="accounts.json")

        self._cache_init = True

    async def get_account(self, puuid: str, force_update: bool = False) -> Optional[RiotAccount]:
        await self._init_account_cache()
        all_data = self._account_cache.read()
        if all_data is None:
            all_data = {}

        data = None
        if puuid in all_data and not force_update:
            data = all_data[puuid]
        else:
            data = await self.get(f"/riot/account/v1/accounts/by-puuid/{puuid}")
            if data:
                all_data[puuid] = data
                self._account_cache.write(all_data)

        return RiotAccount(**data)

    async def get_many_accounts(self, puuids: list[str]) -> list[RiotAccount]:
        await self._init_account_cache()

        limiter = RiotRateLimiter()
        sem = asyncio.Semaphore(20)

        endpoint = "/riot/account/v1/accounts/by-puuid/{puuid}"
        region = get_region_for_url(endpoint)
        base_url = RIOT_API_BASE_URL.format(region=region)

        cache = self._account_cache.read()
        if cache is None:
            cache = {}

        async def fetch(puuid: str):
            if data := cache.get(puuid):
                return data

            async with sem:
                while True:
                    await limiter.acquire()
                    url = base_url + endpoint.format(puuid=puuid)
                    res = await self.client.get(url)
                    limiter.update(res.headers)

                    if res.status_code == 429:
                        retry_after = float(res.headers.get("Retry-After", "1"))
                        await asyncio.sleep(retry_after)
                        continue

                    res.raise_for_status()

                    data = res.json()
                    return data

        data = await asyncio.gather(*(fetch(id) for id in puuids))
        accounts = []
        for entry in data:
            cache[entry.get("puuid")] = entry
            accounts.append(RiotAccount(**entry))

        self._account_cache.write(data)
        return accounts

    async def get_puuid(self, game_name: str, tag_line: str) -> str | None:
        endpoint = f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        res = await self.get(endpoint)
        return res.get("puuid")

    async def get_summoner(self, puuid: str) -> Optional[dict[str, Any]]:
        return await self.get(f"/lol/summoner/v4/summoners/by-puuid/{puuid}")

    async def get_top_champions(self, puuid: str, count: int = 5) -> Optional[dict[str, Any]]:
        mastery_data = await self.get(f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top", params={"count": count})
        if not mastery_data:
            return None

        return mastery_data

    async def get_match_ids(
        self,
        puuid: str,
        *,
        count: int = 20,
        start: int = 0,
        match_type: Optional[MatchType] = None,
        queue_type: Optional[Queue] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> list[str]:
        params = {"count": count, "start": start}
        if match_type is not None:
            params["type"] = match_type
        if queue_type is not None:
            params["queue"] = queue_type.value
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        return await self.get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids", params=params)

    async def get_match(self, match_id: str) -> Match:
        data = await self.get(f"/lol/match/v5/matches/{match_id}")
        return Match.model_validate(data)

    async def get_player_match(self, match_id: str, puuid: str) -> PlayerMatch:
        match = await self.get_match(match_id)
        return PlayerMatch.from_match(match, puuid)

    async def get_match_timeline(self, match_id: str) -> MatchTimeline:
        data = await self.get(f"/lol/match/v5/matches/{match_id}/timeline")
        return MatchTimeline.model_validate(data)

    async def get_recent_matches(
            self,
            puuid: str,
            count: int = 3,
            match_type: MatchType = MatchType.Normal,
            queue_type: Optional[Queue] = None,
        ) -> list[PlayerMatch]:
        match_ids = await self.get_match_ids(puuid, count=count, match_type=match_type, queue_type=queue_type)
        if not match_ids:
            return None

        matches = []
        for match_id in match_ids:
            match = await self.get_match(match_id)
            matches.append(PlayerMatch.from_match(match, puuid))

        return matches

    async def get_recent_replays(self, puuid: str) -> list[str]:
        """Returns the URLs to download the .rofl replay files for (up to) the user's last 5 games"""
        data = await self.get(f"/lol/match/v5/matches/by-puuid/{puuid}/replays")
        return data

    async def get_ranked_data(
        self,
        queue: RankedQueueType,
        tier: RankedTier,
        division: RankedDivision,
        page: int = 1
    ) -> set[LeagueEntry]:
        params = {"page": page}
        data = await self.get(f"/lol/league/v4/entries/{queue.value}/{tier.value.upper()}/{division.value}", params=params)
        if data is not None:
            return [LeagueEntry(**entry) for entry in data]
