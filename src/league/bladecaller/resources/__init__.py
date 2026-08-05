from string import Template
from importlib.resources import files
from importlib.metadata import version, PackageNotFoundError

from PySide6.QtGui import QIcon, QFontDatabase

from league.bladecaller.resources import theme

_ROOT = files("league.bladecaller.resources")


def icon_path(name: str) -> str:
    return str(_ROOT.joinpath("icons", name)).replace("\\", "/")


def load_icon(name: str) -> QIcon:
    return QIcon(icon_path(name))


def load_fonts() -> None:
    """Register the bundled Inter / Barlow Semi Condensed faces with Qt."""
    fonts = _ROOT.joinpath("fonts")
    for entry in fonts.iterdir():
        if entry.name.endswith(".ttf"):
            QFontDatabase.addApplicationFont(str(entry))


def app_version() -> str:
    try:
        return f"v{version('featherstorm')}"
    except PackageNotFoundError:
        return "dev"


def load_stylesheet() -> str:
    tokens = dict(theme.TOKENS)
    tokens.update({
        "ICON_CHEVRON": icon_path("chevron-down.svg"),
        "ICON_CHEVRON_UP": icon_path("chevron-up.svg"),
        "ICON_CHECK": icon_path("check.svg"),
    })
    qss = _ROOT.joinpath("app.qss").read_text(encoding="utf-8")
    return Template(qss).substitute(tokens)
