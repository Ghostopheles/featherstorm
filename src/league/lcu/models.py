from rich import print
from pathlib import Path
from dataclasses import dataclass
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
    Top = "TOP",
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
