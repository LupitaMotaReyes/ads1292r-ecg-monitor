"""Small respiration waveform widget with an explicit "unavailable" state.

The ADS1292R respiration channel may simply not be wired/enabled on a given setup.
When that is the case this widget must say so plainly rather than showing an empty
or misleading plot.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from src.ui import theme


class RespirationPlotWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground(theme.BG_PANEL)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setLabel("bottom", "Time", units="s")
        self.plot_widget.getViewBox().setMouseEnabled(x=True, y=True)
        self._curve = self.plot_widget.plot(pen=pg.mkPen(theme.ACCENT_RESP, width=1.5))

        self._unavailable_label = QLabel("Respiration signal unavailable")
        self._unavailable_label.setAlignment(Qt.AlignCenter)
        self._unavailable_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")

        self._stack.addWidget(self.plot_widget)
        self._stack.addWidget(self._unavailable_label)
        self.set_available(False)

    def set_available(self, available: bool) -> None:
        self._stack.setCurrentIndex(0 if available else 1)

    def update_data(self, x: np.ndarray, y: np.ndarray) -> None:
        self._curve.setData(x, y)
