from enum import StrEnum

from league.enums import Map, Queue, MatchType

from league.enums.queues import QUEUE_DESCRIPTION

class QueueChoice(StrEnum):
    Custom = "Custom"
    DraftPick = "Draft Pick"
    RankedSolo = "Ranked Solo"
    BlindPick = "Blind Pick"
    RankedFlex = "Ranked Flex"
    Swiftplay = "Swiftplay"
    ARAM = "ARAM"
    ARAMMayhem = "ARAM: Mayhem"
    CoopVsAIIntro = "Coop vs. AI (Intro)"
    CoopVsAIBeginner = "Coop vs. AI (Beginner)"
    CoopVsAIIntermediate = "Coop vs. AI (Intermediate)"
    Arena = "Arena"
    Arena16Player = "Arena 16 Player"
    ARURF = "ARURF"
    PickURF = "Pick URF"
    Brawl = "Brawl"
    Practice = "Practice"

_QUEUE_CHOICE_TO_MAP: dict[QueueChoice, Map] = {
    QueueChoice.DraftPick: Map.SUMMONER_S_RIFT_3,
    QueueChoice.RankedSolo: Map.SUMMONER_S_RIFT_3,
    QueueChoice.BlindPick: Map.SUMMONER_S_RIFT_3,
    QueueChoice.RankedFlex: Map.SUMMONER_S_RIFT_3,
    QueueChoice.ARAM: Map.HOWLING_ABYSS,
    QueueChoice.Swiftplay: Map.SUMMONER_S_RIFT_3,
    QueueChoice.CoopVsAIIntro: Map.SUMMONER_S_RIFT_3,
    QueueChoice.CoopVsAIBeginner: Map.SUMMONER_S_RIFT_3,
    QueueChoice.CoopVsAIIntermediate: Map.SUMMONER_S_RIFT_3,
    QueueChoice.ARURF: Map.SUMMONER_S_RIFT_3,
    QueueChoice.PickURF: Map.SUMMONER_S_RIFT_3,
    QueueChoice.Brawl: Map.THE_BANDLEWOOD,
    QueueChoice.ARAMMayhem: Map.HOWLING_ABYSS,
    QueueChoice.Arena: Map.RINGS_OF_WRATH,
    QueueChoice.Arena16Player: Map.RINGS_OF_WRATH,
    QueueChoice.Practice: Map.SUMMONER_S_RIFT_3
}

_QUEUE_CHOICE_TO_QUEUE: dict[QueueChoice, Queue] = {
    QueueChoice.Custom: Queue.ITEM_X,
    QueueChoice.DraftPick: Queue.Q_5V5_DRAFT_PICK_GAMES_2,
    QueueChoice.RankedSolo: Queue.Q_5V5_RANKED_SOLO_GAMES_2,
    QueueChoice.BlindPick: Queue.Q_5V5_BLIND_PICK_GAMES_2,
    QueueChoice.RankedFlex: Queue.Q_5V5_RANKED_FLEX_GAMES,
    QueueChoice.ARAM: Queue.Q_5V5_ARAM_GAMES_3,
    QueueChoice.Swiftplay: Queue.SWIFTPLAY_GAMES,
    QueueChoice.CoopVsAIIntro: Queue.CO_OP_VS_AI_INTRO_BOT_GAMES_4,
    QueueChoice.CoopVsAIBeginner: Queue.CO_OP_VS_AI_BEGINNER_BOT_GAMES_4,
    QueueChoice.CoopVsAIIntermediate: Queue.CO_OP_VS_AI_INTERMEDIATE_BOT_GAMES_4,
    QueueChoice.ARURF: Queue.ARAM_MAYHEM,
    QueueChoice.PickURF: Queue.PICK_URF_GAMES,
    QueueChoice.Brawl: Queue.BRAWL,
    QueueChoice.ARAMMayhem: Queue.ARAM_MAYHEM,
    QueueChoice.Arena: Queue.ARENA,
    QueueChoice.Arena16Player: Queue.ARENA_2,
    QueueChoice.Practice: Queue.PRACTICE
}

def resolve_queue(value: QueueChoice) -> Queue:
    return _QUEUE_CHOICE_TO_QUEUE[value]

def resolve_queue_name(value: QueueChoice | Queue) -> str:
    if isinstance(value, QueueChoice):
        queue = resolve_queue(value)
    else:
        queue = value
    return QUEUE_DESCRIPTION[queue]

def resolve_map_from_queue_choice(value: QueueChoice) -> Map:
    return _QUEUE_CHOICE_TO_MAP[value]

class MatchTypeChoice(StrEnum):
    Normal = "Normal"
    Ranked = "Ranked"
    Tournament = "Tournament"
    Tutorial = "Tutorial"

def resolve_match_type(value: MatchTypeChoice) -> MatchType:
    return MatchType.from_name(value)
