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
    # api_key = os.getenv("RIOT_API_KEY")
    # highlights = await HighlightManager.create(NAME, TAGLINE, GAME_INSTALL_PATH, CACHE_PATH, api_key)
    # await highlights.capture_highlights_for_last_match()

    import httpx

    res = httpx.get("https://127.0.0.1:2999/swagger/v3/openapi.json", verify=False)
    with open("data/openapi.json", "w") as f:
        import json

        json.dump(res.json(), f, indent=4)


if __name__ == "__main__":
    asyncio.run(amain())
