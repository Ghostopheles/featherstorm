from typing import Optional
from enum import StrEnum, Enum
from dataclasses import dataclass, field

from league.enums import Queue, Map


@dataclass
class MyChampSelection:
    assignedPosition: str
    cellId: int
    championId: int
    championPickIntent: int
    gameName: str
    internalName: str
    isAutofilled: bool
    isHumanoid: bool
    nameVisibilityType: str
    obfuscatedPuuid: str
    obfuscatedSummonerId: int
    pickMode: int
    pickTurn: int
    playerAlias: str
    playerType: str
    puuid: str
    selectedSkinId: int
    spell1Id: int
    spell2Id: int
    summonerId: int
    tagLine: str
    team: int
    wardSkinId: int


@dataclass
class SummonerRerollPoints:
    currentPoints: int
    maxRolls: int
    numberOfRolls: int
    pointsCostToRoll: int
    pointsToReroll: int


@dataclass
class Summoner:
    accountId: int
    displayName: str
    gameName: str
    internalName: str
    nameChangeFlag: bool
    percentCompleteForNextLevel: int
    privacy: str
    profileIconId: int
    puuid: str
    rerollPoints: SummonerRerollPoints
    summonerId: int
    summonerLevel: int
    tagLine: str
    unnamed: bool
    xpSinceLastLevel: int
    xpUntilNextLevel: int

    def __post_init__(self):
        self.rerollPoints = SummonerRerollPoints(**self.rerollPoints)


class LobbyGameMode(StrEnum):
    Practice = "PRACTICETOOL"
    Normal = "CLASSIC"


class LobbyType(Enum):
    Normal = 1
    Custom = 2


class LCURole(StrEnum):
    DUO = "DUO"
    DUOCARRY = "DUO_CARRY"
    DUOSUPPORT = "DUO_SUPPORT"
    SOLO = "SOLO"
    SUPPORT = "SUPPORT"
    CARRY = "CARRY"
    UNKNOWN = "NONE"


class LCULane(StrEnum):
    TOP = "TOP"
    MID_LANE = "MIDDLE"
    BOT_LANE = "BOTTOM"
    JUNGLE = "JUNGLE"
    NONE = "NONE"


class LCUPosition(StrEnum):
    Top = "Top"
    Middle = "Middle"
    Jungle = "Jungle"
    Bottom = "Bottom"
    Support = "Support"
    Apex = "Apex"
    Unknown = "N/A"


PlayerRoleMapping = {
    (LCULane.TOP, LCURole.SOLO): LCUPosition.Top,
    (LCULane.MID_LANE, LCURole.SOLO): LCUPosition.Middle,
    (LCULane.JUNGLE, LCURole.UNKNOWN): LCUPosition.Jungle,
    (LCULane.BOT_LANE, LCURole.DUOCARRY): LCUPosition.Bottom,
    (LCULane.BOT_LANE, LCURole.DUOSUPPORT): LCUPosition.Support,
    (LCULane.BOT_LANE, LCURole.SUPPORT): LCUPosition.Support,
    (LCULane.NONE, LCURole.DUO): LCUPosition.Unknown,
    (LCULane.NONE, LCURole.SUPPORT): LCUPosition.Unknown,
}


@dataclass
class MatchPlayer:
    accountId: int
    currentAccountId: int
    currentPlatformId: str
    gameName: str
    matchHistoryUri: str
    platformId: str
    profileIcon: int
    puuid: str
    summonerId: int
    summonerName: str
    tagLine: str


@dataclass
class ParticipantIdentity:
    participantId: int
    player: MatchPlayer

    def __post_init__(self):
        self.player = MatchPlayer(**self.player)


@dataclass
class ParticipantStats:
    assists: int
    causedEarlySurrender: bool
    champLevel: int
    combatPlayerScore: int
    damageDealtToObjectives: int
    damageDealtToTurrets: int
    damageSelfMitigated: int
    deaths: int
    doubleKills: int
    earlySurrenderAccomplice: bool
    firstBloodAssist: bool
    firstBloodKill: bool
    firstInhibitorAssist: bool
    firstInhibitorKill: bool
    firstTowerAssist: bool
    firstTowerKill: bool
    gameEndedInEarlySurrender: bool
    gameEndedInSurrender: bool
    gameEndedInIGNBSurrender: bool
    causedGameEndFromIGNBSurrender: bool
    wasSevereTransgressor: bool
    goldEarned: int
    goldSpent: int
    inhibitorKills: int
    item0: int
    item1: int
    item2: int
    item3: int
    item4: int
    item5: int
    item6: int
    killingSprees: int
    kills: int
    largestCriticalStrike: int
    largestKillingSpree: int
    largestMultiKill: int
    longestTimeSpentLiving: int
    magicDamageDealt: int
    magicDamageDealtToChampions: int
    magicalDamageTaken: int
    neutralMinionsKilled: int
    neutralMinionsKilledEnemyJungle: int
    neutralMinionsKilledTeamJungle: int
    objectivePlayerScore: int
    participantId: int
    pentaKills: int
    perk0: int
    perk0Var1: int
    perk0Var2: int
    perk0Var3: int
    perk1: int
    perk1Var1: int
    perk1Var2: int
    perk1Var3: int
    perk2: int
    perk2Var1: int
    perk2Var2: int
    perk2Var3: int
    perk3: int
    perk3Var1: int
    perk3Var2: int
    perk3Var3: int
    perk4: int
    perk4Var1: int
    perk4Var2: int
    perk4Var3: int
    perk5: int
    perk5Var1: int
    perk5Var2: int
    perk5Var3: int
    perkPrimaryStyle: int
    perkSubStyle: int
    physicalDamageDealt: int
    physicalDamageDealtToChampions: int
    physicalDamageTaken: int
    playerAugment1: int
    playerAugment2: int
    playerAugment3: int
    playerAugment4: int
    playerAugment5: int
    playerAugment6: int
    playerScore0: int
    playerScore1: int
    playerScore2: int
    playerScore3: int
    playerScore4: int
    playerScore5: int
    playerScore6: int
    playerScore7: int
    playerScore8: int
    playerScore9: int
    playerSubteamId: int
    quadraKills: int
    roleBoundItem: int
    sightWardsBoughtInGame: int
    subteamPlacement: int
    teamEarlySurrendered: bool
    timeCCingOthers: int
    totalDamageDealt: int
    totalDamageDealtToChampions: int
    totalDamageTaken: int
    totalHeal: int
    totalMinionsKilled: int
    totalPlayerScore: int
    totalScoreRank: int
    totalTimeCrowdControlDealt: int
    totalUnitsHealed: int
    tripleKills: int
    trueDamageDealt: int
    trueDamageDealtToChampions: int
    trueDamageTaken: int
    turretKills: int
    unrealKills: int
    visionScore: int
    visionWardsBoughtInGame: int
    wardsKilled: int
    wardsPlaced: int
    win: bool


@dataclass
class ParticipantTimeline:
    participantId: int
    lane: LCULane
    role: LCURole
    creepsPerMinDeltas: dict = field(default_factory=dict)
    csDiffPerMinDeltas: dict = field(default_factory=dict)
    damageTakenDiffPerMinDeltas: dict = field(default_factory=dict)
    damageTakenPerMinDeltas: dict = field(default_factory=dict)
    goldPerMinDeltas: dict = field(default_factory=dict)
    xpDiffPerMinDeltas: dict = field(default_factory=dict)
    xpPerMinDeltas: dict = field(default_factory=dict)

    def __post_init__(self):
        self.lane = LCULane(self.lane)
        self.role = LCURole(self.role)


@dataclass
class Participant:
    championId: int
    highestAchievedSeasonTier: str
    participantId: int
    spell1Id: int
    spell2Id: int
    stats: ParticipantStats
    teamId: int
    timeline: ParticipantTimeline

    def __post_init__(self):
        self.stats = ParticipantStats(**self.stats)
        self.timeline = ParticipantTimeline(**self.timeline)


@dataclass
class MatchBan:
    championId: int
    pickTurn: int


@dataclass
class MatchTeam:
    bans: list[MatchBan]
    baronKills: int
    dominionVictoryScore: int
    dragonKills: int
    firstBaron: bool
    firstBlood: bool
    firstDargon: bool
    firstInhibitor: bool
    firstTower: bool
    hordeKills: int
    inhibitorKills: int
    riftHeraldKills: int
    teamId: int
    towerKills: int
    vilemawKills: int
    win: str

    def __post_init__(self):
        self.bans = [MatchBan(**b) for b in self.bans]


@dataclass
class LCUMatch:
    endOfGameResult: str
    gameCreation: int
    gameCreationDate: str
    gameDuration: int
    gameId: int
    gameMode: str
    gameModeMutators: list
    gameType: str
    gameVersion: str
    mapId: Map
    participantIdentities: list[ParticipantIdentity]
    participants: list[Participant]
    platformId: str
    queueId: Queue
    seasonId: int
    teams: list[MatchTeam]

    def __post_init__(self):
        self.participantIdentities = [ParticipantIdentity(**p) for p in self.participantIdentities]
        self.participants = [Participant(**p) for p in self.participants]
        self.mapId = Map(self.mapId)
        self.queueId = Queue(self.queueId)
        self.teams = [MatchTeam(**t) for t in self.teams]


@dataclass
class LCUGames:
    gameBeginDate: str
    gameCount: int
    gameEndDate: str
    gameIndexBegin: int
    gameIndexEnd: int
    games: list[LCUMatch]

    def __post_init__(self):
        self.games = [LCUMatch(**g) for g in self.games]

    def update_games(self, new: list[LCUMatch]):
        self.games = new
        self.gameCount = len(new)


@dataclass
class LCUMatchHistory:
    accountId: int
    games: LCUGames
    platformId: str

    def __post_init__(self):
        self.games = LCUGames(**self.games)

    def get_matches_by_queue_type(self, queue_type: Queue) -> list[LCUMatch]:
        return [m for m in self.games.games if m.queueId == queue_type]


@dataclass
class MapPosition:
    x: int
    y: int


@dataclass
class LCUParticipantFrame:
    currentGold: int
    dominionScore: int
    jungleMinionsKilled: int
    level: int
    minionsKilled: int
    participantId: int
    position: MapPosition
    teamScore: int
    totalGold: int
    xp: int

    def __post_init__(self):
        self.position = MapPosition(**self.position)


@dataclass
class LCUTimelineEvent:
    timestamp: int
    type: str
    assistingParticipantIds: Optional[list[int]] = None
    buildingType: Optional[str] = None
    itemId: Optional[int] = None
    killerId: Optional[int] = None
    laneType: Optional[str] = None
    monsterSubType: Optional[str] = None
    monsterType: Optional[str] = None
    participantId: Optional[int] = None
    position: Optional[MapPosition] = None
    skillSlot: Optional[int] = None
    teamId: Optional[int] = None
    towerType: Optional[str] = None
    victimId: Optional[int] = None

    def __post_init__(self):
        if self.position is not None:
            self.position = MapPosition(**self.position)


@dataclass
class LCUTimelineFrame:
    timestamp: int
    events: list[LCUTimelineEvent]
    participantFrames: dict[str, LCUParticipantFrame]

    def __post_init__(self):
        self.events = [LCUTimelineEvent(**e) for e in self.events]
        self.participantFrames = {k: LCUParticipantFrame(**v) for k, v in self.participantFrames.items()}


@dataclass
class LCUTimeline:
    frames: list[LCUTimelineFrame]

    def __post_init__(self):
        self.frames = [LCUTimelineFrame(**f) for f in self.frames]


class LCUReplayState(StrEnum):
    Download = "download"
    Downloading = "downloading"
    Found = "found"
    Incompatible = "incompatible"
    Error = "error"
    Unsupported = "unsupported"
    Lost = "lost"
    Retry = "retryDownload"
    MissingOrExpired = "missingOrExpired"
    Watch = "watch"
    Checking = "checking"


class LCUReplayDownloadStatus(Enum):
    Success = 1
    Retry = 2
    Failed = 3
    Downloading = 4
    NotStarted = 5


@dataclass
class LCUInventoryItemRarity:
    rarity: int
    region: str


@dataclass
class LCUInventoryItem:
    chromaPath: str | None = None
    chromas: list[dict] | None = None
    colors: list[str] | None = None
    contentId: str | None = None
    description: str | None = None
    descriptions: list[str] | None = None
    gipDescription: str | None = None
    gipImagePath: str | None = None
    gipInventoryType: str | None = None
    gipItemId: int | None = None
    gipImage: str | None = None
    gipName: str | None = None
    id: int | None = None
    name: str | None = None
    parentSkinId: int | None = None
    rarities: list[LCUInventoryItemRarity] | None = None
    relatedPrimeContentId: str | None = None
    skinClassification: str | None = None
    skinLines: list[dict] | None = None
    tilePath: str | None = None
    disabledRegions: list[str] | None = None
    isLegacy: bool | None = None
    title: str | None = None
    yearReleased: int | None = None
    IsWIP: bool | None = None
    TFTOnly: bool | None = None
    TFTRarity: str | None = None
    companionType: str | None = None
    rarityValue: int | None = None
    rarity: str | None = None
    rarityGemPath: str | None = None
    loadoutsIcon: str | None = None
    collectionCardHoverVideoPath: str | None = None
    collectionSplashVideoPath: str | None = None
    emblems: str | None = None
    featuresText: str | None = None
    isBase: bool | None = None
    skinType: str | None = None
    splashPath: str | None = None
    splashVideoPath: str | None = None
    uncenteredSplashPath: str | None = None
    isDefault: bool | None = None
    itemId: int | None = None
    level: int | None = None
    speciesId: int | None = None
    speciesName: str | None = None
    upgrades: list | None = None
    imagePath: str | None = None
    esportsEvent: str | None = None
    esportsTeam: str | None = None
    groupId: int | None = None
    groupName: str | None = None
    loadScreenPath: str | None = None
    previewVideoUrl: str | None = None
    regionRarityId: int | None = None
    inventoryIcon: str | None = None
    taggedChampionsIds: list[int] | None = None
    esportsRegion: str | None = None
    regionalDescriptions: list[dict] | None = None
    wardImagePath: str | None = None
    wardShadowImagePath: str | None = None
    loadScreenVintagePath: str | None = None
    image: str | None = None
    passType: str | None = None


class LCUGameflowPhase(StrEnum):
    Home = "None"  # TODO: help
    Lobby = "Lobby"
    Matchmaking = "Matchmaking"
    ReadyCheck = "ReadyCheck"
    ChampSelect = "ChampSelect"
    InProgress = "InProgress"
    EndOfGame = "EndOfGame"
