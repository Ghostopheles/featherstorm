# champion_winrates.py
"""Read every stored player-game and print champion winrates + playrates.

Example of consuming the crawler dataset: `played` holds one row per player per match,
so a champion's winrate is just its rows grouped by `champion`, and its playrate is how
many distinct matches those rows cover out of every match scanned.
"""

import asyncio
import argparse

from collections import Counter
from dataclasses import dataclass

import league.config as cfg

from league.crawler import PLAYED, CrawlerDatabase


@dataclass
class Totals:
    games: Counter[str]
    wins: Counter[str]
    matches: int


async def champion_totals(queue: int | None, patch: str | None, limit: int | None) -> Totals:
    games: Counter[str] = Counter()
    wins: Counter[str] = Counter()
    match_ids: set[str] = set()

    async with CrawlerDatabase() as db:
        async for row in db.iter_dataset(PLAYED, queue=queue, patch=patch, limit=limit):
            champion = row.get("champion")
            if not champion:
                continue
            match_ids.add(row["match_id"])
            games[champion] += 1
            wins[champion] += bool(row.get("win"))

    return Totals(games=games, wins=wins, matches=len(match_ids))


def main() -> None:
    parser = argparse.ArgumentParser(description="Champion winrates over the stored match dataset")
    parser.add_argument("--queue", type=int, default=None, help="queue id filter (420 = ranked solo)")
    parser.add_argument("--patch", default=None, help="patch filter, e.g. 16.17")
    parser.add_argument("--limit", type=int, default=None, help="stop after N player-games")
    parser.add_argument("--min-games", type=int, default=1, help="hide champions below this sample size")
    parser.add_argument("--sort", choices=("winrate", "playrate"), default="winrate", help="ordering")
    args = parser.parse_args()

    cfg.init()
    totals = asyncio.run(champion_totals(args.queue, args.patch, args.limit))

    rows = [(champion, totals.wins[champion] / total, total / totals.matches, total) for champion, total in totals.games.items() if total >= args.min_games]
    key = 1 if args.sort == "winrate" else 2
    rows.sort(key=lambda row: (row[key], row[3]), reverse=True)

    for champion, winrate, playrate, total in rows:
        print(f"{champion} winrate: {winrate * 100:.1f}% playrate: {playrate * 100:.1f}% ({total} games)")

    if not rows:
        print("no stored player-games matched")
        return

    print(f"\n{totals.matches} matches")


if __name__ == "__main__":
    main()
