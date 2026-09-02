import logging

from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from league.ui.console import get_console

QUIET_LOGGERS = ("httpx", "httpcore", "websockets", "asyncio")


def setup_logging(level: int = logging.INFO, console: Optional[Console] = None) -> None:
    handler = RichHandler(
        console=console or get_console(),
        markup=True,
        rich_tracebacks=True,
        show_path=False,
        log_time_format="[%X]",
    )
    logging.basicConfig(level=level, format="%(message)s", handlers=[handler], force=True)

    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
