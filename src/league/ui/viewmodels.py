from typing import Optional
from dataclasses import dataclass


@dataclass
class MatchRow:
    """Presentation-only view of a match, built from either Riot or LCU models."""

    index: int
    champion: str
    win: bool
    kills: int
    deaths: int
    assists: int
    duration_s: int
    queue_name: str
    match_id: str
    position: Optional[str] = None  # LCU only
    game_mode: Optional[str] = None  # Riot only
