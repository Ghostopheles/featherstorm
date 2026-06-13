from league import config

config.init()

from league.cli.main import app  # noqa: E402

__all__ = ["app"]
