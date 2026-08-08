"""Async, disk-cached pixmap loader for champion / item / spell art.

Champion squares come from `DataDragon.get_art_by_champion_name(..., square)`. The
item and spell fetchers at the bottom are still **stubs** — `DataDragon` has no
item/spell/rune icon fetchers yet, so they return `None` and those callers fall
back to their placeholder. Filling them in needs no widget changes.
"""

import re
import asyncio

from pathlib import Path
from typing import Awaitable, Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from league import config
from league.dragon import ArtAssetType, DataDragon

_provider: Optional["IconProvider"] = None

# split before an upper-case letter that follows a lower-case one, or that starts a
# word after an acronym — "MissFortune" → "Miss Fortune", "JarvanIV" → "Jarvan IV"
_CHAMPION_WORD_BREAK = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

# every champion whose display name the split above can't reach — punctuation the
# Data Dragon key drops, or a name that isn't the key at all
_CHAMPION_DISPLAY_NAMES = {
    "Belveth": "Bel'Veth",
    "Chogath": "Cho'Gath",
    "DrMundo": "Dr. Mundo",
    "Kaisa": "Kai'Sa",
    "Khazix": "Kha'Zix",
    "KogMaw": "Kog'Maw",
    "KSante": "K'Sante",
    "Leblanc": "LeBlanc",
    "MonkeyKing": "Wukong",
    "Nunu": "Nunu & Willump",
    "RekSai": "Rek'Sai",
    "Renata": "Renata Glasc",
    "Velkoz": "Vel'Koz",
}


def display_champion_name(name: str | None) -> str | None:
    """Champion key as shown to the user. Never feed this back to Data Dragon —
    art URLs and id lookups need the unsplit key."""
    if not name:
        return name
    override = _CHAMPION_DISPLAY_NAMES.get(name)
    return override if override is not None else _CHAMPION_WORD_BREAK.sub(" ", name)


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
        self._dragon_lock = asyncio.Lock()
        self._names_lock = asyncio.Lock()

    async def close(self):
        if self._dragon is not None:
            dragon, self._dragon = self._dragon, None
            await dragon.client.aclose()

    async def champion_name(self, champion_id: int) -> str | None:
        cached = self._names.get(champion_id)
        if cached is not None:
            return cached

        # a page of rows asks for ~20 names at once; without the lock every one of
        # them misses the DataDragon lookup cache and refetches champion.json
        async with self._names_lock:
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
        return await self._pixmap(f"champion/{name}", size, lambda d: _champion_square(d, name))

    async def item_pixmap(self, item_id: int, size: int) -> QPixmap | None:
        if not item_id:
            return None
        return await self._pixmap(f"item/{item_id}", size, lambda d: _item_icon(d, item_id))

    async def spell_pixmap(self, spell_id: int, size: int) -> QPixmap | None:
        if not spell_id:
            return None
        return await self._pixmap(f"spell/{spell_id}", size, lambda d: _spell_icon(d, spell_id))

    async def _pixmap(self, key: str, size: int, fetch: Callable[[DataDragon], Awaitable[bytes | None]]) -> QPixmap | None:
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
            try:
                data = await fetch(dragon)
            except Exception:
                return None
            if not data:
                return None
            self._write_cached(filename, data)

        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return None

        pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._memory[memory_key] = pixmap
        return pixmap

    async def _get_dragon(self) -> DataDragon:
        # the lock is load-bearing: every caller awaits before `self._dragon` is
        # assigned, so an unguarded check builds one DataDragon *per row* — and
        # httpx.AsyncClient's constructor blocks ~0.4s building an SSL context
        # from the Windows cert store, freezing the GUI for the whole page
        async with self._dragon_lock:
            if self._dragon is None:
                dragon = await asyncio.to_thread(DataDragon)
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


# ── Fetchers — item/spell are stubs until the DataDragon fetchers land ─────────


async def _champion_square(dragon: DataDragon, champion_name: str) -> bytes | None:
    return await dragon.get_art_by_champion_name(champion_name, asset_type=ArtAssetType.square)


async def _item_icon(dragon: DataDragon, item_id: int) -> bytes | None:
    return None


async def _spell_icon(dragon: DataDragon, spell_id: int) -> bytes | None:
    return None
