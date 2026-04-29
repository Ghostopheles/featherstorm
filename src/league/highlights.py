import os
import signal
import httpx
import asyncio

from pathlib import Path

from league.lcu.lcu import LCUClient
from league.lcu.timeline import LCUTimelineAnalyzer, LCUHighlightEvent
from league.riot_api import RiotAPIClient

LAUNCH_POLL_INTERVAL = 1
LAUNCH_TIMEOUT = 60
DOWNLOAD_CHUNK_SIZE = 8192
CLIP_DURATION = 10  # seconds
GAME_CLIENT_NAME = "League of Legends.exe"

REPLAY_API_URL = "https://127.0.0.1:2999/replay"


class HighlightManager:
    game_path: Path
    cache_path: Path

    lcu: LCUClient | None = None

    riot: RiotAPIClient | None = None
    puuid: str | None = None

    http: httpx.AsyncClient | None = None

    def __init__(self, game_path: Path, cache_path: Path):
        if not game_path.exists():
            raise FileNotFoundError("Invalid League of Legends game path")

        if GAME_CLIENT_NAME not in str(game_path):
            if str(game_path.parent) != "Game":
                game_path = game_path / "Game"

            game_path = game_path / GAME_CLIENT_NAME

        if not game_path.exists():
            raise FileNotFoundError("Unable to find League of Legends executable")

        self.game_path = game_path

        self.cache_path = cache_path
        self.cache_path.mkdir(parents=True, exist_ok=True)

    async def __init_api(self, name: str, tag: str, api_key: str):
        if self.riot is not None:
            return

        self.riot = RiotAPIClient(api_key)
        self.puuid = await self.riot.get_puuid(name, tag)

    def __init_http(self):
        if self.http is not None:
            return

        self.http = httpx.AsyncClient(http2=True, timeout=httpx.Timeout(10.0, read=300.0), verify=False)

    def __init_lcu(self):
        if self.lcu is not None:
            return

        self.lcu = LCUClient(self.game_path.parent.parent)

    async def __init(self, *args, **kwargs):
        await self.__init_api(*args, **kwargs)
        self.__init_http()
        self.__init_lcu()

    @classmethod
    async def create(cls, name: str, tag: str, game_path: Path, cache_path: Path, api_key: str):
        obj = cls(game_path, cache_path)
        await obj.__init(name, tag, api_key)
        return obj

    async def capture_highlights_for_match(self, matchID: int):
        timeline = await self.lcu.get_match_timeline(matchID)
        playerParticipantID = await self.lcu.get_player_participant_id(matchID)
        analyzer = LCUTimelineAnalyzer(playerParticipantID, timeline)
        events = analyzer.get_highlight_info()

        buffer = 7
        timestamps = []
        for event in events:
            time = event.timestamp / 1000
            timestamps.append((time - buffer, time + buffer))

        await self.open_replay(matchID)
        await self.wait_for_replay_ready()
        await self.record(timestamps)

    async def capture_highlights_for_last_match(self):
        matchID = await self.lcu.get_last_match_id()
        return await self.capture_highlights_for_match(matchID)

    async def wait_for_replay_ready(self):
        deadline = asyncio.get_event_loop().time() + LAUNCH_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            try:
                res = await self.http.get(REPLAY_API_URL + "/playback")
                if res.is_success:
                    return
            except httpx.ConnectError:
                print("Failed to connect to replay API")
                pass
            await asyncio.sleep(LAUNCH_POLL_INTERVAL)
        raise TimeoutError("Replay API startup timeout")

    async def open_replay(self, matchID: int):
        await self.lcu.launch_replay(matchID)

    async def close_active_replay(self):
        if self.pid is not None:
            os.kill(self.pid, signal.SIGTERM)

    async def get_replay_pid(self) -> int:
        data = await self.http.get(REPLAY_API_URL + "/game")
        return data.json().get("processID")

    async def record(self, time_ranges: list[set[float]]):
        self.pid = await self.get_replay_pid()

        await self.http.post(REPLAY_API_URL + "/playback", json={"paused": True})
        await asyncio.sleep(5)

        start_time, end_time = time_ranges[0]
        res = await self.http.post(REPLAY_API_URL + "/playback", json={"paused": False, "seeking": False, "speed": 1.0, "time": start_time - 5})
        res.raise_for_status()

        await asyncio.sleep(1)

        file_name = "recording.webm"
        rec = await self.http.post(
            REPLAY_API_URL + "/recording",
            json={
                "recording": True,
                "codec": "webm",
                "lossless": True,
                "path": file_name,
                "width": 2560,
                "height": 1440,
                "startTime": start_time,
                "endTime": end_time,
                "framesPerSecond": 60,
            },
        )
        print("recording")
        rec.raise_for_status()

        await asyncio.sleep(CLIP_DURATION + 5)

        end_rec = await self.http.post(REPLAY_API_URL + "/recording", json={"recording": False})
        end_rec.raise_for_status()

        await self.close_active_replay()
