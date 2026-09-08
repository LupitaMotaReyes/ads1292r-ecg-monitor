"""Settings dialog: Connection, Hardware, ADS1292R, Filters and Display tabs."""

from __future__ import annotations

import copy

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.acquisition.serial_manager import guess_cwxs_port, list_ports
from src.config import SUPPORTED_BAUD_RATES, AppConfig, DataSource, SignalUnits


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(460, 480)
        self._config = copy.deepcopy(config)

        tabs = QTabWidget()
        tabs.addTab(self._build_connection_tab(), "Connection")
        tabs.addTab(self._build_hardware_tab(), "Hardware")
        tabs.addTab(self._build_ads1292r_tab(), "ADS1292R")
        tabs.addTab(self._build_filters_tab(), "Filters")
        tabs.addTab(self._build_display_tab(), "Display")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    def result_config(self) -> AppConfig:
        return self._config

    # -- Connection -----------------------------------------------------------------
    def _build_connection_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self._refresh_ports()
        port_row = QHBoxLayout()
        port_row.addWidget(self.port_combo)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_ports)
        port_row.addWidget(refresh_btn)
        form.addRow("COM Port", port_row)

        self.baud_combo = QComboBox()
        for baud in SUPPORTED_BAUD_RATES:
            self.baud_combo.addItem(str(baud), baud)
        idx = self.baud_combo.findData(self._config.connection.baud_rate)
        self.baud_combo.setCurrentIndex(max(0, idx))
        self.baud_combo.currentIndexChanged.connect(
            lambda: setattr(self._config.connection, "baud_rate", self.baud_combo.currentData())
        )
        form.addRow("Baud Rate", self.baud_combo)

        self.sample_rate_spin = QSpinBox()
        self.sample_rate_spin.setRange(1, 5000)
        self.sample_rate_spin.setValue(self._config.connection.sample_rate_hz)
        self.sample_rate_spin.valueChanged.connect(
            lambda v: setattr(self._config.connection, "sample_rate_hz", v)
        )
        form.addRow("Sample Rate (Hz)", self.sample_rate_spin)

        self.auto_detect_check = QCheckBox("Auto-detect on Connect")
        self.auto_detect_check.setChecked(self._config.connection.auto_detect)
        self.auto_detect_check.toggled.connect(
            lambda v: setattr(self._config.connection, "auto_detect", v)
        )
        form.addRow(self.auto_detect_check)

        return widget

    def _refresh_ports(self) -> None:
        self.port_combo.clear()
        ports = list_ports()
        for p in ports:
            self.port_combo.addItem(f"{p.device} — {p.description}", p.device)
        current = self._config.connection.com_port
        guess = current or guess_cwxs_port(ports) or ""
        if guess:
            idx = self.port_combo.findData(guess)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
            else:
                self.port_combo.setEditText(guess)
        self.port_combo.currentTextChanged.connect(self._on_port_text_changed)

    def _on_port_text_changed(self, text: str) -> None:
        device = self.port_combo.currentData() or text.split(" — ")[0]
        self._config.connection.com_port = device

    # -- Hardware ---------------------------------------------------------------
    def _build_hardware_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItem("CWXS ADS1292R", DataSource.CWXS_ADS1292R)
        self.data_source_combo.addItem("Simulator", DataSource.SIMULATOR)
        idx = self.data_source_combo.findData(self._config.data_source)
        self.data_source_combo.setCurrentIndex(max(0, idx))
        self.data_source_combo.currentIndexChanged.connect(
            lambda: setattr(self._config, "data_source", self.data_source_combo.currentData())
        )
        form.addRow("Data Source", self.data_source_combo)
        return widget

    # -- ADS1292R -----------------------------------------------------------------
    def _build_ads1292r_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self.pga_gain_combo = QComboBox()
        for gain in (1, 2, 3, 4, 6, 8, 12):
            self.pga_gain_combo.addItem(str(gain), gain)
        idx = self.pga_gain_combo.findData(self._config.ads1292r.pga_gain)
        self.pga_gain_combo.setCurrentIndex(max(0, idx))
        self.pga_gain_combo.currentIndexChanged.connect(
            lambda: setattr(self._config.ads1292r, "pga_gain", self.pga_gain_combo.currentData())
        )
        form.addRow("PGA Gain", self.pga_gain_combo)

        self.vref_spin = QDoubleSpinBox()
        self.vref_spin.setRange(0.1, 5.0)
        self.vref_spin.setSingleStep(0.01)
        self.vref_spin.setValue(self._config.ads1292r.vref_volts)
        self.vref_spin.valueChanged.connect(
            lambda v: setattr(self._config.ads1292r, "vref_volts", v)
        )
        form.addRow("VREF (V)", self.vref_spin)

        self.ecg_channel_spin = QSpinBox()
        self.ecg_channel_spin.setRange(1, 2)
        self.ecg_channel_spin.setValue(self._config.ads1292r.ecg_channel)
        self.ecg_channel_spin.valueChanged.connect(
            lambda v: setattr(self._config.ads1292r, "ecg_channel", v)
        )
        form.addRow("ECG Channel", self.ecg_channel_spin)

        self.resp_available_check = QCheckBox("Respiration channel available")
        self.resp_available_check.setChecked(self._config.ads1292r.respiration_channel is not None)
        self.resp_channel_spin = QSpinBox()
        self.resp_channel_spin.setRange(1, 2)
        self.resp_channel_spin.setValue(self._config.ads1292r.respiration_channel or 2)

        def _on_resp_toggle(checked: bool) -> None:
            self._config.ads1292r.respiration_channel = (
                self.resp_channel_spin.value() if checked else None
            )
            self.resp_channel_spin.setEnabled(checked)

        def _on_resp_channel_changed(v: int) -> None:
            if self.resp_available_check.isChecked():
                self._config.ads1292r.respiration_channel = v

        self.resp_available_check.toggled.connect(_on_resp_toggle)
        self.resp_channel_spin.valueChanged.connect(_on_resp_channel_changed)
        self.resp_channel_spin.setEnabled(self.resp_available_check.isChecked())

        form.addRow(self.resp_available_check)
        form.addRow("Respiration Channel", self.resp_channel_spin)

        return widget

    # -- Filters ------------------------------------------------------------------
    def _build_filters_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        f = self._config.filters

        self.highpass_check = QCheckBox("Enable")
        self.highpass_check.setChecked(f.enable_highpass)
        self.highpass_check.toggled.connect(lambda v: setattr(f, "enable_highpass", v))
        self.highpass_cutoff = QDoubleSpinBox()
        self.highpass_cutoff.setRange(0.05, 10.0)
        self.highpass_cutoff.setSingleStep(0.05)
        self.highpass_cutoff.setValue(f.highpass_cutoff_hz)
        self.highpass_cutoff.valueChanged.connect(lambda v: setattr(f, "highpass_cutoff_hz", v))
        form.addRow("High-pass", self.highpass_check)
        form.addRow("High-pass cutoff (Hz)", self.highpass_cutoff)

        self.lowpass_check = QCheckBox("Enable")
        self.lowpass_check.setChecked(f.enable_lowpass)
        self.lowpass_check.toggled.connect(lambda v: setattr(f, "enable_lowpass", v))
        self.lowpass_cutoff = QDoubleSpinBox()
        self.lowpass_cutoff.setRange(5.0, 150.0)
        self.lowpass_cutoff.setValue(f.lowpass_cutoff_hz)
        self.lowpass_cutoff.valueChanged.connect(lambda v: setattr(f, "lowpass_cutoff_hz", v))
        form.addRow("Low-pass", self.lowpass_check)
        form.addRow("Low-pass cutoff (Hz)", self.lowpass_cutoff)

        self.notch50_check = QCheckBox("50 Hz notch")
        self.notch50_check.setChecked(f.enable_notch_50hz)
        self.notch50_check.toggled.connect(lambda v: setattr(f, "enable_notch_50hz", v))
        form.addRow(self.notch50_check)

        self.notch60_check = QCheckBox("60 Hz notch")
        self.notch60_check.setChecked(f.enable_notch_60hz)
        self.notch60_check.toggled.connect(lambda v: setattr(f, "enable_notch_60hz", v))
        form.addRow(self.notch60_check)

        self.dc_removal_check = QCheckBox("DC removal")
        self.dc_removal_check.setChecked(f.enable_dc_removal)
        self.dc_removal_check.toggled.connect(lambda v: setattr(f, "enable_dc_removal", v))
        form.addRow(self.dc_removal_check)

        return widget

    # -- Display ------------------------------------------------------------------
    def _build_display_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        d = self._config.display

        self.time_window_spin = QDoubleSpinBox()
        self.time_window_spin.setRange(2.0, 30.0)
        self.time_window_spin.setValue(d.time_window_s)
        self.time_window_spin.valueChanged.connect(lambda v: setattr(d, "time_window_s", v))
        form.addRow("Time window (s)", self.time_window_spin)

        self.grid_check = QCheckBox("Show grid")
        self.grid_check.setChecked(d.show_grid)
        self.grid_check.toggled.connect(lambda v: setattr(d, "show_grid", v))
        form.addRow(self.grid_check)

        self.autoscale_check = QCheckBox("Autoscale Y")
        self.autoscale_check.setChecked(d.autoscale)
        self.autoscale_check.toggled.connect(lambda v: setattr(d, "autoscale", v))
        form.addRow(self.autoscale_check)

        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-10_000_000, 10_000_000)
        self.y_min_spin.setValue(d.y_min)
        self.y_min_spin.valueChanged.connect(lambda v: setattr(d, "y_min", v))
        form.addRow("Y min (manual)", self.y_min_spin)

        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-10_000_000, 10_000_000)
        self.y_max_spin.setValue(d.y_max)
        self.y_max_spin.valueChanged.connect(lambda v: setattr(d, "y_max", v))
        form.addRow("Y max (manual)", self.y_max_spin)

        self.raw_filtered_combo = QComboBox()
        self.raw_filtered_combo.addItem("Filtered", True)
        self.raw_filtered_combo.addItem("Raw", False)
        idx = self.raw_filtered_combo.findData(d.show_filtered)
        self.raw_filtered_combo.setCurrentIndex(max(0, idx))
        self.raw_filtered_combo.currentIndexChanged.connect(
            lambda: setattr(d, "show_filtered", self.raw_filtered_combo.currentData())
        )
        form.addRow("Trace", self.raw_filtered_combo)

        self.units_combo = QComboBox()
        self.units_combo.addItem("Raw ADC Counts", SignalUnits.RAW_COUNTS)
        self.units_combo.addItem("microvolts (uV)", SignalUnits.MICROVOLTS)
        self.units_combo.addItem("millivolts (mV)", SignalUnits.MILLIVOLTS)
        idx = self.units_combo.findData(d.units)
        self.units_combo.setCurrentIndex(max(0, idx))
        self.units_combo.currentIndexChanged.connect(
            lambda: setattr(d, "units", self.units_combo.currentData())
        )
        form.addRow("Units", self.units_combo)

        return widget
