import random
import asyncio
import logging

from typing import Any, Iterable, Optional, AsyncIterator
from dataclasses import field, dataclass

from surrealdb import RecordID, AsyncSurreal

import league.config as cfg

log = logging.getLogger(__name__)

SUMMONER = "summoner"
MATCH = "match"

DISCOVERED = "discovered"
CLAIMED = "claimed"
EXPANDED = "expanded"
FAILED = "failed"

STATES = (DISCOVERED, CLAIMED, EXPANDED, FAILED)

MAX_CONFLICT_RETRIES = 8
CONFLICT_BACKOFF = 0.05


class TransactionConflict(Exception):
    """RocksDB rejected an optimistic transaction — safe to retry verbatim."""


SCHEMA = """
DEFINE TABLE IF NOT EXISTS summoner SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS state         ON summoner TYPE string DEFAULT 'discovered'
      ASSERT $value IN ['discovered', 'claimed', 'expanded', 'failed'];
DEFINE FIELD IF NOT EXISTS depth         ON summoner TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS discovered_at ON summoner TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS claimed_at    ON summoner TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS expanded_at   ON summoner TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS seen_count    ON summoner TYPE int DEFAULT 1;
DEFINE FIELD IF NOT EXISTS attempts      ON summoner TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS match_count   ON summoner TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS error         ON summoner TYPE option<string>;
DEFINE FIELD IF NOT EXISTS game_name     ON summoner TYPE option<string>;
DEFINE FIELD IF NOT EXISTS tag_line      ON summoner TYPE option<string>;
DEFINE INDEX IF NOT EXISTS summoner_frontier ON summoner FIELDS state, depth;

DEFINE TABLE IF NOT EXISTS match SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS state         ON match TYPE string DEFAULT 'discovered'
      ASSERT $value IN ['discovered', 'claimed', 'expanded', 'failed'];
DEFINE FIELD IF NOT EXISTS depth         ON match TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS discovered_at ON match TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS claimed_at    ON match TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS expanded_at   ON match TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS seen_count    ON match TYPE int DEFAULT 1;
DEFINE FIELD IF NOT EXISTS attempts      ON match TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS platform      ON match TYPE option<string>;
DEFINE FIELD IF NOT EXISTS queue         ON match TYPE option<int>;
DEFINE FIELD IF NOT EXISTS participants  ON match TYPE option<array<record<summoner>>>;
DEFINE FIELD IF NOT EXISTS error         ON match TYPE option<string>;
DEFINE INDEX IF NOT EXISTS match_frontier     ON match FIELDS state, depth;
DEFINE INDEX IF NOT EXISTS match_participants ON match FIELDS participants;

DEFINE TABLE IF NOT EXISTS crawl_run SCHEMALESS;
"""


@dataclass(frozen=True)
class Node:
    """A claimed frontier entry — the record's key plus the BFS depth it was found at."""

    id: str
    depth: int
    attempts: int = 0


@dataclass
class CrawlStats:
    summoners: dict[str, int] = field(default_factory=dict)
    matches: dict[str, int] = field(default_factory=dict)
    requests: int = 0

    @property
    def total_summoners(self) -> int:
        return sum(self.summoners.values())

    @property
    def total_matches(self) -> int:
        return sum(self.matches.values())

    @property
    def matches_per_request(self) -> float:
        return self.total_matches / self.requests if self.requests else 0.0


def platform_of(match_id: str) -> Optional[str]:
    prefix, _, rest = match_id.partition("_")
    return prefix if rest else None


class CrawlerDatabase:
    def __init__(
        self,
        url: Optional[str] = None,
        *,
        namespace: Optional[str] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        crawler = cfg.section("crawler")
        self.url: str = url or crawler.get("db_url", "http://localhost:16800")
        self.namespace: str = namespace or crawler.get("namespace", "featherstorm")
        self.database: str = database or crawler.get("database", "crawler")
        self.username: str = username or crawler.get("username", "root")
        self.password: str = password or crawler.get("password", "root")
        self.db: Any = None

    async def connect(self) -> None:
        self.db = AsyncSurreal(self.url)
        await self.db.signin({"username": self.username, "password": self.password})
        await self.db.use(self.namespace, self.database)
        await self.apply_schema()

    async def close(self) -> None:
        if self.db is None:
            return
        try:
            await self.db.close()
        except NotImplementedError:
            pass  # the HTTP connection is stateless and has nothing to close
        self.db = None

    async def __aenter__(self) -> "CrawlerDatabase":
        await self.connect()
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    async def apply_schema(self) -> None:
        await self._run(SCHEMA)

    # --- query plumbing -------------------------------------------------

    async def _run(self, query: str, params: Optional[dict[str, Any]] = None) -> list[Any]:
        """Run a multi-statement query, raising on any failed statement, returning every result."""
        for attempt in range(MAX_CONFLICT_RETRIES):
            try:
                return await self._run_once(query, params)
            except TransactionConflict:
                # claims are read-then-update, so concurrent workers collide on RocksDB's
                # optimistic transactions constantly — backoff and retry is the fix, not a lock
                if attempt == MAX_CONFLICT_RETRIES - 1:
                    raise
                await asyncio.sleep(CONFLICT_BACKOFF * (2**attempt) * (0.5 + random.random()))
        return []

    async def _run_once(self, query: str, params: Optional[dict[str, Any]] = None) -> list[Any]:
        response = await self.db.query_raw(query, params or {})

        # a parse/validation failure comes back as a top-level error with no per-statement
        # results at all — without this it silently reads as "zero statements ran"
        if error := response.get("error"):
            self._raise(error.get("message", error))

        results = response.get("result") or []

        out = []
        for statement in results:
            if statement.get("status") == "ERR":
                self._raise(statement.get("result"))
            out.append(statement.get("result"))
        return out

    @staticmethod
    def _raise(message: Any) -> None:
        text = str(message)
        if "Transaction conflict" in text or "Resource busy" in text:
            raise TransactionConflict(text)
        raise RuntimeError(f"SurrealDB query failed: {text}")

    async def _run_last(self, query: str, params: Optional[dict[str, Any]] = None) -> Any:
        results = await self._run(query, params)
        return results[-1] if results else None

    @staticmethod
    def _ids(table: str, keys: Iterable[str]) -> list[RecordID]:
        return [RecordID(table, key) for key in keys]

    @staticmethod
    def _nodes(rows: Any) -> list[Node]:
        return [Node(id=str(row["id"].id), depth=row.get("depth", 0), attempts=row.get("attempts", 0)) for row in rows or []]

    # --- discovery ------------------------------------------------------

    async def add_summoners(self, puuids: Iterable[str], *, depth: int = 0) -> int:
        return await self._add(SUMMONER, puuids, depth)

    async def add_matches(self, match_ids: Iterable[str], *, depth: int = 0) -> int:
        return await self._add(MATCH, match_ids, depth)

    async def _add(self, table: str, keys: Iterable[str], depth: int) -> int:
        ids = self._ids(table, dict.fromkeys(keys))
        if not ids:
            return 0

        rows = [{"id": rid, "depth": depth} for rid in ids]
        if table == MATCH:
            for row, rid in zip(rows, ids):
                row["platform"] = platform_of(str(rid.id))

        # ON DUPLICATE KEY UPDATE is the whole dedupe story: an already-expanded
        # record keeps its state, so re-seeing a node costs one bumped counter.
        return await self._run_last(
            f"""
            LET $existing = (SELECT VALUE id FROM {table} WHERE id IN $ids);
            INSERT INTO {table} $rows ON DUPLICATE KEY UPDATE seen_count += 1;
            RETURN array::len($ids) - array::len($existing);
            """,
            {"ids": ids, "rows": rows},
        )

    # --- frontier -------------------------------------------------------

    async def claim_summoners(self, limit: int, *, max_depth: Optional[int] = None) -> list[Node]:
        return await self._claim(SUMMONER, limit, max_depth)

    async def claim_matches(self, limit: int, *, max_depth: Optional[int] = None) -> list[Node]:
        return await self._claim(MATCH, limit, max_depth)

    async def _claim(self, table: str, limit: int, max_depth: Optional[int]) -> list[Node]:
        depth_filter = "AND depth <= $max_depth" if max_depth is not None else ""
        rows = await self._run_last(
            f"""
            LET $batch = (SELECT id, depth, attempts, discovered_at FROM {table}
                          WHERE state = 'discovered' {depth_filter}
                          ORDER BY depth ASC, discovered_at ASC
                          LIMIT $limit);
            UPDATE $batch.id SET state = 'claimed', claimed_at = time::now();
            RETURN $batch;
            """,
            {"limit": limit, "max_depth": max_depth},
        )
        return self._nodes(rows)

    async def release_stale_claims(self, older_than: str = "5m") -> int:
        released = await self._run_last(
            f"""
            LET $stale = (SELECT VALUE id FROM summoner WHERE state = 'claimed' AND claimed_at < time::now() - {older_than});
            LET $stale_m = (SELECT VALUE id FROM match WHERE state = 'claimed' AND claimed_at < time::now() - {older_than});
            UPDATE $stale SET state = 'discovered', claimed_at = NONE;
            UPDATE $stale_m SET state = 'discovered', claimed_at = NONE;
            RETURN array::len($stale) + array::len($stale_m);
            """
        )
        return released or 0

    # --- completion -----------------------------------------------------

    async def complete_summoner(self, puuid: str, match_ids: list[str], *, depth: int) -> int:
        """Mark the summoner expanded and insert everything it discovered, in one round trip."""
        sid = RecordID(SUMMONER, puuid)
        ids = self._ids(MATCH, dict.fromkeys(match_ids))
        rows = [{"id": rid, "depth": depth, "platform": platform_of(str(rid.id))} for rid in ids]

        insert = f"INSERT INTO {MATCH} $rows ON DUPLICATE KEY UPDATE seen_count += 1;" if rows else ""
        return await self._run_last(
            f"""
            LET $existing = (SELECT VALUE id FROM {MATCH} WHERE id IN $ids);
            {insert}
            UPDATE $sid SET state = 'expanded', expanded_at = time::now(), match_count = array::len($ids), error = NONE;
            RETURN array::len($ids) - array::len($existing);
            """,
            {"sid": sid, "ids": ids, "rows": rows},
        )

    async def complete_match(self, match_id: str, puuids: list[str], *, depth: int, queue: Optional[int] = None) -> int:
        mid = RecordID(MATCH, match_id)
        ids = self._ids(SUMMONER, dict.fromkeys(puuids))
        rows = [{"id": rid, "depth": depth} for rid in ids]

        insert = f"INSERT INTO {SUMMONER} $rows ON DUPLICATE KEY UPDATE seen_count += 1;" if rows else ""
        return await self._run_last(
            f"""
            LET $existing = (SELECT VALUE id FROM {SUMMONER} WHERE id IN $ids);
            {insert}
            UPDATE $mid SET state = 'expanded', expanded_at = time::now(),
                            participants = $ids, queue = $queue, error = NONE;
            RETURN array::len($ids) - array::len($existing);
            """,
            {"mid": mid, "ids": ids, "rows": rows, "queue": queue},
        )

    async def fail_summoner(self, puuid: str, error: str, *, permanent: bool = True) -> None:
        await self._fail(SUMMONER, puuid, error, permanent)

    async def fail_match(self, match_id: str, error: str, *, permanent: bool = True) -> None:
        await self._fail(MATCH, match_id, error, permanent)

    async def _fail(self, table: str, key: str, error: str, permanent: bool) -> None:
        state = FAILED if permanent else DISCOVERED
        await self._run(
            "UPDATE $id SET state = $state, error = $error, attempts += 1, claimed_at = NONE;",
            {"id": RecordID(table, key), "state": state, "error": error},
        )

    # --- reading --------------------------------------------------------

    async def counts(self) -> CrawlStats:
        summoners, matches = await self._run(
            """
            SELECT state, count() AS total FROM summoner GROUP BY state;
            SELECT state, count() AS total FROM match GROUP BY state;
            """
        )
        return CrawlStats(
            summoners={row["state"]: row["total"] for row in summoners or []},
            matches={row["state"]: row["total"] for row in matches or []},
        )

    async def total_matches(self) -> int:
        rows = await self._run_last("SELECT count() AS total FROM match GROUP ALL;")
        return rows[0]["total"] if rows else 0

    async def frontier_size(self, table: str, *, max_depth: Optional[int] = None) -> int:
        depth_filter = "AND depth <= $max_depth" if max_depth is not None else ""
        rows = await self._run_last(
            f"SELECT count() AS total FROM {table} WHERE state = 'discovered' {depth_filter} GROUP ALL;",
            {"max_depth": max_depth},
        )
        return rows[0]["total"] if rows else 0

    async def match_ids(self, *, limit: Optional[int] = None, start: int = 0, state: Optional[str] = None) -> list[str]:
        where = "WHERE state = $state" if state else ""
        page = f"LIMIT {int(limit)} START {int(start)}" if limit is not None else ""
        rows = await self._run_last(
            f"SELECT VALUE id FROM {MATCH} {where} ORDER BY id ASC {page};",
            {"state": state},
        )
        return [str(row.id) for row in rows or []]

    async def iter_match_ids(self, batch: int = 1000, *, state: Optional[str] = None) -> AsyncIterator[str]:
        start = 0
        while True:
            page = await self.match_ids(limit=batch, start=start, state=state)
            if not page:
                return
            for match_id in page:
                yield match_id
            start += len(page)

    # --- runs / maintenance ---------------------------------------------

    async def start_run(self, data: dict[str, Any]) -> Any:
        row = await self._run_last("CREATE crawl_run CONTENT $data;", {"data": {**data, "status": "running"}})
        record = row[0] if isinstance(row, list) else row
        return record["id"]

    async def finish_run(self, run_id: Any, status: str, stats: CrawlStats) -> None:
        await self._run(
            """
            UPDATE $id SET status = $status, finished_at = time::now(),
                           summoners = $summoners, matches = $matches, requests = $requests;
            """,
            {
                "id": run_id,
                "status": status,
                "summoners": stats.summoners,
                "matches": stats.matches,
                "requests": stats.requests,
            },
        )

    async def reset(self) -> None:
        await self._run("REMOVE TABLE IF EXISTS summoner; REMOVE TABLE IF EXISTS match; REMOVE TABLE IF EXISTS crawl_run;")
        await self.apply_schema()
