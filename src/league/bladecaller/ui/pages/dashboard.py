from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel

from league import config
from league.bladecaller.core.match import MatchSummary
from league.bladecaller.ui.components import Card, Page, ScrollColumn
from league.bladecaller.ui.widgets.match_row import MatchRow

DEFAULT_RECENT_COUNT = 5


class DashboardPage(Page):
    show_match_history = Signal()

    def __init__(self, parent=None):
        super().__init__("Dashboard", "Live game state and recent activity", parent)

        self._count = config.get_int("bladecaller.dashboard_recent_matches", default=DEFAULT_RECENT_COUNT)

        self._matches: list[MatchSummary] = []

        self._recent = Card("Recent Matches", fill=True)
        self._list = ScrollColumn()
        self._recent.body.addWidget(self._list)
        self.content.addWidget(self._recent)

        self._rebuild()

    def append_matches(self, matches: list[MatchSummary]):
        """Accumulates like the history page, but only the first `_count` render."""
        known = {m.game_id for m in self._matches}
        self._matches.extend(m for m in matches if m.game_id not in known)
        self._rebuild()

    def _rebuild(self):
        self._list.clear()

        if not self._matches:
            self._list.add(_muted("No recent matches."))
            return

        for summary in self._matches[: self._count]:
            row = MatchRow(summary, compact=True, expandable=False)
            row.activated.connect(lambda _: self.show_match_history.emit())
            self._list.add(row)


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("muted", "true")
    return label
