import sys
import qasync
import asyncio

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from league import config
from league.bladecaller.resources import load_fonts, load_stylesheet
from league.bladecaller.resources.theme import FONT_BODY, FONT_SIZE
from league.bladecaller.ui.main_window import MainWindow
from league.bladecaller.controllers.client_status import ClientStatusController
from league.bladecaller.controllers.match_history import MatchHistoryController


def run() -> int:
    config.init()

    app = QApplication(sys.argv)
    app.setOrganizationName("Ghostopheles")
    app.setApplicationName("Bladecaller")

    app.setStyle("Fusion")
    load_fonts()
    app.setFont(QFont(FONT_BODY, FONT_SIZE))
    app.setStyleSheet(load_stylesheet())

    # qasync drives Qt and asyncio off a single loop, so backend callbacks land
    # on the GUI thread and app.exec() is replaced by loop.run_forever()
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()

    status_controller = ClientStatusController(window)
    status_controller.status_changed.connect(window.status.set_status)

    # one controller feeds both pages, so the fetch and the detail cache are shared
    match_controller = MatchHistoryController(window)
    match_controller.matches_loaded.connect(window.match_history.append_matches)
    match_controller.matches_loaded.connect(window.dashboard.append_matches)
    match_controller.load_failed.connect(window.match_history.set_load_error)
    match_controller.detail_loaded.connect(window.match_history.set_detail)
    match_controller.detail_failed.connect(window.match_history.set_detail_error)
    window.match_history.load_more_requested.connect(match_controller.load_page)
    window.match_history.detail_requested.connect(match_controller.load_detail)

    # quitting Qt doesn't stop run_forever() on its own — without this the process
    # outlives the closed window
    app.aboutToQuit.connect(loop.stop)

    window.show()

    with loop:
        status_controller.start()
        match_controller.start()
        loop.run_forever()
        loop.run_until_complete(status_controller.close())
        loop.run_until_complete(match_controller.close())
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
