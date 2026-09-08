"""Main application window: top status bar, ECG + status panel, bottom controls."""

from __future__ import annotations

import time

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.acquisition.circular_buffer import CircularBuffer
from src.acquisition.protocol import CSVProtocolParser, Sample, SampleRateEstimator
from src.acquisition.serial_manager import SerialManager
from src.config import GUI_REFRESH_RATE_HZ, AppConfig, SignalUnits
from src.recording.recorder import Recorder, build_metadata
from src.signal_processing.ecg_processing import ECGProcessor, SignalQuality
from src.signal_processing.heart_rate import HeartRateEstimator
from src.signal_processing.respiration_processing import RespirationProcessor
from src.signal_processing.units import (
    adc_counts_to_volts,
    volts_to_microvolts,
    volts_to_millivolts,
)
from src.ui import theme
from src.ui.ecg_plot import ECGPlotWidget
from src.ui.settings_dialog import SettingsDialog
from src.ui.status_panel import StatusPanel

_QUALITY_STATUS_TEXT = {
    SignalQuality.GOOD: "Signal stable",
    SignalQuality.FAIR: "Signal unstable",
    SignalQuality.POOR: "Poor contact",
    SignalQuality.UNKNOWN: "No signal",
}


def _format_elapsed(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CWXS ADS1292R ECG Monitor")
        self.resize(1280, 800)

        self._config = AppConfig()
        self._serial_manager = SerialManager(self)
        self._serial_manager.data_received.connect(self._on_serial_bytes)
        self._serial_manager.connected.connect(self._on_serial_connected)
        self._serial_manager.disconnected.connect(self._on_serial_disconnected)
        self._serial_manager.error.connect(self._on_serial_error)
        self._csv_parser = CSVProtocolParser()
        self._sample_rate_estimator = SampleRateEstimator()

        self._recorder = Recorder()
        self._is_connected = False
        self._is_acquiring = False
        self._acquisition_start_monotonic = 0.0

        self._latest_bpm: float | None = None
        self._latest_quality = SignalQuality.UNKNOWN
        self._latest_resp_rate: float | None = None

        self._build_processing_pipeline()
        self._build_ui()

        self._gui_timer = QTimer(self)
        self._gui_timer.timeout.connect(self._on_gui_refresh)
        self._gui_timer.start(int(1000 / GUI_REFRESH_RATE_HZ))

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._on_elapsed_tick)
        self._elapsed_timer.start(500)

        self._update_button_states()

    # -- Pipeline setup ---------------------------------------------------------
    def _build_processing_pipeline(self) -> None:
        fs = self._config.connection.sample_rate_hz
        window_samples = int(self._config.display.time_window_s * fs)
        self._ecg_raw_buffer = CircularBuffer(window_samples)
        self._ecg_filtered_buffer = CircularBuffer(window_samples)
        self._resp_buffer = CircularBuffer(window_samples)

        self._ecg_processor = ECGProcessor(fs, self._config.filters)
        self._heart_rate_estimator = HeartRateEstimator(fs=fs)
        self._respiration_processor: RespirationProcessor | None = (
            RespirationProcessor(fs=fs)
            if self._config.ads1292r.respiration_channel is not None
            else None
        )

    # -- UI construction ----------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(16, 16, 16, 16)
        body_layout.setSpacing(16)

        ecg_card = QFrame()
        ecg_card.setObjectName("card")
        ecg_layout = QVBoxLayout(ecg_card)
        ecg_title = QLabel("ECG")
        ecg_title.setObjectName("cardTitle")
        self.ecg_plot = ECGPlotWidget()
        ecg_layout.addWidget(ecg_title)
        ecg_layout.addWidget(self.ecg_plot)
        body_layout.addWidget(ecg_card, 7)

        self.status_panel = StatusPanel()
        body_layout.addWidget(self.status_panel, 3)

        root.addWidget(body, 1)
        root.addWidget(self._build_control_bar())

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("topBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 12, 20, 12)

        title_box = QVBoxLayout()
        title = QLabel("🫀 ECG MONITOR")
        title.setObjectName("appTitle")
        subtitle = QLabel("CWXS ADS1292R  ·  Real-Time Heart Monitor")
        subtitle.setObjectName("appSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        layout.addStretch()

        self.connection_dot_label = QLabel("Disconnected ●")
        self.connection_dot_label.setStyleSheet(f"color: {theme.STATUS_DISCONNECTED};")
        self.com_port_label = QLabel("--")
        self.sample_rate_label = QLabel("-- SPS")
        self.elapsed_label = QLabel("00:00:00")

        for lbl in (
            self.connection_dot_label,
            self.com_port_label,
            self.sample_rate_label,
            self.elapsed_label,
        ):
            lbl.setStyleSheet(lbl.styleSheet() + "font-weight: 600; margin-left: 16px;")
            layout.addWidget(lbl)

        return bar

    def _build_control_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("controlBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 12, 20, 12)

        self.connect_btn = QPushButton("🔌  Connect")
        self.connect_btn.setObjectName("success")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.disconnect_btn = QPushButton("🔌  Disconnect")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.start_btn = QPushButton("▶  Start")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setObjectName("warning")
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        self.record_btn = QPushButton("Record")
        self.record_btn.setObjectName("record")
        self.record_btn.clicked.connect(self._on_record_clicked)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.settings_btn = QPushButton("⚙️  Settings")
        self.settings_btn.setObjectName("info")
        self.settings_btn.clicked.connect(self._on_settings_clicked)

        for btn in (
            self.connect_btn,
            self.disconnect_btn,
            self.start_btn,
            self.pause_btn,
            self.record_btn,
            self.stop_btn,
        ):
            layout.addWidget(btn)

        layout.addStretch()

        self.recording_label = QLabel("")
        self.recording_label.setStyleSheet(f"color: {theme.STATUS_RECORDING}; font-weight: 700;")
        layout.addWidget(self.recording_label)

        layout.addWidget(self.settings_btn)
        return bar

    # -- Connect / Disconnect -----------------------------------------------------
    def _on_connect_clicked(self) -> None:
        port = self._config.connection.com_port
        if not port:
            self._on_serial_error("No COM port selected. Open Settings first.")
            return
        self._serial_manager.connect_to_port(port, self._config.connection.baud_rate)
        self._update_button_states()

    def _on_disconnect_clicked(self) -> None:
        self._on_stop_clicked()
        self._serial_manager.disconnect_port()
        self._update_button_states()

    def _on_serial_connected(self, port: str, baud: int) -> None:
        self._is_connected = True
        self.com_port_label.setText(port)
        self._set_connection_indicator(True)
        self._update_button_states()

    def _on_serial_disconnected(self, reason: str) -> None:
        self._is_connected = False
        self._set_connection_indicator(False)
        self._update_button_states()

    def _on_serial_error(self, message: str) -> None:
        self.connection_dot_label.setText("Error ●")
        self.connection_dot_label.setToolTip(message)
        self.connection_dot_label.setStyleSheet(f"color: {theme.STATUS_DISCONNECTED};")

    def _set_connection_indicator(self, connected: bool) -> None:
        if connected:
            self.connection_dot_label.setText("Connected ●")
            self.connection_dot_label.setStyleSheet(f"color: {theme.STATUS_CONNECTED};")
        else:
            self.connection_dot_label.setText("Disconnected ●")
            self.connection_dot_label.setStyleSheet(f"color: {theme.STATUS_DISCONNECTED};")
            self.com_port_label.setText("--")

    # -- Start / Pause / Stop / Record --------------------------------------------
    def _on_start_clicked(self) -> None:
        if not self._is_connected:
            return
        self._is_acquiring = True
        self._acquisition_start_monotonic = time.monotonic()
        self.status_panel.heart_rate_card.set_beating(True)
        self._update_button_states()

    def _on_pause_clicked(self) -> None:
        paused = not self.ecg_plot.is_paused
        self.ecg_plot.set_paused(paused)
        self.pause_btn.setText("Resume" if paused else "Pause")

    def _on_stop_clicked(self) -> None:
        self._is_acquiring = False
        self.status_panel.heart_rate_card.set_beating(False)
        if self._recorder.is_recording:
            self._stop_recording()
        self.elapsed_label.setText("00:00:00")
        self._update_button_states()

    def _on_record_clicked(self) -> None:
        if not self._recorder.is_recording:
            metadata = build_metadata(self._config)
            self._recorder.start(metadata)
            self.recording_label.setText("🔴 Recording")
            self.record_btn.setText("Stop Recording")
        else:
            self._stop_recording()

    def _stop_recording(self) -> None:
        self._recorder.stop()
        self.recording_label.setText("")
        self.record_btn.setText("Record")

    def _update_button_states(self) -> None:
        self.connect_btn.setEnabled(not self._is_connected)
        self.disconnect_btn.setEnabled(self._is_connected)
        self.start_btn.setEnabled(self._is_connected and not self._is_acquiring)
        self.pause_btn.setEnabled(self._is_acquiring)
        self.record_btn.setEnabled(self._is_acquiring)
        self.stop_btn.setEnabled(self._is_acquiring)

    # -- Settings -----------------------------------------------------------------
    def _on_settings_clicked(self) -> None:
        dialog = SettingsDialog(self._config, self)
        if dialog.exec():
            self._config = dialog.result_config()
            self._build_processing_pipeline()
            self.sample_rate_label.setText(f"{self._config.connection.sample_rate_hz} SPS")

    # -- Real serial data -----------------------------------------------------------
    def _on_serial_bytes(self, data: bytes) -> None:
        samples = self._csv_parser.feed(data)
        if samples and self._is_acquiring:
            self._handle_samples(samples)

    # -- Shared sample handling -----------------------------------------------------
    def _handle_samples(self, samples: list[Sample]) -> None:
        if not samples:
            return
        raw_ecg = np.array([s.ecg_raw for s in samples], dtype=np.float64)
        has_resp = self._config.ads1292r.respiration_channel is not None
        raw_resp = (
            np.array([s.resp_raw if s.resp_raw is not None else 0 for s in samples], dtype=np.float64)
            if has_resp
            else None
        )
        # Status-byte meaning (e.g. lead-off flags) is protocol-specific and not
        # confirmed for the stock CWXS firmware; treated only as a coarse heuristic.
        lead_off = any(s.status != 0 for s in samples)

        processed = self._ecg_processor.process(raw_ecg, lead_off=lead_off)
        self._ecg_raw_buffer.push(processed.raw)
        self._ecg_filtered_buffer.push(processed.filtered)
        self._latest_quality = processed.quality
        self._latest_bpm = self._heart_rate_estimator.process(processed.filtered)

        resp_filtered = None
        if has_resp and self._respiration_processor is not None and raw_resp is not None:
            resp_filtered, self._latest_resp_rate = self._respiration_processor.process(raw_resp)
            self._resp_buffer.push(resp_filtered)

        self._sample_rate_estimator.register_samples(len(samples))

        if self._recorder.is_recording:
            for i, s in enumerate(samples):
                self._recorder.write_sample(
                    timestamp=s.timestamp_ms,
                    ecg_raw=s.ecg_raw,
                    ecg_filtered=float(processed.filtered[i]),
                    resp_raw=(s.resp_raw if has_resp else None),
                    heart_rate=self._latest_bpm,
                    signal_quality=self._latest_quality.value,
                )

    # -- GUI refresh (independent of acquisition rate) -----------------------------
    def _on_gui_refresh(self) -> None:
        fs = self._config.connection.sample_rate_hz
        n = int(self._config.display.time_window_s * fs)

        buffer = self._ecg_filtered_buffer if self._config.display.show_filtered else self._ecg_raw_buffer
        y = buffer.get_latest(n)
        y = self._convert_units(y)
        if len(y) > 1:
            x = (np.arange(len(y)) - len(y)) / fs
            self.ecg_plot.update_data(x, y)

        self.ecg_plot.set_autoscale(self._config.display.autoscale)
        if not self._config.display.autoscale:
            self.ecg_plot.set_y_range(self._config.display.y_min, self._config.display.y_max)
        self.ecg_plot.set_units_label(self._units_label())

        status_text = _QUALITY_STATUS_TEXT[self._latest_quality]
        self.status_panel.heart_rate_card.update_bpm(self._latest_bpm, status_text)
        self.status_panel.signal_quality_card.update_quality(self._latest_quality)

        self.sample_rate_label.setText(f"{self._config.connection.sample_rate_hz} SPS")

    def _convert_units(self, counts: np.ndarray) -> np.ndarray:
        units = self._config.display.units
        if units == SignalUnits.RAW_COUNTS or len(counts) == 0:
            return counts
        volts = adc_counts_to_volts(
            counts, self._config.ads1292r.vref_volts, self._config.ads1292r.pga_gain
        )
        if units == SignalUnits.MICROVOLTS:
            return volts_to_microvolts(volts)
        return volts_to_millivolts(volts)

    def _units_label(self) -> str:
        return {
            SignalUnits.RAW_COUNTS: "ECG (raw counts)",
            SignalUnits.MICROVOLTS: "ECG (uV)",
            SignalUnits.MILLIVOLTS: "ECG (mV)",
        }[self._config.display.units]

    def _on_elapsed_tick(self) -> None:
        if self._is_acquiring:
            elapsed = time.monotonic() - self._acquisition_start_monotonic
            self.elapsed_label.setText(_format_elapsed(elapsed))
