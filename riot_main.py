import os
import json
import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.api import RiotAPIClient

load_dotenv()

async def amain():
    api_key = os.getenv("RIOT_API_KEY")
    client = RiotAPIClient(api_key)
    data = await client.get_rso_match_ids()
    with open("data/rso-matchids.json", "w") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    asyncio.run(amain())
