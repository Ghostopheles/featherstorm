import sys
import yaml
import httpx
import atexit
import asyncio
import logging
import logging.config

from rich import print
from pathlib import Path
from dataclasses import dataclass

from chroma import (ChromaSession,
                    ChromaEffect,
                    ChromaEffectType,
                    ChromaColor,
                    ChromaDevice,
                    ChromaAnimation,
)

from league.api import LeagueClient
from league.models import GameEventType, GameTeam, GameEvent

from govee import GoveeConnectionListener, GoveeColor

GOVEE_REQUEST_TIMEOUT = 0.5

log_file_path = Path(__file__).with_name("logs")
log_file_path.mkdir(exist_ok=True)

log_cfg_path = Path(__file__).with_name("log_config.yaml")

with open(log_cfg_path) as f:
    log_cfg = yaml.safe_load(f)
logging.config.dictConfig(log_cfg)

queue_handler = logging.getHandlerByName("queue_handler")
if queue_handler is not None:
    queue_handler.listener.start()
    atexit.register(queue_handler.listener.stop)

logger = logging.getLogger("league")

logger.info(f"Using Python version {sys.version}")

# disable noisy loggers >:(
logging.getLogger("httpx").propagate = False
logging.getLogger("httpcore.http11").propagate = False

SELF_PATH = Path(__file__).parent
DATA_PATH = SELF_PATH / "data"

DEFAULT_PLAYER_NAME = "Dallas N Tollway"

TEAMMATE_DIM_FACTOR = 0.4  # Peak brightness for teammate events

CHROMA_APP_INFO = {
    "title": "League of Chroma",
    "description": "The colors...",
    "author": {
        "name": "Ghostopheles",
        "contact": "https://ghst.tools"
    },
    "device_supported": [
        "keyboard",
    ],
    "category": "game"
}


def scale_color(color: ChromaColor, factor: float) -> ChromaColor:
    return ChromaColor(int(color.r * factor), int(color.g * factor), int(color.b * factor))


@dataclass
class Effects:
    blue: str                                                    # ORDER team base
    red: str                                                     # CHAOS team base
    white: str                                                   # spectator base
    kill_flash: dict                                             # bright gold (my kill)
    teammate_kill_flash: dict                                    # dim gold (teammate kill)
    objective_flash: dict                                        # purple flash
    turret_flash: dict                                           # bright white (my turret kill)
    teammate_turret_flash: dict                                  # dim white (teammate turret kill)
    first_brick_flash: dict                                      # short white (my FirstBrick)


async def setup_effects(chroma: ChromaSession, device: ChromaDevice) -> Effects:
    async def static(color: ChromaColor) -> str:
        e = ChromaEffect(ChromaEffectType.Static)
        e.set_single_color_param(color)
        return await chroma.create_effect(device, e)

    def make_flash(color: ChromaColor, *, steps=10, flash_duration=0.05, total_fade_duration=1.0):
        return {
            GameTeam.ORDER: ChromaAnimation.flash_fade(color, ChromaColor.blue(),  steps=steps, flash_duration=flash_duration, total_fade_duration=total_fade_duration),
            GameTeam.CHAOS: ChromaAnimation.flash_fade(color, ChromaColor.red(),   steps=steps, flash_duration=flash_duration, total_fade_duration=total_fade_duration),
            None:           ChromaAnimation.flash_fade(color, ChromaColor.white(), steps=steps, flash_duration=flash_duration, total_fade_duration=total_fade_duration),
        }

    return Effects(
        blue=await static(ChromaColor.blue()),
        red=await static(ChromaColor.red()),
        white=await static(ChromaColor.white()),
        kill_flash=make_flash(ChromaColor.gold()),
        teammate_kill_flash=make_flash(scale_color(ChromaColor.gold(), TEAMMATE_DIM_FACTOR)),
        objective_flash=make_flash(ChromaColor.purple()),
        turret_flash=make_flash(ChromaColor.white()),
        teammate_turret_flash=make_flash(scale_color(ChromaColor.white(), TEAMMATE_DIM_FACTOR)),
        first_brick_flash=make_flash(ChromaColor.white(), steps=5, total_fade_duration=0.5),
    )


async def amain():
    client = LeagueClient()
    print("Waiting for League session...")

    print("Setting up [bold blue]govee[/bold blue]...")
    loop = asyncio.get_event_loop()
    govee_listener = GoveeConnectionListener(loop)
    govee_listener.start()

    await asyncio.sleep(GOVEE_REQUEST_TIMEOUT)

    for dev in govee_listener.devices.values():
        dev.set_power_state(True)
        dev.set_brightness(100)
        dev.set_color_and_temperature(GoveeColor.white())

    async with ChromaSession(CHROMA_APP_INFO) as chroma:
        device = ChromaDevice.Keyboard
        effects = await setup_effects(chroma, device)

        active_player_name = None
        active_player_team = None
        player_teams: dict[str, GameTeam] = {}
        player_champions: dict[str, str] = {}

        team_to_chroma_effect = {
            GameTeam.ORDER: effects.blue,
            GameTeam.CHAOS: effects.red,
            GameTeam.SPECTATOR: effects.white
        }

        team_to_govee_color = {
            GameTeam.ORDER: GoveeColor.blue(),
            GameTeam.CHAOS: GoveeColor.red(),
            GameTeam.SPECTATOR: GoveeColor.white()
        }

        async def on_game_start(_: GameEvent):
            nonlocal active_player_name, active_player_team

            active = await client.get_active_player()
            active_player_name = active.riotIdGameName if active else DEFAULT_PLAYER_NAME

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

            # don't forget about govee!
            for dev in govee_listener.devices.values():
                dev.set_power_state(True)
                dev.set_brightness(100)

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


if __name__ == "__main__":
    asyncio.run(amain())
