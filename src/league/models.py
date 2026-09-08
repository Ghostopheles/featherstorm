import logging

from enum import Enum
from typing import Optional
from pydantic import Field, BaseModel, ConfigDict
from dataclasses import dataclass, field, fields

from league.enums import GameEventType, GameResult, GameTeam, Queue, Map, RankedQueueType, RankedTier, RankedDivision

log = logging.getLogger(__name__)


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
            log.warning(f"Unrecognised turret name '{name}'")
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
    """MATCH-V5 `participant.challenges`.

    Riot adds, renames and retires challenge keys every patch and only sends the ones
    a game mode produced, so every field is optional and unknown keys are kept verbatim —
    `model_dump()` round-trips the whole payload for storage.
    """

    model_config = ConfigDict(extra="allow")

    kda: Optional[float] = None
    killParticipation: Optional[float] = None
    teamDamagePercentage: Optional[float] = None
    damageTakenOnTeamPercentage: Optional[float] = None
    damagePerMinute: Optional[float] = None
    goldPerMinute: Optional[float] = None
    visionScorePerMinute: Optional[float] = None
    visionScoreAdvantageLaneOpponent: Optional[float] = None
    gameLength: Optional[float] = None
    bountyGold: Optional[float] = None

    soloKills: Optional[float] = None
    takedowns: Optional[float] = None
    multikills: Optional[float] = None
    killingSprees: Optional[float] = None
    skillshotsHit: Optional[float] = None
    skillshotsDodged: Optional[float] = None
    abilityUses: Optional[float] = None
    legendaryCount: Optional[float] = None
    controlWardsPlaced: Optional[float] = None
    stealthWardsPlaced: Optional[float] = None
    wardTakedowns: Optional[float] = None
    turretPlatesTaken: Optional[float] = None
    turretTakedowns: Optional[float] = None
    dragonTakedowns: Optional[float] = None
    baronTakedowns: Optional[float] = None
    riftHeraldTakedowns: Optional[float] = None
    epicMonsterSteals: Optional[float] = None
    laneMinionsFirst10Minutes: Optional[float] = None
    jungleCsBefore10Minutes: Optional[float] = None
    maxCsAdvantageOnLaneOpponent: Optional[float] = None
    maxLevelLeadLaneOpponent: Optional[float] = None
    laningPhaseGoldExpAdvantage: Optional[float] = None
    earlyLaningPhaseGoldExpAdvantage: Optional[float] = None
    effectiveHealAndShielding: Optional[float] = None
    enemyChampionImmobilizations: Optional[float] = None
    saveAllyFromDeath: Optional[float] = None
    perfectGame: Optional[float] = None


class PerkStats(BaseModel):
    defense: int = 0
    flex: int = 0
    offense: int = 0


class PerkSelection(BaseModel):
    perk: int
    var1: int = 0
    var2: int = 0
    var3: int = 0


class PerkStyle(BaseModel):
    description: str
    style: int
    selections: list[PerkSelection] = Field(default_factory=list)


class ParticipantPerks(BaseModel):
    statPerks: PerkStats = Field(default_factory=PerkStats)
    styles: list[PerkStyle] = Field(default_factory=list)

    @property
    def keystone(self) -> Optional[int]:
        primary = next((s for s in self.styles if s.description == "primaryStyle"), None)
        return primary.selections[0].perk if primary and primary.selections else None


class ParticipantSummary(BaseModel):
    """One player's line in a MATCH-V5 match.

    Only fields Riot has always sent are required; anything mode-specific or added in a
    later patch is optional so historical matches still validate.
    """

    # Identity
    puuid: str
    participantId: int
    teamId: int
    riotIdGameName: str = ""
    riotIdTagline: str = ""
    summonerName: str = ""
    summonerId: Optional[str] = None
    summonerLevel: Optional[int] = None
    profileIcon: Optional[int] = None
    # Arena / subteam
    playerSubteamId: Optional[int] = None
    subteamPlacement: Optional[int] = None
    placement: Optional[int] = None
    # Champion & role
    championId: Optional[int] = None
    championName: str
    championTransform: Optional[int] = None
    champLevel: int
    champExperience: Optional[int] = None
    teamPosition: str = ""
    individualPosition: Optional[str] = None
    lane: Optional[str] = None
    role: Optional[str] = None
    positionAssignedByMatchmaking: Optional[str] = None
    selectedRolePreferences: Optional[str] = None
    # Outcome
    win: bool
    gameEndedInSurrender: bool = False
    gameEndedInEarlySurrender: bool = False
    teamEarlySurrendered: bool = False
    eligibleForProgression: Optional[bool] = None
    wasAfk: Optional[bool] = None
    timePlayed: Optional[int] = None
    # Core combat
    kills: int
    deaths: int
    assists: int
    killingSprees: Optional[int] = None
    largestKillingSpree: Optional[int] = None
    largestMultiKill: Optional[int] = None
    largestCriticalStrike: Optional[int] = None
    doubleKills: int = 0
    tripleKills: int = 0
    quadraKills: int = 0
    pentaKills: int = 0
    # Minions
    totalMinionsKilled: int
    neutralMinionsKilled: int
    totalAllyJungleMinionsKilled: Optional[int] = None
    totalEnemyJungleMinionsKilled: Optional[int] = None
    # Damage dealt
    totalDamageDealt: Optional[int] = None
    totalDamageDealtToChampions: int
    physicalDamageDealt: Optional[int] = None
    physicalDamageDealtToChampions: Optional[int] = None
    magicDamageDealt: Optional[int] = None
    magicDamageDealtToChampions: Optional[int] = None
    trueDamageDealt: Optional[int] = None
    trueDamageDealtToChampions: Optional[int] = None
    damageDealtToBuildings: int = 0
    damageDealtToTurrets: Optional[int] = None
    damageDealtToObjectives: Optional[int] = None
    damageDealtToEpicMonsters: Optional[int] = None
    # Damage taken & mitigation
    totalDamageTaken: int
    physicalDamageTaken: Optional[int] = None
    magicDamageTaken: Optional[int] = None
    trueDamageTaken: Optional[int] = None
    damageSelfMitigated: int = 0
    # Healing & shielding
    totalHeal: int = 0
    totalHealsOnTeammates: int = 0
    totalUnitsHealed: Optional[int] = None
    totalDamageShieldedOnTeammates: int = 0
    # Crowd control
    timeCCingOthers: int = 0
    totalTimeCCDealt: Optional[int] = None
    # Survival
    totalTimeSpentDead: int = 0
    longestTimeSpentLiving: int = 0
    # Vision
    visionScore: int
    wardsPlaced: int
    wardsKilled: int
    detectorWardsPlaced: int = 0
    visionWardsBoughtInGame: Optional[int] = None
    # Gold
    goldEarned: int
    goldSpent: Optional[int] = None
    # Items
    item0: int
    item1: int
    item2: int
    item3: int
    item4: int
    item5: int
    item6: int
    itemsPurchased: Optional[int] = None
    consumablesPurchased: Optional[int] = None
    roleBoundItem: Optional[int] = None
    # Objectives
    turretKills: int = 0
    turretTakedowns: Optional[int] = None
    turretsLost: Optional[int] = None
    inhibitorKills: int = 0
    inhibitorTakedowns: Optional[int] = None
    inhibitorsLost: Optional[int] = None
    nexusKills: Optional[int] = None
    nexusTakedowns: Optional[int] = None
    nexusLost: Optional[int] = None
    dragonKills: int = 0
    baronKills: int = 0
    objectivesStolen: Optional[int] = None
    objectivesStolenAssists: Optional[int] = None
    firstBloodKill: bool = False
    firstBloodAssist: bool = False
    firstTowerKill: bool = False
    firstTowerAssist: bool = False
    # Spells
    summoner1Id: int
    summoner2Id: int
    summoner1Casts: Optional[int] = None
    summoner2Casts: Optional[int] = None
    spell1Casts: Optional[int] = None
    spell2Casts: Optional[int] = None
    spell3Casts: Optional[int] = None
    spell4Casts: Optional[int] = None
    # Arena augments
    playerAugment1: Optional[int] = None
    playerAugment2: Optional[int] = None
    playerAugment3: Optional[int] = None
    playerAugment4: Optional[int] = None
    playerAugment5: Optional[int] = None
    playerAugment6: Optional[int] = None
    # Pings
    allInPings: int = 0
    assistMePings: int = 0
    basicPings: int = 0
    commandPings: int = 0
    dangerPings: int = 0
    enemyMissingPings: int = 0
    enemyVisionPings: int = 0
    getBackPings: int = 0
    holdPings: int = 0
    needVisionPings: int = 0
    onMyWayPings: int = 0
    pushPings: int = 0
    retreatPings: int = 0
    visionClearedPings: int = 0
    # Nested
    perks: Optional[ParticipantPerks] = None
    challenges: Optional[ChallengesSummary] = None

    @property
    def cs(self) -> int:
        return self.totalMinionsKilled + self.neutralMinionsKilled


class TeamBan(BaseModel):
    championId: int
    pickTurn: int


class Objective(BaseModel):
    first: bool = False
    kills: int = 0


class TeamObjectives(BaseModel):
    """Per-objective first-blood/kill counts. Riot adds new objectives (`horde`, `atakhan`)
    mid-season, so unknown keys are preserved rather than dropped."""

    model_config = ConfigDict(extra="allow")

    champion: Optional[Objective] = None
    tower: Optional[Objective] = None
    inhibitor: Optional[Objective] = None
    baron: Optional[Objective] = None
    dragon: Optional[Objective] = None
    riftHerald: Optional[Objective] = None
    horde: Optional[Objective] = None
    atakhan: Optional[Objective] = None


class TeamSummary(BaseModel):
    teamId: int
    win: bool
    bans: list[TeamBan] = Field(default_factory=list)
    objectives: TeamObjectives = Field(default_factory=TeamObjectives)


class MatchInfo(BaseModel):
    gameDuration: int
    gameMode: str
    gameVersion: str
    mapId: Map
    queueId: Queue
    platformId: str
    participants: list[ParticipantSummary]
    teams: list[TeamSummary]

    gameId: Optional[int] = None
    gameName: Optional[str] = None
    gameType: Optional[str] = None
    gameCreation: Optional[int] = None
    gameStartTimestamp: Optional[int] = None
    gameEndTimestamp: Optional[int] = None
    endOfGameResult: Optional[str] = None
    tournamentCode: Optional[str] = None

    @property
    def remake(self) -> bool:
        """Riot marks aborted games with a non-`GameComplete` result; older matches have
        no field at all, where a sub-5-minute duration is the only signal."""
        if self.endOfGameResult is not None:
            return self.endOfGameResult != "GameComplete"
        return self.gameDuration < 300


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
