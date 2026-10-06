import os
import signal
import asyncio
import logging

from pathlib import Path
from typing import Optional

from league.lcu.lcu import LCUClient
from league.replay.api import ReplayAPIClient, LAUNCH_TIMEOUT
from league.reporting import ProgressReporter, NullReporter
from league.lcu.models import LCUReplayState, LCUReplayDownloadStatus
from league.lcu.exceptions import LCUMissingReplayMetadataException, LCUIncompatibleReplayException

log = logging.getLogger(__name__)

DOWNLOAD_POLL_ATTEMPTS = 10
DOWNLOAD_POLL_INTERVAL = 1


def normalize_match_id(match_id: str | int) -> int:
    """Strips the platform prefix Riot API match IDs carry (`NA1_123` -> `123`), since the LCU doesn't use it."""
    if isinstance(match_id, int):
        return match_id
    return int(str(match_id).rsplit("_", 1)[-1])


class ReplayManager:
    """Handles replay files through the LCU (metadata, download, launch) and the running replay via `api`."""

    def __init__(self, client_install_path: Path, lcu: Optional[LCUClient] = None, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter or NullReporter()
        self.lcu = lcu or LCUClient(client_install_path)
        self.api = ReplayAPIClient(self.reporter)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        await self.api.close()
        await self.lcu.close()

    async def resolve_match_id(self, match_id: str | int | None = None) -> int:
        if match_id is None:
            return await self.lcu.get_last_match_id()
        return normalize_match_id(match_id)

    async def get_metadata(self, match_id: str | int) -> Optional[dict]:
        match_id = normalize_match_id(match_id)
        return await self.lcu.get(f"/lol-replays/v1/metadata/{match_id}")

    async def create_metadata(self, match_id: str | int):
        match_id = normalize_match_id(match_id)
        return await self.lcu.post(f"/lol-replays/v2/metadata/{match_id}/create")

    async def get_state(self, match_id: str | int) -> Optional[LCUReplayState]:
        metadata = await self.get_metadata(match_id)
        if metadata is None:
            return None

        state = metadata.get("state")
        try:
            return LCUReplayState(state)
        except ValueError:
            log.warning(f"Unknown replay state: {state}")
            return None

    async def download(self, match_id: str | int) -> LCUReplayDownloadStatus:
        match_id = normalize_match_id(match_id)

        async def start_download():
            return await self.lcu.post(f"/lol-replays/v1/rofls/{match_id}/download/graceful", json={"gameId": match_id}, no_json=True)

        async def check_download() -> LCUReplayDownloadStatus:
            match await self.get_state(match_id):
                case LCUReplayState.Watch:
                    return LCUReplayDownloadStatus.Success
                case LCUReplayState.Retry:
                    return LCUReplayDownloadStatus.Retry
                case LCUReplayState.Incompatible | LCUReplayState.Unsupported | LCUReplayState.MissingOrExpired:
                    return LCUReplayDownloadStatus.Failed
                case _:
                    return LCUReplayDownloadStatus.Downloading

        if await self.get_metadata(match_id) is None:
            await self.create_metadata(match_id)

        download_state = LCUReplayDownloadStatus.NotStarted
        res = await start_download()
        log.debug(f"replay download start status: {getattr(res, 'status_code', None)}")
        for _ in range(DOWNLOAD_POLL_ATTEMPTS):
            download_state = await check_download()
            match download_state:
                case LCUReplayDownloadStatus.Success:
                    break
                case LCUReplayDownloadStatus.Failed:
                    raise LCUIncompatibleReplayException(match_id)
                case LCUReplayDownloadStatus.Downloading:
                    await asyncio.sleep(DOWNLOAD_POLL_INTERVAL)
                case LCUReplayDownloadStatus.NotStarted | LCUReplayDownloadStatus.Retry:
                    start_res = await start_download()
                    log.debug(f"replay download retry status: {getattr(start_res, 'status_code', None)}")

        return download_state

    async def open(self, match_id: str | int):
        match_id = normalize_match_id(match_id)
        metadata = await self.get_metadata(match_id)

        if metadata is None:
            await self.create_metadata(match_id)
            metadata = await self.get_metadata(match_id)

        if metadata is None:
            raise LCUMissingReplayMetadataException(match_id)

        if metadata.get("state") != LCUReplayState.Watch:
            status = await self.download(match_id)
            log.debug(f"replay download status: {status}")

        return await self.lcu.post(f"/lol-replays/v1/rofls/{match_id}/watch", json={"gameId": match_id})

    async def open_and_wait(self, match_id: str | int, timeout: float = LAUNCH_TIMEOUT):
        await self.open(match_id)
        await self.api.wait_until_ready(timeout)

    async def close_active(self):
        pid = await self.api.get_pid()
        if pid is not None:
            os.kill(pid, signal.SIGTERM)
