"""Streaming-friendly digital filters for the raw ECG/respiration signal.

Each filter keeps its own state (``sosfilt`` zi) between calls so it can be applied
chunk-by-chunk on a live stream instead of requiring the whole signal up front. All
filters are optional; the raw signal is never discarded by this module.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps


def remove_dc(chunk: np.ndarray, running_mean: float, alpha: float = 0.001) -> tuple[np.ndarray, float]:
    """Subtract a slowly-updated running mean to remove DC offset / very slow drift."""
    out = np.empty_like(chunk, dtype=np.float64)
    mean = running_mean
    for i, x in enumerate(chunk):
        mean = (1 - alpha) * mean + alpha * x
        out[i] = x - mean
    return out, mean


class StreamingSOSFilter:
    """Wraps a second-order-sections IIR filter with persistent state for streaming use."""

    def __init__(self, sos: np.ndarray) -> None:
        self._sos = sos
        self._zi_base = sps.sosfilt_zi(sos)
        self._zi: np.ndarray | None = None

    def process(self, chunk: np.ndarray) -> np.ndarray:
        if len(chunk) == 0:
            return chunk
        if self._zi is None:
            # Scale the initial state to the first real sample instead of starting
            # from zero, so the filter does not emit an artificial startup
            # transient when the incoming signal has a non-zero DC level.
            self._zi = self._zi_base * chunk[0]
        out, self._zi = sps.sosfilt(self._sos, chunk, zi=self._zi)
        return out


def make_highpass(cutoff_hz: float, fs: float, order: int = 2) -> StreamingSOSFilter:
    sos = sps.butter(order, cutoff_hz, btype="highpass", fs=fs, output="sos")
    return StreamingSOSFilter(sos)


def make_lowpass(cutoff_hz: float, fs: float, order: int = 4) -> StreamingSOSFilter:
    sos = sps.butter(order, cutoff_hz, btype="lowpass", fs=fs, output="sos")
    return StreamingSOSFilter(sos)


def make_notch(freq_hz: float, fs: float, quality_factor: float = 30.0) -> StreamingSOSFilter:
    b, a = sps.iirnotch(freq_hz, quality_factor, fs=fs)
    sos = sps.tf2sos(b, a)
    return StreamingSOSFilter(sos)


def make_bandpass(low_hz: float, high_hz: float, fs: float, order: int = 2) -> StreamingSOSFilter:
    sos = sps.butter(order, [low_hz, high_hz], btype="bandpass", fs=fs, output="sos")
    return StreamingSOSFilter(sos)
