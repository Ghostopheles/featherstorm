from typing import Callable, Any

from rich.theme import Theme
from rich.console import Console

DARK_XAYAH = "#840e3e"
XAYAH = "#b01d5d"

DARK_RAKAN = "magenta"
RAKAN = "#cba6f7"

GOLD = "#c3a17c"

THEME = Theme({
    "xayah": XAYAH,
    "dark_xayah": DARK_XAYAH,
    "rakan": RAKAN,
    "dark_rakan": DARK_RAKAN,
    "featherstorm": f"bold {XAYAH}",
    "heading": f"bold {RAKAN}",
    "highlights": f"bold {RAKAN}",
    "highlights_match_id": "bold blue",
    "warning": f"bold underline {XAYAH}"
})

console = Console(theme=THEME)
err_console = Console(theme=THEME, stderr=True)

def print(*args, **kwargs):
    return console.print(*args, **kwargs)

def print_err(*args, **kwargs):
    return err_console.print(*args, **kwargs)

def get_printer(prefix: str) -> Callable[[Any], None]:
    def _print(*args, **kwargs):
        console.print(prefix, *args, **kwargs)
    return _print
