import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.lcu import LCUClient

load_dotenv()

GAME_INSTALL_PATH = Path("F:/Games/Riot Games/League of Legends")


async def amain():
    client = LCUClient(GAME_INSTALL_PATH)
    print(await client.create_normal_game_lobby())


if __name__ == "__main__":
    asyncio.run(amain())
