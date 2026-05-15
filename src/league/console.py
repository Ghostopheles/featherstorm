from rich.theme import Theme
from rich.console import Console

from pathlib import Path
from typing import Callable, Any, Union

DARK_XAYAH = "#840e3e"
XAYAH = "#b01d5d"

DARK_RAKAN = "magenta"
RAKAN = "#cba6f7"

GOLD = "#c3a17c"

THEME = Theme({
    "log.time": f"bold {GOLD}",
    "xayah": XAYAH,
    "dark_xayah": DARK_XAYAH,
    "rakan": RAKAN,
    "dark_rakan": DARK_RAKAN,
    "gold": GOLD,
    "featherstorm": f"bold {XAYAH}",
    "featherstorm_bg": f"on {XAYAH}",
    "heading": f"bold {RAKAN}",
    "highlights": f"bold {RAKAN}",
    "highlights_match_id": "bold blue",
    "eminence": f"bold {GOLD}",
    "file": f"bold underline {GOLD}",
    "url": f"bold underline {RAKAN}",
    "external_api": f"bold blue",
    "warning": f"bold underline red",
    "error": f"bold red"
})

console = Console(theme=THEME)
console.set_window_title("Featherstorm")

def print(*args, **kwargs):
    return console.print(*args, **kwargs)

def get_printer(prefix: str) -> Callable[[Any], None]:
    def _print(*args, **kwargs):
        console.print(prefix, *args, **kwargs)
    return _print

def format_file_path(path: Union[Path, str]):
    if isinstance(path, Path):
        path = path.as_posix()

    return f"[file][link=file://{path}]{path}[/link][/]"

def format_url(url: str, display_text: str | None = None):
    return f"[url][link={url}]{display_text or url}[/link][/]"

def log(*args, **kwargs):
    return console.log(*args, **kwargs)

def log_warning(*args, **kwargs):
    return console.log(*args, **kwargs, style="warning")

def log_error(msg: str, show_locals: bool = True, show_traceback: bool = True):
    if show_traceback:
        console.print_exception(show_locals=show_locals)
    return console.log(msg, log_locals=show_locals)
