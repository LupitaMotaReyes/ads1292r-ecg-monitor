"""Right-hand panel: Heart Rate, Respiration and Signal Quality cards."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from src.signal_processing.ecg_processing import SignalQuality
from src.ui import theme
from src.ui.respiration_plot import RespirationPlotWidget

_QUALITY_COLORS = {
    SignalQuality.GOOD: theme.QUALITY_GOOD,
    SignalQuality.FAIR: theme.QUALITY_FAIR,
    SignalQuality.POOR: theme.QUALITY_POOR,
    SignalQuality.UNKNOWN: theme.QUALITY_UNKNOWN,
}


class Card(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        self._layout.addWidget(title_label)


class HeartRateCard(Card):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("HEART RATE", parent)
        self.value_label = QLabel("-- BPM")
        self.value_label.setObjectName("metricBig")
        self.status_label = QLabel("No signal")
        self.status_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        self._layout.addWidget(self.value_label)
        self._layout.addWidget(self.status_label)
        self._layout.addStretch()

    def update_bpm(self, bpm: float | None, status_text: str) -> None:
        self.value_label.setText(f"{bpm:.0f} BPM" if bpm is not None else "-- BPM")
        self.status_label.setText(status_text)


class RespirationCard(Card):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("RESPIRATION", parent)
        self.value_label = QLabel("--")
        self.value_label.setObjectName("metricBig")
        self._layout.addWidget(self.value_label)
        self.plot = RespirationPlotWidget()
        self.plot.setMinimumHeight(90)
        self._layout.addWidget(self.plot)

    def set_available(self, available: bool) -> None:
        self.plot.set_available(available)
        if not available:
            self.value_label.setText("--")

    def update_rate(self, breaths_per_min: float | None) -> None:
        self.value_label.setText(
            f"{breaths_per_min:.0f} BPM" if breaths_per_min is not None else "--"
        )


class SignalQualityCard(Card):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("SIGNAL QUALITY", parent)
        self.value_label = QLabel(SignalQuality.UNKNOWN.value)
        self.value_label.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {theme.QUALITY_UNKNOWN};"
        )
        self._layout.addWidget(self.value_label)
        note = QLabel("Heuristic estimate only — not a clinically validated metric.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px;")
        self._layout.addWidget(note)
        self._layout.addStretch()

    def update_quality(self, quality: SignalQuality) -> None:
        color = _QUALITY_COLORS[quality]
        self.value_label.setText(quality.value)
        self.value_label.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {color};")


class StatusPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.heart_rate_card = HeartRateCard()
        self.respiration_card = RespirationCard()
        self.signal_quality_card = SignalQualityCard()
        layout.addWidget(self.heart_rate_card)
        layout.addWidget(self.respiration_card)
        layout.addWidget(self.signal_quality_card)
