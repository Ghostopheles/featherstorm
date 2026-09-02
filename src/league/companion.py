import asyncio
import logging

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
from league.api import LeagueClient
from league.watcher import MatchWatcher
from league.discord import LeagueRichPresence
from league.lcu.socket import LCUWebsocketEvent
from league.lcu.gameflow import LCUGameFlow, LCUGameFlowEvent
from league.models import GameEventType, GameTeam, GameEvent
from league.ui import output, RichProgressReporter
from league.ui.renderers import EventFeedContext, format_event_line, FEED_EVENTS

log = logging.getLogger(__name__)

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
    log.info("Setting up [external_api]govee[/]...")
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


def register_event_feed(watcher: MatchWatcher, feed: EventFeedContext):
    def on_event(event: GameEvent):
        line = format_event_line(event, feed)
        if line:
            output.print(line)

    for event_type in FEED_EVENTS:
        watcher.on(event_type, on_event)


async def register_gameflow_events(gameflow: LCUGameFlow, presence: LeagueRichPresence | None):
    if presence is None:
        return

    async def on_lobby_create(event: LCUWebsocketEvent):
        if isinstance(event.data, list):
            return

        await presence.init_lobby(event.data)

    gameflow.add_callback(LCUGameFlowEvent.LobbyCreated, on_lobby_create)

    async def on_lobby_update(event: LCUWebsocketEvent):
        await presence.update_lobby(event.data)

    gameflow.add_callback(LCUGameFlowEvent.LobbyUpdated, on_lobby_update)

    async def on_lobby_delete(event: LCUWebsocketEvent):
        await presence.init_empty()

    gameflow.add_callback(LCUGameFlowEvent.LobbyDeleted, on_lobby_delete)

    await gameflow.start()


async def run_companion():
    client = LeagueClient()
    gameflow = LCUGameFlow()

    govee = None
    enable_govee = config.get_or_set("companion.govee_enabled", default=False)

    presence = None
    enable_discord = config.get_or_set("discord.enable_rich_presence", default=True)

    log.info("Starting [featherstorm]Featherstorm[/] in companion mode...")

    if enable_govee:
        govee = await init_govee()

    if enable_discord:
        discord_client_id = config.get_or_set("discord.app_id")
        presence = LeagueRichPresence(discord_client_id)
        await presence.init()
        await presence.start_updates()

    await register_gameflow_events(gameflow, presence)

    async def get_game_data():
        return await client.get_all_game_data()

    async with ChromaSession(CHROMA_APP_INFO) as chroma:
        device = ChromaDevice.Keyboard
        effects = await setup_chroma_effects(chroma, device)

        active_player_name = None
        active_player_team = None

        feed = EventFeedContext()
        player_teams = feed.teams
        player_champions = feed.champions

        team_to_chroma_effect = {GameTeam.ORDER: effects.blue, GameTeam.CHAOS: effects.red, GameTeam.SPECTATOR: effects.white}

        team_to_govee_color = {GameTeam.ORDER: GoveeColor.blue(), GameTeam.CHAOS: GoveeColor.red(), GameTeam.SPECTATOR: GoveeColor.white()}

        watcher = MatchWatcher(client, reporter=RichProgressReporter())

        async def on_game_start(_: GameEvent):
            nonlocal active_player_name, active_player_team

            active = await client.get_active_player()
            active_player_name = active.riotIdGameName if active else config.get_str("companion.default_player_name")

            all_data = await get_game_data()
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

            if presence is not None:
                await presence.init_match(all_data, player_teams, player_champions, active_player_name, get_game_data)

        async def on_game_end(_: GameEvent):
            if presence is not None:
                await presence.end_match()

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
            feed.clear()

            log.info("League session started")

        @watcher.on_session_end
        async def on_session_end():
            log.info("League session ended.")

        watcher.on(GameEventType.GameStart, on_game_start)
        watcher.on(GameEventType.GameEnd, on_game_end)
        watcher.on(GameEventType.ChampionKill, on_champion_kill)
        watcher.on(GameEventType.TurretKilled, on_turret_killed)
        watcher.on(GameEventType.FirstBrick, on_first_brick)
        watcher.on(GameEventType.HordeKill, on_objective_kill)
        watcher.on(GameEventType.HeraldKill, on_objective_kill)
        watcher.on(GameEventType.BaronKill, on_objective_kill)
        watcher.on(GameEventType.DragonKill, on_objective_kill)

        register_event_feed(watcher, feed)

        try:
            await watcher.run()
        finally:
            if presence is not None:
                await presence.close()
            await gameflow.lcu.ws.disconnect()
