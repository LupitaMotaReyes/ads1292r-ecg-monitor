"""Application entry point. Run with: python -m src.main

Talks directly to the CWXS ADS1292R hardware over serial — connect the receiver and
use Settings > Connection to pick the COM port before pressing Connect.
"""

from __future__ import annotations

import sys

import pyqtgraph as pg
from PySide6.QtWidgets import QApplication

from src.ui import theme
from src.ui.main_window import MainWindow


def main() -> int:
    pg.setConfigOptions(antialias=True, background=theme.BG_PANEL, foreground=theme.TEXT_PRIMARY)
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
