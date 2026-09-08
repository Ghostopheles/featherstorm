import csv
import sys
import json
import time
import typer
import asyncio

from enum import StrEnum
from typing import Optional, Annotated
from pathlib import Path
from datetime import datetime, timezone

from league import config
from league.ui import output
from league.ui.progress import RichProgressReporter
from league.ui.renderers import crawl_stats_table
from league.http import RiotRateLimiter
from league.riot_api import RiotAPIClient
from league.crawler import GAME, PLAYED, CrawlConfig, FetchConfig, MatchCrawler, MatchFetcher, CrawlerDatabase
from league.crawler.schema import dataset_schema
from league.enums import QueueChoice, MatchTypeChoice, resolve_queue, resolve_match_type

from league.cli._shared import _riot_client

app = typer.Typer(name="crawler", no_args_is_help=True, add_completion=False, help="Match crawler commands")

SECONDS_PER_DAY = 86400


class DatasetTable(StrEnum):
    Played = PLAYED
    Game = GAME


class DatasetFormat(StrEnum):
    Jsonl = "jsonl"
    Csv = "csv"


def _epoch(value: Optional[str], label: str) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        output.error(f"{label} must be YYYY-MM-DD, got {value!r}")
        raise typer.Exit(1)


def _crawler_client() -> RiotAPIClient:
    """The crawler is the one caller that must never trip the app rate limit."""
    client = _riot_client()
    client.limiter = RiotRateLimiter()
    return client


@app.command(name="crawl", help="Crawl match histories until N distinct match IDs are collected.")
def crawl(
    count: int = typer.Option(100, "--count", "-n", help="How many distinct match IDs to collect."),
    game_name: str = config.get("companion.default_player_name"),
    tag_line: str = config.get("companion.default_player_tagline"),
    queue_type: Annotated[QueueChoice, typer.Option(help="Queue Type", case_sensitive=False)] = QueueChoice.RankedSolo,
    match_type: Annotated[MatchTypeChoice, typer.Option(help="Match Type", case_sensitive=False)] = MatchTypeChoice.Ranked,
    days: Optional[int] = typer.Option(None, help="Only crawl matches from the last N days (default: crawler.default_window_days)."),
    since: Optional[str] = typer.Option(None, help="Only crawl matches on/after this date (YYYY-MM-DD)."),
    until: Optional[str] = typer.Option(None, help="Only crawl matches on/before this date (YYYY-MM-DD)."),
    all_time: bool = typer.Option(False, "--all-time", help="No time filter at all."),
    max_depth: Optional[int] = typer.Option(None, help="Stop expanding past this BFS depth."),
    reset: bool = typer.Option(False, "--reset", help="Wipe the database before crawling."),
):
    if all_time and (days is not None or since or until):
        output.error("--all-time cannot be combined with --days/--since/--until")
        raise typer.Exit(1)
    if days is not None and (since or until):
        output.error("--days cannot be combined with --since/--until")
        raise typer.Exit(1)

    window_days = None if (all_time or since) else (days if days is not None else config.get("crawler.default_window_days"))
    start_time = _epoch(since, "--since")
    end_time = _epoch(until, "--until")

    cfg = CrawlConfig(
        target_matches=count,
        seed_name=game_name,
        seed_tagline=tag_line,
        queue=resolve_queue(queue_type),
        match_type=resolve_match_type(match_type),
        start_time=start_time,
        end_time=end_time,
        window_days=window_days,
        max_depth=max_depth,
        history_page_size=config.get("crawler.history_page_size"),
        summoner_workers=config.get("crawler.summoner_workers"),
        match_workers=config.get("crawler.match_workers"),
        claim_batch=config.get("crawler.claim_batch"),
        frontier_low_water=config.get("crawler.frontier_low_water"),
    ).resolved()

    async def run():
        client = _crawler_client()
        async with CrawlerDatabase() as db:
            if reset:
                await db.reset()
                output.warning("Database reset.")

            output.print(f"Seed: [eminence]{game_name}[/][dim]#[/][eminence]{tag_line}[/]")
            output.print(f"Queue: [rakan]{queue_type.value}[/]   Window: {_describe_window(cfg)}")

            crawler = MatchCrawler(client, db, reporter=RichProgressReporter())
            started = time.monotonic()
            stats = await crawler.crawl(cfg)
            elapsed = time.monotonic() - started

            output.print(crawl_stats_table(stats, title=f"Crawl complete in {elapsed:.1f}s"))
            output.success(f"{stats.total_matches:,} match IDs held across {stats.requests} request(s).")

        await client.close()

    asyncio.run(run())


def _describe_window(cfg: CrawlConfig) -> str:
    if cfg.start_time is None and cfg.end_time is None:
        return "[dim]all time[/]"

    def fmt(ts: Optional[int], fallback: str) -> str:
        return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d") if ts else fallback

    return f"{fmt(cfg.start_time, 'beginning')} -> {fmt(cfg.end_time, 'now')}"


@app.command(name="fetch", help="Download and store the full payload for crawled match IDs.")
def fetch(
    count: Optional[int] = typer.Option(None, "--count", "-n", help="Stop after storing N matches (default: drain the backlog)."),
    max_depth: Optional[int] = typer.Option(None, help="Only fetch matches found at or above this BFS depth."),
    workers: Optional[int] = typer.Option(None, help="Concurrent fetch workers (default: crawler.fetch_workers)."),
):
    cfg = FetchConfig(
        target=count,
        max_depth=max_depth,
        workers=workers if workers is not None else config.get("crawler.fetch_workers"),
        claim_batch=config.get("crawler.fetch_claim_batch"),
    )

    async def run():
        client = _crawler_client()
        async with CrawlerDatabase() as db:
            pending = await db.unfetched_count(max_depth=max_depth)
            if not pending:
                output.warning("Nothing to fetch — every crawled match already has its payload stored.")
                return

            output.print(f"Pending: [rakan]{pending:,}[/]   Workers: [eminence]{cfg.workers}[/]")

            fetcher = MatchFetcher(client, db, reporter=RichProgressReporter())
            started = time.monotonic()
            stats = await fetcher.fetch(cfg)
            elapsed = time.monotonic() - started

            output.print(crawl_stats_table(stats, title=f"Fetch complete in {elapsed:.1f}s"))
            output.success(f"Stored {fetcher.stored:,} match(es), {fetcher.failed:,} failed, {stats.played:,} player-games held.")

        await client.close()

    asyncio.run(run())


@app.command(name="dataset", help="Export stored match data as JSONL or CSV for analysis.")
def dataset(
    table: Annotated[DatasetTable, typer.Option("--table", "-t", help="Which table to export.")] = DatasetTable.Played,
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="File to write to; prints to the terminal when omitted."),
    fmt: Annotated[DatasetFormat, typer.Option("--format", "-f", help="Output format.")] = DatasetFormat.Jsonl,
    queue: Optional[int] = typer.Option(None, help="Only rows from this queue id (e.g. 420)."),
    patch: Optional[str] = typer.Option(None, help="Only rows from this patch (e.g. 16.17)."),
    limit: Optional[int] = typer.Option(None, help="Stop after N rows."),
):
    async def run():
        async with CrawlerDatabase() as db:
            rows = db.iter_dataset(table.value, queue=queue, patch=patch, limit=limit)

            if out is None:
                written = await _write_rows(rows, sys.stdout, fmt)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                with out.open("w", encoding="utf-8", newline="") as handle:
                    written = await _write_rows(rows, handle, fmt)

            if not written:
                output.warning(f"No rows in `{table.value}` matching that filter.")
            elif out is not None:
                output.success(f"Wrote {written:,} {table.value} row(s) to {out}")

    asyncio.run(run())


async def _write_rows(rows, handle, fmt: DatasetFormat) -> int:
    """CSV needs a header before the first row and JSONL doesn't, so the writer is only
    built once the first row has told us what the columns are."""
    writer = None
    written = 0

    async for row in rows:
        if fmt is DatasetFormat.Csv:
            if writer is None:
                writer = csv.DictWriter(handle, fieldnames=list(row), extrasaction="ignore")
                writer.writeheader()
            writer.writerow({key: _flatten(value) for key, value in row.items()})
        else:
            handle.write(json.dumps(row, default=str) + "\n")
        written += 1

    return written


def _flatten(value):
    """`challenges` / `perks` / `teams` are nested objects — a CSV cell can only hold text."""
    return json.dumps(value, default=str) if isinstance(value, (dict, list)) else value


@app.command(name="stats", help="Show the current state of the crawl database.")
def stats():
    async def run():
        async with CrawlerDatabase() as db:
            output.print(crawl_stats_table(await db.counts(), title="Crawl database"))

    asyncio.run(run())


@app.command(name="export", help="Write collected match IDs to a file (or stdout).")
def export(
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="File to write to; prints to the terminal when omitted."),
    limit: Optional[int] = typer.Option(None, help="Only export the first N ids."),
    state: Optional[str] = typer.Option(None, help="Only export ids in this state (e.g. expanded)."),
):
    async def run():
        async with CrawlerDatabase() as db:
            ids = await db.match_ids(limit=limit, state=state)
            if not ids:
                output.warning("No match IDs to export.")
                return

            if out is None:
                for match_id in ids:
                    output.print(match_id)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text("\n".join(ids) + "\n", encoding="utf-8")
                output.success(f"Wrote {len(ids):,} match IDs to {out}")

    asyncio.run(run())


@app.command(name="schema", help="Apply (or re-verify) the crawler schema.")
def schema(
    show: bool = typer.Option(False, "--show", help="Print the generated dataset DDL instead of applying it."),
):
    # the `game` / `played` DDL is generated from ParticipantSummary, so printing it is the
    # only way to see the column list an analysis query can rely on
    if show:
        output.print(dataset_schema().strip())
        return

    async def run():
        async with CrawlerDatabase() as db:
            output.success(f"Schema applied to {db.namespace}/{db.database} at {db.url}")

    asyncio.run(run())


@app.command(name="reset", help="Wipe every crawled summoner and match.")
def reset(force: bool = typer.Option(False, "--force", help="Skip the confirmation prompt.")):
    if not force:
        answer = output.prompt("This deletes all crawled data. Type 'yes' to continue")
        if answer.strip().lower() != "yes":
            output.warning("Aborted.")
            raise typer.Exit(1)

    async def run():
        async with CrawlerDatabase() as db:
            await db.reset()
            output.success("Crawl database reset.")

    asyncio.run(run())
