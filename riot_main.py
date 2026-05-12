import os
import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.riot_api import RiotAPIClient
from league.highlights import HighlightManager, TimelineEvent
from league.predicates import rule

load_dotenv()

GAME_INSTALL_PATH = Path("F:/Games/Riot Games/League of Legends")
CACHE_PATH = Path("./data")

MATCH_ID = "NA1_5549872684"

NAME = "Dallas N Tollway"
TAGLINE = "uwu"


@rule
def event_type_is(type_name: str, event: TimelineEvent, **kwargs) -> bool:
    """Match events of a specific type. Args: ["CHAMPION_KILL"]"""
    return event.type == type_name

@rule
def event_caused_by_participant(targetParticipantID: int, event: TimelineEvent, **kwargs) -> bool:
    """Match events caused by a specific participant. Args: [1]"""
    print("caused by", event, targetParticipantID)
    return event.killerId == targetParticipantID

@rule
def event_assisted_by_participant(targetParticipantID: int, event: TimelineEvent, **kwargs) -> bool:
    """Match events assisted by a specific participant. Args: [1]"""
    print("assisted by", event, targetParticipantID)
    return event.assistingParticipantIds is not None and targetParticipantID in event.assistingParticipantIds

@rule
def event_victim_is_participant(targetParticipantID: int, event: TimelineEvent, **kwargs) -> bool:
    """Match events where the victim is a specific participant. Args: [1]"""
    print("victim_is", event, targetParticipantID)
    return event.victimId == targetParticipantID

async def amain():
    api_key = os.getenv("RIOT_API_KEY")
    highlights = await HighlightManager.create(NAME, TAGLINE, GAME_INSTALL_PATH, CACHE_PATH, api_key)
    await highlights.capture_highlights_for_match(MATCH_ID, numHighlights=1)


if __name__ == "__main__":
    asyncio.run(amain())
