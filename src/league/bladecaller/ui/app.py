import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from league.bladecaller.resources import load_fonts, load_stylesheet
from league.bladecaller.resources.theme import FONT_BODY, FONT_SIZE
from league.bladecaller.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("Ghostopheles")
    app.setApplicationName("Bladecaller")

    app.setStyle("Fusion")
    load_fonts()
    app.setFont(QFont(FONT_BODY, FONT_SIZE))
    app.setStyleSheet(load_stylesheet())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
