from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget


class Card(QFrame):
    """Bordered surface with an optional uppercase title. `body` holds content.

    Hugs its contents unless `fill` is set, in which case it claims the leftover
    vertical space of its parent layout.
    """

    def __init__(self, title: str | None = None, fill: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Expanding if fill else QSizePolicy.Maximum,
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        if title:
            outer.addWidget(CardTitle(title))

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        outer.addLayout(self.body, 1)


class CardTitle(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setObjectName("cardTitle")


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str | None = None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("pageSubtitle")
            layout.addWidget(sub)


class Page(QWidget):
    """Standard page shell: header at the top, `content` fills the rest."""

    def __init__(self, title: str, subtitle: str | None = None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(PageHeader(title, subtitle))

        self.content = QVBoxLayout()
        self.content.setContentsMargins(0, 0, 0, 0)
        self.content.setSpacing(12)
        layout.addLayout(self.content, 1)


class Separator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("separator")
        self.setFixedHeight(1)


class StatLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("statLabel")


class StatValue(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("statValue")
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
