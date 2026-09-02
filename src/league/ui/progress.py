from typing import Iterator, Optional
from contextlib import contextmanager

from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    SpinnerColumn,
    MofNCompleteColumn,
    TimeElapsedColumn,
)

from league.ui.output import Output, output as default_output


class RichProgressReporter:
    """Terminal implementation of league.reporting.ProgressReporter."""

    def __init__(self, output: Optional[Output] = None, prefix: str = ""):
        self._output = output or default_output
        self._prefix = prefix
        self._progress: Optional[Progress] = None
        self._task_id = None
        self._indeterminate = False

    def message(self, text: str) -> None:
        console = self._progress.console if self._progress else self._output.console
        console.print(f"{self._prefix}{text}" if self._prefix else text)

    def step(self, text: str) -> None:
        if self._progress is None or self._indeterminate is False:
            return
        self._progress.update(self._task_id, description=text)

    def advance(self, amount: int = 1) -> None:
        if self._progress is None or self._indeterminate:
            return
        self._progress.update(self._task_id, advance=amount)

    @contextmanager
    def task(self, description: str = "", total: Optional[int] = None) -> Iterator[None]:
        if total is None:
            progress = self._output.progress(
                SpinnerColumn(spinner_name="simpleDotsScrolling", style="featherstorm"),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                transient=True,
            )
        else:
            progress = self._output.progress(
                BarColumn(bar_width=None, pulse_style="featherstorm"),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TextColumn(f"[featherstorm]{description}[/]"),
                expand=True,
            )

        with progress:
            self._progress = progress
            self._indeterminate = total is None
            self._task_id = progress.add_task(description, total=total)
            try:
                yield
            finally:
                self._progress = None
                self._task_id = None
                self._indeterminate = False
