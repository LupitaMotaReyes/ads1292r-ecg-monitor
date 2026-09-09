"""Bright, friendly, kid-oriented color palette and stylesheet.

Light background, big rounded cards/buttons and playful accent colors instead of a
serious dark "control room" look — this app is meant to feel approachable for children.
"""

from __future__ import annotations

BG_APP = "#eaf6ff"
BG_PANEL = "#ffffff"
BG_CARD = "#ffffff"
BORDER = "#cfe6f7"

TEXT_PRIMARY = "#1f2d40"
TEXT_SECONDARY = "#5c7290"
TEXT_MUTED = "#93a7c2"

ACCENT_ECG = "#ff4d6d"
ACCENT_RESP = "#00b4d8"
ACCENT_BLUE = "#4d7cff"
ACCENT_PURPLE = "#9b5de5"
ACCENT_YELLOW = "#ffc93c"

STATUS_CONNECTED = "#06d6a0"
STATUS_DISCONNECTED = "#ff6b6b"
STATUS_RECORDING = "#ff4d6d"

QUALITY_GOOD = "#06d6a0"
QUALITY_FAIR = "#ffc93c"
QUALITY_POOR = "#ff6b6b"
QUALITY_UNKNOWN = "#93a7c2"

FONT_FAMILY = "Comic Sans MS, Comic Sans, Segoe UI, Verdana, Helvetica Neue, Arial, sans-serif"

STYLESHEET = f"""
QWidget {{
    background-color: {BG_APP};
    color: {TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: 14px;
}}

QLabel {{
    background: transparent;
}}

QFrame#card {{
    background-color: {BG_CARD};
    border: 2px solid {BORDER};
    border-radius: 18px;
}}

QFrame#topBar {{
    background-color: {ACCENT_BLUE};
    border-bottom: none;
}}

QFrame#controlBar {{
    background-color: {BG_PANEL};
    border-top: 2px solid {BORDER};
}}

QLabel#appTitle {{
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
}}

QLabel#appSubtitle {{
    font-size: 12px;
    color: #dfeaff;
}}

QLabel#cardTitle {{
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {TEXT_SECONDARY};
}}

QLabel#metricBig {{
    font-size: 38px;
    font-weight: 800;
    color: {TEXT_PRIMARY};
}}

QLabel#metricUnit {{
    font-size: 12px;
    color: {TEXT_SECONDARY};
}}

QPushButton {{
    background-color: #eef3fb;
    border: 2px solid {BORDER};
    border-radius: 18px;
    padding: 10px 18px;
    color: {TEXT_PRIMARY};
    font-weight: 700;
}}

QPushButton:hover {{
    border-color: {ACCENT_BLUE};
}}

QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: {BORDER};
    background-color: #f3f7fc;
}}

QPushButton#primary {{
    background-color: {ACCENT_BLUE};
    border-color: {ACCENT_BLUE};
    color: #ffffff;
}}

QPushButton#success {{
    background-color: {STATUS_CONNECTED};
    border-color: {STATUS_CONNECTED};
    color: #ffffff;
}}

QPushButton#warning {{
    background-color: {ACCENT_YELLOW};
    border-color: {ACCENT_YELLOW};
    color: {TEXT_PRIMARY};
}}

QPushButton#record {{
    background-color: {ACCENT_ECG};
    border-color: {ACCENT_ECG};
    color: #ffffff;
}}

QPushButton#info {{
    background-color: {ACCENT_PURPLE};
    border-color: {ACCENT_PURPLE};
    color: #ffffff;
}}

QPushButton#danger {{
    background-color: {STATUS_DISCONNECTED};
    border-color: {STATUS_DISCONNECTED};
    color: #ffffff;
}}

QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background-color: #ffffff;
    border: 2px solid {BORDER};
    border-radius: 12px;
    padding: 5px 10px;
}}

QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
    border-color: {ACCENT_BLUE};
}}

QTabWidget::pane {{
    border: 2px solid {BORDER};
    border-radius: 14px;
}}

QTabBar::tab {{
    background-color: {BG_APP};
    border-radius: 10px;
    padding: 8px 16px;
    margin: 2px;
    color: {TEXT_SECONDARY};
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background-color: {ACCENT_BLUE};
    color: #ffffff;
}}
"""
