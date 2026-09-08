"""Synthetic ECG/respiration generator used by Simulation Mode.

Produces a stylized waveform (P wave, QRS complex, T wave) with small RR-interval
variability, slow baseline wander, and configurable noise, scaled to look like raw
ADS1292R ADC counts. This is NOT a physiological model or a substitute for real
patient data — it exists purely so the UI and processing pipeline can be exercised
and demonstrated without any hardware connected. The app must always make it obvious
when Simulation Mode is active.
"""

from __future__ import annotations

import numpy as np


def _gaussian(t: np.ndarray, center: float, width: float, amplitude: float) -> np.ndarray:
    return amplitude * np.exp(-0.5 * ((t - center) / width) ** 2)


class ECGSimulator:
    def __init__(
        self,
        fs: float = 500.0,
        heart_rate_bpm: float = 72.0,
        rr_variability: float = 0.03,
        noise_amplitude: float = 0.015,
        baseline_wander_amplitude: float = 0.06,
        baseline_wander_hz: float = 0.2,
        respiration_rate_bpm: float = 15.0,
        ecg_amplitude_counts: float = 300_000.0,
        resp_amplitude_counts: float = 20_000.0,
        seed: int | None = None,
    ) -> None:
        self.fs = fs
        self.heart_rate_bpm = heart_rate_bpm
        self.rr_variability = rr_variability
        self.noise_amplitude = noise_amplitude
        self.baseline_wander_amplitude = baseline_wander_amplitude
        self.baseline_wander_hz = baseline_wander_hz
        self.respiration_rate_bpm = respiration_rate_bpm
        self.ecg_amplitude_counts = ecg_amplitude_counts
        self.resp_amplitude_counts = resp_amplitude_counts

        self._rng = np.random.default_rng(seed)
        self._time_s = 0.0
        self._beat_centers: list[float] = []
        self._next_beat_time_s = self._sample_rr_interval_s()
        self._wander_phase = self._rng.uniform(0.0, 2 * np.pi)

    def _sample_rr_interval_s(self) -> float:
        base_rr = 60.0 / self.heart_rate_bpm
        jitter = self._rng.normal(0.0, self.rr_variability * base_rr)
        return max(0.25, base_rr + jitter)

    @staticmethod
    def _beat_waveform(dt: np.ndarray) -> np.ndarray:
        p = _gaussian(dt, -0.20, 0.025, 0.12)
        q = _gaussian(dt, -0.05, 0.010, -0.12)
        r = _gaussian(dt, 0.00, 0.008, 1.00)
        s = _gaussian(dt, 0.04, 0.012, -0.28)
        t = _gaussian(dt, 0.25, 0.050, 0.28)
        return p + q + r + s + t

    def generate_chunk(self, n_samples: int) -> tuple[np.ndarray, np.ndarray]:
        """Returns (ecg_counts, respiration_counts) arrays of length ``n_samples``."""
        if n_samples <= 0:
            return np.empty(0), np.empty(0)

        times = self._time_s + np.arange(n_samples) / self.fs
        horizon = times[-1] + 1.0

        while self._next_beat_time_s < horizon:
            self._beat_centers.append(self._next_beat_time_s)
            self._next_beat_time_s += self._sample_rr_interval_s()
        cutoff = self._time_s - 1.0
        self._beat_centers = [c for c in self._beat_centers if c >= cutoff]

        shape = np.zeros(n_samples)
        for center in self._beat_centers:
            dt = times - center
            mask = np.abs(dt) < 0.45
            if np.any(mask):
                shape[mask] += self._beat_waveform(dt[mask])

        baseline = self.baseline_wander_amplitude * np.sin(
            2 * np.pi * self.baseline_wander_hz * times + self._wander_phase
        )
        noise = (
            self._rng.normal(0.0, self.noise_amplitude, n_samples)
            if self.noise_amplitude > 0
            else 0.0
        )
        ecg_norm = shape + baseline + noise
        ecg_counts = ecg_norm * self.ecg_amplitude_counts

        resp_noise = (
            self._rng.normal(0.0, self.noise_amplitude * 0.3, n_samples)
            if self.noise_amplitude > 0
            else 0.0
        )
        resp_norm = np.sin(2 * np.pi * (self.respiration_rate_bpm / 60.0) * times) + resp_noise
        resp_counts = resp_norm * self.resp_amplitude_counts

        self._time_s = times[-1] + 1.0 / self.fs
        return ecg_counts, resp_counts
