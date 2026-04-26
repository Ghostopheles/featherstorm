import os
import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.riot_api import RiotAPIClient
from league.highlights import HighlightManager

load_dotenv()

GAME_INSTALL_PATH = Path("F:/Games/Riot Games/League of Legends")
CACHE_PATH = Path("./data")

NAME = "Dallas N Tollway"
TAGLINE = "uwu"

async def amain():
    api_key = os.getenv("RIOT_API_KEY")
    highlights = await HighlightManager.create(NAME, TAGLINE, GAME_INSTALL_PATH, CACHE_PATH, api_key)
    await highlights.capture()

if __name__ == "__main__":
    asyncio.run(amain())
