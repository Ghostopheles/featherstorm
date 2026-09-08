import asyncio
import logging
import contextlib

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
from league.lcu import LCUClient
from league.models import GameTeam, GameEvent
from league.discord import LeagueRichPresence
from league.lcu.socket import LCUWebsocketEvent
from league.ui import output, RichProgressReporter
from league.bridge import LeagueEventBridge, LeagueEvent
from league.ui.renderers import EventFeedContext, format_event_line, FEED_EVENTS

log = logging.getLogger(__name__)

CHROMA_APP_INFO = {
    "title": "Featherstorm",
    "description": "Compromise is so unsatisfying...",
    "author": {"name": "Ghostopheles", "contact": "https://ghst.tools"},
    "device_supported": [
        "keyboard",
    ],
    "category": "game",
}

TEAM_TO_GOVEE_COLOR = {
    GameTeam.ORDER: GoveeColor.blue(),
    GameTeam.CHAOS: GoveeColor.red(),
    GameTeam.SPECTATOR: GoveeColor.white(),
}


def scale_color(color: ChromaColor, factor: float) -> ChromaColor:
    return ChromaColor(int(color.r * factor), int(color.g * factor), int(color.b * factor))


def feature_enabled(flag: bool, key: str, *, default: bool) -> bool:
    """CLI flags can only turn a feature off - the config key is what turns it on."""
    return flag and config.get_or_set(key, default=default)


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

    def base_for(self, team: GameTeam | None) -> str:
        return {GameTeam.ORDER: self.blue, GameTeam.CHAOS: self.red}.get(team, self.white)

    def flash_for(self, name: str, team: GameTeam | None) -> ChromaAnimation:
        animations = getattr(self, name)
        return animations.get(team, animations[None])


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


class ChromaLighting:
    """Razer Chroma keyboard lighting. Every method no-ops when disabled."""

    def __init__(self, enabled: bool, device: ChromaDevice = ChromaDevice.Keyboard):
        self.enabled = enabled
        self.device = device
        self.session: ChromaSession | None = None
        self.effects: Effects | None = None
        self._stack = contextlib.AsyncExitStack()

    async def __aenter__(self) -> "ChromaLighting":
        if self.enabled:
            log.info("Setting up [external_api]chroma[/]...")
            self.session = await self._stack.enter_async_context(ChromaSession(CHROMA_APP_INFO))
            self.effects = await setup_chroma_effects(self.session, self.device)

        return self

    async def __aexit__(self, *exc_info):
        await self._stack.aclose()
        self.session = None
        self.effects = None

    async def set_team(self, team: GameTeam | None):
        if self.effects is None:
            return

        await self.session.set_effect(self.effects.base_for(team))

    def flash(self, name: str, team: GameTeam | None):
        if self.effects is None:
            return

        asyncio.create_task(self.session.play_animation(self.effects.flash_for(name, team), self.device))


class GoveeLights:
    """Govee LAN lights. Every method no-ops when disabled."""

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.listener: GoveeConnectionListener | None = None

    async def __aenter__(self) -> "GoveeLights":
        if not self.enabled:
            return self

        log.info("Setting up [external_api]govee[/]...")
        listener = GoveeConnectionListener()
        listener.start()

        await asyncio.sleep(config.get_float("govee.request_timeout"))

        for dev in listener.devices.values():
            dev.set_power_state(config.get_bool("govee.default_power_state"))
            dev.set_brightness(config.get_int("govee.default_brightness"))
            dev.set_color_and_temperature(GoveeColor.white())

        self.listener = listener
        return self

    async def __aexit__(self, *exc_info):
        if self.listener is not None:
            self.listener.cleanup()
            self.listener = None

    def set_team(self, team: GameTeam | None):
        if self.listener is None:
            return

        color = TEAM_TO_GOVEE_COLOR.get(team, GoveeColor.white())
        for dev in self.listener.devices.values():
            dev.set_color_and_temperature(color)


@contextlib.asynccontextmanager
async def open_presence(enabled: bool, lcu_client: LCUClient | None = None):
    if not enabled:
        yield None
        return

    log.info("Setting up [external_api]discord[/]...")
    presence = LeagueRichPresence(config.get_or_set("discord.app_id"), lcu_client)
    await presence.init()
    await presence.start_updates()

    try:
        yield presence
    finally:
        await presence.close()


def register_event_feed(bridge: LeagueEventBridge, feed: EventFeedContext):
    def on_event(event: GameEvent):
        line = format_event_line(event, feed)
        if line:
            output.print(line)

    bridge.on_game_events(FEED_EVENTS, on_event)


def register_presence_lobby_events(bridge: LeagueEventBridge, presence: LeagueRichPresence):
    async def on_lobby_create(event: LCUWebsocketEvent):
        await presence.init_lobby(event.data)

    async def on_lobby_update(event: LCUWebsocketEvent):
        await presence.update_lobby(event.data)

    async def on_lobby_delete(event: LCUWebsocketEvent):
        await presence.init_empty()

    bridge.on(LeagueEvent.LobbyCreated, on_lobby_create)
    bridge.on(LeagueEvent.LobbyUpdated, on_lobby_update)
    bridge.on(LeagueEvent.LobbyDeleted, on_lobby_delete)


async def run_companion(*, enable_govee: bool = True, enable_discord: bool = True, enable_chroma: bool = True):
    log.info("Starting [featherstorm]Featherstorm[/] in companion mode...")

    bridge = LeagueEventBridge(exit_on_timeout=True, reporter=RichProgressReporter())
    feed = EventFeedContext()

    active_player_name = None
    active_player_team = None

    async with (
        ChromaLighting(feature_enabled(enable_chroma, "companion.chroma_enabled", default=False)) as chroma,
        GoveeLights(feature_enabled(enable_govee, "companion.govee_enabled", default=False)) as govee,
        open_presence(feature_enabled(enable_discord, "discord.enable_rich_presence", default=True), bridge.lcu) as presence,
    ):

        async def on_game_start(_: GameEvent):
            nonlocal active_player_name, active_player_team

            active = await bridge.get_active_player()
            active_player_name = active.riotIdGameName if active else config.get_str("companion.default_player_name")

            all_data = await bridge.get_game_data()
            for player in all_data.allPlayers:
                feed.teams[player.riotIdGameName] = player.team
                feed.champions[player.riotIdGameName] = player.championName

            active_player_team = feed.teams.get(active_player_name)

            await chroma.set_team(active_player_team)
            govee.set_team(active_player_team)

            if presence is not None:
                await presence.init_match(all_data, feed.teams, feed.champions, active_player_name, bridge.get_game_data)

        async def on_game_end(_: GameEvent):
            if presence is not None:
                await presence.end_match()

        async def on_champion_kill(event: GameEvent):
            killer = event.KillerName
            if killer == active_player_name:
                chroma.flash("kill_flash", active_player_team)
            elif feed.teams.get(killer) == active_player_team:
                chroma.flash("teammate_kill_flash", active_player_team)

        async def on_turret_killed(event: GameEvent):
            killer = event.KillerName
            if killer == active_player_name:
                chroma.flash("turret_flash", active_player_team)
            elif feed.teams.get(killer) == active_player_team:
                chroma.flash("teammate_turret_flash", active_player_team)

        async def on_first_brick(event: GameEvent):
            if event.KillerName == active_player_name:
                chroma.flash("first_brick_flash", active_player_team)

        async def on_objective_kill(event: GameEvent):
            if feed.teams.get(event.KillerName) == active_player_team:
                chroma.flash("objective_flash", active_player_team)

        @bridge.on(LeagueEvent.SessionStart)
        async def on_session_start():
            nonlocal active_player_name, active_player_team
            active_player_name = None
            active_player_team = None
            feed.clear()

            log.info("League session started")

        @bridge.on(LeagueEvent.SessionEnd)
        async def on_session_end():
            log.info("League session ended.")

        bridge.on(LeagueEvent.GameStart, on_game_start)
        bridge.on(LeagueEvent.GameEnd, on_game_end)
        bridge.on(LeagueEvent.ChampionKill, on_champion_kill)
        bridge.on(LeagueEvent.TurretKilled, on_turret_killed)
        bridge.on(LeagueEvent.FirstBrick, on_first_brick)
        bridge.on(
            (LeagueEvent.HordeKill, LeagueEvent.HeraldKill, LeagueEvent.BaronKill, LeagueEvent.DragonKill),
            on_objective_kill,
        )

        register_event_feed(bridge, feed)
        if presence is not None:
            register_presence_lobby_events(bridge, presence)

        await bridge.run()
