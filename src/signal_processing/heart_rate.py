"""R-peak detection and heart-rate (BPM) estimation from filtered ECG.

Uses a Pan-Tompkins-inspired pipeline (derivative -> square -> moving-window
integration -> adaptive-threshold peak search) plus a refractory period, RR-interval
plausibility rejection, and BPM smoothing across recent beats. This is an engineering
heuristic, not a validated clinical algorithm, and BPM is only ever reported when at
least one physiologically plausible RR interval has actually been measured — it is
never fabricated.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from scipy.signal import find_peaks


def detect_r_peaks(ecg_filtered: np.ndarray, fs: float, refractory_ms: float = 300.0) -> np.ndarray:
    """Batch R-peak detector over a static array. Returns sample indices of detected peaks."""
    ecg_filtered = np.asarray(ecg_filtered, dtype=np.float64)
    window_samples = max(1, int(round(0.15 * fs)))
    distance = max(1, int(round(refractory_ms / 1000.0 * fs)))
    # np.convolve(..., mode="same") returns length max(len(signal), window_samples),
    # not len(signal), when the smoothing window is longer than the signal. Bail out
    # rather than let that length mismatch corrupt the returned peak indices.
    if len(ecg_filtered) < max(3, window_samples):
        return np.array([], dtype=int)
    derivative = np.diff(ecg_filtered, prepend=ecg_filtered[0])
    squared = derivative**2
    integrated = np.convolve(squared, np.ones(window_samples) / window_samples, mode="same")
    peak_value = np.max(integrated)
    if peak_value <= 0:
        return np.array([], dtype=int)
    threshold = 0.3 * peak_value
    peaks, _ = find_peaks(integrated, distance=distance, height=threshold)
    return peaks


@dataclass
class HeartRateEstimator:
    """Streaming R-peak / BPM estimator fed one filtered-ECG chunk at a time."""

    fs: float
    refractory_ms: float = 300.0
    smoothing_beats: int = 5
    min_bpm: float = 30.0
    max_bpm: float = 200.0

    _sample_index: int = field(default=0, init=False)
    _last_peak_index: int | None = field(default=None, init=False)
    _rr_history: deque = field(default=None, init=False)
    _tail_buffer: np.ndarray = field(default=None, init=False)
    _bpm: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._refractory_samples = max(1, int(round(self.refractory_ms / 1000.0 * self.fs)))
        self._rr_history = deque(maxlen=self.smoothing_beats)
        self._tail_buffer = np.empty(0, dtype=np.float64)
        self._tail_capacity = int(self.fs * 2)  # keep ~2 s of context for the integration window

    @property
    def bpm(self) -> float | None:
        return self._bpm

    @property
    def rr_intervals_ms(self) -> list[float]:
        return list(self._rr_history)

    def reset(self) -> None:
        self._sample_index = 0
        self._last_peak_index = None
        self._rr_history.clear()
        self._tail_buffer = np.empty(0, dtype=np.float64)
        self._bpm = None

    def process(self, filtered_chunk: np.ndarray) -> float | None:
        chunk = np.asarray(filtered_chunk, dtype=np.float64)
        if len(chunk) == 0:
            return self._bpm

        combined = np.concatenate((self._tail_buffer, chunk))
        offset = self._sample_index - len(self._tail_buffer)
        peaks = detect_r_peaks(combined, self.fs, refractory_ms=self.refractory_ms)

        # _register_peak is safe to call repeatedly with the same (or an earlier)
        # peak: anything not further than the refractory period past the last
        # accepted peak is ignored, so re-finding the same peak across overlapping
        # windows on successive ticks has no effect on the RR history.
        for local_peak in peaks:
            self._register_peak(offset + int(local_peak))

        self._sample_index += len(chunk)
        keep = min(len(combined), self._tail_capacity)
        self._tail_buffer = combined[-keep:] if keep else np.empty(0, dtype=np.float64)
        return self._bpm

    def _register_peak(self, global_index: int) -> None:
        if self._last_peak_index is None:
            self._last_peak_index = global_index
            return

        rr_samples = global_index - self._last_peak_index
        if rr_samples < self._refractory_samples:
            return  # too close to the previous peak to be a distinct beat

        rr_ms = rr_samples / self.fs * 1000.0
        bpm_instant = 60000.0 / rr_ms
        self._last_peak_index = global_index

        if self.min_bpm <= bpm_instant <= self.max_bpm:
            self._rr_history.append(rr_ms)
            self._bpm = self._smoothed_bpm()
        # else: RR interval outside a plausible physiological range, discarded

    def _smoothed_bpm(self) -> float | None:
        if not self._rr_history:
            return None
        mean_rr_ms = sum(self._rr_history) / len(self._rr_history)
        return 60000.0 / mean_rr_ms
