from typing import TYPE_CHECKING

from league.replay.api import ReplayAPIClient

if TYPE_CHECKING:
    from league.replay.manager import ReplayManager, normalize_match_id

__all__ = ["ReplayAPIClient", "ReplayManager", "normalize_match_id"]


# manager pulls in LCUClient -> DataDragon -> pydantic models (~120ms); load it only when asked for
# so Replay API-only callers (e.g. `replay record start`) stay fast
def __getattr__(name: str):
    if name in ("ReplayManager", "normalize_match_id"):
        from league.replay import manager

        return getattr(manager, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
