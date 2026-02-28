from enum import Enum
from typing import Optional
from dataclasses import dataclass

from league.enums import GameEventType, GameResult, GameTeam


def cast_to_enum(value, enum: Enum):
    if value is None:
        return value

    return enum[value]


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

    def __post_init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            key = key[0].lower() + key[1:]
            setattr(self, key, value)

        self.EventName = cast_to_enum(self.EventName, GameEventType)
        self.AcingTeam = cast_to_enum(self.AcingTeam, GameTeam)
        self.Result = cast_to_enum(self.Result, GameResult)

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
        self.events = [GameEvent(**e) for e in self.events["Events"]]
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