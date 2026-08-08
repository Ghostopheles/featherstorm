from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QLabel

from league.bladecaller.resources.theme import RADIUS_SM
from league.bladecaller.ui.icons import display_champion_name, icons, run_async


class ChampionIcon(QLabel):
    """Square champion portrait, falling back to the first two letters of the name.

    The art arrives asynchronously, so the letter placeholder renders first and is
    replaced once the DataDragon square lands.
    """

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self.setObjectName("championIcon")
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)

        self._size = size
        font = self.font()
        font.setPointSize(max(7, int(size * 0.28)))
        font.setBold(True)
        self.setFont(font)

        self._set_placeholder(None)

    def set_champion(self, champion_id: int | None = None, champion_name: str | None = None):
        self._set_placeholder(champion_name)
        if champion_id is None and champion_name is None:
            return
        run_async(self._load(champion_id, champion_name))

    async def _load(self, champion_id: int | None, champion_name: str | None):
        provider = icons()

        name = champion_name
        if name is None and champion_id is not None:
            name = await provider.champion_name(champion_id)
            if name:
                self._set_placeholder(name)

        if not name:
            return

        pixmap = await provider.champion_pixmap(name, self._size)
        if pixmap is not None:
            self.setText("")
            self.setPixmap(_rounded(pixmap, RADIUS_SM))

    def _set_placeholder(self, name: str | None):
        self.clear()
        self.setText(name[:2].upper() if name else "?")
        self.setToolTip(display_champion_name(name) or "")


def _rounded(pixmap: QPixmap, radius: int) -> QPixmap:
    """QSS `border-radius` doesn't clip a QLabel's pixmap — the corners get masked here."""
    out = QPixmap(pixmap.size())
    out.setDevicePixelRatio(pixmap.devicePixelRatio())
    out.fill(Qt.transparent)

    path = QPainterPath()
    path.addRoundedRect(QRectF(pixmap.rect()), radius, radius)

    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return out
