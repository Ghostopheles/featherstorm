import asyncio

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from league import config
from league.lcu import LCUClient
from league.lcu.models import LCUGameflowPhase
from league.bladecaller.core.status import ClientStatus

DEFAULT_POLL_INTERVAL = 3.0

IN_MATCH_PHASES = {LCUGameflowPhase.InProgress}


class ClientStatusController(QObject):
    """Polls the LCU gameflow phase and reports a `ClientStatus`.

    Emits `status_changed` only on transitions. Runs on the qasync loop, so the
    signal is already delivered on the GUI thread.

    Status comes from the gameflow phase rather than the Live Client API: probing
    `127.0.0.1:2999` costs ~2s per poll when no game is running (Windows doesn't
    promptly refuse the closed loopback port), while the phase answers in ~3ms and
    also reports `InProgress` during the load screen.
    """

    status_changed = Signal(ClientStatus)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lcu: LCUClient | None = None
        self._status = ClientStatus.DISCONNECTED
        self._interval = config.get_float("bladecaller.status_poll_interval", default=DEFAULT_POLL_INTERVAL)
        self._task: asyncio.Task | None = None

    @property
    def status(self) -> ClientStatus:
        return self._status

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.ensure_future(self._loop())

    def stop(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def close(self):
        self.stop()
        await self._drop_lcu()

    async def _loop(self):
        while True:
            status = await self.poll_once()
            if status != self._status:
                self._status = status
                self.status_changed.emit(status)
            await asyncio.sleep(self._interval)

    async def poll_once(self) -> ClientStatus:
        phase = await self._get_phase()
        if phase is None:
            return ClientStatus.DISCONNECTED
        return ClientStatus.IN_MATCH if phase in IN_MATCH_PHASES else ClientStatus.CONNECTED

    async def _get_phase(self) -> LCUGameflowPhase | None:
        if self._lcu is None:
            try:
                self._lcu = LCUClient(client_install_path=Path(config.get("lcu.client_install_path")))
            except Exception:
                return None
        try:
            # a failed request yields None, which LCUGameflowPhase() rejects
            return await self._lcu.get_gameflow_phase()
        except Exception:
            # client exited, or the lockfile went stale — rebuild on the next poll
            await self._drop_lcu()
            return None

    async def _drop_lcu(self):
        if self._lcu is None:
            return
        lcu, self._lcu = self._lcu, None
        await lcu.client.aclose()
        await lcu.dragon.client.aclose()
