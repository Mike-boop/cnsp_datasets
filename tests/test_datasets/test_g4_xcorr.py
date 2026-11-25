"""Shared windowed xcorr fit (jehn2025_base.alignment.xcorr) on synthetic signals."""
import numpy as np

from cnsp_datasets.datasets.jehn2025_base.alignment.xcorr import window_fit


def test_window_fit_recovers_lag():
    rng = np.random.default_rng(1)
    s = rng.standard_normal(60_000)
    y = np.r_[np.zeros(1000 + 7), s, np.zeros(1000)]  # s starts 7 samples after ref = 1000
    onset, slope, n = window_fit(y, s, 1000, 30, 0.3)
    assert n >= 10 and abs(onset - 7) < 1e-6 and abs(slope) < 1e-9


def test_window_fit_no_windows():
    rng = np.random.default_rng(2)
    onset, slope, n = window_fit(rng.standard_normal(30_000), rng.standard_normal(20_000), 100, 30, 0.9)
    assert n == 0 and np.isnan(onset) and np.isnan(slope)
