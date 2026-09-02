import typer
import asyncio

from typing import Optional, Annotated

from league import config
from league.ui import output, MatchRow
from league.ui.renderers import match_table, ranked_ladder_table, format_ladder_name, player_timeline_panel
from league.enums import (
    RankedQueueTypeChoice,
    RankedDivision,
    RankedTier,
    RANKED_QUEUE_TYPE_MAP,
    MatchTypeChoice,
    QueueChoice,
    resolve_queue,
    resolve_queue_name,
    resolve_match_type,
)

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
        with output.status("[eminence]Processing matches...[/]"):
            client = _riot_client()
            puuid = await client.get_puuid(game_name, tag_line)
            if not puuid:
                output.error(f"Player {game_name}#{tag_line} not found")
                return
            match_ids = await client.get_match_ids(puuid, count=count, match_type=match_type, queue_type=queue_type)
            if not match_ids:
                output.print("No matches found.")
                return

            rows = []
            for i, match_id in enumerate(match_ids, 1):
                match = await client.get_match(match_id)
                player = next((p for p in match.info.participants if p.puuid == puuid), None)
                if player is None:
                    output.warning(f"{match.metadata.matchId} has no participant for {game_name}#{tag_line}")
                    continue

                rows.append(
                    MatchRow(
                        index=i,
                        champion=player.championName,
                        win=player.win,
                        kills=player.kills,
                        deaths=player.deaths,
                        assists=player.assists,
                        duration_s=match.info.gameDuration,
                        queue_name=resolve_queue_name(match.info.queueId),
                        match_id=match.metadata.matchId,
                        game_mode=match.info.gameMode,
                    )
                )

            title = f"({count} most recent matches for [rakan]{game_name}[/][dim]#[/][rakan]{tag_line}[/])"
            output.print(match_table(rows, title=title))

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
            output.print(value)
        else:
            output.print(match)

    asyncio.run(run())


@app.command(name="puuid", help="Fetch a summoner's puuid")
def riot_puuid(
    game_name: str = config.get("companion.default_player_name"),
    tag_line: str = config.get("companion.default_player_tagline"),
):
    async def run():
        client = _riot_client()
        puuid = await client.get_puuid(game_name, tag_line)
        output.print(f"puuid for [featherstorm]{game_name}[/]#[featherstorm]{tag_line}[/]:")
        output.print(f"[eminence]{puuid}[/]")

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
            output.error(f"Player {game_name}#{tag_line} not found")
            return
        match, timeline = await asyncio.gather(
            client.get_match(match_id),
            client.get_match_timeline(match_id),
        )
        player = next((p for p in match.info.participants if p.puuid == puuid), None)
        if player is None:
            output.error(f"{game_name}#{tag_line} not in match {match_id}")
            return
        participant_champions = {p.participantId: p.championName for p in match.info.participants}
        output.print(
            player_timeline_panel(
                timeline,
                player.participantId,
                participant_champions,
                game_duration_seconds=match.info.gameDuration,
                bar_width=max(60, output.console.width - 4),
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
        entries = await client.get_ranked_data(real_queue, tier, division)

        with output.status("Loading players..."):
            accounts = await client.get_many_accounts([e.puuid for e in entries])

        names = {a.puuid: format_ladder_name(a.gameName, a.tagLine) for a in accounts}

        title = f"[green]{queue.value}[/] Ranked Ladder - {tier} {division}"
        output.print(ranked_ladder_table(entries, names, title=title))

    asyncio.run(run())


@app.command(name="live-game", help="Fetch the currently ongoing match for a player")
def riot_live_match(
    game_name: str = config.get("companion.default_player_name"),
    tag_line: str = config.get("companion.default_player_tagline"),
):
    client = _riot_client()

    async def run():
        puuid = await client.get_puuid(game_name, tag_line)
        if puuid is None:
            output.error(f"Unable to fetch [white]puuid[/white] for [eminence]{game_name}#{tag_line}[/]")
            return

        game = await client.get_live_match_for_puuid(puuid)
        if game is None:
            output.print(f"[eminence]{game_name}#{tag_line}[/] does not have a currently active match.")
            return

        output.print(game)

    asyncio.run(run())
