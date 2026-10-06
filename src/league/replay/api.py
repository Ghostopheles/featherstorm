import httpx
import asyncio

from typing import Optional, Callable, Awaitable

from league.reporting import ProgressReporter, NullReporter

REPLAY_API_URL = "https://127.0.0.1:2999/replay"

LAUNCH_POLL_INTERVAL = 1
LAUNCH_TIMEOUT = 60
DEFAULT_SEEK_BUFFER = 0  # seconds to seek before the event timestamp to account for loading times
DEFAULT_CAMERA_FOV = 60

CAMERA_SELECTION_OFFSET = {"x": 0, "y": 2200, "z": -1400}

HIDDEN_UI_SETTINGS = {
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
}


class ReplayAPIClient:
    """Client for the in-game Replay API, only reachable while a replay is running."""

    def __init__(self, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter or NullReporter()
        self.client = httpx.AsyncClient(
            base_url=REPLAY_API_URL,
            http2=True,
            verify=False,
            timeout=httpx.Timeout(10.0, read=300.0),
        )

    # unlike BaseAPIClient this raises, since the waiters rely on ConnectError propagating
    async def _request(self, method: str, endpoint: str, **kwargs):
        res = await self.client.request(method, endpoint, **kwargs)
        res.raise_for_status()
        return res.json() if res.content else None

    async def close(self):
        await self.client.aclose()

    async def wait_for(self, func: Callable[[], Awaitable[bool]], timeout: Optional[float] = LAUNCH_TIMEOUT):
        """Polls `func` until it returns True. `timeout=None` waits forever."""
        deadline = asyncio.get_event_loop().time() + timeout if timeout is not None else None
        while deadline is None or asyncio.get_event_loop().time() < deadline:
            try:
                if await func():
                    return
            except httpx.ConnectError:
                self.reporter.message("Failed to connect to replay API")
            except httpx.HTTPStatusError:
                pass
            await asyncio.sleep(LAUNCH_POLL_INTERVAL)
        raise TimeoutError("Waiting timeout")

    async def wait_until_ready(self, timeout: float = LAUNCH_TIMEOUT):
        async def check():
            res = await self.client.get("/playback")
            return res.is_success

        return await self.wait_for(check, timeout)

    async def wait_for_seek(self):
        async def check():
            playback = await self.get_playback()
            return playback.get("seeking") == False

        return await self.wait_for(check)

    async def wait_for_recording(self, timeout: Optional[float] = LAUNCH_TIMEOUT):
        async def check():
            recording = await self.get_recording()
            return recording.get("recording") == False

        return await self.wait_for(check, timeout)

    async def get_game(self) -> dict:
        return await self._request("GET", "/game")

    async def get_pid(self) -> int:
        game = await self.get_game()
        return game.get("processID")

    async def get_playback(self) -> dict:
        return await self._request("GET", "/playback")

    async def update_playback(self, **kwargs) -> dict:
        return await self._request("POST", "/playback", json=kwargs)

    async def pause(self) -> dict:
        return await self.update_playback(paused=True)

    async def resume(self) -> dict:
        return await self.update_playback(paused=False)

    async def toggle_playback(self) -> bool:
        """Pauses if playing, resumes if paused. Returns the new paused state."""
        paused = not (await self.get_playback()).get("paused")
        await self.update_playback(paused=paused)
        return paused

    async def set_speed(self, speed: float) -> dict:
        return await self.update_playback(speed=speed)

    async def seek_to(self, timestamp: float, buffer: float = DEFAULT_SEEK_BUFFER) -> dict:
        return await self.update_playback(paused=True, seeking=True, speed=1.0, time=timestamp - buffer)

    async def seek_by(self, offset: float) -> float:
        """Seeks `offset` seconds from the current time (negative goes back), clamped to the game length. Returns the target time."""
        playback = await self.get_playback()
        target = max(0.0, playback.get("time", 0) + offset)
        length = playback.get("length")
        if length is not None:
            target = min(target, length)
        await self.seek_to(target)
        return target

    async def apply_sequence(self, sequence: dict) -> dict:
        return await self._request("POST", "/sequence", json=sequence)

    async def get_render(self) -> dict:
        return await self._request("GET", "/render")

    async def update_render(self, **kwargs) -> dict:
        return await self._request("POST", "/render", json=kwargs)

    async def move_camera_to(self, x: float, y: float, fov: int = DEFAULT_CAMERA_FOV) -> dict:
        return await self.update_render(cameraPosition={"x": x, "y": y}, fieldOfView=fov)

    async def follow_player(self, name: str, offset: dict = CAMERA_SELECTION_OFFSET) -> dict:
        return await self.update_render(cameraMode="fps", cameraAttached=True, selectionName=name, selectionOffset=offset)

    async def hide_ui(self) -> dict:
        return await self.update_render(**HIDDEN_UI_SETTINGS)

    async def get_recording(self) -> dict:
        return await self._request("GET", "/recording")

    async def start_recording(
        self,
        file_path: Optional[str],
        start_time: float,
        end_time: float,
        width: int = 2560,
        height: int = 1440,
        fps: int = 60,
        lossless: bool = False,
        codec: str = "webm",
        enforce_frame_rate: bool = False,
    ) -> dict:
        """`file_path=None` lets the game client record into its default replay directory."""
        body = {
            "recording": True,
            "codec": codec,
            "lossless": lossless,
            "width": width,
            "height": height,
            "startTime": start_time,
            "endTime": end_time,
            "framesPerSecond": fps,
            "enforceFrameRate": enforce_frame_rate,
        }
        if file_path is not None:
            body["path"] = file_path

        return await self._request("POST", "/recording", json=body)

    async def stop_recording(self) -> dict:
        return await self._request("POST", "/recording", json={"recording": False})

    async def toggle_recording(self, file_path: Optional[str] = None, **kwargs) -> tuple[bool, dict]:
        """Stops an active recording, otherwise records from the current time to the end of the game.
        Returns `(started, state)` — `state` is the pre-stop recording state when stopping, so its `path` is still set."""
        recording = await self.get_recording()
        if recording.get("recording"):
            await self.stop_recording()
            return False, recording

        playback = await self.get_playback()
        # the Replay API only captures frames while the replay is playing
        await self.resume()
        state = await self.start_recording(file_path, playback.get("time", 0), playback.get("length"), **kwargs)
        return True, state or {}
