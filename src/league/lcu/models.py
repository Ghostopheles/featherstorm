from pathlib import Path
from dataclasses import dataclass, field
from enum import StrEnum, Enum
from typing import Optional


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
    Duo = "DUO"
    DuoCarry = "DUO_CARRY"
    DuoSupport = "DUO_SUPPORT"
    Solo = "SOLO"
    Unknown = "NONE"


class LCULane(StrEnum):
    Top = "TOP_LANE"
    Middle = "MID_LANE"
    Bottom = "BOT_LANE"
    Jungle = "JUNGLE"


class LCUPosition(StrEnum):
    Top = "TOP"
    Middle = "MIDDLE"
    Jungle = "JUNGLE"
    Bottom = "BOTTOM"
    Support = "UTILITY"
    Apex = "APEX"
    Unknown = "NONE"


PlayerRoleMapping = {
    (LCULane.Top, LCURole.Solo): LCUPosition.Top,
    (LCULane.Middle, LCURole.Solo): LCUPosition.Middle,
    (LCULane.Jungle, LCURole.Unknown): LCUPosition.Jungle,
    (LCULane.Bottom, LCURole.DuoCarry): LCUPosition.Bottom,
    (LCULane.Bottom, LCURole.DuoSupport): LCUPosition.Support,
}


# ---------------------------------------------------------------------------
# LCU Match History models (older v4-style format from the LCU API)
# ---------------------------------------------------------------------------


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
    lane: str
    role: str
    creepsPerMinDeltas: dict = field(default_factory=dict)
    csDiffPerMinDeltas: dict = field(default_factory=dict)
    damageTakenDiffPerMinDeltas: dict = field(default_factory=dict)
    damageTakenPerMinDeltas: dict = field(default_factory=dict)
    goldPerMinDeltas: dict = field(default_factory=dict)
    xpDiffPerMinDeltas: dict = field(default_factory=dict)
    xpPerMinDeltas: dict = field(default_factory=dict)


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
    mapId: int
    participantIdentities: list[ParticipantIdentity]
    participants: list[Participant]
    platformId: str
    queueId: int
    seasonId: int
    teams: list[MatchTeam]

    def __post_init__(self):
        self.participantIdentities = [ParticipantIdentity(**p) for p in self.participantIdentities]
        self.participants = [Participant(**p) for p in self.participants]
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


@dataclass
class LCUMatchHistory:
    accountId: int
    games: LCUGames
    platformId: str

    def __post_init__(self):
        self.games = LCUGames(**self.games)


# ---------------------------------------------------------------------------
# LCU Timeline models
# ---------------------------------------------------------------------------


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
