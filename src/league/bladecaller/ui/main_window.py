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

from league.bladecaller.core.status import STATUS_LABELS, STATUS_TOOLTIPS, ClientStatus
from league.bladecaller.resources import app_version, load_icon
from league.bladecaller.resources.theme import SIDEBAR_WIDTH


class SidebarHeader(QWidget):
    """Logo mark + app name, pinned to the top of the sidebar."""

    MARK_SIZE = 28
    MARK_ICON_SIZE = 16

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarHeader")
        # QWidget subclasses don't paint QSS background/border without this.
        self.setAttribute(Qt.WA_StyledBackground, True)

        mark = QLabel()
        mark.setObjectName("logoMark")
        mark.setFixedSize(self.MARK_SIZE, self.MARK_SIZE)
        mark.setAlignment(Qt.AlignCenter)
        mark.setPixmap(load_icon("feather.svg").pixmap(self.MARK_ICON_SIZE, self.MARK_ICON_SIZE))

        name = QLabel(title.upper())
        name.setObjectName("appTitle")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 15)
        layout.setSpacing(10)
        layout.addWidget(mark)
        layout.addWidget(name)
        layout.addStretch()


class SidebarStatus(QWidget):
    """Dot + label showing League client / match state.

    Not wired to a backend — drive it with `set_status()`.
    """

    DOT_SIZE = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarStatus")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._dot = QLabel()
        self._dot.setObjectName("statusDot")
        self._dot.setFixedSize(self.DOT_SIZE, self.DOT_SIZE)

        self._label = QLabel()
        self._label.setObjectName("statusText")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 9, 12, 9)
        layout.setSpacing(9)
        layout.addWidget(self._dot)
        layout.addWidget(self._label)
        layout.addStretch()

        self._status = ClientStatus.DISCONNECTED
        self.set_status(self._status)

    @property
    def status(self) -> ClientStatus:
        return self._status

    def set_status(self, status: ClientStatus):
        self._status = status
        self._label.setText(STATUS_LABELS[status])
        self.setToolTip(STATUS_TOOLTIPS[status])
        self._dot.setProperty("state", str(status))
        # `state` is a QSS selector — a live widget needs a repolish to pick it up.
        self._dot.style().unpolish(self._dot)
        self._dot.style().polish(self._dot)


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

        self.status = SidebarStatus()

        version = QLabel(app_version().upper())
        version.setObjectName("appVersion")

        footer = QWidget()
        footer.setObjectName("sidebarFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(11, 8, 14, 10)
        footer_layout.addWidget(self.settings_button)
        footer_layout.addStretch()
        footer_layout.addWidget(version)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(self.NAV_WIDTH)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_layout.addWidget(SidebarHeader(self.WINDOW_TITLE))
        sidebar_layout.addWidget(self.nav, stretch=1)
        sidebar_layout.addWidget(self.status)
        sidebar_layout.addWidget(footer)

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
        from league.bladecaller.ui.pages import DashboardPage, MatchHistoryPage, SettingsPage

        self.dashboard = DashboardPage()
        self.match_history = MatchHistoryPage()

        # nav row index and stack index are the same number, so every add_page()
        # must come before any other stack.addWidget()
        self.add_page("Dashboard", self.dashboard, load_icon("layout-dashboard.svg"))
        self.add_page("Match History", self.match_history, load_icon("history.svg"))

        self.dashboard.show_match_history.connect(lambda: self.nav.setCurrentRow(1))

        from league.config import get_full_config

        config = get_full_config()
        self.set_settings_page(SettingsPage(config=config))
