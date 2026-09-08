import numpy as np

from src.signal_processing.filters import make_lowpass, make_notch, remove_dc


def test_remove_dc_reduces_offset():
    fs = 500
    t = np.arange(2 * fs) / fs
    signal = 5.0 + 0.1 * np.sin(2 * np.pi * 1.0 * t)

    out, _ = remove_dc(signal, running_mean=0.0, alpha=0.01)

    assert abs(np.mean(out[fs:])) < 1.0


def test_lowpass_attenuates_high_frequency():
    fs = 500.0
    t = np.arange(fs * 2) / fs
    low = np.sin(2 * np.pi * 5 * t)
    high = np.sin(2 * np.pi * 120 * t)
    combined = low + high

    lp = make_lowpass(cutoff_hz=40.0, fs=fs)
    out = lp.process(combined)

    settled = slice(int(fs), None)
    residual_high_energy = np.std(out[settled] - low[settled])
    original_high_energy = np.std(high[settled])
    assert residual_high_energy < original_high_energy


def test_notch_attenuates_50hz_tone():
    fs = 500.0
    t = np.arange(fs * 2) / fs
    tone50 = np.sin(2 * np.pi * 50 * t)

    notch = make_notch(50.0, fs)
    out = notch.process(tone50)

    settled = slice(int(fs), None)
    assert np.std(out[settled]) < 0.3 * np.std(tone50[settled])
