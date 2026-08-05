import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout, QListWidget, QListWidgetItem, QMainWindow,
    QStackedWidget, QWidget,
)

class MainWindow(QMainWindow):
    NAV_WIDTH = 180

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bladecaller")
        self.resize(1600, 900)

        self.nav = QListWidget()
        self.nav.setFixedWidth(self.NAV_WIDTH)
        self.nav.setIconSize(QSize(18, 18))
        self.nav.setFocusPolicy(Qt.StrongFocus)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.stack = QStackedWidget()
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, stretch=1)
        self.setCentralWidget(central)

        self._build_pages()
        self.nav.setCurrentRow(0)

    def add_page(self, label: str, widget: QWidget, icon: QIcon | None = None):
        item = QListWidgetItem(label)
        item.setSizeHint(QSize(0, 40))
        if icon:
            item.setIcon(icon)
        self.nav.addItem(item)
        self.stack.addWidget(widget)

    def _build_pages(self):
        from .pages.dashboard import DashboardPage
        from .pages.settings import SettingsPage

        self.add_page("Dashboard", DashboardPage())
        self.add_page("Settings", SettingsPage())
