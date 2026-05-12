import os
import httpx
import typer
import asyncio

from dotenv import load_dotenv

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from chroma import (
    ChromaSession,
    ChromaEffect,
    ChromaEffectType,
    ChromaColor,
    ChromaDevice,
    ChromaAnimation,
)

from league.lcu import LCUClient
from league.api import LeagueClient
from league import config
from league.models import GameEventType, GameTeam, GameEvent
from league.riot_api import RiotAPIClient
from league.dragon import CommunityDataDragon
from league.enums import QueueType
from league.highlights import HighlightManager
from league.console import print

from govee import GoveeConnectionListener, GoveeColor

PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_PATH = PROJECT_DIR / "data"

CHROMA_APP_INFO = {
    "title": "League of Chroma",
    "description": "The colors...",
    "author": {"name": "Ghostopheles", "contact": "https://ghst.tools"},
    "device_supported": [
        "keyboard",
    ],
    "category": "game",
}


def scale_color(color: ChromaColor, factor: float) -> ChromaColor:
    return ChromaColor(int(color.r * factor), int(color.g * factor), int(color.b * factor))


@dataclass
class Effects:
    blue: str  # ORDER team base
    red: str  # CHAOS team base
    white: str  # spectator base
    kill_flash: dict  # bright gold (my kill)
    teammate_kill_flash: dict  # dim gold (teammate kill)
    objective_flash: dict  # purple flash
    turret_flash: dict  # bright white (my turret kill)
    teammate_turret_flash: dict  # dim white (teammate turret kill)
    first_brick_flash: dict  # short white (my FirstBrick)


async def setup_effects(chroma: ChromaSession, device: ChromaDevice) -> Effects:
    async def static(color: ChromaColor) -> str:
        e = ChromaEffect(ChromaEffectType.Static)
        e.set_single_color_param(color)
        return await chroma.create_effect(device, e)

    def make_flash(color: ChromaColor, *, steps=10, flash_duration=0.05, total_fade_duration=1.0):
        return {
            GameTeam.ORDER: ChromaAnimation.flash_fade(
                color, ChromaColor.blue(), steps=steps, flash_duration=flash_duration, total_fade_duration=total_fade_duration
            ),
            GameTeam.CHAOS: ChromaAnimation.flash_fade(
                color, ChromaColor.red(), steps=steps, flash_duration=flash_duration, total_fade_duration=total_fade_duration
            ),
            None: ChromaAnimation.flash_fade(color, ChromaColor.white(), steps=steps, flash_duration=flash_duration, total_fade_duration=total_fade_duration),
        }

    teammate_dim_factor = config.get("teammate_dim_factor", "chroma")
    return Effects(
        blue=await static(ChromaColor.blue()),
        red=await static(ChromaColor.red()),
        white=await static(ChromaColor.white()),
        kill_flash=make_flash(ChromaColor.gold()),
        teammate_kill_flash=make_flash(scale_color(ChromaColor.gold(), teammate_dim_factor)),
        objective_flash=make_flash(ChromaColor.purple()),
        turret_flash=make_flash(ChromaColor.white()),
        teammate_turret_flash=make_flash(scale_color(ChromaColor.white(), teammate_dim_factor)),
        first_brick_flash=make_flash(ChromaColor.white(), steps=5, total_fade_duration=0.5),
    )


async def amain(govee: bool):
    client = LeagueClient()
    print("Waiting for League session...")

    if govee:
        print("Setting up [bold blue]govee[/bold blue]...")
        loop = asyncio.get_event_loop()
        govee_listener = GoveeConnectionListener(loop)
        govee_listener.start()

        timeout = config.get("request_timeout", "govee")
        await asyncio.sleep(timeout)

        for dev in govee_listener.devices.values():
            dev.set_power_state(config.get("default_power_state", "govee"))
            dev.set_brightness(config.get("default_brightness", "govee"))
            dev.set_color_and_temperature(GoveeColor.white())

    async with ChromaSession(CHROMA_APP_INFO) as chroma:
        device = ChromaDevice.Keyboard
        effects = await setup_effects(chroma, device)

        active_player_name = None
        active_player_team = None
        player_teams: dict[str, GameTeam] = {}
        player_champions: dict[str, str] = {}

        team_to_chroma_effect = {GameTeam.ORDER: effects.blue, GameTeam.CHAOS: effects.red, GameTeam.SPECTATOR: effects.white}

        team_to_govee_color = {GameTeam.ORDER: GoveeColor.blue(), GameTeam.CHAOS: GoveeColor.red(), GameTeam.SPECTATOR: GoveeColor.white()}

        async def on_game_start(_: GameEvent):
            nonlocal active_player_name, active_player_team

            active = await client.get_active_player()
            active_player_name = active.riotIdGameName if active else config.get("default_player_name", "companion")

            all_data = await client.get_all_game_data()
            for player in all_data.allPlayers:
                player_teams[player.riotIdGameName] = player.team
                player_champions[player.riotIdGameName] = player.championName

            player_team = player_teams.get(active_player_name) if active else None

            if player_team is None:
                for player in all_data.allPlayers:
                    if player.riotIdGameName == active_player_name:
                        player_team = player.team
                        break

            active_player_team = player_team

            effect = team_to_chroma_effect.get(player_team)
            await chroma.set_effect(effect)

            def format_player(name: str) -> str:
                team = player_teams.get(name)
                champion = player_champions.get(name)
                display = f"{name} [bold white]({champion})[/bold white]" if champion else name
                if team == GameTeam.ORDER:
                    return f"[bold blue]{display}[/bold blue]"
                elif team == GameTeam.CHAOS:
                    return f"[bold red]{display}[/bold red]"
                else:
                    return display

            client.format_player = format_player

            if not govee:
                # don't forget about govee!
                for dev in govee_listener.devices.values():
                    color = team_to_govee_color.get(player_team)
                    dev.set_color_and_temperature(color)

        async def on_champion_kill(event: GameEvent):
            killer = event.KillerName
            if killer == active_player_name:
                asyncio.create_task(chroma.play_animation(effects.kill_flash[active_player_team], device))
            elif player_teams.get(killer) == active_player_team:
                asyncio.create_task(chroma.play_animation(effects.teammate_kill_flash[active_player_team], device))

        async def on_turret_killed(event: GameEvent):
            killer = event.KillerName
            if killer == active_player_name:
                asyncio.create_task(chroma.play_animation(effects.turret_flash[active_player_team], device))
            elif player_teams.get(killer) == active_player_team:
                asyncio.create_task(chroma.play_animation(effects.teammate_turret_flash[active_player_team], device))

        async def on_first_brick(event: GameEvent):
            if event.KillerName == active_player_name:
                asyncio.create_task(chroma.play_animation(effects.first_brick_flash[active_player_team], device))

        async def on_objective_kill(event: GameEvent):
            killer = event.KillerName
            if player_teams.get(killer) == active_player_team:
                asyncio.create_task(chroma.play_animation(effects.objective_flash[active_player_team], device))

        client.add_event_callback(GameEventType.GameStart, on_game_start)
        client.add_event_callback(GameEventType.ChampionKill, on_champion_kill)
        client.add_event_callback(GameEventType.TurretKilled, on_turret_killed)
        client.add_event_callback(GameEventType.FirstBrick, on_first_brick)
        client.add_event_callback(GameEventType.HordeKill, on_objective_kill)
        client.add_event_callback(GameEventType.HeraldKill, on_objective_kill)
        client.add_event_callback(GameEventType.BaronKill, on_objective_kill)
        client.add_event_callback(GameEventType.DragonKill, on_objective_kill)

        while True:  # reconnect loop
            print("Waiting for League client...")
            while True:  # waiting state: check every 2s
                try:
                    events = await client.get_all_events()
                    if events is not None:
                        break
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(2)

            print("League client connected.")
            client.reset()
            active_player_name = None
            active_player_team = None
            player_teams.clear()
            player_champions.clear()
            client.format_player = lambda name: name

            while True:  # active polling state: every 250ms
                try:
                    await client.poll_events()
                except httpx.ConnectError:
                    print("League client disconnected.")
                    break
                except Exception as exc:
                    print(f"Poll error: {exc}")
                await asyncio.sleep(0.25)


# --------------------------------------- CLI SETUP BELOW THIS LINE ---------------------------------------


config.init()

app = typer.Typer(name="Featherstorm", no_args_is_help=True)


@app.command(name="companion", help="Runs the app in it's default mode, watching the current ongoing match.")
def default(govee: Optional[bool] = True):
    asyncio.run(amain(govee))


lcu_app = typer.Typer(name="lcu", no_args_is_help=True, help="League Client API commands")
app.add_typer(lcu_app)

lcu_champselect_app = typer.Typer(name="champ-select", no_args_is_help=True)
lcu_app.add_typer(lcu_champselect_app)

default_client_path = Path(config.get("client_install_path", "lcu"))


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
def get_cfg_value(key: str, category: Optional[str] = None):
    value = config.get(key, category)
    print(f"{category + '.' if category else ''}{key}: {value}")


@cfg_app.command(name="set", help="Set a saved config value")
def set_cfg_value(key: str, value: str, category: Optional[str] = None):
    config.set(key, value, category)


@cfg_app.command(name="reset", help="Reset saved configuration back to defaults")
def set_cfg_value(force: Optional[bool] = False):
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
    game_name: str = config.get("default_player_name", "companion"),
    tag_line: str = config.get("default_player_tagline", "companion"),
    count: int = 5,
    match_type: Optional[QueueType] = None,
):
    async def run():
        client = _riot_client()
        puuid = await client.get_puuid(game_name, tag_line)
        if not puuid:
            print(f"[bold red]Player {game_name}#{tag_line} not found[/bold red]")
            return
        matches = await client.get_match_ids(puuid, count=count, match_type=match_type)
        if not matches:
            print("No matches found.")
            return
        for i, match_id in enumerate(matches, 1):
            match = await client.get_match(match_id)
            pm = match.info.participants
            player = next((p for p in pm if p.puuid == puuid), None)
            if player:
                mins = match.info.gameDuration // 60
                result = "[bold green]WIN[/bold green]" if player.win else "[bold red]LOSS[/bold red]"
                print(
                    f"{i}. {match.metadata.matchId} | {result} | {player.championName} {player.kills}/{player.deaths}/{player.assists} | {mins}m | {match.info.gameMode}"
                )
            else:
                print(f"{i}. {match.metadata.matchId}")

    asyncio.run(run())


@riot_app.command(name="match", help="Show details for a specific match.")
def riot_match(match_id: str):
    async def run():
        client = _riot_client()
        match = await client.get_match(match_id)
        print(match)

    asyncio.run(run())


@riot_app.command(name="timeline", help="Show timeline for a specific match.")
def riot_timeline(match_id: str):
    async def run():
        client = _riot_client()
        timeline = await client.get_match_timeline(match_id)
        print(timeline)

    asyncio.run(run())


highlights_app = typer.Typer(name="highlights", no_args_is_help=True, help="Highlights commands")
app.add_typer(highlights_app)


@highlights_app.command(name="capture", help="Capture highlights from your last match.")
def capture_highlights(
    game_path: Path = Path(config.get("client_install_path", "lcu")),
    highlights_path: Path = Path(config.get("highlights_path", "highlights")),
    name: str = config.get("default_player_name", "companion"),
    tagline: str = config.get("default_player_tagline", "companion"),
    count: int = None
):
    load_dotenv()
    api_key = os.getenv("RIOT_API_KEY")

    async def run():
        highlights = await HighlightManager.create(name, tagline, game_path, highlights_path, api_key)
        last_match_id = await highlights.get_last_match_id()
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
