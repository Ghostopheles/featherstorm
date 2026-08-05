import inspect
import asyncio

from typing import Callable, Any
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, TextColumn, BarColumn

from league import config
from league.models import GameEvent
from league.api import LeagueClient
from league.enums import GameEventType, LeagueClientStatus
from league.console import log, log_warning, console

type SessionCallback = Callable[[], Any]
type EventCallback = Callable[[GameEvent], Any]

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

    def __init__(self, client: LeagueClient, exit_on_timeout: bool = True):
        self._client = client
        self._exit_on_timeout = exit_on_timeout
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
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(pulse_style="featherstorm"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[yellow]Polling[/]", total=None)
            start = progress.get_time()
            while not progress.finished:
                elapsed = progress.get_time() - start
                if elapsed >= SESSION_TIMEOUT:
                    return False

                status = await self._client.get_client_status()
                if status == LeagueClientStatus.DISCONNECTED:
                    progress.update(task, description="[yellow]Waiting for client[/]")
                elif status == LeagueClientStatus.LOADING:
                    progress.update(task, description="[yellow]Waiting for match[/]")
                else:
                    progress.update(task, description="[green]Done![/]", total=1, completed=1)

                if self._is_reconnecting:
                    if self._retries >= MAX_RECONNECT_ATTEMPTS:
                        return None
                    self._retries += 1

                await asyncio.sleep(WAIT_INTERVAL)
            return True

    async def _poll_session(self):
        while True:
            status = await self._client.get_client_status()
            if status == LeagueClientStatus.BANISHED:
                log("[warning]League client disconnected - retrying.[/]")
                self._is_reconnecting = await self._should_try_reconnect()
                self._retries = 0
                return

            await self._client.poll_events()
            await asyncio.sleep(POLL_INTERVAL)

    async def run(self):
        while True:
            connected = await self._wait_for_session()
            if connected:  # we've exhausted our retries, or gracefully disconnected
                verb = f"reconnected after [highlight]{self._retries}[/highlight] attempt(s)" if self._is_reconnecting else "connected"
                log(f"[green]League client {verb}.[/]")
            elif self._is_reconnecting:
                self._is_reconnecting = False
                log_warning(f"[warning]Failed to reconnect to League client after [highlight]{self._retries}[/highlight] attempt(s)[/]")
                break
            else:
                if not self._exit_on_timeout:
                    continue
                log(f"League client disconnected.")
                break

            await self._fire(self._session_start_callbacks)
            await self._poll_session()
            await self._fire(self._session_end_callbacks)
