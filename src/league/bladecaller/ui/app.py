import sys

from PySide6.QtWidgets import QApplication

from league.bladecaller.resources import load_stylesheet
from league.bladecaller.ui.main_window import MainWindow

def run() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("Ghostopheles")
    app.setApplicationName("Bladecaller")

    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
