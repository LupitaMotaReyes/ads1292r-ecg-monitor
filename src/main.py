"""Application entry point. Run with: python -m src.main

Starts directly in Simulation Mode so the interface can be explored with no hardware
connected; switch to "CWXS ADS1292R" in Settings > Hardware once real hardware is
attached.
"""

from __future__ import annotations

import sys

import pyqtgraph as pg
from PySide6.QtWidgets import QApplication

from src.ui import theme
from src.ui.main_window import MainWindow


def main() -> int:
    pg.setConfigOptions(antialias=True)
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
