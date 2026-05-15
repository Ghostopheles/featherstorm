import copy
import toml
import typer

from typing import Any
from pathlib import Path
from contextlib import contextmanager

from league.constants import APP_NAME

APP_DIR = Path(typer.get_app_dir(APP_NAME, roaming=False))
CONFIG_PATH = APP_DIR / "cfg.toml"

DEFAULT_CONFIG = {
    "lcu": {"client_install_path": "F:/Games/Riot Games/League of Legends"},
    "govee": {"default_power_state": True, "default_brightness": 100, "request_timeout": 0.5},
    "chroma": {"teammate_dim_factor": 0.4},
    "companion": {"default_player_name": "Dallas N Tollway", "default_player_tagline": "uwu", "govee_enabled": False},
}

_cache: dict | None = None
_mtime: float = 0.0
_batch_depth: int = 0
_dirty: bool = False


def _resolve(key: str, category: str | None) -> tuple[str, str]:
    if category is not None:
        return category, key
    if "." in key:
        cat, _, k = key.partition(".")
        return cat, k
    raise ValueError(f"No category for {key!r} — use dot notation or pass category")


def _load() -> dict:
    global _cache, _mtime
    try:
        mtime = CONFIG_PATH.stat().st_mtime
    except FileNotFoundError:
        mtime = 0.0
    if _cache is None or mtime != _mtime:
        with open(CONFIG_PATH) as f:
            _cache = toml.load(f)
        _mtime = mtime
    return _cache


def _write() -> None:
    global _dirty, _mtime
    if _batch_depth > 0:
        _dirty = True
        return
    with open(CONFIG_PATH, "w") as f:
        toml.dump(_cache, f)
    _mtime = CONFIG_PATH.stat().st_mtime
    _dirty = False


@contextmanager
def batch():
    global _batch_depth, _dirty
    _batch_depth += 1
    try:
        yield
    finally:
        _batch_depth -= 1
        if _batch_depth == 0 and _dirty:
            _write()


def _merge_defaults(cfg: dict, defaults: dict) -> bool:
    changed = False
    for key, value in defaults.items():
        if key not in cfg:
            cfg[key] = copy.deepcopy(value)
            changed = True
        elif isinstance(value, dict) and isinstance(cfg[key], dict):
            changed |= _merge_defaults(cfg[key], value)
    return changed


def get_full_config() -> dict:
    return _load()


def init(force: bool = False) -> bool:
    global _cache
    if force or not CONFIG_PATH.is_file():
        APP_DIR.mkdir(parents=True, exist_ok=True)
        _cache = copy.deepcopy(DEFAULT_CONFIG)
        _write()
        return True
    if _merge_defaults(_load(), DEFAULT_CONFIG):
        _write()
    return False


def get_category(category: str) -> Any:
    return _load().get(category)


def get(key: str, category: str | None = None) -> Any:
    cat, k = _resolve(key, category)
    section = _load().get(cat)
    if section is None:
        return None
    return section.get(k)


def get_str(key: str, category: str | None = None, default: str | None = None) -> str | None:
    val = get(key, category)
    return str(val) if val is not None else default


def get_int(key: str, category: str | None = None, default: int | None = None) -> int | None:
    val = get(key, category)
    return int(val) if val is not None else default


def get_float(key: str, category: str | None = None, default: float | None = None) -> float | None:
    val = get(key, category)
    return float(val) if val is not None else default


def get_bool(key: str, category: str | None = None, default: bool | None = None) -> bool | None:
    val = get(key, category)
    return bool(val) if val is not None else default


def get_or_set(key: str, category: str | None = None, default: Any = None) -> Any:
    val = get(key, category)
    if val is None and default is not None:
        set(key, default, category)
        return default
    return val


def set(key: str, value: Any, category: str | None = None) -> None:
    cat, k = _resolve(key, category)
    cfg = _load()
    cfg.setdefault(cat, {})[k] = value
    _write()


def delete(key: str, category: str | None = None) -> None:
    cat, k = _resolve(key, category)
    cfg = _load()
    cfg.get(cat, {}).pop(k, None)
    _write()


class ConfigSection:
    def __init__(self, category: str):
        self._cat = category

    def get(self, key: str, default: Any = None) -> Any:
        val = globals()["get"](key, self._cat)
        return val if val is not None else default

    def get_str(self, key: str, default: str | None = None) -> str | None:
        return get_str(key, self._cat, default)

    def get_int(self, key: str, default: int | None = None) -> int | None:
        return get_int(key, self._cat, default)

    def get_float(self, key: str, default: float | None = None) -> float | None:
        return get_float(key, self._cat, default)

    def get_bool(self, key: str, default: bool | None = None) -> bool | None:
        return get_bool(key, self._cat, default)

    def set(self, key: str, value: Any) -> None:
        globals()["set"](key, value, self._cat)

    def delete(self, key: str) -> None:
        globals()["delete"](key, self._cat)

    def all(self) -> dict:
        return get_category(self._cat) or {}


def section(category: str) -> ConfigSection:
    return ConfigSection(category)
