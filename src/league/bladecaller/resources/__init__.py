from importlib.resources import files

from PySide6.QtGui import QIcon

def load_stylesheet() -> str:
    return files("league.bladecaller.resources").joinpath("app.qss").read_text(encoding="utf-8")

def load_icon(name: str) -> QIcon:
    path = files("league.bladecaller.resources").joinpath("icons", name)
    return QIcon(str(path))
