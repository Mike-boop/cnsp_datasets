"""
Windowed cross-correlation of the audio-copy drift scripts: 10 s windows every 5 s at 1 kHz, a 2-200 Hz
band-pass and a Theil-Sen line through the window lags (window_fit: yang2026, kern2022; constants and band-pass
also jehn2025, schueller2024, habersetzer2025).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, correlate
from scipy.stats import theilslopes

WIN, HOP, MAX_LAG = 10_000, 5_000, 30  # samples at 1 kHz
SOS = butter(4, [2, 200], "bp", fs=1000, output="sos")


def window_fit(y: np.ndarray, s: np.ndarray, ref: int, max_lag: int, min_r: float,
               win: int = WIN, hop: int = HOP) -> tuple[float, float, int]:
    """
    Theil-Sen line through the lags of s in y[ref:] (windows of `win` samples every `hop`, signed normalised xcorr
    within +-max_lag, sub-sample peak, windows with r > min_r): intercept (samples), slope (fraction), number of
    windows. Fewer than 2 valid windows: (nan, nan, n).
    """
    t, lags = [], []
    for a in range(0, len(s) - win + 1, hop):
        seg = y[ref + a - max_lag:ref + a + win + max_lag]
        if ref + a < max_lag or len(seg) < win + 2 * max_lag:
            continue
        w = s[a:a + win]
        energy = np.cumsum(np.r_[0, seg ** 2])
        c = correlate(seg, w, "valid", method="fft") / np.sqrt(
            (energy[win:] - energy[:-win]) * (w ** 2).sum() + 1e-30)
        k = int(np.argmax(c))
        if c[k] > min_r:
            den = c[k - 1] - 2 * c[k] + c[k + 1] if 0 < k < len(c) - 1 else 0
            t.append(a + win / 2)
            lags.append(k - max_lag + (0.5 * (c[k - 1] - c[k + 1]) / den if den else 0.0))
    if len(t) < 2:
        return np.nan, np.nan, len(t)
    slope, intercept, _, _ = theilslopes(lags, t)
    return intercept, slope, len(t)
