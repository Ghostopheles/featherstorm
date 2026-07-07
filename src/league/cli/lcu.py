import typer
import asyncio

from rich import box
from rich.table import Table
from rich.align import Align
from pathlib import Path
from dataclasses import asdict
from typing import Optional, Annotated

from league.lcu import LCUClient
from league.lcu.models import LCUPosition, LCUInventoryItem
from league.dragon import DataDragon
from league.console import print, console, print_json
from league.enums import QueueChoice, resolve_queue, resolve_queue_name

from league.cli._shared import default_client_path

app = typer.Typer(name="lcu", no_args_is_help=True, help="League Client API commands")


@app.command(name="summoner", help="Fetch current summoner info")
def lcu_summoner(client_install_path: Optional[Path] = default_client_path):
    client = LCUClient(client_install_path=client_install_path)
    summoner = asyncio.run(client.get_current_summoner())
    print(summoner)

@app.command(name="matches", help="Fetch LCU match history")
def lcu_matches(
    client_install_path: Optional[Path] = default_client_path,
    count: int = 5,
    queue_type: Annotated[QueueChoice, typer.Option(help="Queue Type", case_sensitive=False)] = None,
):
    client = LCUClient(client_install_path=client_install_path)
    dragon = DataDragon()

    if queue_type is not None:
        queue_type = resolve_queue(queue_type)

    async def run():
        with console.status("[eminence]Processing matches...[/]", spinner="simpleDotsScrolling", spinner_style="featherstorm"):
            matches = await client.get_match_history(count=count, queue_type=queue_type)
            if not matches:
                print("No matches found.")
                return

            match_table = Table(
                title=f"({count} most recent matches)", show_header=True, border_style="rakan", header_style="featherstorm", box=box.ROUNDED, show_lines=True
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

                queue_name = resolve_queue_name(match.queueId)

                player_champion = await dragon.get_champion(player.championId)
                player_champion_name = player_champion.get("name")

                lane, role = player.timeline.lane, player.timeline.role
                player_position = client.get_position_for_lane_and_role(lane, role)
                if player_position == LCUPosition.Unknown:
                    player_position = f"[dim]{player_position}[/]"

                match_table.add_row(
                    f"{i}",
                    player_position,
                    player_champion_name,
                    result,
                    kda_str,
                    f"[green]{mins}[/]m",
                    queue_name,
                    f"{match.platformId}_{match.gameId}",
                    style=row_style,
                )

            print(Align.center(match_table))

    asyncio.run(run())


@app.command(name="last", help="Fetch last match from LCU")
def lcu_last_match(
    client_install_path: Optional[Path] = default_client_path,
    queue_type: Annotated[QueueChoice, typer.Option(help="Queue Type", case_sensitive=False)] = None,
    filter: Annotated[str, typer.Option(help="Key to filter by when printing the match data")] = None,
    json: Annotated[bool, typer.Option(help="Return the match as JSON")] = False,
):
    client = LCUClient(client_install_path=client_install_path)

    if queue_type is not None:
        queue_type = resolve_queue(queue_type)

    match = asyncio.run(client.get_last_match(queue_type=queue_type))
    if filter is not None:
        out = getattr(match, filter)
    else:
        out = match

    if json:
        print_json(data=asdict(out))
    else:
        print(out)


champselect_app = typer.Typer(name="champ-select", no_args_is_help=True)
app.add_typer(champselect_app)


@champselect_app.command(name="locked", help="Returns the ID of your currently locked-in champion")
def get_locked(client_install_path: Optional[Path] = default_client_path):
    client = LCUClient(client_install_path)
    print(asyncio.run(client.get_locked_champion()))


@champselect_app.command(name="hovered", help="Returns the currently hovered champion")
def get_hovered(client_install_path: Optional[Path] = default_client_path):
    client = LCUClient(client_install_path)
    print(asyncio.run(client.get_hovered_champion()))


lobby_app = typer.Typer(name="lobby", no_args_is_help=True)
app.add_typer(lobby_app)


@lobby_app.command(name="get", help="Returns the current lobby the player belongs to")
def get_lobby(client_install_path: Optional[Path] = default_client_path):
    client = LCUClient(client_install_path)
    print(asyncio.run(client.get_current_summoner()))


inventory_app = typer.Typer(name="inventory", no_args_is_help=True)
app.add_typer(inventory_app)

@inventory_app.command(name="item", help="Fetch an item from your summoner inventory")
def lcu_inventory_item(client_install_path: Optional[Path] = default_client_path, content_id: str | None = None):
    client = LCUClient(client_install_path=client_install_path)

    data = None
    if content_id is None:
        data = asyncio.run(client.get_inventory())
    else:
        data = asyncio.run(client.get_inventory_item(content_id))

    print(data)

@inventory_app.command(name="asset", help="Fetch an inventory item asset")
def lcu_inventory_item_asset(endpoint: str, client_install_path: Optional[Path] = default_client_path):
    if endpoint is None:
        return

    client = LCUClient(client_install_path=client_install_path)
    data = asyncio.run(client.get_asset(endpoint))
    out = Path.cwd() / "test.jpg"
    out.write_bytes(data.content)

@inventory_app.command(name="tiles", help="Fetch skin tiles for a champion")
def lcu_fetch_tiles(champion_id: int, output_dir: Path | None = None, client_install_path: Optional[Path] = default_client_path):
    client = LCUClient(client_install_path=client_install_path)
    dragon = DataDragon()

    if output_dir is None:
        output_dir = Path.cwd()

    async def run():
        await dragon.initialize()
        champion_name = await dragon.get_champion_name(champion_id)
        dir = output_dir / champion_name.lower()
        dir.mkdir(parents=True, exist_ok=True)

        champion = await dragon.get_champion(champion_id)
        skin_ids = []
        skins = champion.get("skins")
        for skin in skins:
            if "parentSkin" in skin:
                continue

            skin_id = int(skin.get("id"))
            skin_ids.append(skin_id)

        endpoints = []
        inventory = await client.get_inventory()
        for item in inventory.values():
            id = item.get("id")
            if (id is not None) and (id in skin_ids):
                endpoints.append(
                    (id, item.get("tilePath"))
                )

        for id, endpoint in endpoints:
            print(f"Fetching tile for skin {id}...")
            data = await client.get_asset(endpoint)
            better_id = id % 1000
            out = dir / f"{better_id}.jpg"
            out.write_bytes(data.content)

    asyncio.run(run())
