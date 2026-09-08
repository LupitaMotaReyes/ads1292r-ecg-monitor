"""Optional filtering pipeline and heuristic signal-quality estimate for raw ECG.

The raw signal is always preserved alongside the filtered one — filtering here never
overwrites or discards it, in line with the project rule that raw data must remain
available (for recording, re-analysis, and comparing filter settings).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from src.config import FilterConfig
from src.signal_processing.filters import (
    StreamingSOSFilter,
    make_highpass,
    make_lowpass,
    make_notch,
    remove_dc,
)


class SignalQuality(Enum):
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    UNKNOWN = "--"


def assess_signal_quality(
    raw_chunk: np.ndarray, full_scale_counts: float, lead_off: bool = False
) -> SignalQuality:
    """Heuristic-only signal-quality estimate.

    NOT a clinically validated metric. It combines four simple, documented heuristics:
    lead-off status, ADC saturation (clipping), a too-flat amplitude (likely a
    disconnected or poorly-attached electrode), and a high noise-to-amplitude ratio
    (baseline instability / high-frequency noise). Thresholds are engineering
    approximations, not derived from any clinical standard.
    """
    if lead_off:
        return SignalQuality.POOR
    if len(raw_chunk) < 10:
        return SignalQuality.UNKNOWN

    amplitude = float(np.percentile(raw_chunk, 95) - np.percentile(raw_chunk, 5))
    saturation_ratio = float(np.mean(np.abs(raw_chunk) > 0.98 * full_scale_counts))
    noise_std = float(np.std(np.diff(raw_chunk))) if len(raw_chunk) > 1 else 0.0

    if saturation_ratio > 0.01:
        return SignalQuality.POOR
    if amplitude < 1e-5 * full_scale_counts:
        return SignalQuality.POOR

    noise_ratio = noise_std / (amplitude + 1e-9)
    if noise_ratio > 0.5:
        return SignalQuality.FAIR
    return SignalQuality.GOOD


@dataclass
class ProcessedChunk:
    raw: np.ndarray
    filtered: np.ndarray
    quality: SignalQuality


class ECGProcessor:
    """Applies the configured optional filter chain to successive chunks of raw ECG."""

    def __init__(self, fs: float, filter_config: FilterConfig, full_scale_counts: float = 2**23) -> None:
        self._fs = fs
        self._full_scale = full_scale_counts
        self._dc_mean = 0.0
        self._config = filter_config
        self._highpass: StreamingSOSFilter | None = None
        self._lowpass: StreamingSOSFilter | None = None
        self._notch50: StreamingSOSFilter | None = None
        self._notch60: StreamingSOSFilter | None = None
        self.reconfigure(filter_config)

    def reconfigure(self, filter_config: FilterConfig) -> None:
        self._config = filter_config
        self._highpass = (
            make_highpass(filter_config.highpass_cutoff_hz, self._fs)
            if filter_config.enable_highpass
            else None
        )
        self._lowpass = (
            make_lowpass(filter_config.lowpass_cutoff_hz, self._fs)
            if filter_config.enable_lowpass
            else None
        )
        self._notch50 = make_notch(50.0, self._fs) if filter_config.enable_notch_50hz else None
        self._notch60 = make_notch(60.0, self._fs) if filter_config.enable_notch_60hz else None

    def process(self, raw_chunk: np.ndarray, lead_off: bool = False) -> ProcessedChunk:
        raw_chunk = np.asarray(raw_chunk, dtype=np.float64)
        filtered = raw_chunk.copy()
        if self._config.enable_dc_removal:
            filtered, self._dc_mean = remove_dc(filtered, self._dc_mean)
        if self._highpass is not None:
            filtered = self._highpass.process(filtered)
        if self._lowpass is not None:
            filtered = self._lowpass.process(filtered)
        if self._notch50 is not None:
            filtered = self._notch50.process(filtered)
        if self._notch60 is not None:
            filtered = self._notch60.process(filtered)
        quality = assess_signal_quality(raw_chunk, self._full_scale, lead_off=lead_off)
        return ProcessedChunk(raw=raw_chunk, filtered=filtered, quality=quality)
