import json
import httpx
import asyncio
import logging

from pathlib import Path
from typing import Optional, Any, override

import league.config as cfg

from league.markup import format_url
from league.cache import DataCache
from league.http import BaseAPIClient, RiotRateLimiter
from league.enums import MatchType, Queue, RankedQueueType, RankedTier, RankedDivision
from league.models import Match, MatchTimeline, PlayerMatch, LeagueEntry, RiotAccount, CurrentGameInfo

log = logging.getLogger(__name__)

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

    def __init__(self, api_key: str, limiter: Optional[RiotRateLimiter] = None):
        headers = {"X-Riot-Token": api_key, "Content-Type": "application/json"}

        self.client = httpx.AsyncClient(http2=True, headers=headers)
        self.limiter = limiter
        self._cache_init = False

    @override
    async def get(self, endpoint, *args, _limiter: Optional[RiotRateLimiter] = None, **kwargs):
        region = get_region_for_url(endpoint)
        url = RIOT_API_BASE_URL.format(region=region) + endpoint
        limiter = _limiter or self.limiter
        if limiter is None:
            return await super().get(url, *args, **kwargs)
        return await self._get_limited(url, limiter, *args, **kwargs)

    async def _get_limited(self, url: str, limiter: RiotRateLimiter, *args, _return_exception: bool = False, no_json: bool = False, **kwargs):
        """get() through the rate limiter: wait for capacity, feed the response headers back, retry 429s."""
        while True:
            await limiter.acquire()
            try:
                # errors are suppressed here because a 429 is normal traffic on this path —
                # the retry below handles it, and the base logger would cry wolf about it
                res = await super().get(url, *args, no_json=True, _return_exception=True, _suppress_exception=True, **kwargs)
            finally:
                limiter.release()

            if isinstance(res, httpx.HTTPStatusError):
                # 429s carry the freshest window data, so update before deciding what to do
                limiter.update(res.response.headers)
                if res.response.status_code == 429:
                    retry_after = float(res.response.headers.get("Retry-After", "1"))
                    log.warning(f"Rate limited, retrying in {retry_after:.0f}s")
                    await asyncio.sleep(retry_after)
                    continue
                log.error(f"[error]HTTP Status Error ({res.response.status_code}) from {format_url(str(res.request.url))}[/]: {res}")
                return res if _return_exception else None
            if isinstance(res, Exception):
                log.error(f"[error]HTTP Request Error ({type(res).__name__})[/]: {res}")
                return res if _return_exception else None
            if res is None:
                return None

            limiter.update(res.headers)
            if no_json:
                return res
            try:
                return res.json()
            except json.decoder.JSONDecodeError:
                return None

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

        limiter = self.limiter or RiotRateLimiter()
        sem = asyncio.Semaphore(20)

        endpoint = "/riot/account/v1/accounts/by-puuid/{puuid}"

        cache = self._account_cache.read()
        if cache is None:
            cache = {}

        async def fetch(puuid: str):
            if data := cache.get(puuid):
                return data
            async with sem:
                return await self.get(endpoint.format(puuid=puuid), _limiter=limiter)

        data = await asyncio.gather(*(fetch(id) for id in puuids))
        accounts = []
        for entry in data:
            if entry is None:
                continue
            cache[entry.get("puuid")] = entry
            accounts.append(RiotAccount(**entry))

        self._account_cache.write(cache)
        return accounts

    async def get_puuid(self, game_name: str, tag_line: str) -> str | None:
        endpoint = f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        res = await self.get(endpoint)
        if res is not None:
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
        _return_exception: bool = False,
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
        return await self.get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids", params=params, _return_exception=_return_exception)

    async def get_match(self, match_id: str) -> Match:
        # surface the transport error instead of feeding None to pydantic — callers
        # need the status code to tell "unavailable" apart from "broken"
        data = await self.get(f"/lol/match/v5/matches/{match_id}", _return_exception=True)
        if isinstance(data, Exception):
            raise data
        if data is None:
            raise ValueError(f"No match data returned for {match_id}")
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
        match_type: MatchType = MatchType.Ranked,
        queue_type: Optional[Queue] = None,
    ) -> list[PlayerMatch] | None:
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

    async def get_ranked_data(self, queue: RankedQueueType, tier: RankedTier, division: RankedDivision, page: int = 1) -> set[LeagueEntry]:
        params = {"page": page}
        data = await self.get(f"/lol/league/v4/entries/{queue.value}/{tier.value.upper()}/{division.value}", params=params)
        if data is not None:
            return [LeagueEntry(**entry) for entry in data]

    async def get_live_match_for_puuid(self, puuid: str) -> CurrentGameInfo | None:
        data = await self.get(f"/lol/spectator/v5/active-games/by-summoner/{puuid}")
        if data is not None:
            return CurrentGameInfo(**data)
