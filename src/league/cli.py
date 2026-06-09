import os
import re
import typer
import asyncio

from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from rich import box
from rich.table import Table
from rich.align import Align

from league import config
from league.lcu import LCUClient
from league.lcu.models import LCUMap, LCULane, LCURole, LCUPosition
from league.enums import QueueType, MapQueueType, MapQueueTypeName
from league.constants import APP_NAME
from league.riot_api import RiotAPIClient
from league.companion import run_companion
from league.dragon import CommunityDataDragon
from league.highlights import HighlightManager
from league.timeline import render_player_timeline
from league.console import print, console, format_file_path

config.init()

def try_get_cfg_or_input(category: str, key: str, prompt: str, *args, **kwargs):
    value = config.get(key, category)
    if value is not None:
        return value, False

    prompt = f"[featherstorm]{prompt}[/]: "
    value = console.input(prompt, *args, **kwargs)
    return value, True

def split_camel(s):
    return re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', s)

app = typer.Typer(name=APP_NAME, no_args_is_help=True, add_completion=False)


@app.callback()
def app_main():
    console.rule(f"[featherstorm]{APP_NAME.title()}[/]", style="dark_xayah")


@app.command(name="companion", help=f"Runs Featherstorm in 'companion' mode alongside your current match.")
def default():
    asyncio.run(run_companion())

default_client_path = Path(config.get("lcu.client_install_path"))

lcu_app = typer.Typer(name="lcu", no_args_is_help=True, help="League Client API commands")
app.add_typer(lcu_app)

@lcu_app.command(name="summoner", help="Fetch current summoner info")
def lcu_summoner(client_install_path: Optional[Path] = default_client_path):
    client = LCUClient(client_install_path=client_install_path)
    summoner = asyncio.run(client.get_current_summoner())
    print(summoner)


@lcu_app.command(name="matches", help="Fetch LCU match history")
def lcu_matches(
    client_install_path: Optional[Path] = default_client_path,
    count: int = 5,
    map_queue_type: Optional[MapQueueTypeName] = None
):
    client = LCUClient(client_install_path=client_install_path)
    dragon = CommunityDataDragon()

    if map_queue_type is not None:
        if isinstance(map_queue_type, str):
            map_queue_type = MapQueueType[map_queue_type]
        elif isinstance(map_queue_type, int):
            map_queue_type = MapQueueType(map_queue_type)

    async def run():
        with console.status("[eminence]Processing matches...[/]", spinner="simpleDotsScrolling", spinner_style="featherstorm"):
            matches = await client.get_match_history(count=count, map_queue_type=map_queue_type)
            if not matches:
                print("No matches found.")
                return

            match_table = Table(
                title=f"({count} most recent matches)",
                show_header=True,
                border_style="rakan",
                header_style="featherstorm",
                box=box.ROUNDED,
                show_lines=True
            )
            match_table.add_column("#", width=3)
            match_table.add_column("Position", width=15, style="highlights")
            match_table.add_column("Champion", width=15, style="eminence")
            match_table.add_column("Result", width=8)
            match_table.add_column("KDA Ratio : K/D/A", width=20)
            match_table.add_column("Duration", width=8, highlight=True)
            match_table.add_column("Queue Type", width=14)
            match_table.add_column("Match ID", width=15)

            summoner = await client.get_current_summoner()
            puuid = summoner.puuid

            await dragon.initialize()

            for i, match in enumerate(matches.games.games, 1):
                player_participant_id = None
                for id in match.participantIdentities:
                    if id.player.puuid == puuid:
                        player_participant_id = id.participantId
                        break

                if player_participant_id is None:
                    print(f"[warning]Unable to find participant ID for player in match {i} ({match.gameId})")
                    continue

                player = None
                for participant in match.participants:
                    if participant.participantId == player_participant_id:
                        player = participant
                        break

                if player is None:
                    print(f"[warning]Unable to find player in match {i} ({match.gameId})")
                    continue

                mins = match.gameDuration // 60
                result = "[bold green]WIN[/bold green]" if player.stats.win else "[bold red]LOSS[/bold red]"

                kda_ratio = (player.stats.kills + player.stats.assists) / max(1, player.stats.deaths)
                kda_left = f"{kda_ratio:.2f}".rjust(5)

                row_style = ""
                if kda_ratio < 1:
                    kda_left = f"[bold red]{kda_left}[/]"
                    row_style = "less_dim"
                elif kda_ratio > 4:
                    kda_left = f"[bold green]{kda_left}[/]"

                kda_right = f"{player.stats.kills}/{player.stats.deaths}/{player.stats.assists}"
                kda_str = f"KDA {kda_left} : {kda_right}"

                queue_name = split_camel(MapQueueType(match.queueId).name)

                player_champion = await dragon.get_champion(player.championId)
                player_champion_name = player_champion.get("name")

                lane, role = player.timeline.lane, player.timeline.role
                player_position = client.get_position_for_lane_and_role(lane, role)
                if player_position == LCUPosition.Unknown:
                    player_position = f"[dim]{player_position}[/]"

                match_table.add_row(f"{i}", player_position, player_champion_name, result, kda_str, f"[green]{mins}[/]m", queue_name, f"{match.platformId}_{match.gameId}", style=row_style)

            print(Align.center(match_table))

    asyncio.run(run())

@lcu_app.command(name="last", help="Fetch last match from LCU")
def lcu_last_match(
    client_install_path: Optional[Path] = default_client_path,
    map_queue_type: Optional[MapQueueTypeName] = None,
    filter: Optional[str] = None
):
    client = LCUClient(client_install_path=client_install_path)

    if map_queue_type is not None:
        map_queue_type = MapQueueType[map_queue_type]

    match = asyncio.run(client.get_last_match(map_queue_type=map_queue_type))
    if filter is not None:
        print(getattr(match, filter))
    else:
        print(match)

lcu_champselect_app = typer.Typer(name="champ-select", no_args_is_help=True)
lcu_app.add_typer(lcu_champselect_app)

@lcu_champselect_app.command(name="locked", help="Returns the ID of your currently locked-in champion")
def get_locked(client_install_path: Optional[Path] = default_client_path):
    client = LCUClient(client_install_path)
    print(asyncio.run(client.get_locked_champion()))


@lcu_champselect_app.command(name="hovered", help="Returns the currently hovered champion")
def get_hovered(client_install_path: Optional[Path] = default_client_path):
    client = LCUClient(client_install_path)
    print(asyncio.run(client.get_selected_champion()))


lcu_lobby_app = typer.Typer(name="lobby", no_args_is_help=True)
lcu_app.add_typer(lcu_lobby_app)


@lcu_lobby_app.command(name="get", help="Returns the current lobby the player belongs to")
def get_lobby(client_install_path: Optional[Path] = default_client_path):
    client = LCUClient(client_install_path)
    print(asyncio.run(client.get_current_summoner()))


cfg_app = typer.Typer(name="cfg", no_args_is_help=True, help="Configuration commands")
app.add_typer(cfg_app)


@cfg_app.command(name="view", help="View your saved config")
def view_cfg(category: Optional[str] = None):
    cfg = config.get_full_config()
    if category is not None:
        print(f"Category {category}:")
        print(cfg.get(category))
    else:
        print("Saved config:")
        print(cfg)


@cfg_app.command(name="get", help="Get a saved config value")
def get_cfg_value(category: str, key: str):
    value = config.get(key, category)
    print(f"[featherstorm]{category + '.' if category else ''}{key}[/]=[gold]{value}[/]")


@cfg_app.command(name="set", help="Set a saved config value")
def set_cfg_value(category: str, key: str, value: str):
    config.set(key, value, category)
    print(f"[featherstorm]{category + '.' if category else ''}{key}[/]=[gold]{value}[/]")


@cfg_app.command(name="clear", help="Clear a saved config value")
def clear_cfg_value(category: str, key: str):
    config.delete(key, category)
    print(f"Cleared [featherstorm]{category + '.' if category else ''}{key}[/]")


@cfg_app.command(name="reset", help="Reset saved configuration back to defaults")
def reset_cfg(force: Optional[bool] = False):
    if config.init(force):
        print("Config reset.")
    else:
        print("Config not reset, specify the --force flag to confirm your reset.")


riot_app = typer.Typer(name="riot", no_args_is_help=True, help="Riot Web API commands")
app.add_typer(riot_app)


def _riot_client() -> RiotAPIClient:
    load_dotenv()
    api_key = os.getenv("RIOT_API_KEY")
    if not api_key:
        print("[bold red]RIOT_API_KEY not set[/bold red]")
        raise typer.Exit(1)
    return RiotAPIClient(api_key)


@riot_app.command(name="matches", help="Show recent matches for a player.")
def riot_matches(
    game_name: str = config.get("companion.default_player_name"),
    tag_line: str = config.get("companion.default_player_tagline"),
    count: int = 5,
    match_type: Optional[QueueType] = None,
    map_queue_type: Optional[MapQueueTypeName] = None
):
    if map_queue_type is not None:
        if isinstance(map_queue_type, str):
            map_queue_type = MapQueueType[map_queue_type]
        elif isinstance(map_queue_type, int):
            map_queue_type = MapQueueType(map_queue_type)

    async def run():
        with console.status("[eminence]Processing matches...[/]", spinner="simpleDotsScrolling", spinner_style="featherstorm"):
            client = _riot_client()
            puuid = await client.get_puuid(game_name, tag_line)
            if not puuid:
                print(f"[bold red]Player {game_name}#{tag_line} not found[/bold red]")
                return
            matches = await client.get_match_ids(puuid, count=count, match_type=match_type, map_queue_type=map_queue_type)
            if not matches:
                print("No matches found.")
                return

            match_table = Table(
                title=f"({count} most recent matches for {game_name}#{tag_line})",
                show_header=True,
                border_style="rakan",
                header_style="featherstorm",
                box=box.ROUNDED,
                show_lines=True
            )
            match_table.add_column("#", width=3)
            match_table.add_column("Champion", width=15, style="eminence")
            match_table.add_column("Result", width=8)
            match_table.add_column("KDA Ratio : K/D/A", width=20)
            match_table.add_column("Duration", width=8, highlight=True)
            match_table.add_column("Game Mode", width=10)
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

                    match_table.add_row(f"{i}", player.championName, result, kda_str, f"[green]{mins}[/]m", match.info.gameMode, match.metadata.matchId, style=row_style)
                else:
                    print(f"{i}. {match.metadata.matchId}")

            print(Align.center(match_table))

    asyncio.run(run())


@riot_app.command(name="match", help="Show details for a specific match.")
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

@riot_app.command(name="puuid", help="Fetch a summoner's puuid")
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


@riot_app.command(name="timeline", help="Show player event timeline for a specific match.")
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
        console.print(render_player_timeline(
            timeline,
            player.participantId,
            participant_champions,
            game_duration_seconds=match.info.gameDuration,
            bar_width=max(60, console.width - 4),
        ))

    asyncio.run(run())



highlights_app = typer.Typer(name="highlights", no_args_is_help=True, help="Highlights commands")
app.add_typer(highlights_app)


@highlights_app.command(name="capture", help="Capture highlights from your last match.")
def capture_highlights(
    game_path: Optional[Path] = None,
    export_path: Optional[Path] = None,
    name: Optional[str] = config.get("companion.default_player_name"),
    tagline: Optional[str] = config.get("companion.default_player_tagline"),
    count: Optional[int] = 2,
    map_queue_type: Optional[MapQueueTypeName] = None
):
    load_dotenv()
    api_key = os.getenv("RIOT_API_KEY")

    if map_queue_type is not None:
        map_queue_type = MapQueueType[map_queue_type]

    print(map_queue_type.name, map_queue_type.value)

    if game_path is None:
        path, was_input = try_get_cfg_or_input("lcu", "client_install_path", "League of Legends install path")
        game_path = Path(path)
        if was_input:
            if game_path.exists() and game_path.is_dir():
                config.set("lcu.client_install_path", game_path.as_posix())
                print(f"Saved client install path ({format_file_path(game_path)}) to config")
            else:
                raise SystemError("you've given me a bungus game path")

    if export_path is None:
        path, was_input = try_get_cfg_or_input("highlights", "export_path", "Highlights export path")
        export_path = Path(path)
        if was_input:
            if export_path.exists() and export_path.is_dir():
                config.set("highlights.export_path", export_path.as_posix())
                print(f"Saved highlight export path ({format_file_path(export_path)}) to config")
            else:
                raise SystemError("you've given me a bungus export path")

    async def run():
        highlights = await HighlightManager.create(name, tagline, game_path, export_path, api_key)
        last_match_id = await highlights.get_last_match_id(map_queue_type)
        await highlights.capture_highlights_for_match(last_match_id, numHighlights=count)

    asyncio.run(run())


dragon_app = typer.Typer(name="dragon", no_args_is_help=True, help="rawr")
app.add_typer(dragon_app)


@dragon_app.command(name="item", help="Get item info by ID.")
def dragon_item(item_id: int):
    async def run():
        dragon = CommunityDataDragon()
        await dragon.initialize()
        item = await dragon.get_item(item_id)
        if item is None:
            print(f"[bold red]Item {item_id} not found[/bold red]")
            return
        print(item)

    asyncio.run(run())


if __name__ == "__main__":
    app()
