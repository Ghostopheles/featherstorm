"""View models for the match history UI.

Widgets never touch `LCUMatch` / `PlayerMatch` directly — everything they render
is derived here, so formatting lives in one place and the pages stay free of
backend imports beyond these dataclasses.
"""

from typing import Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from league.enums import Queue
from league.enums.queues import QUEUE_DESCRIPTION
from league.lcu.models import LCUMatch
from league.models import Match, PlayerMatch, ParticipantSummary

BLUE_TEAM_ID = 100

_ITEM_SLOTS = 7


def _queue_name(queue: Queue) -> str:
    return QUEUE_DESCRIPTION.get(queue) or queue.name


def _parse_created(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except AttributeError, ValueError:
        return None


def _relative_time(created: Optional[datetime]) -> str:
    if created is None:
        return "—"

    delta = datetime.now(timezone.utc) - created
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    if seconds < 604800:
        return f"{seconds // 86400}d ago"
    return created.astimezone().strftime("%b %d")


def _duration_text(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


@dataclass(slots=True)
class ScoreRow:
    """One participant line in the expanded scoreboard."""

    display_name: str
    team_id: int
    kills: int
    deaths: int
    assists: int
    gold: int
    is_you: bool = False
    champion_id: Optional[int] = None
    champion_name: Optional[str] = None

    @property
    def is_blue(self) -> bool:
        return self.team_id == BLUE_TEAM_ID


@dataclass(slots=True)
class MatchSummary:
    """A single row in the match list — everything the LCU list endpoint gives us.

    The LCU history endpoint only returns the current summoner's participant, so
    this is strictly "your" performance. The full lobby arrives with `MatchDetail`.
    """

    game_id: int
    platform_id: str
    puuid: str
    participant_id: int
    champion_id: int
    queue: Queue
    win: bool
    kills: int
    deaths: int
    assists: int
    cs: int
    vision_score: int
    gold: int
    damage_dealt: int
    damage_taken: int
    duration_s: int
    surrendered: bool
    items: list[int] = field(default_factory=list)
    created: Optional[datetime] = None

    @classmethod
    def from_lcu(cls, match: LCUMatch) -> "MatchSummary":
        participant = match.participants[0]
        stats = participant.stats
        identity = match.participantIdentities[0]

        return cls(
            game_id=match.gameId,
            platform_id=match.platformId,
            puuid=identity.player.puuid,
            participant_id=identity.participantId,
            champion_id=participant.championId,
            queue=match.queueId,
            win=stats.win,
            kills=stats.kills,
            deaths=stats.deaths,
            assists=stats.assists,
            cs=stats.totalMinionsKilled + stats.neutralMinionsKilled,
            vision_score=stats.visionScore,
            gold=stats.goldEarned,
            damage_dealt=stats.totalDamageDealtToChampions,
            damage_taken=stats.totalDamageTaken,
            duration_s=match.gameDuration,
            surrendered=stats.gameEndedInSurrender,
            items=[getattr(stats, f"item{i}") for i in range(_ITEM_SLOTS)],
            created=_parse_created(match.gameCreationDate),
        )

    @property
    def match_id(self) -> str:
        """Riot MATCH-V5 id, assembled from the LCU's platform + game id."""
        return f"{self.platform_id}_{self.game_id}"

    @property
    def result_text(self) -> str:
        return "Victory" if self.win else "Defeat"

    @property
    def kda_text(self) -> str:
        return f"{self.kills} / {self.deaths} / {self.assists}"

    @property
    def kda_ratio(self) -> float:
        return (self.kills + self.assists) / max(self.deaths, 1)

    @property
    def kda_ratio_text(self) -> str:
        if self.deaths == 0:
            return "Perfect"
        return f"{self.kda_ratio:.2f} KDA"

    @property
    def cs_per_min(self) -> float:
        minutes = self.duration_s / 60
        return self.cs / minutes if minutes else 0.0

    @property
    def cs_text(self) -> str:
        return f"{self.cs} CS"

    @property
    def cs_detail_text(self) -> str:
        return f"{self.cs_per_min:.1f}/min"

    @property
    def duration_text(self) -> str:
        return _duration_text(self.duration_s)

    @property
    def relative_time(self) -> str:
        return _relative_time(self.created)

    @property
    def queue_name(self) -> str:
        return _queue_name(self.queue)

    @property
    def meta_text(self) -> str:
        parts = [self.queue_name, self.duration_text, self.relative_time]
        if self.surrendered:
            parts.append("surrendered")
        return "  ·  ".join(parts)


@dataclass(slots=True)
class MatchDetail:
    """Contents of an expanded match row.

    `rows` is the full 10-player scoreboard and is only populated when the Riot
    API answered — the LCU list endpoint can't supply the other nine players.
    """

    game_id: int
    damage_dealt: int
    damage_taken: int
    gold: int
    items: list[int]
    kill_participation: Optional[float] = None
    rows: Optional[list[ScoreRow]] = None
    note: Optional[str] = None

    @classmethod
    def from_summary(cls, summary: MatchSummary, note: Optional[str] = None) -> "MatchDetail":
        """Degraded path — no Riot API key, or the request failed."""
        return cls(
            game_id=summary.game_id,
            damage_dealt=summary.damage_dealt,
            damage_taken=summary.damage_taken,
            gold=summary.gold,
            items=list(summary.items),
            kill_participation=None,
            rows=None,
            note=note,
        )

    @classmethod
    def from_match(cls, summary: MatchSummary, match: Match) -> "MatchDetail":
        """Full path — a MATCH-V5 payload narrowed to the summary's player."""
        puuid = _riot_puuid_for(match, summary.participant_id)
        if puuid is None:
            raise ValueError(f"participant {summary.participant_id} not present in {match.metadata.matchId}")
        return cls.from_player_match(summary.game_id, PlayerMatch.from_match(match, puuid))

    @classmethod
    def from_player_match(cls, game_id: int, match: PlayerMatch) -> "MatchDetail":
        player = match.player
        participants = [player, *match.teammates, *match.enemies]

        challenges = player.challenges
        kill_participation = challenges.killParticipation if challenges is not None else None

        return cls(
            game_id=game_id,
            damage_dealt=player.totalDamageDealtToChampions,
            damage_taken=player.totalDamageTaken,
            gold=player.goldEarned,
            items=[getattr(player, f"item{i}") for i in range(_ITEM_SLOTS)],
            kill_participation=kill_participation,
            rows=_score_rows(participants, player.puuid),
        )

    @property
    def kill_participation_text(self) -> str:
        if self.kill_participation is None:
            return "—"
        return f"{self.kill_participation * 100:.0f}%"


def _riot_puuid_for(match: Match, participant_id: int) -> Optional[str]:
    """Find the queried player's real puuid inside a MATCH-V5 payload.

    The LCU reports an anonymized per-match UUID where Riot reports the account's
    78-character puuid, so the two never compare equal — `participantId` is the
    only field that lines the two sources up.
    """
    for participant in match.info.participants:
        if participant.participantId == participant_id:
            return participant.puuid
    return None


def _score_rows(participants: list[ParticipantSummary], puuid: str) -> list[ScoreRow]:
    rows = [
        ScoreRow(
            display_name=p.riotIdGameName or p.championName,
            team_id=p.teamId,
            kills=p.kills,
            deaths=p.deaths,
            assists=p.assists,
            gold=p.goldEarned,
            is_you=p.puuid == puuid,
            champion_name=p.championName,
        )
        for p in participants
    ]
    # blue team first, then in the order Riot reports them
    rows.sort(key=lambda r: (not r.is_blue,))
    return rows
