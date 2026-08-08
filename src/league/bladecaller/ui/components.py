from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget


def repolish(widget: QWidget):
    """Re-apply the stylesheet after a dynamic property used as a selector changes.

    Qt only evaluates property selectors at polish time, so a property set after
    the widget is shown does nothing without this.
    """
    widget.style().unpolish(widget)
    widget.style().polish(widget)


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


class Badge(QLabel):
    """Small uppercase pill. `variant` is one of win / loss / gold / purple."""

    def __init__(self, text: str, variant: str | None = None, parent=None):
        super().__init__(text.upper(), parent)
        self.setObjectName("badge")
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        if variant:
            self.setProperty("variant", variant)

    def set_variant(self, variant: str):
        self.setProperty("variant", variant)
        repolish(self)


class StatTile(QFrame):
    """Value over label on its own surface. Used in the match detail panel."""

    VALUE_SIZE = 22

    def __init__(self, value: str, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statTile")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._value = StatValue(value)
        font = self._value.font()
        font.setPointSize(self.VALUE_SIZE)
        self._value.setFont(font)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        layout.addWidget(self._value)
        layout.addWidget(StatLabel(label))

    def set_value(self, value: str):
        self._value.setText(value)


class ScrollColumn(QScrollArea):
    """Vertically scrolling column — the design's `.grow-scroll`.

    Content goes in `self.body`; a trailing stretch is already in place so rows
    stack from the top.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)

        inner = QWidget()
        inner.setAttribute(Qt.WA_TranslucentBackground, True)
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(6)
        # a scroll area sizes its widget to minimumSizeHint; without this the
        # column reports a smaller minimum than its rows need and they overlap
        self.body.setSizeConstraint(QLayout.SetMinimumSize)
        self.body.addStretch()
        self.setWidget(inner)

    def add(self, widget: QWidget):
        """Insert above the trailing stretch."""
        self.body.insertWidget(self.body.count() - 1, widget)

    def clear(self):
        while self.body.count() > 1:
            item = self.body.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # unparent first — deleteLater() alone leaves the widget visible at
                # its last geometry until the event loop destroys it
                widget.setParent(None)
                widget.deleteLater()
