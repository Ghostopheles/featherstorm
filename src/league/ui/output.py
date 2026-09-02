from typing import Any, Optional

from rich.status import Status
from rich.console import Console
from rich.progress import Progress, ProgressColumn

from league.ui.registry import render
from league.ui.console import get_console

SPINNER = "simpleDotsScrolling"
SPINNER_STYLE = "featherstorm"


class Output:
    """The only thing in the project that writes to the terminal."""

    def __init__(self, console: Optional[Console] = None):
        self._console = console or get_console()

    @property
    def console(self) -> Console:
        return self._console

    def print(self, *objects: Any, **kwargs) -> None:
        self._console.print(*(render(obj) for obj in objects), **kwargs)

    def json(self, *args, **kwargs) -> None:
        self._console.print_json(*args, **kwargs)

    def rule(self, title: str, style: str = "dark_xayah") -> None:
        self._console.rule(title, style=style)

    def info(self, message: str) -> None:
        self._console.print(message)

    def success(self, message: str) -> None:
        self._console.print(message, style="success")

    def warning(self, message: str) -> None:
        self._console.print(message, style="warning")

    def error(self, message: str) -> None:
        self._console.print(message, style="error")

    def prompt(self, message: str, **kwargs) -> str:
        return self._console.input(f"[featherstorm]{message}[/]: ", **kwargs)

    def status(self, message: str = "", *, spinner: str = SPINNER) -> Status:
        return self._console.status(message, spinner=spinner, spinner_style=SPINNER_STYLE)

    def progress(self, *columns: ProgressColumn, **kwargs) -> Progress:
        return Progress(*columns, console=self._console, **kwargs)


output = Output()
