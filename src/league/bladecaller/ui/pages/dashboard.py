from PySide6.QtWidgets import QLabel

from league.bladecaller.ui.components import Card, Page


class DashboardPage(Page):
    def __init__(self, parent=None):
        super().__init__("Dashboard", "Live game state and recent activity", parent)

        placeholder = Card("Overview")
        placeholder.body.addWidget(QLabel("Nothing to show yet."))
        self.content.addWidget(placeholder)
        self.content.addStretch()
