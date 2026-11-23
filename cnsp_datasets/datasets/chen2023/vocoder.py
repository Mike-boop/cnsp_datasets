"""
Noise vocoder ported from Gaudrain's MATLAB vocoder toolbox (github.com/egaudrain/vocoder, commit 09e4452:
vocode.m, filter_bands.m, greenwud.m), with the toolbox defaults and the parameters in Chen et al. (2023):
200-7000 Hz, Greenwood-spaced bands, half-wave rectified envelope low-passed at 250 Hz, noise carrier, RMS matched.

The authors' noise was seeded from the clock (toolbox default `sum(100*clock)`), so the noise fine structure cannot
be reproduced: a rebuild matches the presented sound in its band envelopes only. See notes.md, section 4.
scipy's filtfilt pads the edges slightly differently from MATLAB's (first and last samples only).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt, sosfiltfilt

RANGE_HZ = (200.0, 7000.0)  # paper
BAND_ORDER = 3  # filter_bands default (Butterworth, applied forward and backward)
ENV_FC_HZ, ENV_ORDER = 250.0, 2  # vocode defaults (paper: low-pass at 250 Hz)


def greenwood_bands(n: int, lo: float = RANGE_HZ[0], hi: float = RANGE_HZ[1]) -> np.ndarray:
    """Band edges (n + 1) equidistant on the cochlea (greenwud.m: a = 0.06, k = 165.4)."""
    mm = np.log10(np.array([lo, hi]) / 165.4 + 1) / 0.06
    return 165.4 * (10 ** (0.06 * np.linspace(mm[0], mm[1], n + 1)) - 1)


def vocode(x: np.ndarray, fs: float, n: int, seed: int) -> np.ndarray:
    """n-channel noise-vocoded copy of the mono signal x (vocode.m, output 'synth', carrier 'noise')."""
    x = np.asarray(x, dtype=float)
    edges = greenwood_bands(n)
    rms_out = _rms(sosfiltfilt(butter(BAND_ORDER, edges[[0, -1]], "bandpass", fs=fs, output="sos"), x))
    b_env, a_env = butter(ENV_ORDER, ENV_FC_HZ, "low", fs=fs)
    out = np.zeros_like(x)
    for lo, hi in zip(edges[:-1], edges[1:]):
        band = butter(BAND_ORDER, [lo, hi], "bandpass", fs=fs, output="sos")
        y = sosfiltfilt(band, x)
        env = np.maximum(filtfilt(b_env, a_env, np.maximum(y, 0)), 0)
        noise = np.sign(np.random.default_rng(seed).random(x.size) - 0.5)  # re-seeded per band, as rng() in vocode.m
        # env / max(env) as in vocode.m; a no-op under the band RMS match below
        mod = sosfiltfilt(band, env / env.max() * noise)
        out += mod / _rms(mod) * _rms(y)
    return out / _rms(out) * rms_out


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2)))
