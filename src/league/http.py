import json
import time
import httpx
import asyncio

from league.console import log_error, format_url


class BaseAPIClient:
    client: httpx.AsyncClient

    async def _make_request(self, method, *args, no_json: bool = False, _return_exception: bool = False, _suppress_exception: bool = False, **kwargs):
        try:
            res = await self.client.request(method, *args, **kwargs)
            res.raise_for_status()

            if no_json:
                return res

            try:
                return res.json()
            except json.decoder.JSONDecodeError:
                if res.status_code != 204 and not _suppress_exception:
                    log_error(f"[error]JSON decode error from {format_url(res.request.url)}[/]")
                return None
        except httpx.HTTPStatusError as e:
            if not _suppress_exception:
                log_error(
                    f"[error]HTTP Status Error ({e.response.status_code}) from {format_url(e.request.url)}[/]: {str(e)}",
                    show_locals=False,
                    show_traceback=False,
                )
            return e if _return_exception else None
        except httpx.RequestError as e:
            if not _suppress_exception:
                log_error(
                    f"[error]HTTP Request Error ({type(e).__name__}) from {format_url(e.request.url)}[/]: {str(e)}", show_locals=False, show_traceback=False
                )
            return e if _return_exception else None

    async def get(self, *args, **kwargs):
        return await self._make_request("GET", *args, **kwargs)

    async def post(self, *args, **kwargs):
        return await self._make_request("POST", *args, **kwargs)

    async def close(self):
        await self.client.aclose()


class RiotRateLimiter:
    def __init__(self):
        # window_seconds -> (limit, reset_at_monotonic, count)
        self._windows: dict[int, tuple[int, float, int]] = {}
        self._lock = asyncio.Lock()

    def update(self, headers: httpx.Headers) -> None:
        limit_h = headers.get("X-App-Rate-Limit")
        count_h = headers.get("X-App-Rate-Limit-Count")
        if not limit_h or not count_h:
            return

        limits = self._parse(limit_h)  # {window: limit}
        counts = self._parse(count_h)  # {window: count}
        now = time.monotonic()

        for window, limit in limits.items():
            count = counts.get(window, 0)
            existing = self._windows.get(window)
            # Reset the window timer only when the count rolls back to a low value
            if existing is None or count <= existing[2]:
                reset_at = now + window
            else:
                reset_at = existing[1]
            self._windows[window] = (limit, reset_at, count)

    @staticmethod
    def _parse(header: str) -> dict[int, int]:
        out = {}
        for part in header.split(","):
            value, window = part.split(":")
            out[int(window)] = int(value)
        return out

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                wait = 0.0
                for window, (limit, reset_at, count) in self._windows.items():
                    if now >= reset_at:
                        continue  # window expired, count is stale
                    if count >= limit:
                        wait = max(wait, reset_at - now)
                if wait <= 0:
                    return
                await asyncio.sleep(wait)
