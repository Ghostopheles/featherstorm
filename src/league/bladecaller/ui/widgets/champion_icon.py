from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from league.bladecaller.ui.icons import icons, run_async


class ChampionIcon(QLabel):
    """Square champion portrait, falling back to the first two letters of the name.

    The art arrives asynchronously — and today never does, since the DataDragon
    URL builders in `ui/icons.py` are stubs — so the letter placeholder is what
    renders until those land. No change here is needed when they do.
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
            self.setPixmap(pixmap)

    def _set_placeholder(self, name: str | None):
        self.clear()
        self.setText(name[:2].upper() if name else "?")
        self.setToolTip(name or "")
