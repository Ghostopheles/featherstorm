from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLayout, QSizePolicy, QVBoxLayout, QWidget

from league.bladecaller.core.match import MatchDetail, MatchSummary
from league.bladecaller.ui.components import Badge, Separator, StatTile, repolish
from league.bladecaller.ui.icons import icons, run_async
from league.bladecaller.ui.widgets.champion_icon import ChampionIcon
from league.bladecaller.ui.widgets.scoreboard import Scoreboard

ACCENT_WIDTH = 4
ICON_SIZE = 40
STAT_COLUMN = 88
ITEM_SIZE = 40
ITEM_SLOTS = 7


class MatchRow(QFrame):
    """One collapsed match line.

    `compact` drops the trailing stat columns for the dashboard card. `expandable`
    decides whether a click toggles a detail panel or just reports the click so
    the dashboard can jump to the full page.
    """

    # game ids exceed 32 bits, which Qt's `int` signal type truncates — pass them
    # through as Python objects instead
    expand_requested = Signal(object)
    activated = Signal(object)

    def __init__(self, summary: MatchSummary, compact: bool = False, expandable: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("matchRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        # Minimum, not Maximum: inside a scroll column the row must never be
        # squeezed below its size hint, it should push the column taller instead
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self.summary = summary
        self._expandable = expandable
        self._expanded = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        # a scroll area sizes its widget to minimumSizeHint, and nested layouts
        # report a smaller minimum than they actually need — this pins the two together
        layout.setSizeConstraint(QLayout.SetMinimumSize)

        accent = QFrame()
        accent.setObjectName("matchAccent")
        accent.setFixedWidth(ACCENT_WIDTH)
        accent.setProperty("result", "win" if summary.win else "loss")
        layout.addWidget(accent)

        icon = ChampionIcon(ICON_SIZE)
        icon.set_champion(summary.champion_id)
        layout.addWidget(icon)

        champion = QLabel("…")
        champion.setObjectName("matchChamp")
        self._champion_label = champion
        run_async(self._resolve_champion(summary.champion_id))

        meta = QLabel(summary.meta_text)
        meta.setObjectName("matchMeta")

        identity = QVBoxLayout()
        identity.setContentsMargins(0, 0, 0, 0)
        identity.setSpacing(2)
        identity.addWidget(champion)
        identity.addWidget(meta)
        layout.addLayout(identity, 1)

        layout.addWidget(Badge(summary.result_text, "win" if summary.win else "loss"))
        layout.addWidget(_stat_column(summary.kda_text, summary.kda_ratio_text))

        if not compact:
            layout.addWidget(_stat_column(summary.cs_text, summary.cs_detail_text))
            layout.addWidget(_stat_column(f"{summary.vision_score} VS", f"{summary.gold:,}g"))

    @property
    def expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self.setProperty("expanded", "true" if expanded else "false")
        repolish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._expandable:
                self.expand_requested.emit(self.summary.game_id)
            else:
                self.activated.emit(self.summary.game_id)
        super().mousePressEvent(event)

    async def _resolve_champion(self, champion_id: int):
        name = await icons().champion_name(champion_id)
        self._champion_label.setText(name or f"Champion {champion_id}")


class MatchDetailPanel(QFrame):
    """Expanded body under a `MatchRow`: stat tiles, scoreboard, build order."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("matchDetail")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 14)
        self._layout.setSpacing(12)
        self._layout.setSizeConstraint(QLayout.SetMinimumSize)

        self.set_loading()

    def set_loading(self):
        self._reset()
        self._layout.addWidget(_muted("Loading match details…"))

    def set_error(self, message: str):
        self._reset()
        self._layout.addWidget(_muted(message))

    def set_detail(self, detail: MatchDetail):
        self._reset()

        tiles = QHBoxLayout()
        tiles.setContentsMargins(0, 0, 0, 0)
        tiles.setSpacing(8)
        tiles.addWidget(StatTile(f"{detail.damage_dealt:,}", "Damage Dealt"))
        tiles.addWidget(StatTile(f"{detail.damage_taken:,}", "Damage Taken"))
        tiles.addWidget(StatTile(detail.kill_participation_text, "Kill Participation"))
        tiles.addWidget(StatTile(f"{detail.gold:,}", "Gold Earned"))
        self._layout.addLayout(tiles)

        if detail.rows:
            self._layout.addWidget(Separator())
            self._layout.addWidget(Scoreboard(detail.rows))
        elif detail.note:
            self._layout.addWidget(_muted(detail.note))

        self._layout.addWidget(Separator())
        self._layout.addWidget(_section_title("Build Order"))
        self._layout.addWidget(_item_strip(detail.items))

    def _reset(self):
        _clear_layout(self._layout)


class MatchEntry(QWidget):
    """A `MatchRow` plus the detail panel that slides in under it."""

    # game ids exceed 32 bits, which Qt's `int` signal type truncates — pass them
    # through as Python objects instead
    expand_requested = Signal(object)
    activated = Signal(object)

    def __init__(self, summary: MatchSummary, compact: bool = False, expandable: bool = True, parent=None):
        super().__init__(parent)
        self.summary = summary
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        self.row = MatchRow(summary, compact=compact, expandable=expandable)
        self.row.expand_requested.connect(self.expand_requested)
        self.row.activated.connect(self.activated)

        self.panel = MatchDetailPanel()
        self.panel.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setSizeConstraint(QLayout.SetMinimumSize)
        layout.addWidget(self.row)
        layout.addWidget(self.panel)

    @property
    def expanded(self) -> bool:
        return self.panel.isVisible()

    def expand(self):
        self.panel.set_loading()
        self.panel.setVisible(True)
        self.row.set_expanded(True)

    def collapse(self):
        self.panel.setVisible(False)
        self.row.set_expanded(False)

    def set_detail(self, detail: MatchDetail):
        self.panel.set_detail(detail)

    def set_error(self, message: str):
        self.panel.set_error(message)


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            # unparent first — deleteLater() alone leaves the widget visible at its
            # last geometry until the event loop gets around to destroying it
            widget.setParent(None)
            widget.deleteLater()
            continue
        child = item.layout()
        if child is not None:
            _clear_layout(child)
            child.deleteLater()


def _stat_column(value: str, detail: str) -> QWidget:
    column = QWidget()
    column.setFixedWidth(STAT_COLUMN)

    top = QLabel(value)
    top.setObjectName("matchKda")
    top.setAlignment(Qt.AlignCenter)

    bottom = QLabel(detail)
    bottom.setObjectName("matchMeta")
    bottom.setAlignment(Qt.AlignCenter)

    layout = QVBoxLayout(column)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    layout.addWidget(top)
    layout.addWidget(bottom)
    return column


def _item_strip(items: list[int]) -> QWidget:
    strip = QWidget()
    layout = QHBoxLayout(strip)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    slots = list(items[:ITEM_SLOTS]) + [0] * max(0, ITEM_SLOTS - len(items))
    for item_id in slots:
        square = QLabel()
        square.setObjectName("itemSquare")
        square.setFixedSize(ITEM_SIZE, ITEM_SIZE)
        square.setAlignment(Qt.AlignCenter)
        if not item_id:
            square.setProperty("empty", "true")
        else:
            square.setToolTip(f"Item {item_id}")
            run_async(_load_item(square, item_id))
        layout.addWidget(square)

    layout.addStretch()
    return strip


async def _load_item(label: QLabel, item_id: int):
    pixmap = await icons().item_pixmap(item_id, ITEM_SIZE)
    if pixmap is not None:
        label.setPixmap(pixmap)


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("muted", "true")
    label.setWordWrap(True)
    return label


def _section_title(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("sectionTitle")
    return label
