"""joint_fit drift bias: is it the linear lag interpolation (exact at b = 0, smoothing elsewhere)? Compare
(a) joint_fit on the scores, (b) joint_fit on scores smoothed along lags (Gaussian, 2 samples), (c) Theil-Sen through
the peaks of 60-s chunk means, under white noise and noise correlated along lags (sigma 4 samples) and windows
(5-window boxcar = 5 s segments at 1 s hop). usage: joint_fit_synth2.py <out.json>"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 1)
import json, sys
import numpy as np
from scipy.ndimage import gaussian_filter1d, uniform_filter1d
from scipy.stats import theilslopes
from cnsp_datasets.align.scan import joint_fit, peak_offset

FS, SEG, HOP = 128, 640, 128
LAGS = np.arange(-round(1.5 * FS), round(0.5 * FS) + 1)
rng = np.random.default_rng(1)


def synth(dur_s, onset_s, drift_ppm, snr, smooth):
    starts = np.arange(max(0, -LAGS.min()), round(dur_s * FS) - LAGS.max() - SEG, HOP)
    t = (starts + SEG / 2) / FS
    d = LAGS[:, None] - (onset_s * FS + drift_ppm * 1e-6 * t * FS)[None, :]
    sig = 7.7
    peak = np.exp(-d ** 2 / (2 * sig ** 2)) - 0.5 * np.exp(-(d - 3 * sig) ** 2 / (2 * sig ** 2))
    n = rng.standard_normal(peak.shape)
    if smooth:
        n = uniform_filter1d(gaussian_filter1d(n, 4, axis=0), 5, axis=1)
        n /= n.std()
    return snr * peak + n, starts


def chunk_ts(s, st, chunk_s=60):
    t = (st + SEG / 2) / FS
    edges = np.arange(t.min(), t.max() + chunk_s, chunk_s)
    tc, pk = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (t >= a) & (t < b)
        if m.sum() < 10:
            continue
        c = s[:, m].mean(1)
        tc.append(t[m].mean()); pk.append(LAGS[0] + peak_offset(c))
    if len(pk) < 3:
        return np.nan
    return theilslopes(np.array(pk) / FS, tc)[0] * 1e6


res = []
for smooth in (False, True):
    for dur in (300, 600, 1200):
        for drift in (-100, -40, 0, 40, 100):
            for snr in (0.1, 0.3):
                e = []
                for rep in range(25):
                    s, st = synth(dur, rng.uniform(-0.7, -0.4), drift, snr, smooth)
                    fa = joint_fit(s, st, LAGS, FS, SEG)['drift_ppm']
                    fb = joint_fit(gaussian_filter1d(s, 2, axis=0), st, LAGS, FS, SEG)['drift_ppm']
                    e.append((fa - drift, fb - drift, chunk_ts(s, st) - drift))
                e = np.array(e)
                r = dict(smooth=smooth, dur=dur, drift=drift, snr=snr)
                for i, name in enumerate(('raw', 'lagsmooth', 'chunkTS')):
                    r[f'{name}_bias'] = float(np.nanmedian(e[:, i])); r[f'{name}_rmse'] = float(np.sqrt(np.nanmean(e[:, i] ** 2)))
                res.append(r)
                print(' '.join(f'{k} {v:.3g}' if isinstance(v, float) else f'{k} {v}' for k, v in r.items()), flush=True)
json.dump(res, open(sys.argv[1], 'w'), indent=1)
