from enum import Enum, StrEnum


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