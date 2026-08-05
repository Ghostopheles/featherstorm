from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from league.bladecaller.resources import app_version, load_icon
from league.bladecaller.resources.theme import SIDEBAR_WIDTH


class SidebarHeader(QWidget):
    """Logo mark + app name + version, pinned to the top of the sidebar."""

    MARK_SIZE = 28
    MARK_ICON_SIZE = 16

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarHeader")

        mark = QLabel()
        mark.setObjectName("logoMark")
        mark.setFixedSize(self.MARK_SIZE, self.MARK_SIZE)
        mark.setAlignment(Qt.AlignCenter)
        mark.setPixmap(load_icon("feather.svg").pixmap(self.MARK_ICON_SIZE, self.MARK_ICON_SIZE))

        name = QLabel(title.upper())
        name.setObjectName("appTitle")

        version = QLabel(app_version().upper())
        version.setObjectName("appVersion")

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(0)
        text.addWidget(name)
        text.addWidget(version)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)
        layout.addWidget(mark)
        layout.addLayout(text)
        layout.addStretch()


class MainWindow(QMainWindow):
    NAV_WIDTH = SIDEBAR_WIDTH
    WINDOW_TITLE = "Bladecaller"
    WINDOW_WIDTH = 1600
    WINDOW_HEIGHT = 900

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setWindowIcon(load_icon("feather.svg"))
        self.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setIconSize(QSize(16, 16))
        self.nav.setFocusPolicy(Qt.StrongFocus)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.currentRowChanged.connect(self._on_nav_row_changed)

        self.settings_button = QToolButton()
        self.settings_button.setObjectName("navSettings")
        self.settings_button.setIcon(load_icon("gear.svg"))
        self.settings_button.setIconSize(QSize(18, 18))
        self.settings_button.setToolTip("Settings")
        self.settings_button.setCheckable(True)
        self.settings_button.setFocusPolicy(Qt.StrongFocus)
        self.settings_button.setFixedSize(34, 34)
        self.settings_button.clicked.connect(self._show_settings)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(self.NAV_WIDTH)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_layout.addWidget(SidebarHeader(self.WINDOW_TITLE))
        sidebar_layout.addWidget(self.nav, stretch=1)

        footer = QHBoxLayout()
        footer.setContentsMargins(11, 8, 8, 10)
        footer.addWidget(self.settings_button)
        footer.addStretch()
        sidebar_layout.addLayout(footer)

        self.stack = QStackedWidget()
        self.settings_page: QWidget | None = None

        central = QWidget()
        central.setObjectName("root")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(sidebar)
        layout.addWidget(self.stack, stretch=1)
        self.setCentralWidget(central)

        self._build_pages()
        self.nav.setCurrentRow(0)

    def add_page(self, label: str, widget: QWidget, icon: QIcon | None = None):
        item = QListWidgetItem(label)
        item.setSizeHint(QSize(0, 38))
        if icon:
            item.setIcon(icon)
        self.nav.addItem(item)
        self.stack.addWidget(widget)

    def set_settings_page(self, widget: QWidget):
        self.settings_page = widget
        self.stack.addWidget(widget)

    def _on_nav_row_changed(self, row: int):
        if row < 0:
            return
        self.settings_button.setChecked(False)
        self.stack.setCurrentIndex(row)

    def _show_settings(self):
        if self.settings_page is None:
            return
        self.settings_button.setChecked(True)
        self.nav.setCurrentRow(-1)
        self.stack.setCurrentWidget(self.settings_page)

    def _build_pages(self):
        from league.bladecaller.ui.pages import DashboardPage, SettingsPage

        self.add_page("Dashboard", DashboardPage(), load_icon("layout-dashboard.svg"))

        from league.config import get_full_config

        config = get_full_config()
        self.set_settings_page(SettingsPage(config=config))
