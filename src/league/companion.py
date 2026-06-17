import asyncio

from dataclasses import dataclass

from chroma import (
    ChromaSession,
    ChromaEffect,
    ChromaEffectType,
    ChromaColor,
    ChromaDevice,
    ChromaAnimation,
)

from govee import GoveeConnectionListener, GoveeColor

from league import config
from league.console import log, print
from league.api import LeagueClient
from league.watcher import MatchWatcher
from league.models import GameEventType, GameTeam, GameEvent, GameResult, Turret


DATA_PATH = config.get("meta.cache_dir")

CHROMA_APP_INFO = {
    "title": "Featherstorm",
    "description": "Compromise is so unsatisfying...",
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


async def setup_chroma_effects(chroma: ChromaSession, device: ChromaDevice) -> Effects:
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

    teammate_dim_factor = config.get_float("chroma.teammate_dim_factor")
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


async def init_govee() -> GoveeConnectionListener:
    log("Setting up [external_api]govee[/]...")
    loop = asyncio.get_event_loop()
    govee_listener = GoveeConnectionListener(loop)
    govee_listener.start()

    timeout = config.get_float("govee.request_timeout")
    await asyncio.sleep(timeout)

    for dev in govee_listener.devices.values():
        dev.set_power_state(config.get_bool("govee.default_power_state"))
        dev.set_brightness(config.get_int("govee.default_brightness"))
        dev.set_color_and_temperature(GoveeColor.white())

    return govee_listener


def format_assists(assisters, format_player) -> str:
    if not assisters:
        return ""
    return ", assisted by: " + ", ".join(format_player(a) for a in assisters)


def register_event_feed(watcher: MatchWatcher, format_player):
    def print_event(event: GameEvent, message: str):
        print(f"{event.get_formatted_timestamp()}: {message}")

    def on_game_start(event: GameEvent):
        print_event(event, "Game has started")

    def on_minions_spawning(event: GameEvent):
        print_event(event, "Minions have spawned")

    def on_first_blood(event: GameEvent):
        print_event(event, f"First blood claimed by {format_player(event.Recipient)}")

    def on_first_brick(event: GameEvent):
        print_event(event, f"First brick claimed by {format_player(event.KillerName)}")

    def on_champion_kill(event: GameEvent):
        killer = format_player(event.KillerName)
        victim = format_player(event.VictimName)
        msg = f"{killer} has slain {victim}" + format_assists(event.Assisters, format_player)
        print_event(event, msg)

    def on_turret_killed(event: GameEvent):
        turret = Turret.from_str(event.TurretKilled)
        killer = format_player(event.KillerName)
        msg = f"{turret.to_str()} was destroyed by {killer}" + format_assists(event.Assisters, format_player)
        print_event(event, msg)

    def on_inhib_killed(event: GameEvent):
        killer = format_player(event.KillerName)
        msg = f"{event.InhibKilled} was destroyed by {killer}" + format_assists(event.Assisters, format_player)
        print_event(event, msg)

    def on_dragon_killed(event: GameEvent):
        killer = format_player(event.KillerName)
        verb = "stolen" if event.Stolen else "slain"
        msg = f"The {event.DragonType} dragon was {verb} by {killer}" + format_assists(event.Assisters, format_player)
        print_event(event, msg)

    def on_herald_killed(event: GameEvent):
        killer = format_player(event.KillerName)
        verb = "stolen" if event.Stolen else "slain"
        msg = f"The Rift Herald was {verb} by {killer}" + format_assists(event.Assisters, format_player)
        print_event(event, msg)

    def on_baron_killed(event: GameEvent):
        killer = format_player(event.KillerName)
        verb = "stolen" if event.Stolen else "slain"
        msg = f"Baron Nashor was {verb} by {killer}" + format_assists(event.Assisters, format_player)
        print_event(event, msg)

    def on_horde_killed(event: GameEvent):
        killer = format_player(event.KillerName)
        verb = "stolen" if event.Stolen else "slain"
        msg = f"A grub has been {verb} by {killer}" + format_assists(event.Assisters, format_player)
        print_event(event, msg)

    def on_multikill(event: GameEvent):
        print_event(event, f"{event.get_killstreak_str()} for {format_player(event.KillerName)}")

    def on_ace(event: GameEvent):
        print_event(event, f"{format_player(event.Acer)} has scored an ace for {event.AcingTeam}")

    def on_game_end(event: GameEvent):
        print_event(event, f"You {'lose!' if event.Result == GameResult.Lose else 'win!'}")

    watcher.on(GameEventType.GameStart, on_game_start)
    watcher.on(GameEventType.MinionsSpawning, on_minions_spawning)
    watcher.on(GameEventType.FirstBlood, on_first_blood)
    watcher.on(GameEventType.FirstBrick, on_first_brick)
    watcher.on(GameEventType.ChampionKill, on_champion_kill)
    watcher.on(GameEventType.TurretKilled, on_turret_killed)
    watcher.on(GameEventType.InhibKilled, on_inhib_killed)
    watcher.on(GameEventType.DragonKill, on_dragon_killed)
    watcher.on(GameEventType.HeraldKill, on_herald_killed)
    watcher.on(GameEventType.BaronKill, on_baron_killed)
    watcher.on(GameEventType.HordeKill, on_horde_killed)
    watcher.on(GameEventType.Multikill, on_multikill)
    watcher.on(GameEventType.Ace, on_ace)
    watcher.on(GameEventType.GameEnd, on_game_end)


async def run_companion():
    client = LeagueClient()

    govee = None
    enable_govee = config.get_or_set("companion.govee_enabled", default=False)

    log("Starting [featherstorm]Featherstorm[/] in companion mode...")

    if enable_govee:
        govee = await init_govee()

    async with ChromaSession(CHROMA_APP_INFO) as chroma:
        device = ChromaDevice.Keyboard
        effects = await setup_chroma_effects(chroma, device)

        active_player_name = None
        active_player_team = None
        player_teams: dict[str, GameTeam] = {}
        player_champions: dict[str, str] = {}

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

        team_to_chroma_effect = {GameTeam.ORDER: effects.blue, GameTeam.CHAOS: effects.red, GameTeam.SPECTATOR: effects.white}

        team_to_govee_color = {GameTeam.ORDER: GoveeColor.blue(), GameTeam.CHAOS: GoveeColor.red(), GameTeam.SPECTATOR: GoveeColor.white()}

        watcher = MatchWatcher(client)

        async def on_game_start(_: GameEvent):
            nonlocal active_player_name, active_player_team

            active = await client.get_active_player()
            active_player_name = active.riotIdGameName if active else config.get_str("companion.default_player_name")

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

            if govee:
                # don't forget about govee!
                for dev in govee.devices.values():
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

        @watcher.on_session_start
        async def on_session_start():
            nonlocal active_player_name, active_player_team
            client.reset()
            active_player_name = None
            active_player_team = None
            player_teams.clear()
            player_champions.clear()

            log("League session started")

        @watcher.on_session_end
        async def on_session_end():
            log("League session ended.")

        watcher.on(GameEventType.GameStart, on_game_start)
        watcher.on(GameEventType.ChampionKill, on_champion_kill)
        watcher.on(GameEventType.TurretKilled, on_turret_killed)
        watcher.on(GameEventType.FirstBrick, on_first_brick)
        watcher.on(GameEventType.HordeKill, on_objective_kill)
        watcher.on(GameEventType.HeraldKill, on_objective_kill)
        watcher.on(GameEventType.BaronKill, on_objective_kill)
        watcher.on(GameEventType.DragonKill, on_objective_kill)

        register_event_feed(watcher, format_player)

        await watcher.run()
