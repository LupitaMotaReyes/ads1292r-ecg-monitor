from src.signal_processing.heart_rate import HeartRateEstimator, detect_r_peaks
from src.simulation.ecg_simulator import ECGSimulator


def _clean_simulator(fs: float, bpm: float, seed: int) -> ECGSimulator:
    return ECGSimulator(
        fs=fs,
        heart_rate_bpm=bpm,
        rr_variability=0.0,
        noise_amplitude=0.0,
        baseline_wander_amplitude=0.0,
        seed=seed,
    )


def test_heart_rate_estimator_recovers_known_rate():
    fs = 500.0
    target_bpm = 72.0
    simulator = _clean_simulator(fs, target_bpm, seed=42)
    estimator = HeartRateEstimator(fs=fs)

    chunk_size = 50
    bpm = None
    for _ in range(200):  # 200 * 50 / 500 Hz = 20 s of signal
        ecg, _ = simulator.generate_chunk(chunk_size)
        bpm = estimator.process(ecg)

    assert bpm is not None
    assert abs(bpm - target_bpm) < 5.0


def test_detect_r_peaks_batch_matches_expected_count():
    fs = 500.0
    duration_s = 10.0
    target_bpm = 60.0
    simulator = _clean_simulator(fs, target_bpm, seed=1)
    ecg, _ = simulator.generate_chunk(int(fs * duration_s))

    peaks = detect_r_peaks(ecg, fs)

    expected_beats = duration_s * target_bpm / 60.0
    assert abs(len(peaks) - expected_beats) <= 2
