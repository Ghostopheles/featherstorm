import json
import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.lcu import LCUClient, LCUTimeline

load_dotenv()

GAME_INSTALL_PATH = Path("F:/Games/Riot Games/League of Legends")


async def amain():
    client = LCUClient(GAME_INSTALL_PATH)
    id = await client.get_last_match_id()
    timeline = await client.get_raw_match_timeline(id)
    with open("data/timeline.json", "w") as f:
        json.dump(timeline, f, indent=4)



if __name__ == "__main__":
    asyncio.run(amain())
