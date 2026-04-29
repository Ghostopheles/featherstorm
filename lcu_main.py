import json
import signal
import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.lcu import LCUClient
from league.lcu.socket import LCUWebsocketEvent

load_dotenv()

GAME_INSTALL_PATH = Path("F:/Games/Riot Games/League of Legends")

async def amain():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    def handle_signal(*_):
        loop.call_soon_threadsafe(stop.set_result, None)

    signal.signal(signal.SIGINT, handle_signal)

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)

    client = LCUClient(GAME_INSTALL_PATH)

    async def on_champion_selected(event: LCUWebsocketEvent):
        champID = event.data
        if champID == 0:
            return

        champion = await client.dragon.get_champion(champID)
        print(champion)

    client.on("OnJsonApiEvent_lol-champ-select_v1_current-champion", on_champion_selected)

    await client.start_websocket()

    await stop

    await client.close_websocket()



if __name__ == "__main__":
    asyncio.run(amain())
