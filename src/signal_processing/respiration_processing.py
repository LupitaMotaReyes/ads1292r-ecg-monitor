"""Respiration waveform filtering and breathing-rate estimation.

Only meaningful if the ADS1292R's respiration channel is actually wired and enabled
(``src.config.ADS1292RConfig.respiration_channel``). If that channel is not available,
callers should not construct a ``RespirationProcessor`` at all and should instead show
"Respiration signal unavailable" in the UI — this module never fabricates a rate.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
from scipy.signal import find_peaks

from src.signal_processing.filters import StreamingSOSFilter, make_bandpass

# Typical adult resting respiration is roughly 8-25 breaths/min; the band is kept a
# little wider to tolerate slow/fast breathing without being a clinical claim.
RESPIRATION_BANDPASS_LOW_HZ = 0.1
RESPIRATION_BANDPASS_HIGH_HZ = 0.5


@dataclass
class RespirationProcessor:
    fs: float
    min_breaths_per_min: float = 4.0
    max_breaths_per_min: float = 40.0
    smoothing_breaths: int = 4

    _filter: StreamingSOSFilter = field(default=None, init=False)
    _sample_index: int = field(default=0, init=False)
    _last_peak_index: int | None = field(default=None, init=False)
    _interval_history: deque = field(default=None, init=False)
    _tail_buffer: np.ndarray = field(default=None, init=False)
    _rate_bpm: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._filter = make_bandpass(
            RESPIRATION_BANDPASS_LOW_HZ, RESPIRATION_BANDPASS_HIGH_HZ, self.fs, order=2
        )
        self._refractory_samples = max(1, int(round(60.0 / self.max_breaths_per_min * self.fs)))
        self._interval_history = deque(maxlen=self.smoothing_breaths)
        # keep enough context to span slow breathing (down to min_breaths_per_min)
        self._tail_capacity = int(round(2 * 60.0 / self.min_breaths_per_min * self.fs))
        self._tail_buffer = np.empty(0, dtype=np.float64)

    @property
    def breaths_per_minute(self) -> float | None:
        return self._rate_bpm

    def process(self, raw_chunk: np.ndarray) -> tuple[np.ndarray, float | None]:
        """Filter a new chunk and update the breathing-rate estimate.

        Returns (filtered_chunk, current_breaths_per_minute_or_None).
        """
        chunk = np.asarray(raw_chunk, dtype=np.float64)
        if len(chunk) == 0:
            return chunk, self._rate_bpm

        filtered = self._filter.process(chunk)

        combined = np.concatenate((self._tail_buffer, filtered))
        offset = self._sample_index - len(self._tail_buffer)
        peak_amplitude = np.max(np.abs(combined)) if len(combined) else 0.0
        if peak_amplitude > 0 and len(combined) > self._refractory_samples:
            threshold = 0.3 * peak_amplitude
            peaks, _ = find_peaks(combined, distance=self._refractory_samples, height=threshold)
            for local_peak in peaks:
                global_index = offset + int(local_peak)
                if global_index >= self._sample_index:
                    self._register_peak(global_index)

        self._sample_index += len(chunk)
        keep = min(len(combined), self._tail_capacity)
        self._tail_buffer = combined[-keep:] if keep else np.empty(0, dtype=np.float64)
        return filtered, self._rate_bpm

    def _register_peak(self, global_index: int) -> None:
        if self._last_peak_index is None:
            self._last_peak_index = global_index
            return

        interval_samples = global_index - self._last_peak_index
        if interval_samples < self._refractory_samples:
            return

        interval_s = interval_samples / self.fs
        rate_instant = 60.0 / interval_s
        self._last_peak_index = global_index

        if self.min_breaths_per_min <= rate_instant <= self.max_breaths_per_min:
            self._interval_history.append(interval_s)
            mean_interval_s = sum(self._interval_history) / len(self._interval_history)
            self._rate_bpm = 60.0 / mean_interval_s
