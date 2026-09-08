import time
import httpx
import asyncio
import logging

from typing import Optional
from dataclasses import replace, dataclass

from pydantic import ValidationError

from league.riot_api import RiotAPIClient
from league.enums import Queue, MatchType
from league.reporting import NullReporter, ProgressReporter
from league.crawler.database import MATCH, SUMMONER, Node, CrawlStats, CrawlerDatabase

log = logging.getLogger(__name__)

# MATCH-V5 never serves these: Brawl is 403, custom/Practice Tool is 404. Permanent, not transient.
PERMANENT_STATUSES = frozenset({403, 404})

SECONDS_PER_DAY = 86400


@dataclass(frozen=True)
class CrawlConfig:
    target_matches: int
    seed_name: str
    seed_tagline: str
    match_type: Optional[MatchType] = MatchType.Ranked
    queue: Optional[Queue] = Queue.Q_5V5_RANKED_SOLO_GAMES_2
    history_page_size: int = 100
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    window_days: Optional[int] = 14
    max_depth: Optional[int] = None
    summoner_workers: int = 8
    match_workers: int = 4
    claim_batch: int = 8
    frontier_low_water: int = 32
    max_attempts: int = 3

    def resolved(self) -> "CrawlConfig":
        """Freeze the time window now, so a long or resumed run can't slide it underneath itself."""
        if self.start_time is not None or self.window_days is None:
            return self
        return replace(self, start_time=int(time.time()) - self.window_days * SECONDS_PER_DAY)


class CrawlerExhausted(Exception):
    """The reachable graph inside the window ran out before the target was met."""


class MatchCrawler:
    def __init__(self, riot: RiotAPIClient, db: CrawlerDatabase, reporter: ProgressReporter = NullReporter()):
        self.riot = riot
        self.db = db
        self.reporter = reporter
        self.requests = 0

        self._stop = asyncio.Event()
        self._found = 0
        self._inflight = 0
        self._idle: set[str] = set()
        self._workers = 0
        self._frontier: dict[str, tuple[float, int]] = {}

    async def crawl(self, cfg: CrawlConfig) -> CrawlStats:
        cfg = cfg.resolved()

        released = await self.db.release_stale_claims()
        if released:
            log.info(f"Released [eminence]{released}[/] stale claim(s) from a previous run")

        run_id = await self.db.start_run(
            {
                "target": cfg.target_matches,
                "seed": f"{cfg.seed_name}#{cfg.seed_tagline}",
                "queue": cfg.queue.value if cfg.queue else None,
                "match_type": str(cfg.match_type) if cfg.match_type else None,
                "start_time": cfg.start_time,
                "end_time": cfg.end_time,
                "max_depth": cfg.max_depth,
            }
        )

        await self._seed(cfg)

        self._stop = asyncio.Event()
        self._found = await self.db.total_matches()
        self._inflight = 0
        self._idle = set()
        self._workers = cfg.summoner_workers + cfg.match_workers
        self._frontier = {}

        if self._found >= cfg.target_matches:
            self._stop.set()

        status = "complete"
        with self.reporter.task(f"Crawling to {cfg.target_matches} matches", total=cfg.target_matches) as _:
            self.reporter.advance(min(self._found, cfg.target_matches))
            try:
                async with asyncio.TaskGroup() as tg:
                    for i in range(cfg.summoner_workers):
                        tg.create_task(self._summoner_worker(f"s{i}", cfg))
                    for i in range(cfg.match_workers):
                        tg.create_task(self._match_worker(f"m{i}", cfg))
            except* CrawlerExhausted:
                status = "exhausted"

        stats = await self.db.counts()
        stats.requests = self.requests
        await self.db.finish_run(run_id, status, stats)

        if status == "exhausted":
            log.warning(
                f"Frontier exhausted at [eminence]{self._found}[/] of {cfg.target_matches} matches — widen the window (--days) or loosen --queue/--max-depth"
            )
        return stats

    async def _seed(self, cfg: CrawlConfig) -> None:
        puuid = await self._request(self.riot.get_puuid(cfg.seed_name, cfg.seed_tagline))
        if not puuid:
            raise ValueError(f"Unable to resolve puuid for {cfg.seed_name}#{cfg.seed_tagline}")
        await self.db.add_summoners([puuid], depth=0)

    async def _request(self, coro):
        self.requests += 1
        return await coro

    # --- workers --------------------------------------------------------

    async def _summoner_worker(self, name: str, cfg: CrawlConfig) -> None:
        while not self._stop.is_set():
            nodes = await self.db.claim_summoners(cfg.claim_batch, max_depth=cfg.max_depth)
            if not await self._settle(name, nodes, cfg):
                continue
            for node in nodes:
                if self._stop.is_set():
                    break
                await self._expand_summoner(node, cfg)
            self._inflight -= len(nodes)

    async def _match_worker(self, name: str, cfg: CrawlConfig) -> None:
        while not self._stop.is_set():
            # a match expansion only exists to refill the summoner frontier, so it stays
            # demand-driven — under a tight window this still fires often
            if await self._frontier_size(SUMMONER, cfg) >= cfg.frontier_low_water:
                self._idle.discard(name)
                await asyncio.sleep(0.2)
                continue

            nodes = await self.db.claim_matches(cfg.claim_batch, max_depth=cfg.max_depth)
            if not await self._settle(name, nodes, cfg):
                continue
            for node in nodes:
                if self._stop.is_set():
                    break
                await self._expand_match(node, cfg)
            self._inflight -= len(nodes)

    async def _settle(self, name: str, nodes: list[Node], cfg: CrawlConfig) -> bool:
        """Track idleness and decide whether the graph is genuinely exhausted. True = work to do."""
        if nodes:
            self._idle.discard(name)
            self._inflight += len(nodes)
            return True

        self._idle.add(name)
        if len(self._idle) >= self._workers and self._inflight == 0:
            summoners = await self._frontier_size(SUMMONER, cfg, fresh=True)
            matches = await self._frontier_size(MATCH, cfg, fresh=True)
            if summoners == 0 and matches == 0:
                self._stop.set()
                raise CrawlerExhausted
        await asyncio.sleep(0.2)
        return False

    async def _frontier_size(self, table: str, cfg: CrawlConfig, *, fresh: bool = False) -> int:
        cached = self._frontier.get(table)
        now = time.monotonic()
        if not fresh and cached is not None and now - cached[0] < 1.0:
            return cached[1]

        size = await self.db.frontier_size(table, max_depth=cfg.max_depth)
        self._frontier[table] = (now, size)
        return size

    # --- expansion ------------------------------------------------------

    async def _expand_summoner(self, node: Node, cfg: CrawlConfig) -> None:
        match_ids: list[str] = []
        start = 0
        while True:
            page = await self._request(
                self.riot.get_match_ids(
                    node.id,
                    count=cfg.history_page_size,
                    start=start,
                    match_type=cfg.match_type,
                    queue_type=cfg.queue,
                    start_time=cfg.start_time,
                    end_time=cfg.end_time,
                    _return_exception=True,
                )
            )
            if isinstance(page, Exception):
                await self._handle_failure(SUMMONER, node, page, cfg)
                return
            if not page:
                break

            match_ids.extend(page)
            # a windowed page rarely fills; a short result means the window is done, not that
            # there is more to fetch
            if len(page) < cfg.history_page_size:
                break
            start += len(page)

        new = await self.db.complete_summoner(node.id, match_ids, depth=node.depth + 1)
        self._record(new, cfg)

    async def _expand_match(self, node: Node, cfg: CrawlConfig) -> None:
        try:
            match = await self._request(self.riot.get_match(node.id))
        except httpx.HTTPStatusError as e:
            await self._handle_failure(MATCH, node, e, cfg)
            return
        except (httpx.RequestError, ValidationError, ValueError) as e:
            await self._handle_failure(MATCH, node, e, cfg)
            return

        # the full payload is already in hand, so storing the dataset row costs no extra
        # request — `store_match()` settles the BFS state as well as writing `game`/`played`
        new = await self.db.store_match(match, depth=node.depth + 1)
        self._record(new, cfg)

    def _record(self, new: int, cfg: CrawlConfig) -> None:
        if not new:
            return
        before = self._found
        self._found += new

        # the bar caps at the target even though the last batch usually overshoots it
        delta = min(self._found, cfg.target_matches) - min(before, cfg.target_matches)
        if delta > 0:
            self.reporter.advance(delta)
        if self._found >= cfg.target_matches:
            self._stop.set()

    async def _handle_failure(self, table: str, node: Node, error: Exception, cfg: CrawlConfig) -> None:
        status = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
        permanent = status in PERMANENT_STATUSES or node.attempts + 1 >= cfg.max_attempts

        message = f"HTTP {status}" if status else f"{type(error).__name__}: {error}"
        if table == SUMMONER:
            await self.db.fail_summoner(node.id, message, permanent=permanent)
        else:
            await self.db.fail_match(node.id, message, permanent=permanent)

        # 403/404 on MATCH-V5 are queues Riot simply does not serve — not a request fault
        if status not in PERMANENT_STATUSES:
            log.debug(f"{table} {node.id} failed: {message}")
