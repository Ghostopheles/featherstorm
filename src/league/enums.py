from enum import Enum, StrEnum

class LeagueClientStatus(Enum):
    DISCONNECTED = 1
    LOADING = 2
    CONNECTED = 3
    BANISHED = 4

class GameEventType(StrEnum):
    GameStart = "GameStart"
    GameEnd = "GameEnd"
    MinionsSpawning = "MinionsSpawning"
    FirstBlood = "FirstBlood"
    TurretKilled = "TurretKilled"
    InhibKilled = "InhibKilled"
    DragonKill = "DragonKill"
    HeraldKill = "HeraldKill"
    BaronKill = "BaronKill"
    ChampionKill = "ChampionKill"
    Multikill = "Multikill"
    Ace = "Ace"
    HordeKill = "HordeKill"
    FirstBrick = "FirstBrick"
    AtakahnKill = "AtakahnKill"
    InhibRespawned = "InhibRespawned"


class GameTeam(StrEnum):
    ORDER = "ORDER"
    CHAOS = "CHAOS"
    SPECTATOR = "SPECTATOR"


class GameResult(Enum):
    Win = 0
    Lose = 1

class GamePlayerPosition(StrEnum):
    TOP = "Top"
    JUNGLE = "Jungle"
    MIDDLE = "Middle"
    BOTTOM = "Bottom"
    SUPPORT = "Support"


class QueueType(StrEnum):
    Ranked = "ranked"
    Normal = "normal"
    Tournament = "tourney"
    Tutorial = "tutorial"

class MapQueueTypeName(StrEnum):
    Custom = "Custom"
    DraftPick = "DraftPick"
    RankedSolo = "RankedSolo"
    BlindPick = "BlindPick"
    RankedFlex = "RankedFlex"
    ARAM = "ARAM"
    Swiftplay = "Swiftplay"
    TwistedTreelineAIBeginner = "TwistedTreelineAIBeginner"
    CoopVsAIIntro = "CoopVsAIIntro"
    CoopVsAIBeginner = "CoopVsAIBeginner"
    CoopVsAIIntermediate = "CoopVsAIIntermediate"
    ARURF = "ARURF"
    TeamfightTacticsNormal = "TeamfightTacticsNormal"
    TeamfightTacticsRanked = "TeamfightTacticsRanked"
    TeamfightTacticsTutorial = "TeamfightTacticsTutorial"
    TeamfightTacticsTest = "TeamfightTacticsTest"
    TeamfightTacticsChonccTreasureMode = "TeamfightTacticsChonccTreasureMode"
    NexusBlitz = "NexusBlitz"
    UltimateSpellbookGames = "UltimateSpellbookGames"
    Arena = "Arena"
    Arena16Player = "Arena16Player"
    Swarm1Player = "Swarm1Player"
    Swarm2Player = "Swarm2Player"
    Swarm3Player = "Swarm3Player"
    Swarm4Player = "Swarm4Player"
    PickURF = "PickURF"
    Tutorial1 = "Tutorial1"
    Tutorial2 = "Tutorial2"
    Tutorial3 = "Tutorial3"
    Brawl = "Brawl"
    ARAMMayhem = "ARAMMayhem"

class MapQueueType(Enum):
    Custom = 0
    DraftPick = 400
    RankedSolo = 420
    BlindPick = 430
    RankedFlex = 440
    ARAM = 450
    Swiftplay = 480
    TwistedTreelineAIBeginner = 820
    CoopVsAIIntro = 870
    CoopVsAIBeginner = 880
    CoopVsAIIntermediate = 890
    ARURF = 900
    TeamfightTacticsNormal = 1090
    TeamfightTacticsRanked = 1100
    TeamfightTacticsTutorial = 1110
    TeamfightTacticsTest = 1111
    TeamfightTacticsChonccTreasureMode = 1210
    NexusBlitz = 1300
    UltimateSpellbookGames = 1400
    Arena = 1700
    Arena16Player = 1710
    Swarm1Player = 1810
    Swarm2Player = 1820
    Swarm3Player = 1830
    Swarm4Player = 1840
    PickURF = 1900
    Tutorial1 = 2000
    Tutorial2 = 2010
    Tutorial3 = 2020
    Brawl = 2300
    ARAMMayhem = 2400
    PracticeTool = 3140

class ReplaySequenceEasing(StrEnum):
    LINEAR = "linear"
    SNAP = "snap"
    SMOOTH_STEP = "smoothStep"
    SMOOTHER_STEP = "smootherStep"
    QUADRATIC_EASE_IN = "quadraticEaseIn"
    QUADRATIC_EASE_OUT = "quadraticEaseOut"
    QUADRATIC_EASE_IN_OUT = "quadraticEaseInOut"
    CUBIC_EASE_IN = "cubicEaseIn"
    CUBIC_EASE_OUT = "cubicEaseOut"
    CUBIC_EASE_IN_OUT = "cubicEaseInOut"
    QUARTIC_EASE_IN = "quarticEaseIn"
    QUARTIC_EASE_OUT = "quarticEaseOut"
    QUARTIC_EASE_IN_OUT = "quarticEaseInOut"
    QUINTIC_EASE_IN = "quinticEaseIn"
    QUINTIC_EASE_OUT = "quinticEaseOut"
    QUINTIC_EASE_IN_OUT = "quinticEaseInOut"
    SINE_EASE_IN = "sineEaseIn"
    SINE_EASE_OUT = "sineEaseOut"
    SINE_EASE_IN_OUT = "sineEaseInOut"
    CIRCULAR_EASE_IN = "circularEaseIn"
    CIRCULAR_EASE_OUT = "circularEaseOut"
    CIRCULAR_EASE_IN_OUT = "circularEaseInOut"
    EXPONENTIAL_EASE_IN = "exponentialEaseIn"
    EXPONENTIAL_EASE_OUT = "exponentialEaseOut"
    EXPONENTIAL_EASE_IN_OUT = "exponentialEaseInOut"
    ELASTIC_EASE_IN = "elasticEaseIn"
    ELASTIC_EASE_OUT = "elasticEaseOut"
    ELASTIC_EASE_IN_OUT = "elasticEaseInOut"
    BACK_EASE_IN = "backEaseIn"
    BACK_EASE_OUT = "backEaseOut"
    BACK_EASE_IN_OUT = "backEaseInOut"
    BOUNCE_EASE_IN = "bounceEaseIn"
    BOUNCE_EASE_OUT = "bounceEaseOut"
    BOUNCE_EASE_IN_OUT = "bounceEaseInOut"
