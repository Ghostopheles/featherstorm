from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from league.bladecaller.core.match import MatchDetail, MatchSummary
from league.bladecaller.ui.components import Card, Page, ScrollColumn, StatLabel, StatValue, repolish
from league.bladecaller.ui.widgets.match_row import MatchEntry

ALL_QUEUES = "All queues"

DEFAULT_QUEUE = "Ranked Solo/Duo"

FILTERS = ("All", "Wins", "Losses")

SPLIT_BAR_HEIGHT = 6

RECENT_WINDOW = 20


class MatchHistoryPage(Page):
    """Paged, filterable match list. Rows expand into a full match breakdown."""

    load_more_requested = Signal()
    # game ids exceed 32 bits — see MatchRow
    detail_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__("Match History", "No matches loaded", parent)

        self._matches: list[MatchSummary] = []
        self._entries: dict[int, MatchEntry] = {}
        self._details: dict[int, MatchDetail] = {}
        self._expanded: int | None = None
        self._filter = FILTERS[0]
        self._queue = DEFAULT_QUEUE

        self._subtitle = self.findChild(QLabel, "pageSubtitle")

        self.content.addLayout(self._build_filters())
        self.content.addWidget(self._build_summary())

        self._list = ScrollColumn()
        self.content.addWidget(self._list, 1)

        self._load_more = QPushButton("Load more")
        self._load_more.clicked.connect(self.load_more_requested)
        self._load_more.setEnabled(False)
        self.content.addWidget(self._load_more, 0, Qt.AlignHCenter)

    # ── construction ──────────────────────────────────────────────────────────

    def _build_filters(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._chips: dict[str, QPushButton] = {}
        for name in FILTERS:
            chip = QPushButton(name)
            chip.setObjectName("filterChip")
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _=False, n=name: self._set_filter(n))
            self._chips[name] = chip
            row.addWidget(chip)

        row.addStretch()

        self._queue_box = QComboBox()
        self._queue_box.addItems([ALL_QUEUES, DEFAULT_QUEUE])
        self._queue_box.setCurrentText(self._queue)
        self._queue_box.currentTextChanged.connect(self._set_queue)
        row.addWidget(self._queue_box)

        self._mark_active_chip()
        return row

    def _build_summary(self) -> Card:
        card = Card("Summary")

        self._total = _stat_pair("0", "Games")
        self._wins = _stat_pair("0", "Wins")
        self._losses = _stat_pair("0", "Losses")
        self._avg_kda = _stat_pair("—", "Avg KDA")
        self._avg_cs = _stat_pair("—", "Avg CS/min")
        self._avg_vision = _stat_pair("—", "Avg Vision")

        stats = QHBoxLayout()
        stats.setContentsMargins(0, 0, 0, 0)
        stats.setSpacing(32)
        stats.addStretch()
        for pair in (self._total, self._wins, self._losses, self._avg_kda, self._avg_cs, self._avg_vision):
            stats.addWidget(pair[0])
        stats.addStretch()

        self._split_bar = QFrame()
        self._split_bar.setObjectName("splitBar")
        self._split_bar.setAttribute(Qt.WA_StyledBackground, True)
        self._split_bar.setFixedHeight(SPLIT_BAR_HEIGHT)

        self._split_fill = QFrame(self._split_bar)
        self._split_fill.setObjectName("splitFill")
        self._split_fill.setAttribute(Qt.WA_StyledBackground, True)

        split_layout = QHBoxLayout(self._split_bar)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)
        split_layout.addWidget(self._split_fill)
        split_layout.addStretch()

        card.body.addLayout(stats)
        card.body.addWidget(self._split_bar)
        card.body.addLayout(self._build_winrate())
        return card

    def _build_winrate(self) -> QHBoxLayout:
        self._winrate_label = StatLabel(f"Last {RECENT_WINDOW}")
        self._winrate_value = QLabel("—")
        self._winrate_value.setObjectName("winrateValue")

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self._winrate_label)
        row.addStretch()
        row.addWidget(self._winrate_value)
        return row

    # ── controller slots ──────────────────────────────────────────────────────

    def append_matches(self, matches: list[MatchSummary]):
        known = {m.game_id for m in self._matches}
        self._matches.extend(m for m in matches if m.game_id not in known)
        self._load_more.setEnabled(bool(matches))
        self._refresh_queue_box()
        self._rebuild()

    def set_load_error(self, message: str):
        self._load_more.setEnabled(False)
        if not self._matches:
            self._list.clear()
            self._list.add(_muted(message))
            self._set_subtitle(message)

    def set_detail(self, game_id: int, detail: MatchDetail):
        self._details[game_id] = detail
        entry = self._entries.get(game_id)
        if entry is not None:
            entry.set_detail(detail)

    def set_detail_error(self, game_id: int, message: str):
        entry = self._entries.get(game_id)
        if entry is not None:
            entry.set_error(message)

    # ── filtering ─────────────────────────────────────────────────────────────

    def _set_filter(self, name: str):
        self._filter = name
        self._mark_active_chip()
        self._rebuild()

    def _set_queue(self, queue: str):
        self._queue = queue
        self._rebuild()

    def _mark_active_chip(self):
        for name, chip in self._chips.items():
            chip.setProperty("active", "true" if name == self._filter else "false")
            repolish(chip)

    def _refresh_queue_box(self):
        names = sorted({m.queue_name for m in self._matches})
        current = self._queue_box.currentText()

        self._queue_box.blockSignals(True)
        self._queue_box.clear()
        self._queue_box.addItem(ALL_QUEUES)
        self._queue_box.addItems(names)
        index = self._queue_box.findText(current)
        self._queue_box.setCurrentIndex(index if index >= 0 else 0)
        self._queue_box.blockSignals(False)

        self._queue = self._queue_box.currentText()

    def _queue_filtered(self) -> list[MatchSummary]:
        if self._queue == ALL_QUEUES:
            return list(self._matches)
        return [m for m in self._matches if m.queue_name == self._queue]

    def _filtered(self) -> list[MatchSummary]:
        matches = self._queue_filtered()
        if self._filter == "Wins":
            matches = [m for m in matches if m.win]
        elif self._filter == "Losses":
            matches = [m for m in matches if not m.win]
        return matches

    # ── rendering ─────────────────────────────────────────────────────────────

    def _rebuild(self):
        matches = self._filtered()

        self._list.clear()
        self._entries.clear()
        expanded, self._expanded = self._expanded, None

        for summary in matches:
            entry = MatchEntry(summary)
            entry.expand_requested.connect(self._toggle)
            self._entries[summary.game_id] = entry
            self._list.add(entry)

        if not matches:
            self._list.add(_muted("No matches match this filter."))

        if expanded in self._entries:
            self._toggle(expanded)

        self._update_summary(matches)

    def _toggle(self, game_id: int):
        entry = self._entries.get(game_id)
        if entry is None:
            return

        if self._expanded == game_id:
            entry.collapse()
            self._expanded = None
            return

        if self._expanded is not None:
            previous = self._entries.get(self._expanded)
            if previous is not None:
                previous.collapse()

        self._expanded = game_id
        entry.expand()

        cached = self._details.get(game_id)
        if cached is not None:
            entry.set_detail(cached)
        else:
            self.detail_requested.emit(game_id)

    def _update_summary(self, matches: list[MatchSummary]):
        total = len(matches)
        wins = sum(1 for m in matches if m.win)
        losses = total - wins

        self._total[1].setText(str(total))
        self._wins[1].setText(str(wins))
        self._losses[1].setText(str(losses))

        if total:
            self._avg_kda[1].setText(f"{sum(m.kda_ratio for m in matches) / total:.2f}")
            self._avg_cs[1].setText(f"{sum(m.cs_per_min for m in matches) / total:.1f}")
            self._avg_vision[1].setText(f"{sum(m.vision_score for m in matches) / total:.0f}")
        else:
            for pair in (self._avg_kda, self._avg_cs, self._avg_vision):
                pair[1].setText("—")

        # QSS has no percentage widths, so the win share is a stretch factor
        layout = self._split_bar.layout()
        layout.setStretch(0, wins)
        layout.setStretch(1, losses)
        self._split_bar.setVisible(total > 0)

        self._update_winrate()

        self._set_subtitle(f"{self._queue} · {total} games")

    def _update_winrate(self):
        # the win/loss chips would make the rate meaningless — queue filter only
        recent = self._queue_filtered()[:RECENT_WINDOW]
        self._winrate_label.setText(f"Last {len(recent) or RECENT_WINDOW} · {self._queue}")

        if not recent:
            self._winrate_value.setText("—")
            self._winrate_value.setProperty("result", "none")
        else:
            wins = sum(1 for m in recent if m.win)
            losses = len(recent) - wins
            self._winrate_value.setText(f"{wins / len(recent) * 100:.0f}% WR  ·  {wins}W {losses}L")
            self._winrate_value.setProperty("result", "win" if wins >= losses else "loss")

        repolish(self._winrate_value)

    def _set_subtitle(self, text: str):
        if self._subtitle is not None:
            self._subtitle.setText(text)


def _stat_pair(value: str, label: str) -> tuple[QWidget, StatValue]:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    stat = StatValue(value)
    stat.setAlignment(Qt.AlignCenter)
    text = StatLabel(label)
    text.setAlignment(Qt.AlignCenter)

    layout.addWidget(stat)
    layout.addWidget(text)
    return widget, stat


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("muted", "true")
    label.setWordWrap(True)
    return label
