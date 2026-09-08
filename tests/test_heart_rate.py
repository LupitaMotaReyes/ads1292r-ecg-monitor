import numpy as np

from src.signal_processing.heart_rate import HeartRateEstimator, detect_r_peaks


def _gaussian(t: np.ndarray, center: float, width: float, amplitude: float) -> np.ndarray:
    return amplitude * np.exp(-0.5 * ((t - center) / width) ** 2)


def _beat_waveform(dt: np.ndarray) -> np.ndarray:
    p = _gaussian(dt, -0.20, 0.025, 0.12)
    q = _gaussian(dt, -0.05, 0.010, -0.12)
    r = _gaussian(dt, 0.00, 0.008, 1.00)
    s = _gaussian(dt, 0.04, 0.012, -0.28)
    t = _gaussian(dt, 0.25, 0.050, 0.28)
    return p + q + r + s + t


class _CleanECGSignal:
    """Generates a noise-free, fixed-rate P-QRS-T waveform with a known BPM.

    Test-only fixture for validating the R-peak detector and BPM estimator against a
    signal whose true heart rate is known exactly; unrelated to any app data source.
    """

    def __init__(self, fs: float, heart_rate_bpm: float) -> None:
        self.fs = fs
        self._rr_interval_s = 60.0 / heart_rate_bpm
        self._time_s = 0.0
        self._next_beat_time_s = self._rr_interval_s
        self._beat_centers: list[float] = []

    def generate_chunk(self, n_samples: int) -> np.ndarray:
        times = self._time_s + np.arange(n_samples) / self.fs
        horizon = times[-1] + 1.0

        while self._next_beat_time_s < horizon:
            self._beat_centers.append(self._next_beat_time_s)
            self._next_beat_time_s += self._rr_interval_s
        cutoff = self._time_s - 1.0
        self._beat_centers = [c for c in self._beat_centers if c >= cutoff]

        shape = np.zeros(n_samples)
        for center in self._beat_centers:
            dt = times - center
            mask = np.abs(dt) < 0.45
            if np.any(mask):
                shape[mask] += _beat_waveform(dt[mask])

        self._time_s = times[-1] + 1.0 / self.fs
        return shape * 300_000.0


def test_heart_rate_estimator_recovers_known_rate():
    fs = 500.0
    target_bpm = 72.0
    signal = _CleanECGSignal(fs, target_bpm)
    estimator = HeartRateEstimator(fs=fs)

    chunk_size = 50
    bpm = None
    for _ in range(200):  # 200 * 50 / 500 Hz = 20 s of signal
        ecg = signal.generate_chunk(chunk_size)
        bpm = estimator.process(ecg)

    assert bpm is not None
    assert abs(bpm - target_bpm) < 5.0


def test_detect_r_peaks_batch_matches_expected_count():
    fs = 500.0
    duration_s = 10.0
    target_bpm = 60.0
    signal = _CleanECGSignal(fs, target_bpm)
    ecg = signal.generate_chunk(int(fs * duration_s))

    peaks = detect_r_peaks(ecg, fs)

    expected_beats = duration_s * target_bpm / 60.0
    assert abs(len(peaks) - expected_beats) <= 2
