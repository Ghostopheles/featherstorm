import httpx
import asyncio
import logging

from typing import Optional
from dataclasses import dataclass

from pydantic import ValidationError

from league.riot_api import RiotAPIClient
from league.reporting import NullReporter, ProgressReporter
from league.crawler.database import Node, CrawlStats, CrawlerDatabase
from league.crawler.match_crawler import PERMANENT_STATUSES

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchConfig:
    """`target=None` drains the whole pending backlog."""

    target: Optional[int] = None
    workers: int = 8
    claim_batch: int = 8
    max_depth: Optional[int] = None
    max_attempts: int = 3


class MatchFetcher:
    """Second pass over the crawled graph: pull each match's full payload and store it.

    The BFS crawl only ever fetches the handful of matches it needs to keep the summoner
    frontier fed, so the vast majority of discovered match IDs are never downloaded. This
    walks the `fetch_state` frontier instead — one request per match, one `store_match()`
    per response — and is safe to stop and resume, because a killed run leaves rows in
    `claimed` that `release_stale_fetch_claims()` returns to `pending` on the next start.
    """

    def __init__(self, riot: RiotAPIClient, db: CrawlerDatabase, reporter: ProgressReporter = NullReporter()):
        self.riot = riot
        self.db = db
        self.reporter = reporter
        self.requests = 0

        self._stop = asyncio.Event()
        self._stored = 0
        self._failed = 0
        self._idle: set[str] = set()
        self._workers = 0

    async def fetch(self, cfg: FetchConfig) -> CrawlStats:
        released = await self.db.release_stale_fetch_claims()
        if released:
            log.info(f"Released [eminence]{released}[/] stale fetch claim(s) from a previous run")

        pending = await self.db.unfetched_count(max_depth=cfg.max_depth)
        total = pending if cfg.target is None else min(cfg.target, pending)

        self._stop = asyncio.Event()
        self._stored = 0
        self._failed = 0
        self._idle = set()
        self._workers = cfg.workers

        if total:
            with self.reporter.task(f"Fetching {total:,} match payloads", total=total):
                async with asyncio.TaskGroup() as tg:
                    for i in range(cfg.workers):
                        tg.create_task(self._worker(f"f{i}", cfg))

        stats = await self.db.counts()
        stats.requests = self.requests
        return stats

    @property
    def stored(self) -> int:
        return self._stored

    @property
    def failed(self) -> int:
        return self._failed

    async def _worker(self, name: str, cfg: FetchConfig) -> None:
        while not self._stop.is_set():
            nodes = await self.db.claim_unfetched(cfg.claim_batch, max_depth=cfg.max_depth)
            if not nodes:
                self._idle.add(name)
                if len(self._idle) >= self._workers:
                    self._stop.set()
                    return
                await asyncio.sleep(0.2)
                continue

            self._idle.discard(name)
            for node in nodes:
                if self._stop.is_set():
                    # anything claimed but not reached goes back to the frontier rather
                    # than waiting out the stale-claim timeout on the next run
                    await self.db.fail_fetch(node.id, "run stopped", permanent=False)
                    continue
                await self._store(node, cfg)

    async def _store(self, node: Node, cfg: FetchConfig) -> None:
        self.requests += 1
        try:
            match = await self.riot.get_match(node.id)
        except httpx.HTTPStatusError as e:
            await self._handle_failure(node, e, cfg)
            return
        except (httpx.RequestError, ValidationError, ValueError) as e:
            await self._handle_failure(node, e, cfg)
            return

        await self.db.store_match(match, depth=node.depth + 1)

        self._stored += 1
        self._advance(cfg)
        if cfg.target is not None and self._stored >= cfg.target:
            self._stop.set()

    async def _handle_failure(self, node: Node, error: Exception, cfg: FetchConfig) -> None:
        status = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None

        # a payload that pydantic can't parse won't parse on a retry either
        permanent = status in PERMANENT_STATUSES or isinstance(error, ValidationError) or node.attempts + 1 >= cfg.max_attempts

        message = f"HTTP {status}" if status else f"{type(error).__name__}: {error}"
        await self.db.fail_fetch(node.id, message, permanent=permanent)

        self._failed += 1
        self._advance(cfg)
        if status not in PERMANENT_STATUSES:
            log.debug(f"match {node.id} fetch failed: {message}")

    def _advance(self, cfg: FetchConfig) -> None:
        # every worker finishes the item it is holding when the target is hit, so the run
        # always overshoots by up to one batch — the bar shouldn't show that
        if cfg.target is None or self._stored + self._failed <= cfg.target:
            self.reporter.advance(1)
