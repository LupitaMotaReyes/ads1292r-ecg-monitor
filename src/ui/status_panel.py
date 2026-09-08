"""Right-hand panel: Heart Rate, Respiration and Signal Quality cards."""

from __future__ import annotations

from PySide6.QtCore import QTimer, QVariantAnimation
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.signal_processing.ecg_processing import SignalQuality
from src.ui import theme

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
    _HEART_MIN_PX = 26
    _HEART_MAX_PX = 42
    _IDLE_BEAT_MS = 800  # pulse rate shown while acquiring but no BPM has been computed yet

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("HEART RATE", parent)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.heart_label = QLabel("❤️")
        self.heart_label.setStyleSheet(f"font-size: {self._HEART_MIN_PX}px;")
        self.value_label = QLabel("-- BPM")
        self.value_label.setObjectName("metricBig")
        self.value_label.setStyleSheet(f"color: {theme.ACCENT_ECG};")
        row.addWidget(self.heart_label)
        row.addWidget(self.value_label, 1)
        self._layout.addLayout(row)

        self.status_label = QLabel("No signal")
        self.status_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        self._layout.addWidget(self.status_label)
        self._layout.addStretch()

        self._beat_anim = QVariantAnimation(self)
        self._beat_anim.setKeyValueAt(0.0, self._HEART_MIN_PX)
        self._beat_anim.setKeyValueAt(0.2, self._HEART_MAX_PX)
        self._beat_anim.setKeyValueAt(0.4, self._HEART_MIN_PX)
        self._beat_anim.setKeyValueAt(1.0, self._HEART_MIN_PX)
        self._beat_anim.valueChanged.connect(self._on_beat_value_changed)
        self._beat_timer = QTimer(self)
        self._beat_timer.timeout.connect(self._beat_anim.start)
        self._set_beat_interval_ms(self._IDLE_BEAT_MS)

    def _on_beat_value_changed(self, value: int | None) -> None:
        if value is None:
            return
        self.heart_label.setStyleSheet(f"font-size: {int(value)}px;")

    def _set_beat_interval_ms(self, interval_ms: int) -> None:
        interval_ms = max(250, interval_ms)
        self._beat_anim.setDuration(interval_ms)
        self._beat_timer.setInterval(interval_ms)

    def set_beating(self, active: bool) -> None:
        """Starts/stops the animated heart icon — called when acquisition starts/stops."""
        if active:
            self._beat_timer.start()
            self._beat_anim.start()
        else:
            self._beat_timer.stop()
            self._beat_anim.stop()
            self.heart_label.setStyleSheet(f"font-size: {self._HEART_MIN_PX}px;")

    def update_bpm(self, bpm: float | None, status_text: str) -> None:
        self.value_label.setText(f"{bpm:.0f} BPM" if bpm is not None else "-- BPM")
        self.status_label.setText(status_text)
        if bpm is not None and bpm > 0:
            self._set_beat_interval_ms(int(round(60_000 / bpm)))


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
        self.signal_quality_card = SignalQualityCard()
        layout.addWidget(self.heart_rate_card)
        layout.addWidget(self.signal_quality_card)
