from typing import Protocol, Iterator, Optional
from contextlib import contextmanager, AbstractContextManager


class ProgressReporter(Protocol):
    """Backend-facing progress channel. Implementations live in the ui layer."""

    def message(self, text: str) -> None: ...

    def step(self, text: str) -> None: ...

    def advance(self, amount: int = 1) -> None: ...

    def task(self, description: str = "", total: Optional[int] = None) -> AbstractContextManager[None]: ...


class NullReporter:
    def message(self, text: str) -> None:
        pass

    def step(self, text: str) -> None:
        pass

    def advance(self, amount: int = 1) -> None:
        pass

    @contextmanager
    def task(self, description: str = "", total: Optional[int] = None) -> Iterator[None]:
        yield
