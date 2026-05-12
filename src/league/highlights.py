import os
import signal
import httpx
import asyncio

from pathlib import Path

from league.lcu.lcu import LCUClient
from league.lcu.models import LCUTimelineEvent, LCUMatch
from league.lcu.timeline import LCUTimelineAnalyzer, LCUHighlightEvent, LCUTimeline
from league.riot_api import RiotAPIClient

LAUNCH_POLL_INTERVAL = 1
LAUNCH_TIMEOUT = 60
DOWNLOAD_CHUNK_SIZE = 8192
CLIP_DURATION = 15  # seconds
HALF_CLIP_DURATION = CLIP_DURATION // 2
GAME_CLIENT_NAME = "League of Legends.exe"
DEFAULT_SEEK_BUFFER = 0 # seconds to seek before the event timestamp to account for loading times
DEFAULT_CAMERA_FOV = 60

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

    async def get_last_match(self) -> LCUMatch:
        return await self.lcu.get_last_match()

    async def get_last_match_id(self) -> int:
        return await self.lcu.get_last_match_id()

    async def get_timeline_for_match(self, matchID: int) -> LCUTimeline:
        timeline = await self.lcu.get_match_timeline(matchID)
        return timeline

    async def get_highlight_events_for_last_match(self) -> list[LCUHighlightEvent]:
        matchID = await self.get_last_match_id()
        return await self.get_highlight_events(matchID)

    async def get_highlight_events(self, matchID: int) -> list[LCUHighlightEvent]:
        timeline = await self.get_timeline_for_match(matchID)
        playerParticipantID = await self.lcu.get_player_participant_id(matchID)
        analyzer = LCUTimelineAnalyzer(playerParticipantID, timeline)
        return analyzer.get_highlight_events()

    async def get_all_events_for_last_match(self) -> list[LCUTimelineEvent]:
        matchID = await self.get_last_match_id()
        return await self.get_all_events_for_match(matchID)

    async def get_all_events_for_match(self, matchID: int) -> list[LCUTimelineEvent]:
        timeline = await self.get_timeline_for_match(matchID)
        playerParticipantID = await self.lcu.get_player_participant_id(matchID)
        analyzer = LCUTimelineAnalyzer(playerParticipantID, timeline)
        return analyzer.get_all_events()

    async def capture_highlights_for_match(self, matchID: int, numHighlights: int = None):
        events = await self.get_highlight_events(matchID)
        events.sort(key=lambda x: x.timestamp) # sort by the start time

        await self.open_replay(matchID)
        await self.wait_for_replay_ready()
        await self.record(events, numHighlights)

    async def capture_highlights_for_last_match(self, numHighlights: int = None):
        matchID = await self.get_last_match_id()
        return await self.capture_highlights_for_match(matchID, numHighlights)

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

    async def wait_for_seek(self):
        deadline = asyncio.get_event_loop().time() + LAUNCH_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            try:
                res = await self.http.get(REPLAY_API_URL + "/playback")
                if res.json().get("seeking") == False:
                    return
            except httpx.ConnectError:
                print("Failed to connect to replay API")
                pass
            await asyncio.sleep(LAUNCH_POLL_INTERVAL)
        raise TimeoutError("Timeout waiting for seek")

    async def open_replay(self, matchID: int):
        await self.lcu.launch_replay(matchID)

    async def close_active_replay(self):
        if self.pid is not None:
            os.kill(self.pid, signal.SIGTERM)

    async def get_replay_pid(self) -> int:
        data = await self.http.get(REPLAY_API_URL + "/game")
        return data.json().get("processID")

    async def pause(self):
        res = await self.http.post(REPLAY_API_URL + "/playback", json={"paused": True})
        res.raise_for_status()
        return res.json()

    async def resume(self):
        res = await self.http.post(REPLAY_API_URL + "/playback", json={"paused": False})
        res.raise_for_status()
        return res.json()

    async def seek_to(self, timestamp: float, buffer: float = DEFAULT_SEEK_BUFFER) -> float:
        res = await self.http.post(REPLAY_API_URL + "/playback", json={"paused": True, "seeking": True, "speed": 1.0, "time": timestamp - buffer})
        res.raise_for_status()
        return res.json()

    async def move_camera_to(self, x: float, y: float, fov: int = DEFAULT_CAMERA_FOV):
        res = await self.http.post(REPLAY_API_URL + "/render", json={
            "cameraPosition": {
                "x": x,
                "y": y,
            },
            "fieldOfView": fov,
        })
        res.raise_for_status()
        return res.json()

    async def start_recording(
            self,
            file_name: str,
            start_time: float,
            end_time: float,
            width: int = 2560,
            height: int = 1440,
            fps: int = 60,
            lossless: bool = True,
            codec: str = "webm",
            encforce_frame_rate: bool = True
        ):
        res = await self.http.post(
            REPLAY_API_URL + "/recording",
            json={
                "recording": True,
                "codec": codec,
                "lossless": lossless,
                "path": file_name,
                "width": width,
                "height": height,
                "startTime": start_time,
                "endTime": end_time,
                "framesPerSecond": fps,
                "enforceFrameRate": encforce_frame_rate
            }
        )
        res.raise_for_status()
        return res.json()

    async def stop_recording(self):
        res = await self.http.post(REPLAY_API_URL + "/recording", json={"recording": False})
        res.raise_for_status()

    async def record(self, events: list[LCUHighlightEvent], numHighlights: int = None):
        self.pid = await self.get_replay_pid()

        await self.pause()
        print("waiting for replay to catch up with reality...")
        await asyncio.sleep(5)

        print("--capturing highlights--")
        for i, event in enumerate(events):
            if numHighlights is not None and i >= numHighlights:
                break

            timestamp = event.timestamp

            start_time = max(0, timestamp - HALF_CLIP_DURATION)
            end_time = timestamp + HALF_CLIP_DURATION
            await self.seek_to(timestamp)

            await self.move_camera_to(event.position.x, event.position.y)

            await self.wait_for_seek()

            await self.resume()

            file_name = f"highlight_{i}.webm"
            await self.start_recording(file_name, start_time, end_time)

            print(f"recording highlight {i}...")

            time_to_wait = CLIP_DURATION + 5
            print(f"sleeping for {time_to_wait} seconds to capture the full highlight...")
            await asyncio.sleep(time_to_wait)

            await self.stop_recording()

            print(f"captured highlight {i}!")
            await self.pause()

        print("done!")
        await self.close_active_replay()

        return True
