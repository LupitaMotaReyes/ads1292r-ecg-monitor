"""Dark, biosignal-monitor-inspired color palette and stylesheet."""

from __future__ import annotations

BG_DARK = "#0a0f14"
BG_PANEL = "#121a24"
BG_CARD = "#182231"
BORDER = "#26344a"

TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b9bb4"
TEXT_MUTED = "#5a6b85"

ACCENT_ECG = "#39ff9d"
ACCENT_RESP = "#4fc3f7"
ACCENT_BLUE = "#3d8bfd"

STATUS_CONNECTED = "#39ff9d"
STATUS_DISCONNECTED = "#ff5c5c"
STATUS_RECORDING = "#ff5c5c"

QUALITY_GOOD = "#39ff9d"
QUALITY_FAIR = "#ffc857"
QUALITY_POOR = "#ff5c5c"
QUALITY_UNKNOWN = "#5a6b85"

FONT_FAMILY = "Segoe UI, -apple-system, Helvetica Neue, Arial, sans-serif"

STYLESHEET = f"""
QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: 13px;
}}

QFrame#card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QFrame#topBar {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
}}

QFrame#controlBar {{
    background-color: {BG_PANEL};
    border-top: 1px solid {BORDER};
}}

QLabel#appTitle {{
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 1px;
    color: {TEXT_PRIMARY};
}}

QLabel#appSubtitle {{
    font-size: 11px;
    color: {TEXT_SECONDARY};
}}

QLabel#cardTitle {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    color: {TEXT_SECONDARY};
}}

QLabel#metricBig {{
    font-size: 34px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

QLabel#metricUnit {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}

QPushButton {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 14px;
    color: {TEXT_PRIMARY};
}}

QPushButton:hover {{
    border-color: {ACCENT_BLUE};
}}

QPushButton:disabled {{
    color: {TEXT_MUTED};
}}

QPushButton#primary {{
    background-color: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
    color: #ffffff;
    font-weight: 600;
}}

QPushButton#danger {{
    background-color: {STATUS_DISCONNECTED};
    border-color: {STATUS_DISCONNECTED};
    color: #ffffff;
    font-weight: 600;
}}

QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 8px;
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QTabBar::tab {{
    background-color: {BG_PANEL};
    padding: 8px 16px;
    color: {TEXT_SECONDARY};
}}

QTabBar::tab:selected {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
}}
"""
