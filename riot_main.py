import os
import json
import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.riot_api import RiotAPIClient

load_dotenv()

async def amain():
    api_key = os.getenv("RIOT_API_KEY")
    client = RiotAPIClient(api_key)
    puuid = await client.get_puuid("Dallas N Tollway", "uwu")
    data = await client.get_recent_matches(puuid, 1)
    print(data)


if __name__ == "__main__":
    asyncio.run(amain())
