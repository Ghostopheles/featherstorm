import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.lcu import LCUClient

load_dotenv()

GAME_INSTALL_PATH = Path("F:/Games/Riot Games/League of Legends")


async def amain():
    client = LCUClient(GAME_INSTALL_PATH)
    match_ids = await client.get_recent_match_ids()
    for match in match_ids:
        print(await client.get_replay_metadata(match))


if __name__ == "__main__":
    asyncio.run(amain())
