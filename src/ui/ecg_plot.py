"""Scrolling real-time ECG plot built on pyqtgraph (never matplotlib, for redraw speed).

The widget only ever receives a *snapshot* array to draw — it has no idea how fast
samples are being acquired. The caller (main_window) is responsible for pulling that
snapshot from the circular buffer at ``GUI_REFRESH_RATE_HZ``, which is what keeps the
acquisition rate (e.g. 500 Hz) fully decoupled from the redraw rate.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.ui import theme


class ECGPlotWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paused = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground(theme.BG_PANEL)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.setLabel("bottom", "Time", units="s")
        self.plot_widget.setLabel("left", "ECG")
        self.plot_widget.getViewBox().setMouseEnabled(x=True, y=True)  # drag-pan + wheel-zoom

        self._curve = self.plot_widget.plot(pen=pg.mkPen(theme.ACCENT_ECG, width=2.5))
        layout.addWidget(self.plot_widget)

        self.set_autoscale(True)

    @property
    def is_paused(self) -> bool:
        return self._paused

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def set_autoscale(self, enabled: bool) -> None:
        if enabled:
            self.plot_widget.enableAutoRange(axis="y")
        else:
            self.plot_widget.disableAutoRange(axis="y")

    def set_y_range(self, y_min: float, y_max: float) -> None:
        self.plot_widget.setYRange(y_min, y_max, padding=0.05)

    def reset_view(self) -> None:
        self.plot_widget.enableAutoRange()

    def set_units_label(self, text: str) -> None:
        self.plot_widget.setLabel("left", text)

    def update_data(self, x: np.ndarray, y: np.ndarray) -> None:
        if self._paused:
            return
        self._curve.setData(x, y)
