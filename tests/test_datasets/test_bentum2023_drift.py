import numpy as np
import pytest

from cnsp_datasets.datasets.bentum2023.drift import (
    BlockTiming,
    estimate_drift,
    estimate_marker_offset,
    to_audio_clock,
)


def _synthetic_timings(offset=-1.5, n_recordings=60, seed=0):
    """Recordings with random drift and block durations of 250, 700 or 900 s, like the corpus."""
    rng = np.random.default_rng(seed)
    timings, true_drift = [], {}
    for r in range(n_recordings):
        rec = f"EEG/pp{r:03d}.vhdr"
        drift = rng.normal(33e-6, 6e-6)
        true_drift[rec] = drift
        base = [250_000, 700_000, 900_000][r % 3]
        for _ in range(6):
            dur = base + int(rng.integers(-5_000, 5_000))
            timings.append(BlockTiming(rec, dur, round(offset + drift * dur)))
    return timings, true_drift


def test_marker_offset_recovered():
    timings, _ = _synthetic_timings(offset=-1.5)
    assert estimate_marker_offset(timings) == pytest.approx(-1.5, abs=0.6)


def test_per_recording_drift_recovered():
    timings, true_drift = _synthetic_timings(offset=-1.5)
    est = estimate_drift(timings, marker_offset=-1.5)
    errors = [est.by_recording[rec] - d for rec, d in true_drift.items()]
    # integer rounding of inacc limits precision to about 1 sample / duration
    assert np.max(np.abs(errors)) < 1 / 250_000


def test_unknown_recording_falls_back_to_global():
    timings, _ = _synthetic_timings()
    est = estimate_drift(timings, marker_offset=0)
    assert est.drift("EEG/missing.vhdr") == est.global_drift
    assert est.drift("EEG/pp000.vhdr", mode="global") == est.global_drift
    with pytest.raises(ValueError):
        est.drift("EEG/pp000.vhdr", mode="nope")


def test_to_audio_clock_aligns_a_sinusoid():
    fs, drift, f = 1000.0, 35e-6, 150.0
    n = 120_000
    eeg_times = np.arange(n) / (fs * (1 + drift))   # EEG sample times in audio seconds
    data = np.vstack([np.sin(2 * np.pi * f * eeg_times), np.cos(2 * np.pi * f * eeg_times)])

    out = to_audio_clock(data, drift)
    audio_times = np.arange(out.shape[1]) / fs
    expected = np.vstack([np.sin(2 * np.pi * f * audio_times), np.cos(2 * np.pi * f * audio_times)])

    assert out.shape[1] == int(np.floor((n - 1) / (1 + drift))) + 1
    # ignore the spline's edge samples
    assert np.max(np.abs(out[:, 50:-50] - expected[:, 50:-50])) < 1e-3
    # without correction the end would be ~4 samples (about half a cycle at 150 Hz) out of phase
    assert np.max(np.abs(data[:, -1000:] - expected[:, -1000:])) > 0.5


def test_to_audio_clock_without_drift_is_identity():
    data = np.random.default_rng(0).normal(size=(3, 1000))
    assert to_audio_clock(data, 0.0) is data
