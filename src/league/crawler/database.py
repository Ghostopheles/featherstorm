import random
import asyncio
import logging

from typing import Any, Iterable, Optional, AsyncIterator
from datetime import datetime
from dataclasses import field, dataclass

from surrealdb import RecordID, AsyncSurreal

import league.config as cfg

from league.models import Match
from league.crawler.schema import (
    GAME,
    PLAYED,
    PENDING,
    game_row,
    played_row,
    summoner_row,
    dataset_schema,
    played_upsert_clause,
)

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
    fetch: dict[str, int] = field(default_factory=dict)
    games: int = 0
    played: int = 0
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
        await self._run(dataset_schema())

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
        # This has to stay a single statement. Multi-statement queries are not run in one
        # transaction, so a `LET $batch = (SELECT ...)` followed by an `UPDATE $batch.id`
        # lets two workers select the same rows before either marks them claimed — measured
        # at ~12% duplicate claims across 8 workers, i.e. that many wasted Riot requests.
        # `UPDATE (subquery) ... RETURN` is atomic and hands back the rows it just claimed.
        depth_filter = "AND depth <= $max_depth" if max_depth is not None else ""
        rows = await self._run_last(
            f"""
            UPDATE (SELECT VALUE id FROM {table}
                    WHERE state = 'discovered' {depth_filter}
                    ORDER BY depth ASC, discovered_at ASC
                    LIMIT $limit)
                SET state = 'claimed', claimed_at = time::now()
                RETURN id, depth, attempts;
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

    async def store_match(self, match: Match, *, depth: int) -> int:
        """Persist a full match payload and settle both of the match node's state axes.

        A stored match has, by definition, already told us its ten participants, so this
        does everything `complete_match()` does *and* writes the dataset — one round trip,
        one API response, no second expansion pass.
        """
        match_id = match.metadata.matchId
        participants = match.info.participants

        gid = RecordID(GAME, match_id)
        sids = self._ids(SUMMONER, dict.fromkeys(p.puuid for p in participants))

        summoners = [{"id": RecordID(SUMMONER, p.puuid), **summoner_row(p, depth=depth)} for p in participants]
        edges = [
            {
                "id": RecordID(PLAYED, f"{match_id}_{p.participantId}"),
                "in": RecordID(SUMMONER, p.puuid),
                "out": gid,
                **played_row(match, p),
            }
            for p in participants
        ]

        return await self._run_last(
            f"""
            LET $existing = (SELECT VALUE id FROM {SUMMONER} WHERE id IN $sids);
            INSERT INTO {SUMMONER} $summoners ON DUPLICATE KEY UPDATE
                seen_count += 1,
                game_name      = $input.game_name ?? game_name,
                tag_line       = $input.tag_line ?? tag_line,
                summoner_level = $input.summoner_level ?? summoner_level,
                profile_icon   = $input.profile_icon ?? profile_icon;
            UPSERT $gid CONTENT $game;
            INSERT RELATION INTO {PLAYED} $edges ON DUPLICATE KEY UPDATE {played_upsert_clause()};
            UPSERT $mid SET state = 'expanded', expanded_at = time::now(), error = NONE,
                            participants = $sids, queue = $queue, platform = $platform,
                            fetch_state = 'stored', fetched_at = time::now(),
                            fetch_claimed_at = NONE, fetch_error = NONE;
            RETURN array::len($sids) - array::len($existing);
            """,
            {
                "sids": sids,
                "summoners": summoners,
                "gid": gid,
                "game": game_row(match),
                "edges": edges,
                "mid": RecordID(MATCH, match_id),
                "queue": int(match.info.queueId),
                "platform": match.info.platformId,
            },
        )

    # --- fetch frontier -------------------------------------------------

    async def claim_unfetched(self, limit: int, *, max_depth: Optional[int] = None) -> list[Node]:
        """Claim matches whose detail payload hasn't been stored yet.

        This is a second, independent frontier over the same `match` rows: BFS expansion
        only ever touches the fraction of matches needed to keep the summoner frontier
        fed, so most discovered matches are never fetched by the crawl itself.
        """
        depth_filter = "AND depth <= $max_depth" if max_depth is not None else ""
        rows = await self._run_last(
            f"""
            UPDATE (SELECT VALUE id FROM {MATCH}
                    WHERE fetch_state = '{PENDING}' {depth_filter}
                    ORDER BY depth ASC, discovered_at ASC
                    LIMIT $limit)
                SET fetch_state = 'claimed', fetch_claimed_at = time::now()
                RETURN id, depth, fetch_attempts AS attempts;
            """,
            {"limit": limit, "max_depth": max_depth},
        )
        return self._nodes(rows)

    async def release_stale_fetch_claims(self, older_than: str = "5m") -> int:
        released = await self._run_last(
            f"""
            LET $stale = (SELECT VALUE id FROM {MATCH}
                          WHERE fetch_state = 'claimed' AND fetch_claimed_at < time::now() - {older_than});
            UPDATE $stale SET fetch_state = '{PENDING}', fetch_claimed_at = NONE;
            RETURN array::len($stale);
            """
        )
        return released or 0

    async def fail_fetch(self, match_id: str, error: str, *, permanent: bool = True) -> None:
        await self._run(
            "UPDATE $id SET fetch_state = $state, fetch_error = $error, fetch_attempts += 1, fetch_claimed_at = NONE;",
            {"id": RecordID(MATCH, match_id), "state": "failed" if permanent else PENDING, "error": error},
        )

    async def unfetched_count(self, *, max_depth: Optional[int] = None) -> int:
        depth_filter = "AND depth <= $max_depth" if max_depth is not None else ""
        rows = await self._run_last(
            f"SELECT count() AS total FROM {MATCH} WHERE fetch_state = '{PENDING}' {depth_filter} GROUP ALL;",
            {"max_depth": max_depth},
        )
        return rows[0]["total"] if rows else 0

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
        summoners, matches, fetch, games, played = await self._run(
            f"""
            SELECT state, count() AS total FROM summoner GROUP BY state;
            SELECT state, count() AS total FROM match GROUP BY state;
            SELECT fetch_state AS state, count() AS total FROM match GROUP BY state;
            SELECT count() AS total FROM {GAME} GROUP ALL;
            SELECT count() AS total FROM {PLAYED} GROUP ALL;
            """
        )
        return CrawlStats(
            summoners={row["state"]: row["total"] for row in summoners or []},
            matches={row["state"]: row["total"] for row in matches or []},
            fetch={row["state"]: row["total"] for row in fetch or []},
            games=games[0]["total"] if games else 0,
            played=played[0]["total"] if played else 0,
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

    # --- dataset reads --------------------------------------------------

    async def iter_dataset(
        self,
        table: str = PLAYED,
        *,
        batch: int = 1000,
        queue: Optional[int] = None,
        patch: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Page through `played` or `game` rows, record links flattened to plain strings.

        Kept as a generator so an export of a few million player-games never has to be
        held in memory, here or in whatever reads the file.
        """
        filters = []
        if queue is not None:
            filters.append("queue = $queue")
        if patch is not None:
            filters.append("patch = $patch")
        where = f"WHERE {' AND '.join(filters)}" if filters else ""

        start, yielded = 0, 0
        while True:
            size = batch if limit is None else min(batch, limit - yielded)
            if size <= 0:
                return

            rows = await self._run_last(
                f"SELECT * FROM {table} {where} ORDER BY id ASC LIMIT {int(size)} START {int(start)};",
                {"queue": queue, "patch": patch},
            )
            if not rows:
                return

            for row in rows:
                yield {key: self._plain(value) for key, value in row.items()}
            yielded += len(rows)
            start += len(rows)

    @staticmethod
    def _plain(value: Any) -> Any:
        """RecordIDs export as their key alone — `summoner:<puuid>` is noise in a CSV."""
        if isinstance(value, RecordID):
            return str(value.id)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [CrawlerDatabase._plain(item) for item in value]
        return value

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
        await self._run(
            f"""
            REMOVE TABLE IF EXISTS {PLAYED};
            REMOVE TABLE IF EXISTS {GAME};
            REMOVE TABLE IF EXISTS summoner;
            REMOVE TABLE IF EXISTS match;
            REMOVE TABLE IF EXISTS crawl_run;
            """
        )
        await self.apply_schema()
