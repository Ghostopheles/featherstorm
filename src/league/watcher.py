import time
import inspect
import asyncio
import logging

from typing import Callable, Any

from league import config
from league.models import GameEvent
from league.api import LeagueClient
from league.reporting import ProgressReporter, NullReporter
from league.enums import GameEventType, LeagueClientStatus

type SessionCallback = Callable[[], Any]
type EventCallback = Callable[[GameEvent], Any]

log = logging.getLogger(__name__)

MAX_RECONNECT_ATTEMPTS = config.get_int("companion.max_reconnect_attempts", default=5)
WAIT_INTERVAL = config.get_float("companion.wait_interval", default=2.0)
POLL_INTERVAL = config.get_float("companion.poll_interval", default=0.25)
SESSION_TIMEOUT = config.get_float("companion.session_timeout", default=30.0)


class MatchWatcher:
    _client: LeagueClient
    _session_start_callbacks: list[SessionCallback]
    _session_end_callbacks: list[SessionCallback]
    _retries: int = 0
    _is_reconnecting: bool = False

    def __init__(self, client: LeagueClient, exit_on_timeout: bool = True, reporter: ProgressReporter | None = None):
        self._client = client
        self._exit_on_timeout = exit_on_timeout
        self._reporter = reporter or NullReporter()
        self._session_start_callbacks = []
        self._session_end_callbacks = []

    def on(self, event_type: GameEventType, callback: EventCallback | None = None):
        if callback is None:

            def decorator(fn: EventCallback) -> EventCallback:
                self._client.on(event_type, fn)
                return fn

            return decorator
        self._client.on(event_type, callback)

    def on_session_start(self, callback: SessionCallback | None = None):
        if callback is None:

            def decorator(fn: SessionCallback) -> SessionCallback:
                self._session_start_callbacks.append(fn)
                return fn

            return decorator
        self._session_start_callbacks.append(callback)

    def on_session_end(self, callback: SessionCallback | None = None):
        if callback is None:

            def decorator(fn: SessionCallback) -> SessionCallback:
                self._session_end_callbacks.append(fn)
                return fn

            return decorator
        self._session_end_callbacks.append(callback)

    async def _fire(self, callbacks: list[SessionCallback]):
        for cb in callbacks:
            if inspect.iscoroutinefunction(cb):
                await cb()
            else:
                cb()

    async def _should_try_reconnect(self) -> bool:
        last = await self._client.get_last_event()
        if not last:
            return False

        return last.EventName != GameEventType.GameEnd

    async def _wait_for_session(self):
        with self._reporter.task("[yellow]Polling[/]"):
            start = time.monotonic()
            while True:
                if time.monotonic() - start >= SESSION_TIMEOUT:
                    return False

                status = await self._client.get_client_status()
                if status == LeagueClientStatus.DISCONNECTED:
                    self._reporter.step("[yellow]Waiting for client[/]")
                elif status == LeagueClientStatus.LOADING:
                    self._reporter.step("[yellow]Waiting for match[/]")
                else:
                    self._reporter.step("[green]Done![/]")
                    return True

                if self._is_reconnecting:
                    if self._retries >= MAX_RECONNECT_ATTEMPTS:
                        return None
                    self._retries += 1

                await asyncio.sleep(WAIT_INTERVAL)

    async def _poll_session(self):
        while True:
            status = await self._client.get_client_status()
            if status == LeagueClientStatus.BANISHED:
                log.warning("[warning]League client disconnected - retrying.[/]")
                self._is_reconnecting = await self._should_try_reconnect()
                self._retries = 0
                return

            await self._client.poll_events()
            await asyncio.sleep(POLL_INTERVAL)

    async def run(self):
        while True:
            connected = await self._wait_for_session()
            if connected:  # we've exhausted our retries, or gracefully disconnected
                verb = f"reconnected after [heading]{self._retries}[/heading] attempt(s)" if self._is_reconnecting else "connected"
                log.info(f"[green]League client {verb}.[/]")
            elif self._is_reconnecting:
                self._is_reconnecting = False
                log.warning(f"[warning]Failed to reconnect to League client after [heading]{self._retries}[/heading] attempt(s)[/]")
                break
            else:
                if not self._exit_on_timeout:
                    continue
                log.info("League client disconnected.")
                break

            await self._fire(self._session_start_callbacks)
            await self._poll_session()
            await self._fire(self._session_end_callbacks)
