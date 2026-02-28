import asyncio
from dataclasses import dataclass

from rich import print
from pathlib import Path

from chroma import (ChromaSession,
                    ChromaEffect,
                    ChromaEffectType,
                    ChromaColor,
                    ChromaDevice,
)

from league.api import LeagueClient
from league.models import GameEventType, GameTeam, GameEvent

SELF_PATH = Path(__file__).parent
DATA_PATH = SELF_PATH / "data"

DEFAULT_PLAYER_NAME = "Dallas N Tollway"

FLASH_CURVE = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.0, 0.9, 0.7, 0.5, 0.3, 0.1]
SHORT_FLASH_CURVE = [0.3, 0.6, 1.0, 0.6, 0.3]  # 5 frames ≈ 0.5s
FLASH_FRAME_DELAY = 0.1  # seconds per frame
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
        "chromalink"
    ],
    "category": "game"
}


def scale_color(color: ChromaColor, factor: float) -> ChromaColor:
    return ChromaColor(int(color.r * factor), int(color.g * factor), int(color.b * factor))


@dataclass
class Effects:
    blue: str                       # ORDER team base
    red: str                        # CHAOS team base
    white: str                      # spectator base
    kill_flash: list[str]           # bright gold (my kill)
    teammate_kill_flash: list[str]  # dim gold (teammate kill)
    objective_flash: list[str]      # purple, dim→bright→dim
    turret_flash: list[str]         # bright white (my turret kill)
    teammate_turret_flash: list[str]  # dim white (teammate turret kill)
    first_brick_flash: list[str]    # short white (my FirstBrick)


async def setup_effects(chroma: ChromaSession, device: ChromaDevice) -> Effects:
    async def static(color: ChromaColor) -> str:
        e = ChromaEffect(ChromaEffectType.Static)
        e.set_single_color_param(color)
        return await chroma.create_effect(device, e)

    async def flash_frames(color: ChromaColor, curve: list[float] = FLASH_CURVE) -> list[str]:
        return [await static(scale_color(color, f)) for f in curve]

    return Effects(
        blue=await static(ChromaColor.blue()),
        red=await static(ChromaColor.red()),
        white=await static(ChromaColor.white()),
        kill_flash=await flash_frames(ChromaColor.gold()),
        teammate_kill_flash=await flash_frames(scale_color(ChromaColor.gold(), TEAMMATE_DIM_FACTOR)),
        objective_flash=await flash_frames(ChromaColor.purple()),
        turret_flash=await flash_frames(ChromaColor.white()),
        teammate_turret_flash=await flash_frames(scale_color(ChromaColor.white(), TEAMMATE_DIM_FACTOR)),
        first_brick_flash=await flash_frames(ChromaColor.white(), SHORT_FLASH_CURVE),
    )


async def amain():
    client = LeagueClient()
    print("League session startup...")

    async with ChromaSession(CHROMA_APP_INFO) as chroma:
        device = ChromaDevice.Keyboard
        effects = await setup_effects(chroma, device)

        current_base_effect_id = None
        active_player_name = None
        active_player_team = None
        player_teams: dict[str, GameTeam] = {}

        async def on_game_start(_: GameEvent):
            nonlocal current_base_effect_id, active_player_name, active_player_team

            active = await client.get_active_player()
            active_player_name = active.riotIdGameName if active else DEFAULT_PLAYER_NAME

            all_data = await client.get_all_game_data()
            for player in all_data.allPlayers:
                player_teams[player.riotIdGameName] = player.team

            player_team = player_teams.get(active_player_name) if active else None
            active_player_team = player_team

            if player_team is None:
                print("[bold blue]Session is in spectator mode[/bold blue]")
                player_team = GameTeam.SPECTATOR

            if player_team == GameTeam.ORDER:
                current_base_effect_id = effects.blue
                await chroma.set_effect(effects.blue)
            elif player_team == GameTeam.CHAOS:
                current_base_effect_id = effects.red
                await chroma.set_effect(effects.red)
            elif player_team == GameTeam.SPECTATOR:
                current_base_effect_id = effects.white
                await chroma.set_effect(effects.white)
            else:
                print("team???????????")

        async def flash(frame_ids: list[str]):
            for fid in frame_ids:
                await chroma.set_effect(fid)
                await asyncio.sleep(FLASH_FRAME_DELAY)
            if current_base_effect_id is not None:
                await chroma.set_effect(current_base_effect_id)

        async def on_champion_kill(event: GameEvent):
            killer = event.KillerName
            if killer == active_player_name:
                asyncio.create_task(flash(effects.kill_flash))
            elif player_teams.get(killer) == active_player_team:
                asyncio.create_task(flash(effects.teammate_kill_flash))

        async def on_turret_killed(event: GameEvent):
            killer = event.KillerName
            if killer == active_player_name:
                asyncio.create_task(flash(effects.turret_flash))
            elif player_teams.get(killer) == active_player_team:
                asyncio.create_task(flash(effects.teammate_turret_flash))

        async def on_first_brick(event: GameEvent):
            if event.KillerName == active_player_name:
                asyncio.create_task(flash(effects.first_brick_flash))

        async def on_horde_herald_baron_kill(_: GameEvent):
            asyncio.create_task(flash(effects.objective_flash))

        client.add_event_callback(GameEventType.GameStart, on_game_start)
        client.add_event_callback(GameEventType.ChampionKill, on_champion_kill)
        client.add_event_callback(GameEventType.TurretKilled, on_turret_killed)
        client.add_event_callback(GameEventType.FirstBrick, on_first_brick)
        client.add_event_callback(GameEventType.HordeKill, on_horde_herald_baron_kill)
        client.add_event_callback(GameEventType.HeraldKill, on_horde_herald_baron_kill)
        client.add_event_callback(GameEventType.BaronKill, on_horde_herald_baron_kill)

        while True:
            await client.poll_events()
            await asyncio.sleep(0.25)


if __name__ == "__main__":
    asyncio.run(amain())
