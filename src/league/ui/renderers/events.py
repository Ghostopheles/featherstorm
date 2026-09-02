from typing import Optional
from dataclasses import dataclass, field

from league.markup import format_player
from league.models import GameEvent, GameEventType, GameTeam, GameResult, Turret


@dataclass
class EventFeedContext:
    """Player metadata the feed needs to colour names. Filled in on GameStart."""

    teams: dict[str, GameTeam] = field(default_factory=dict)
    champions: dict[str, str] = field(default_factory=dict)

    def clear(self) -> None:
        self.teams.clear()
        self.champions.clear()

    def player(self, name: Optional[str]) -> str:
        if not name:
            return "someone"
        return format_player(name, self.champions.get(name), self.teams.get(name))

    def assists(self, assisters: Optional[list[str]]) -> str:
        if not assisters:
            return ""
        return ", assisted by: " + ", ".join(self.player(a) for a in assisters)


def _slain_by(event: GameEvent, ctx: EventFeedContext, subject: str) -> str:
    verb = "stolen" if event.Stolen else "slain"
    return f"{subject} was {verb} by {ctx.player(event.KillerName)}{ctx.assists(event.Assisters)}"


def describe_event(event: GameEvent, ctx: EventFeedContext) -> Optional[str]:
    match event.EventName:
        case GameEventType.GameStart:
            return "Game has started"
        case GameEventType.MinionsSpawning:
            return "Minions have spawned"
        case GameEventType.FirstBlood:
            return f"First blood claimed by {ctx.player(event.Recipient)}"
        case GameEventType.FirstBrick:
            return f"First brick claimed by {ctx.player(event.KillerName)}"
        case GameEventType.ChampionKill:
            return f"{ctx.player(event.KillerName)} has slain {ctx.player(event.VictimName)}{ctx.assists(event.Assisters)}"
        case GameEventType.TurretKilled:
            turret = Turret.from_str(event.TurretKilled).to_str() if event.TurretKilled else "A turret"
            return f"{turret} was destroyed by {ctx.player(event.KillerName)}{ctx.assists(event.Assisters)}"
        case GameEventType.InhibKilled:
            return f"{event.InhibKilled} was destroyed by {ctx.player(event.KillerName)}{ctx.assists(event.Assisters)}"
        case GameEventType.DragonKill:
            return _slain_by(event, ctx, f"The {event.DragonType} dragon")
        case GameEventType.HeraldKill:
            return _slain_by(event, ctx, "The Rift Herald")
        case GameEventType.BaronKill:
            return _slain_by(event, ctx, "Baron Nashor")
        case GameEventType.HordeKill:
            return _slain_by(event, ctx, "A grub")
        case GameEventType.Multikill:
            return f"{event.get_killstreak_str()} for {ctx.player(event.KillerName)}"
        case GameEventType.Ace:
            return f"{ctx.player(event.Acer)} has scored an ace for {event.AcingTeam}"
        case GameEventType.GameEnd:
            return f"You {'lose!' if event.Result == GameResult.Lose else 'win!'}"
    return None


def format_event_line(event: GameEvent, ctx: EventFeedContext) -> Optional[str]:
    message = describe_event(event, ctx)
    if message is None:
        return None
    return f"{event.get_formatted_timestamp()}: {message}"


FEED_EVENTS: tuple[GameEventType, ...] = (
    GameEventType.GameStart,
    GameEventType.MinionsSpawning,
    GameEventType.FirstBlood,
    GameEventType.FirstBrick,
    GameEventType.ChampionKill,
    GameEventType.TurretKilled,
    GameEventType.InhibKilled,
    GameEventType.DragonKill,
    GameEventType.HeraldKill,
    GameEventType.BaronKill,
    GameEventType.HordeKill,
    GameEventType.Multikill,
    GameEventType.Ace,
    GameEventType.GameEnd,
)
