from rich.console import Console

from league.constants import APP_NAME
from league.ui.theme import THEME

console = Console(theme=THEME)
console.set_window_title(APP_NAME.title())


def get_console() -> Console:
    return console
