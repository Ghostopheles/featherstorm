from enum import Enum
from typing import Optional
from pydantic import BaseModel
from dataclasses import dataclass, field, fields

from league.enums import GameEventType, GameResult, GameTeam, Queue, Map, RankedQueueType, RankedTier, RankedDivision


def cast_to_enum(value, enum: Enum):
    if value is None:
        return value

    return enum[value]


def try_cast_to_enum(value, enum: Enum):
    """Cast `value` to `enum`, leaving it untouched when there's no matching member."""
    try:
        return cast_to_enum(value, enum)
    except KeyError:
        return value


@dataclass
class LeagueEntryMiniSeries:
    losses: int
    progress: str
    target: int
    wins: int


@dataclass
class LeagueEntry:
    puuid: str
    queueType: RankedQueueType
    tier: RankedTier
    rank: RankedDivision
    leaguePoints: int
    wins: int
    losses: int
    hotStreak: bool
    veteran: bool
    freshBlood: bool
    inactive: bool

    leagueId: Optional[str] = None
    summonerId: Optional[str] = None
    miniSeries: Optional[LeagueEntryMiniSeries] = None

    def __post_init__(self):
        self.queueType = RankedQueueType(self.queueType)
        self.tier = RankedTier(self.tier.title())
        self.rank = RankedDivision(self.rank)

        if self.miniSeries is not None:
            self.miniSeries = LeagueEntryMiniSeries(**self.miniSeries)


@dataclass
class RiotAccount:
    puuid: str
    gameName: Optional[str] = None
    tagLine: Optional[str] = None


@dataclass
class StatRune:
    id: int
    rawDescription: str


@dataclass
class Rune:
    displayName: str
    id: int
    rawDescription: str
    rawDisplayName: str


@dataclass
class SummonerSpell:
    displayName: str
    rawDescription: str
    rawDisplayName: str


@dataclass
class Scores:
    assists: int
    creepScore: int
    deaths: int
    kills: int
    wardScore: float


@dataclass
class DragonItemImage:
    full: str
    sprite: str
    group: str
    x: int
    y: int
    w: int
    h: int


@dataclass
class DragonItemGold:
    base: int
    purchasable: bool
    total: int
    sell: int


@dataclass
class DragonItem:
    name: str
    description: str
    plaintext: str
    image: DragonItemImage
    gold: DragonItemGold
    tags: list[str]
    maps: dict[str, bool]
    stats: dict[str, float]
    colloq: str = ""
    builds_from: list[str] = field(default_factory=list)
    builds_into: list[str] = field(default_factory=list)
    depth: Optional[int] = None
    consumed: Optional[bool] = None
    consumeOnFull: Optional[bool] = None
    inStore: Optional[bool] = None
    stacks: Optional[int] = None
    specialRecipe: Optional[int] = None
    hideFromAll: bool = False
    requiredChampion: str = ""
    requiredAlly: str = ""
    effect: Optional[dict[str, str]] = None

    def __post_init__(self):
        if isinstance(self.image, dict):
            self.image = DragonItemImage(**self.image)
        if isinstance(self.gold, dict):
            self.gold = DragonItemGold(**self.gold)


@dataclass
class Item:
    canUse: bool
    consumable: bool
    count: int
    displayName: str
    itemID: int
    price: int
    rawDescription: str
    rawDisplayName: str
    slot: int


@dataclass
class Ability:
    displayName: str
    id: str
    rawDescription: str
    rawDisplayName: str
    abilityLevel: Optional[int] = None


@dataclass
class ChampionStats:
    abilityHaste: float
    abilityPower: float
    armor: float
    armorPenetrationFlat: float
    armorPenetrationPercent: float
    attackDamage: float
    attackRange: float
    attackSpeed: float
    bonusArmorPenetrationPercent: float
    bonusMagicPenetrationPercent: float
    critChance: float
    critDamage: float
    currentHealth: float
    healShieldPower: float
    healthRegenRate: float
    lifeSteal: float
    magicLethality: float
    magicPenetrationFlat: float
    magicPenetrationPercent: float
    magicResist: float
    maxHealth: float
    moveSpeed: float
    omnivamp: float
    physicalLethality: float
    physicalVamp: float
    resourceMax: float
    resourceRegenRate: float
    resourceType: str
    resourceValue: float
    spellVamp: float
    tenacity: float


@dataclass
class Abilities:
    Q: Ability
    W: Ability
    E: Ability
    R: Ability
    Passive: Ability

    def __post_init__(self):
        self.Q = Ability(**self.Q)
        self.W = Ability(**self.W)
        self.E = Ability(**self.E)
        self.R = Ability(**self.R)
        self.Passive = Ability(**self.Passive)


@dataclass
class PlayerRunes:
    keystone: Rune
    primaryRuneTree: Rune
    secondaryRuneTree: Rune

    def __post_init__(self):
        self.keystone = Rune(**self.keystone)
        self.primaryRuneTree = Rune(**self.primaryRuneTree)
        self.secondaryRuneTree = Rune(**self.secondaryRuneTree)


@dataclass
class FullRunes:
    generalRunes: list[Rune]
    keystone: Rune
    primaryRuneTree: Rune
    secondaryRuneTree: Rune
    statRunes: list[StatRune]

    def __post_init__(self):
        self.generalRunes = [Rune(**r) for r in self.generalRunes]
        self.keystone = Rune(**self.keystone)
        self.primaryRuneTree = Rune(**self.primaryRuneTree)
        self.secondaryRuneTree = Rune(**self.secondaryRuneTree)
        self.statRunes = [StatRune(**r) for r in self.statRunes]


@dataclass
class SummonerSpells:
    summonerSpellOne: SummonerSpell
    summonerSpellTwo: SummonerSpell

    def __post_init__(self):
        self.summonerSpellOne = SummonerSpell(**self.summonerSpellOne)
        self.summonerSpellTwo = SummonerSpell(**self.summonerSpellTwo)


@dataclass
class ActivePlayer:
    abilities: Abilities
    championStats: ChampionStats
    currentGold: float
    fullRunes: Optional[FullRunes]
    level: int
    riotId: str
    riotIdGameName: str
    riotIdTagLine: str
    summonerName: str
    teamRelativeColors: bool

    def __post_init__(self):
        self.abilities = Abilities(**self.abilities)
        self.championStats = ChampionStats(**self.championStats)
        self.fullRunes = FullRunes(**self.fullRunes) if self.fullRunes else None


@dataclass
class Player:
    championName: str
    isBot: bool
    isDead: bool
    items: list[Item]
    level: int
    position: str
    rawChampionName: str
    rawSkinName: str
    respawnTimer: float
    riotId: str
    riotIdGameName: str
    riotIdTagLine: str
    runes: Optional[PlayerRunes]
    scores: Scores
    skinID: int
    skinName: str
    summonerName: str
    summonerSpells: SummonerSpells
    team: GameTeam
    screenPositionBottom: Optional[str] = None
    screenPositionCenter: Optional[str] = None

    def __post_init__(self):
        self.items = [Item(**i) for i in self.items]
        self.runes = PlayerRunes(**self.runes) if self.runes else None
        self.scores = Scores(**self.scores)
        self.summonerSpells = SummonerSpells(**self.summonerSpells)
        self.team = GameTeam(self.team)


@dataclass
class GameData:
    gameMode: str
    gameTime: float
    mapName: str
    mapNumber: int
    mapTerrain: str


@dataclass
class GameEvent:
    EventID: int
    EventName: GameEventType
    EventTime: float
    KillerName: Optional[str] = None
    VictimName: Optional[str] = None
    Assisters: Optional[list[str]] = None
    TurretKilled: Optional[str] = None
    InhibKilled: Optional[str] = None
    DragonType: Optional[str] = None
    Stolen: Optional[bool] = None
    KillStreak: Optional[int] = None
    Acer: Optional[str] = None
    AcingTeam: Optional[GameTeam] = None
    Recipient: Optional[str] = None
    Result: Optional[GameResult] = None

    def __post_init__(self):
        # unknown members are left as raw strings so a new Riot event type can't kill the poll loop
        self.EventName = try_cast_to_enum(self.EventName, GameEventType)
        self.AcingTeam = try_cast_to_enum(self.AcingTeam, GameTeam)
        self.Result = try_cast_to_enum(self.Result, GameResult)

    @classmethod
    def from_dict(cls, raw: dict) -> "GameEvent":
        """Build from a raw API payload, keeping fields we don't model as plain attributes."""
        known = {f.name for f in fields(cls)}
        event = cls(**{k: v for k, v in raw.items() if k in known})
        for key, value in raw.items():
            if key not in known:
                setattr(event, key, value)
        return event

    def get_formatted_timestamp(self) -> str:
        minutes, secs = divmod(self.EventTime, 60)
        return f"{int(minutes):02}:{int(secs):02}"

    def get_formatted_assists(self) -> str:
        if self.Assisters is None or len(self.Assisters) == 0:
            return ""

        return ", assisted by: " + ", ".join(self.Assisters)

    def get_killstreak_str(self) -> str:
        if self.KillStreak is None:
            return ""

        match self.KillStreak:
            case 2:
                return "Double Kill"
            case 3:
                return "Triple Kill"
            case 4:
                return "Quadra Kill"
            case 5:
                return "Pentakill"


@dataclass
class AllGameData:
    activePlayer: Optional[ActivePlayer]
    allPlayers: list[Player]
    events: list[GameEvent]
    gameData: GameData

    def __post_init__(self):
        self.activePlayer = None if "error" in self.activePlayer else ActivePlayer(**self.activePlayer)
        self.allPlayers = [Player(**p) for p in self.allPlayers]
        self.events = [GameEvent.from_dict(e) for e in self.events["Events"]]
        self.gameData = GameData(**self.gameData)


class Lane(Enum):
    Bottom = 0
    Middle = 1
    Top = 2


class TurretTier(Enum):
    Nexus = 0
    Inhibitor = 1
    Inner = 2
    Outer = 3
    ARAM_Outer = 4
    ARAM_Inner = 5


@dataclass
class Turret:
    Team: GameTeam
    Lane: Lane
    Tier: TurretTier

    def to_str(self) -> str:
        return f"{self.Team.title()} {self.Lane.name.lower()} lane {self.Tier.name.lower()} turret"

    @classmethod
    def from_str(cls, name: str):
        name_split = name.split("_")
        if len(name_split) < 4:
            print(name)
            return cls(GameTeam.SPECTATOR, Lane.Middle, TurretTier.Outer)

        team = name_split[1].replace("T", "").upper()
        team = GameTeam[team]

        lane = int(name_split[2].replace("L", ""))
        lane = Lane(lane)

        tier = int(name_split[3].replace("P", ""))
        tier = TurretTier(tier)

        return cls(team, lane, tier)


class ChampionMastery(BaseModel):
    championId: int
    championName: Optional[str] = None
    championLevel: int
    championPoints: int
    championPointsUntilNextLevel: int

    @classmethod
    def with_champion_name(cls, data: dict, champion_name: str):
        data.setdefault("championName", champion_name)
        return cls.model_validate(data)


type TopChampions = list[ChampionMastery]


class MatchMetadata(BaseModel):
    dataVersion: str
    matchId: str
    participants: list[str]


class ChallengesSummary(BaseModel):
    kda: Optional[float] = None
    killParticipation: Optional[float] = None
    teamDamagePercentage: Optional[float] = None
    damagePerMinute: Optional[float] = None
    goldPerMinute: Optional[float] = None
    soloKills: Optional[int] = None
    takedowns: Optional[int] = None
    skillshotsHit: Optional[int] = None
    skillshotsDodged: Optional[int] = None
    visionScorePerMinute: Optional[float] = None
    legendaryCount: Optional[int] = None
    controlWardsPlaced: Optional[int] = None


class ParticipantSummary(BaseModel):
    # Identity
    puuid: str
    participantId: int
    riotIdGameName: str
    riotIdTagline: str
    teamId: int
    # Champion & role
    championName: str
    champLevel: int
    teamPosition: str
    # Outcome
    win: bool
    gameEndedInSurrender: bool
    # Core combat
    kills: int
    deaths: int
    assists: int
    totalMinionsKilled: int
    neutralMinionsKilled: int
    # Damage
    totalDamageDealtToChampions: int
    totalDamageTaken: int
    damageSelfMitigated: int
    damageDealtToBuildings: int
    # Vision
    visionScore: int
    wardsPlaced: int
    wardsKilled: int
    detectorWardsPlaced: int
    # Gold
    goldEarned: int
    # Items
    item0: int
    item1: int
    item2: int
    item3: int
    item4: int
    item5: int
    item6: int
    # Multi-kills
    doubleKills: int
    tripleKills: int
    quadraKills: int
    pentaKills: int
    # Objectives
    turretKills: int
    inhibitorKills: int
    dragonKills: int
    baronKills: int
    firstBloodKill: bool
    # Survival & CC
    totalTimeSpentDead: int
    longestTimeSpentLiving: int
    timeCCingOthers: int
    # Healing & shielding
    totalHeal: int
    totalHealsOnTeammates: int
    totalDamageShieldedOnTeammates: int
    # Summoner spells
    summoner1Id: int
    summoner2Id: int
    # Challenges
    challenges: Optional[ChallengesSummary] = None


class TeamSummary(BaseModel):
    teamId: int
    win: bool
    bans: list[dict]
    objectives: dict


class MatchInfo(BaseModel):
    gameDuration: int
    gameMode: str
    gameVersion: str
    mapId: Map
    queueId: Queue
    platformId: str
    participants: list[ParticipantSummary]
    teams: list[TeamSummary]


class Match(BaseModel):
    metadata: MatchMetadata
    info: MatchInfo


# Platform status DTOs


class ContentDto(BaseModel):
    locale: str
    content: str


class UpdateDto(BaseModel):
    id: int
    author: str
    publish: bool
    publish_locations: list[str]
    translations: list[ContentDto]
    created_at: str
    updated_at: str


class StatusDto(BaseModel):
    id: int
    maintenance_status: Optional[str] = None  # scheduled | in_progress | complete
    incident_severity: Optional[str] = None  # info | warning | critical
    titles: list[ContentDto]
    updates: list[UpdateDto]
    created_at: str
    archive_at: Optional[str] = None
    updated_at: str
    platforms: list[str]


class PlatformDataDto(BaseModel):
    id: str
    name: str
    locales: list[str]
    maintenances: list[StatusDto]
    incidents: list[StatusDto]


# Timeline DTOs


class PositionDto(BaseModel):
    x: int
    y: int


class ParticipantFrameDto(BaseModel):
    participantId: int
    totalGold: int
    level: int
    xp: int
    minionsKilled: int
    jungleMinionsKilled: int
    position: Optional[PositionDto] = None


class TimelineEvent(BaseModel):
    type: str
    timestamp: int
    # Participant / killer / victim
    participantId: Optional[int] = None
    killerId: Optional[int] = None
    victimId: Optional[int] = None
    creatorId: Optional[int] = None
    assistingParticipantIds: Optional[list[int]] = None
    # Items
    itemId: Optional[int] = None
    afterId: Optional[int] = None
    beforeId: Optional[int] = None
    goldGain: Optional[int] = None
    # Level / skill
    level: Optional[int] = None
    skillSlot: Optional[int] = None
    levelUpType: Optional[str] = None
    # Wards
    wardType: Optional[str] = None
    # Buildings
    buildingType: Optional[str] = None
    laneType: Optional[str] = None
    towerType: Optional[str] = None
    teamId: Optional[int] = None
    # Monsters
    monsterType: Optional[str] = None
    monsterSubType: Optional[str] = None
    killerTeamId: Optional[int] = None
    # Kill details
    killType: Optional[str] = None
    killStreakLength: Optional[int] = None
    multiKillLength: Optional[int] = None
    bounty: Optional[int] = None
    shutdownBounty: Optional[int] = None
    # Shared position
    position: Optional[PositionDto] = None
    # Game end
    winningTeam: Optional[int] = None


class TimelineFrame(BaseModel):
    timestamp: int
    participantFrames: dict[str, ParticipantFrameDto]
    events: list[TimelineEvent]


class TimelineParticipant(BaseModel):
    participantId: int
    puuid: str


class TimelineInfo(BaseModel):
    frameInterval: int
    gameId: int
    frames: list[TimelineFrame]
    participants: list[TimelineParticipant]


class MatchTimeline(BaseModel):
    metadata: MatchMetadata
    info: TimelineInfo


class StatComparison(BaseModel):
    """Comparison of a single stat for the queried player against match averages."""

    stat_name: str
    player_value: float
    team_avg: float
    enemy_avg: float
    match_avg: float
    player_rank: int  # 1 = best among all 10 participants
    vs_avg_pct: float  # player_value / match_avg * 100 (100 = average)
    higher_is_better: bool


class MatchPerformanceReport(BaseModel):
    """Per-stat performance breakdown for a player in a single match."""

    matchId: str
    gameDurationMinutes: float
    champion: str
    role: str
    win: bool
    stats: list[StatComparison]


class PlayerMatch(BaseModel):
    """A match result structured around a specific queried player."""

    matchId: str
    gameDuration: int
    gameMode: str
    gameVersion: str
    mapId: Map
    queueId: Queue
    teams: list[TeamSummary]
    player: ParticipantSummary
    teammates: list[ParticipantSummary]
    enemies: list[ParticipantSummary]

    @classmethod
    def from_match(cls, match: Match, puuid: str) -> "PlayerMatch":
        participants = match.info.participants
        player = next(p for p in participants if p.puuid == puuid)
        teammates = [p for p in participants if p.teamId == player.teamId and p.puuid != puuid]
        enemies = [p for p in participants if p.teamId != player.teamId]
        return cls(
            matchId=match.metadata.matchId,
            gameDuration=match.info.gameDuration,
            gameMode=match.info.gameMode,
            gameVersion=match.info.gameVersion,
            mapId=match.info.mapId,
            queueId=match.info.queueId,
            teams=match.info.teams,
            player=player,
            teammates=teammates,
            enemies=enemies,
        )


@dataclass
class BannedChampion:
    pickTurn: int
    championId: int
    teamId: int


@dataclass
class Observer:
    encryptionKey: str


@dataclass
class GameCustomizationObject:
    category: str
    content: str


@dataclass
class Perks:
    perkIds: list[int]
    perkStyle: int
    perkSubStyle: int


@dataclass
class CurrentGameParticipant:
    championId: int
    perks: Perks
    profileIconId: int
    bot: bool
    teamId: int
    puuid: str
    spell1Id: int
    spell2Id: int
    gameCustomizationObjects: list[GameCustomizationObject]

    def __post_init__(self):
        self.perks = Perks(**self.perks)
        self.gameCustomizationObjects = [GameCustomizationObject(**obj) for obj in self.gameCustomizationObjects]


@dataclass
class CurrentGameInfo:
    gameId: int
    gameType: str
    gameStartTime: int
    mapId: int
    gameLength: int
    platformId: str
    gameMode: str
    bannedChampions: list[BannedChampion]
    gameQueueConfigId: Queue
    observers: Observer
    participants: list[CurrentGameParticipant]

    def __post_init__(self):
        self.bannedChampions = [BannedChampion(**champ) for champ in self.bannedChampions]
        self.gameQueueConfigId = Queue(self.gameQueueConfigId)
        self.observers = Observer(**self.observers)
        self.participants = [CurrentGameParticipant(**player) for player in self.participants]
