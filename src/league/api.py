import httpx
import inspect

from rich import print
from typing import Callable, Optional

from league.http import BaseAPIClient
from league.enums import GameEventType, GameResult
from league.models import ActivePlayer, AllGameData, GameEvent, GameTeam, Turret

DEFAULT_RIOT_API_REGION = "na1"


def convert_timestamp(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes):02}:{int(secs):02}"


def format_assists(assists):
    if len(assists) == 0:
        return ""

    return ", assisted by: " + ", ".join(assists)


type GameEventCallback = Callable[[GameEvent], None]


class LeagueClient(BaseAPIClient):
    callbacks: dict[GameEventType, list[GameEventCallback]]

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url="https://127.0.0.1:2999/liveclientdata",
            http2=True,
            verify=False,
        )
        self.last_event_count = 0
        self.callbacks = {}
        self.format_player: Callable[[str], str] = lambda name: name

    async def get_all_game_data(self) -> AllGameData:
        return AllGameData(**await self.get("/allgamedata"))

    async def get_active_player(self) -> Optional[ActivePlayer]:
        raw = await self.get("/activeplayer")
        if raw is None or "error" in raw:
            return None

        return ActivePlayer(**raw)

    async def get_active_player_team(self) -> Optional[GameTeam]:
        active = await self.get_active_player()
        if active is None:
            return None

        raw = await self.get("/allgamedata")
        for player in raw["allPlayers"]:
            if player["riotId"] == active.riotId:
                return GameTeam(player["team"])
        return None

    async def get_all_events(self):
        events = await self.get("/eventdata")
        if events is not None and "Events" in events:
            return events["Events"]

    def reset(self):
        self.last_event_count = 0

    def add_event_callback(self, eventType: GameEventType, callback: GameEventCallback):
        if eventType not in self.callbacks:
            self.callbacks[eventType] = []

        self.callbacks[eventType].append(callback)

    async def poll_events(self):
        events = await self.get_all_events()
        if events is None:
            return
        event_count = len(events)
        if event_count == self.last_event_count:
            return

        num_new_events = event_count - self.last_event_count
        if event_count > 0:
            new_events = events[-num_new_events:]
            if isinstance(new_events, list):
                for event in new_events:
                    await self.on_event(event)
            else:
                await self.on_event(new_events)

        self.last_event_count = event_count

    def print_timestamped_message(self, event: GameEvent, message: str):
        print(f"{event.get_formatted_timestamp()}: {message}")

    def format_assists(self, assisters) -> str:
        if not assisters:
            return ""
        return ", assisted by: " + ", ".join(self.format_player(a) for a in assisters)

    async def try_fire_callbacks_for_event(self, event: GameEvent):
        eventName = event.EventName
        if eventName not in self.callbacks:
            return

        for callback in self.callbacks[eventName]:
            if inspect.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)

    async def on_event(self, eventRaw: dict):
        event = GameEvent(**eventRaw)
        print(event)

        match event.EventName:
            case GameEventType.GameStart:
                self.on_game_start(event)
            case GameEventType.MinionsSpawning:
                self.on_minions_spawning(event)
            case GameEventType.FirstBlood:
                self.on_first_blood(event)
            case GameEventType.FirstBrick:
                self.on_first_brick(event)
            case GameEventType.TurretKilled:
                self.on_turret_killed(event)
            case GameEventType.InhibKilled:
                self.on_inhib_killed(event)
            case GameEventType.HordeKill:
                self.on_horde_killed(event)
            case GameEventType.DragonKill:
                self.on_dragon_killed(event)
            case GameEventType.HeraldKill:
                self.on_herald_killed(event)
            case GameEventType.BaronKill:
                self.on_baron_killed(event)
            case GameEventType.ChampionKill:
                self.on_champion_kill(event)
            case GameEventType.Multikill:
                self.on_multikill(event)
            case GameEventType.Ace:
                self.on_ace(event)
            case GameEventType.GameEnd:
                self.on_game_end(event)
            case _:
                print(event)
                print(f"Unhandled event: {event.EventName}")

        await self.try_fire_callbacks_for_event(event)

    def on_game_start(self, event: GameEvent):
        self.print_timestamped_message(event, "Game has started")

    def on_minions_spawning(self, event: GameEvent):
        self.print_timestamped_message(event, "Minions have spawned")

    def on_first_blood(self, event: GameEvent):
        self.print_timestamped_message(event, f"First blood claimed by {self.format_player(event.Recipient)}")

    def on_first_brick(self, event: GameEvent):
        self.print_timestamped_message(event, f"First brick claimed by {self.format_player(event.KillerName)}")

    def on_champion_kill(self, event: GameEvent):
        killer = self.format_player(event.KillerName)
        victim = self.format_player(event.VictimName)

        msg = f"{killer} has slain {victim}"
        msg = msg + self.format_assists(event.Assisters)

        self.print_timestamped_message(event, msg)

    def on_turret_killed(self, event: GameEvent):
        turret = Turret.from_str(event.TurretKilled)
        killer = self.format_player(event.KillerName)

        msg = f"{turret.to_str()} was destroyed by {killer}"
        msg = msg + self.format_assists(event.Assisters)

        self.print_timestamped_message(event, msg)

    def on_inhib_killed(self, event: GameEvent):
        inhib = event.InhibKilled
        killer = self.format_player(event.KillerName)

        msg = f"{inhib} was destroyed by {killer}"
        msg = msg + self.format_assists(event.Assisters)

        self.print_timestamped_message(event, msg)

    def on_dragon_killed(self, event: GameEvent):
        dragonType = event.DragonType
        killer = self.format_player(event.KillerName)
        stolen = event.Stolen

        msg = f"The {dragonType} dragon was {'stolen' if stolen else 'slain'} by {killer}"
        msg = msg + self.format_assists(event.Assisters)

        self.print_timestamped_message(event, msg)

    def on_herald_killed(self, event: GameEvent):
        killer = self.format_player(event.KillerName)
        stolen = event.Stolen

        msg = f"The Rift Herald was {'stolen' if stolen else 'slain'} by {killer}"
        msg = msg + self.format_assists(event.Assisters)

        self.print_timestamped_message(event, msg)

    def on_baron_killed(self, event: GameEvent):
        killer = self.format_player(event.KillerName)
        stolen = event.Stolen

        msg = f"Baron Nashor was {'stolen' if stolen else 'slain'} by {killer}"
        msg = msg + self.format_assists(event.Assisters)

        self.print_timestamped_message(event, msg)

    def on_horde_killed(self, event: GameEvent):
        killer = self.format_player(event.KillerName)
        stolen = event.Stolen

        msg = f"A grub has been {'stolen' if stolen else 'slain'} by {killer}"
        msg = msg + self.format_assists(event.Assisters)

        self.print_timestamped_message(event, msg)

    def on_multikill(self, event: GameEvent):
        msg = f"{event.get_killstreak_str()} for {self.format_player(event.KillerName)}"
        self.print_timestamped_message(event, msg)

    def on_ace(self, event: GameEvent):
        msg = f"{self.format_player(event.Acer)} has scored an ace for {event.AcingTeam}"
        self.print_timestamped_message(event, msg)

    def on_game_end(self, event: GameEvent):
        msg = f"You {'lose!' if event.Result == GameResult.Lose else 'win!'}"
        self.print_timestamped_message(event, msg)
