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


class QueueType(StrEnum):
    Ranked = "ranked"
    Normal = "normal"
    Tournament = "tourney"
    Tutorial = "tutorial"


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
