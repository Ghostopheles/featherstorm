import json
import signal
import asyncio

from rich import print
from pathlib import Path
from dotenv import load_dotenv

from league.lcu import LCUClient
from league.lcu.socket import LCUWebsocketEvent, LCUWebsocketEventType

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
        if event.eventType == LCUWebsocketEventType.Delete:
            return

        champID = event.data
        if champID == 0:
            return

        champion = await client.dragon.get_champion(champID)
        champ_name = champion.get("name")
        print(f"You've locked in {champ_name}. See the build: https://onetricks.gg/champions/builds/{champ_name}")

    client.on("OnJsonApiEvent_lol-champ-select_v1_current-champion", on_champion_selected)

    async def on_any(event: LCUWebsocketEvent):
        print(event)

    other_events = [
        "OnJsonApiEvent_lol-matchmaking_v1_ready-check",
        "OnJsonApiEvent_lol-lobby-team-builder_champ-select_v1",
        "OnJsonApiEvent_lol-lobby_v2_lobby",
    ]
    for e in other_events:
        client.on(e, on_any)

    await client.start_websocket()

    await stop

    await client.close_websocket()


if __name__ == "__main__":
    asyncio.run(amain())
