from .enum_base import LookupStrEnum

class MatchType(LookupStrEnum):
    Normal = "normal"
    Ranked = "ranked"
    Tournament = "tourney"
    Tutorial = "tutorial"
