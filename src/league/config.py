import copy
import toml
import typer

from pathlib import Path
from typing import Any

from league.constants import APP_NAME

APP_DIR = Path(typer.get_app_dir(APP_NAME, roaming=False))
CONFIG_PATH = APP_DIR / "cfg.toml"

DEFAULT_CONFIG = {
    "lcu": {"client_install_path": "F:/Games/Riot Games/League of Legends"},
    "govee": {"default_power_state": True, "default_brightness": 100, "request_timeout": 0.5},
    "chroma": {"teammate_dim_factor": 0.4},
    "companion": {"default_player_name": "Dallas N Tollway", "default_player_tagline": "uwu"},
}

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        with open(CONFIG_PATH) as f:
            _cache = toml.load(f)
    return _cache


def _write() -> None:
    with open(CONFIG_PATH, "w") as f:
        toml.dump(_cache, f)


def _merge_defaults(cfg: dict, defaults: dict) -> bool:
    """Recursively add missing keys from defaults into cfg. Returns True if any were added."""
    changed = False
    for key, value in defaults.items():
        if key not in cfg:
            cfg[key] = copy.deepcopy(value)
            changed = True
        elif isinstance(value, dict) and isinstance(cfg[key], dict):
            changed |= _merge_defaults(cfg[key], value)
    return changed


def get_full_config():
    return _load()


def init(force: bool = False) -> bool:
    """Create config from defaults if missing. Returns True if created/reset."""
    global _cache
    if force or not CONFIG_PATH.is_file():
        APP_DIR.mkdir(parents=True, exist_ok=True)
        _cache = copy.deepcopy(DEFAULT_CONFIG)
        _write()
        return True
    if _merge_defaults(_load(), DEFAULT_CONFIG):
        _write()
    return False


def get(key: str, category: str | None = None) -> Any:
    cfg = _load()
    return cfg[category][key] if category else cfg[key]


def set(key: str, value: Any, category: str | None = None) -> None:
    cfg = _load()
    if category:
        cfg.setdefault(category, {})[key] = value
    else:
        cfg[key] = value
    _write()
