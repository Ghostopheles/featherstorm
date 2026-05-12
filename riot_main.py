import os
import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.riot_api import RiotAPIClient
from league.highlights import HighlightManager, TimelineEvent
from league.timeline import MatchTimelineAnalyzer

load_dotenv()

GAME_INSTALL_PATH = Path("F:/Games/Riot Games/League of Legends")
CACHE_PATH = Path("./data")
HIGHLIGHTS_PATH = CACHE_PATH / "highlights"

MATCH_ID = "NA1_5549854658"

NAME = "Dallas N Tollway"
TAGLINE = "uwu"

LAME_EVENTS = ["CHAMPION_KILL", "ELITE_MONSTER_KILL", "BUILDING_KILL", "TURRET_PLATE_DESTROYED", "GAME_END"]

async def amain():
    api_key = os.getenv("RIOT_API_KEY")
    highlights = await HighlightManager.create(NAME, TAGLINE, GAME_INSTALL_PATH, HIGHLIGHTS_PATH, api_key)
    #matchID = await highlights.get_last_match_id()
    #await highlights.capture_highlights_for_match(matchID, numHighlights=1)
    highlights.test()



if __name__ == "__main__":
    asyncio.run(amain())
