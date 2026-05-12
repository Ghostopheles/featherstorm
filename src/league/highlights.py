import os
import signal
import httpx
import asyncio

from pathlib import Path
from rich import print as p

from league.lcu.lcu import LCUClient
from league.models import PlayerMatch, TimelineEvent, MatchTimeline
from league.enums import QueueType, ReplaySequenceEasing
from league.timeline import MatchTimelineAnalyzer, HighlightEvent
from league.riot_api import RiotAPIClient

LAUNCH_POLL_INTERVAL = 1
LAUNCH_TIMEOUT = 60
DOWNLOAD_CHUNK_SIZE = 8192
CLIP_DURATION = 15  # seconds
HALF_CLIP_DURATION = CLIP_DURATION // 2
GAME_CLIENT_NAME = "League of Legends.exe"
DEFAULT_SEEK_BUFFER = 0 # seconds to seek before the event timestamp to account for loading times
DEFAULT_CAMERA_FOV = 60

SEQUENCE_CAMERA_HEIGHT = 2200
SEQUENCE_CAMERA_PITCH = 55

CAMERA_SELECTION_OFFSET = {
    "x": 0,
    "y": 2200,
    "z": -1400
}

REPLAY_API_URL = "https://127.0.0.1:2999/replay"


class HighlightManager:
    game_path: Path
    cache_path: Path

    lcu: LCUClient | None = None

    riot: RiotAPIClient | None = None
    puuid: str | None = None

    http: httpx.AsyncClient | None = None

    __matches: list[PlayerMatch] | None = None
    __match_cache: dict[str, PlayerMatch] | None = None
    __timeline_cache: dict[str, MatchTimeline] | None = None

    __current_match: PlayerMatch | None = None

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

    @staticmethod
    def get_player_participant_id(match: PlayerMatch) -> int:
        return match.player.participantId

    async def get_match(self, matchID: str) -> PlayerMatch:
        if self.__match_cache is None:
            self.__match_cache = {}
            match = await self.riot.get_player_match(matchID, self.puuid)
            self.__match_cache.setdefault(matchID, match)

        return self.__match_cache.get(matchID)

    async def get_recent_matches(self, count: int = None) -> list[PlayerMatch]:
        if self.__matches is None:
            self.__matches = await self.riot.get_recent_matches(self.puuid, count=count, match_type=QueueType.Normal)

            self.__match_cache = {
                match.matchId: match for match in self.__matches
            }

        return self.__matches

    async def get_last_match(self) -> PlayerMatch:
        matches = await self.get_recent_matches()
        return matches[0]

    async def get_last_match_id(self) -> str:
        match = await self.get_last_match()
        return match.matchId

    async def get_timeline_for_match(self, matchID: str) -> MatchTimeline:
        if self.__timeline_cache is None:
            self.__timeline_cache = {}
            timeline = await self.riot.get_match_timeline(matchID)
            self.__timeline_cache.setdefault(matchID, timeline)

        return self.__timeline_cache.get(matchID)

    async def get_highlight_events(self, matchID: str) -> list[HighlightEvent]:
        timeline = await self.get_timeline_for_match(matchID)

        match = await self.get_match(matchID)
        playerParticipantID = self.get_player_participant_id(match)

        analyzer = MatchTimelineAnalyzer(playerParticipantID, timeline)
        return analyzer.get_highlight_events()

    async def get_all_events_for_match(self, matchID: str) -> list[TimelineEvent]:
        timeline = await self.get_timeline_for_match(matchID)

        match = await self.get_match(matchID)
        playerParticipantID = self.get_player_participant_id(match)

        analyzer = MatchTimelineAnalyzer(playerParticipantID, timeline)
        return analyzer.get_all_events()

    async def capture_highlights_for_match(self, matchID: str, numHighlights: int = None):
        events = await self.get_highlight_events(matchID)
        events.sort(key=lambda x: x.timestamp) # sort by the start time

        match = await self.get_match(matchID)
        self.__current_match = match

        await self.open_replay(matchID)
        await self.wait_for_replay_ready()
        await self.record(events, numHighlights)

    async def wait_for(self, func):
        deadline = asyncio.get_event_loop().time() + LAUNCH_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            try:
                if await func():
                    return
            except httpx.ConnectError:
                print("Failed to connect to replay API")
                pass
            await asyncio.sleep(LAUNCH_POLL_INTERVAL)
        raise TimeoutError("Waiting timeout")

    async def wait_for_replay_ready(self):
        async def check():
            res = await self.http.get(REPLAY_API_URL + "/playback")
            return res.is_success
        return await self.wait_for(check)

    async def wait_for_seek(self):
        async def check():
            res = await self.http.get(REPLAY_API_URL + "/playback")
            return res.json().get("seeking") == False
        return await self.wait_for(check)

    async def wait_for_recording(self):
        async def check():
            res = await self.http.get(REPLAY_API_URL + "/recording")
            return res.json().get("recording") == False
        return await self.wait_for(check)

    async def open_replay(self, matchID: str):
        matchID = matchID.replace("NA1_", "") # need to remove prefix since the LCU doesn't use them
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

    async def seek_to(self, timestamp: float, buffer: float = DEFAULT_SEEK_BUFFER):
        res = await self.http.post(REPLAY_API_URL + "/playback", json={"paused": True, "seeking": True, "speed": 1.0, "time": timestamp - buffer})
        res.raise_for_status()
        return res.json()

    async def apply_sequence(self, sequence: dict):
        res = await self.http.post(REPLAY_API_URL + "/sequence", json=sequence)
        res.raise_for_status()
        return res.json()

    async def update_render_settings    (self, **kwargs):
        res = await self.http.post(REPLAY_API_URL + "/render", json=kwargs)
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

    async def track_player_with_camera(self):
        name = self.__current_match.player.riotIdGameName
        res = await self.http.post(REPLAY_API_URL + "/render", json={
            "cameraMode": "fps",
            "cameraAttached": True,
            "selectionName": name,
            "selectionOffset": CAMERA_SELECTION_OFFSET
        })
        res.raise_for_status()
        return res.json()

    async def hide_replay_ui(self):
        data = {
            "interfaceAll": True,
            "interfaceAnnounce": True,
            "interfaceChat": False,
            "interfaceFrames": True,
            "interfaceKillCallouts": True,
            "interfaceMinimap": True,
            "interfaceNeutralTimers": False,
            "interfaceQuests": False,
            "interfaceReplay": False,
            "interfaceScore": True,
            "interfaceScoreboard": False,
            "interfaceTarget": False,
            "interfaceTimeline": False,
            "depthFogEnabled": True,
        }
        res = await self.http.post(REPLAY_API_URL + "/render", json=data)
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
            lossless: bool = False,
            codec: str = "webm",
            enforce_frame_rate: bool = False
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
                "enforceFrameRate": enforce_frame_rate
            }
        )
        res.raise_for_status()
        return res.json()

    async def stop_recording(self):
        res = await self.http.post(REPLAY_API_URL + "/recording", json={"recording": False})
        res.raise_for_status()

    async def record(self, events: list[HighlightEvent], numHighlights: int = None):
        self.pid = await self.get_replay_pid()

        await self.pause()
        print("waiting for replay to catch up with reality...")
        await asyncio.sleep(5)

        await self.hide_replay_ui()

        print("--capturing highlights--")
        for i, batch in enumerate(events):
            if numHighlights is not None and i >= numHighlights:
                break

            timestamp = batch.timestamp

            start_time = max(0, timestamp - 4)
            length = batch.event_length
            end_time = timestamp + length + 4
            await self.seek_to(timestamp)

            await self.wait_for_seek()

            await self.track_player_with_camera()

            print("resuming replay...")
            await self.resume()

            file_name = f"highlight_{i}.webm"
            await self.start_recording(file_name, start_time, end_time)

            print(f"recording highlight {i}...")

            print(f"waiting for recording...")
            await self.wait_for_recording()

            print(f"captured highlight {i}!")
            await self.pause()

        print("done!")
        await self.close_active_replay()

        return True
