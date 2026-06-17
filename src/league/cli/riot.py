import typer
import asyncio

from rich import box
from rich.table import Table
from rich.align import Align
from typing import Optional, Annotated

from league import config
from league.timeline import render_player_timeline
from league.console import print, console
from league.enums import (
    RankedQueueTypeChoice,
    RankedDivision,
    RankedTier,
    RANKED_QUEUE_TYPE_MAP,
    MatchTypeChoice,
    QueueChoice,
    resolve_queue,
    resolve_queue_name,
    resolve_match_type
)
from league.models import LeagueEntry

from league.cli._shared import _riot_client

app = typer.Typer(name="riot", no_args_is_help=True, help="Riot Web API commands")


@app.command(name="matches", help="Show recent matches for a player.")
def riot_matches(
    game_name: str = config.get("companion.default_player_name"),
    tag_line: str = config.get("companion.default_player_tagline"),
    count: int = 5,
    match_type: Annotated[MatchTypeChoice, typer.Option(help="Match Type", case_sensitive=False)] = None,
    queue_type: Annotated[QueueChoice, typer.Option(help="Queue Type", case_sensitive=False)] = None,
):
    if match_type is not None:
        match_type = resolve_match_type(match_type)

    if queue_type is not None:
        queue_type = resolve_queue(queue_type)

    async def run():
        with console.status("[eminence]Processing matches...[/]", spinner="simpleDotsScrolling", spinner_style="featherstorm"):
            client = _riot_client()
            puuid = await client.get_puuid(game_name, tag_line)
            if not puuid:
                print(f"[bold red]Player {game_name}#{tag_line} not found[/bold red]")
                return
            matches = await client.get_match_ids(puuid, count=count, match_type=match_type, queue_type=queue_type)
            if not matches:
                print("No matches found.")
                return

            match_table = Table(
                title=f"({count} most recent matches for [rakan]{game_name}[/][dim]#[/][rakan]{tag_line}[/])",
                show_header=True,
                border_style="rakan",
                header_style="featherstorm",
                box=box.ROUNDED,
                show_lines=True,
            )
            match_table.add_column("#", width=3)
            match_table.add_column("Champion", width=15, style="eminence")
            match_table.add_column("Result", width=8)
            match_table.add_column("KDA Ratio : K/D/A", width=20)
            match_table.add_column("Duration", width=8, highlight=True)
            match_table.add_column("Game Mode", width=10)
            match_table.add_column("Queue Type", width=14)
            match_table.add_column("Match ID", width=15)

            for i, match_id in enumerate(matches, 1):
                match = await client.get_match(match_id)
                pm = match.info.participants
                player = next((p for p in pm if p.puuid == puuid), None)
                if player:
                    mins = match.info.gameDuration // 60
                    result = "[bold green]WIN[/bold green]" if player.win else "[bold red]LOSS[/bold red]"

                    kda_ratio = (player.kills + player.assists) / max(1, player.deaths)

                    kda_left = f"{kda_ratio:.2f}".rjust(5)

                    row_style = ""
                    if kda_ratio < 1:
                        kda_left = f"[bold red]{kda_left}[/]"
                        row_style = "less_dim"
                    elif kda_ratio > 4:
                        kda_left = f"[bold green]{kda_left}[/]"

                    kda_right = f"{player.kills}/{player.deaths}/{player.assists}"
                    kda_str = f"KDA {kda_left} : {kda_right}"

                    queue_type_name = resolve_queue_name(match.info.queueId)
                    match_table.add_row(
                        f"{i}",
                        player.championName,
                        result,
                        kda_str,
                        f"[green]{mins}[/]m",
                        match.info.gameMode,
                        f"{queue_type_name}",
                        match.metadata.matchId,
                        style=row_style,
                    )
                else:
                    print(f"{i}. {match.metadata.matchId}")

            print(Align.center(match_table))

    asyncio.run(run())


@app.command(name="match", help="Show details for a specific match.")
def riot_match(match_id: str, filter: Optional[str] = None):
    async def run():
        client = _riot_client()
        match = await client.get_match(match_id)

        if filter is not None:
            attrs = filter.split(".")
            value = getattr(match, attrs[0])
            for entry in attrs[1:]:
                value = getattr(value, entry)
            print(value)
        else:
            print(match)

    asyncio.run(run())


@app.command(name="puuid", help="Fetch a summoner's puuid")
def riot_puuid(
    game_name: str = config.get("companion.default_player_name"),
    tag_line: str = config.get("companion.default_player_tagline"),
):
    async def run():
        client = _riot_client()
        puuid = await client.get_puuid(game_name, tag_line)
        print(f"puuid for [featherstorm]{game_name}[/]#[featherstorm]{tag_line}[/]:")
        print(f"[eminence]{puuid}[/]")

    asyncio.run(run())


@app.command(name="timeline", help="Show player event timeline for a specific match.")
def riot_timeline(
    match_id: str,
    game_name: str = config.get("companion.default_player_name"),
    tag_line: str = config.get("companion.default_player_tagline"),
):
    async def run():
        client = _riot_client()
        puuid = await client.get_puuid(game_name, tag_line)
        if not puuid:
            print(f"[bold red]Player {game_name}#{tag_line} not found[/bold red]")
            return
        match, timeline = await asyncio.gather(
            client.get_match(match_id),
            client.get_match_timeline(match_id),
        )
        player = next((p for p in match.info.participants if p.puuid == puuid), None)
        if player is None:
            print(f"[bold red]{game_name}#{tag_line} not in match {match_id}[/bold red]")
            return
        participant_champions = {p.participantId: p.championName for p in match.info.participants}
        console.print(
            render_player_timeline(
                timeline,
                player.participantId,
                participant_champions,
                game_duration_seconds=match.info.gameDuration,
                bar_width=max(60, console.width - 4),
            )
        )

    asyncio.run(run())

@app.command(name="ranked")
def riot_ranked_data(
    queue: Annotated[RankedQueueTypeChoice, typer.Argument(case_sensitive=False, help="Ranked queue type")],
    tier: Annotated[RankedTier, typer.Argument(case_sensitive=False, help="Ranked tier")],
    division: Annotated[RankedDivision, typer.Argument(case_sensitive=False, help="Ranked division within tier")],
):
    client = _riot_client()
    real_queue = RANKED_QUEUE_TYPE_MAP[queue]

    async def run():
        data = await client.get_ranked_data(real_queue, tier, division)
        puuids = [e.puuid for e in data]

        with console.status("Loading players...", spinner="simpleDotsScrolling", spinner_style="featherstorm"):
            accounts = await client.get_many_accounts(puuids)

        accounts = {
            a.puuid: a for a in accounts
        }

        title = f"[green]{queue.value}[/] Ranked Ladder - {tier} {division}"

        table = Table(
            title=title,
            show_header=True,
            border_style="rakan",
            header_style="featherstorm",
            box=box.ROUNDED,
            show_lines=True
        )
        table.add_column("#", width=3)
        table.add_column("Name", width=30)
        table.add_column("Record", width=11, justify="center")
        table.add_column("Winrate", width=7, justify="center")
        table.add_column("LP", width=5)

        for i, entry in enumerate(data, 1):
            name = None
            account = accounts.get(entry.puuid)
            if account and account.gameName:
                name = f"{account.gameName}[dim]#{account.tagLine}[/]"

            if name is None:
                name = "N/A"

            win_loss_str = f"{entry.wins}[green]W[/] : {entry.losses}[red]L[/]"
            total_games = entry.wins + entry.losses
            winrate = int((entry.wins / total_games) * 100)
            if winrate < 50:
                winrate_str = f"[red]{winrate}[/]%"
            else:
                winrate_str = f"[green]{winrate}[/]%"

            table.add_row(
                f"{i}",
                name,
                win_loss_str,
                winrate_str,
                f"{entry.leaguePoints} LP",
            )

        print(table)

    asyncio.run(run())
