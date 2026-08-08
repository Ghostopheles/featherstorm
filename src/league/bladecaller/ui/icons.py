"""Async, disk-cached pixmap loader for champion / item / spell art.

The loading, caching and scaling machinery is real. The three URL builders at the
bottom are **stubs** — `DataDragon` has no item/spell/rune icon fetchers yet, so
they return `None` and every caller falls back to its placeholder. Filling them in
is a one-line change each and needs no widget changes.
"""

import asyncio

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from league import config
from league.dragon import DataDragon

_provider: Optional["IconProvider"] = None


def icons() -> "IconProvider":
    """Process-wide provider, so the champion-name lookup and disk cache are shared."""
    global _provider
    if _provider is None:
        _provider = IconProvider()
    return _provider


class IconProvider:
    def __init__(self):
        self._dragon: DataDragon | None = None
        self._cache_dir: Path | None = None
        self._memory: dict[tuple[str, int], QPixmap] = {}
        self._names: dict[int, str] = {}

    async def close(self):
        if self._dragon is not None:
            dragon, self._dragon = self._dragon, None
            await dragon.client.aclose()

    async def champion_name(self, champion_id: int) -> str | None:
        cached = self._names.get(champion_id)
        if cached is not None:
            return cached
        try:
            dragon = await self._get_dragon()
            name = await dragon.get_champion_name(champion_id)
        except Exception:
            return None
        if name:
            self._names[champion_id] = name
        return name

    async def champion_pixmap(self, champion: int | str, size: int) -> QPixmap | None:
        name = champion if isinstance(champion, str) else await self.champion_name(champion)
        if not name:
            return None
        return await self._pixmap(f"champion/{name}", size, lambda d: _champion_square_url(d, name))

    async def item_pixmap(self, item_id: int, size: int) -> QPixmap | None:
        if not item_id:
            return None
        return await self._pixmap(f"item/{item_id}", size, lambda d: _item_icon_url(d, item_id))

    async def spell_pixmap(self, spell_id: int, size: int) -> QPixmap | None:
        if not spell_id:
            return None
        return await self._pixmap(f"spell/{spell_id}", size, lambda d: _spell_icon_url(d, spell_id))

    async def _pixmap(self, key: str, size: int, url_for: Callable[[DataDragon], str | None]) -> QPixmap | None:
        memory_key = (key, size)
        cached = self._memory.get(memory_key)
        if cached is not None:
            return cached

        try:
            dragon = await self._get_dragon()
        except Exception:
            return None

        filename = key.replace("/", "_") + ".png"
        data = self._read_cached(filename)

        if data is None:
            url = url_for(dragon)
            if url is None:
                return None
            try:
                response = await dragon.get_full_url(url, no_json=True)
                data = response.content
            except Exception:
                return None
            self._write_cached(filename, data)

        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return None

        pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._memory[memory_key] = pixmap
        return pixmap

    async def _get_dragon(self) -> DataDragon:
        if self._dragon is None:
            dragon = DataDragon()
            await dragon.initialize()
            self._dragon = dragon
            root = Path(config.get_str("cache_dir", "meta", "./data")) / "dragon" / (dragon.latest_version or "latest")
            self._cache_dir = root / "img"
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        return self._dragon

    def _read_cached(self, filename: str) -> bytes | None:
        if self._cache_dir is None:
            return None
        path = self._cache_dir / filename
        return path.read_bytes() if path.exists() else None

    def _write_cached(self, filename: str, data: bytes):
        if self._cache_dir is None:
            return
        (self._cache_dir / filename).write_bytes(data)


def run_async(coro):
    """Schedule a coroutine on the qasync loop.

    Falls back to the loop set by `ui/app.py` when none is running yet — widgets
    are often constructed before `run_forever()` starts, and a task created on a
    not-yet-running loop simply waits for it. With no loop at all (the offscreen
    render harness) the coroutine is dropped and placeholders are what render.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = _current_loop()

    if loop is None or loop.is_closed():
        coro.close()
        return None

    task = loop.create_task(coro)
    task.add_done_callback(_swallow)
    return task


def _current_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        return None


def _swallow(task: asyncio.Task):
    if not task.cancelled():
        task.exception()


# ── URL builders — stubs until the DataDragon fetchers land ────────────────────


def _champion_square_url(dragon: DataDragon, champion_name: str) -> str | None:
    return None


def _item_icon_url(dragon: DataDragon, item_id: int) -> str | None:
    return None


def _spell_icon_url(dragon: DataDragon, spell_id: int) -> str | None:
    return None
