"""Central application configuration shared by the UI, acquisition and processing layers.

Values marked "UNVERIFIED" below are not confirmed facts about the CWXS kit — they are
either generic ADS1292R datasheet power-on defaults or arbitrary placeholders chosen so
the application has something reasonable to start with. See docs/cwxs_hardware.md,
section "Hardware assumptions requiring verification", before relying on them for any
real measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

APP_NAME = "CWXS ADS1292R ECG Monitor"
APP_VERSION = "0.1.0"

# The CWXS kit is advertised at ~500 SPS. Not verified against the actual received
# sample rate — use tools/serial_inspector.py or SampleRateEstimator to measure it.
DEFAULT_SAMPLE_RATE_HZ = 500

# UNVERIFIED: the real baud rate used by the CWXS Bluetooth link is unknown.
# 115200 is only a common default used for initial testing.
DEFAULT_BAUD_RATE = 115200
SUPPORTED_BAUD_RATES = (9600, 57600, 115200, 230400, 460800)

GUI_REFRESH_RATE_HZ = 45  # UI redraw rate, intentionally decoupled from acquisition rate
ECG_DISPLAY_WINDOW_S = 8.0  # seconds of ECG shown on screen at once


class DataSource(Enum):
    SIMULATOR = "simulator"
    CWXS_ADS1292R = "cwxs_ads1292r"


class SignalUnits(Enum):
    RAW_COUNTS = "raw_counts"
    MICROVOLTS = "uv"
    MILLIVOLTS = "mv"


@dataclass
class ADS1292RConfig:
    """Analog front-end parameters needed to convert ADC counts to volts.

    Defaults are the ADS1292R datasheet power-on-reset values (internal 2.42 V
    reference, PGA gain of 6), NOT a confirmed CWXS register configuration.
    They are provided only so unit conversion has a sane starting point and must
    be checked against the actual register writes performed by the firmware
    (see docs/ads1292r.md). Mark as TO BE VERIFIED ON HARDWARE.
    """

    vref_volts: float = 2.42
    pga_gain: int = 6
    resolution_bits: int = 24
    ecg_channel: int = 1
    respiration_channel: int | None = 2


@dataclass
class FilterConfig:
    enable_dc_removal: bool = True
    enable_highpass: bool = True
    highpass_cutoff_hz: float = 0.5
    enable_lowpass: bool = True
    lowpass_cutoff_hz: float = 40.0
    enable_notch_50hz: bool = False
    enable_notch_60hz: bool = False


@dataclass
class DisplayConfig:
    time_window_s: float = ECG_DISPLAY_WINDOW_S
    show_grid: bool = True
    autoscale: bool = True
    y_min: float = -1.0
    y_max: float = 1.0
    show_filtered: bool = True
    units: SignalUnits = SignalUnits.RAW_COUNTS


@dataclass
class ConnectionConfig:
    com_port: str = ""
    baud_rate: int = DEFAULT_BAUD_RATE
    sample_rate_hz: int = DEFAULT_SAMPLE_RATE_HZ
    auto_detect: bool = True


@dataclass
class AppConfig:
    data_source: DataSource = DataSource.SIMULATOR
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    ads1292r: ADS1292RConfig = field(default_factory=ADS1292RConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    software_version: str = APP_VERSION
