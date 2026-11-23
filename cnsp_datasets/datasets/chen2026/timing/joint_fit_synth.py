"""Synthetic test of align/scan.py:joint_fit (never used before): per-window score matrices with a known onset and
drift, lag(t) = onset + b t (lag_scores convention), Gaussian peak (sigma 60 ms) with a negative side lobe plus white
noise. Grid: SNR (peak / noise SD per window), drift, chapter length. Reports bias, RMSE and the jackknife-SE
calibration (SD of z = (est - true) / se). usage: joint_fit_synth.py <out_dir>"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 1)
import json, os, sys
import numpy as np
from cnsp_datasets.align.scan import joint_fit, pooled_drift

FS, SEG, HOP = 128, 640, 128
LAGS = np.arange(-round(1.5 * FS), round(0.5 * FS) + 1)
rng = np.random.default_rng(0)
out = sys.argv[1]; os.makedirs(out, exist_ok=True)


def synth(dur_s, onset_s, drift_ppm, snr):
    starts = np.arange(max(0, -LAGS.min()), round(dur_s * FS) - LAGS.max() - SEG, HOP)
    t = (starts + SEG / 2) / FS
    true_lag = onset_s * FS + drift_ppm * 1e-6 * t * FS
    d = LAGS[:, None] - true_lag[None, :]
    sig = 7.7  # samples = 60 ms
    peak = np.exp(-d ** 2 / (2 * sig ** 2)) - 0.5 * np.exp(-(d - 3 * sig) ** 2 / (2 * sig ** 2))
    return snr * peak + rng.standard_normal(peak.shape), starts


res = []
for dur in (120, 300, 600, 1200):
    for drift in (-100, -30, 0, 30, 100):
        for snr in (0.05, 0.1, 0.2, 0.5):
            est = []
            for rep in range(40):
                onset = rng.uniform(-0.7, -0.4)
                s, st = synth(dur, onset, drift, snr)
                f = joint_fit(s, st, LAGS, FS, SEG)
                est.append((f['onset'] / FS - onset, f['onset_se'] / FS, f['drift_ppm'] - drift, f['drift_se']))
            e = np.array(est)
            r = dict(dur=dur, drift=drift, snr=snr,
                     onset_bias_ms=1e3 * np.median(e[:, 0]), onset_rmse_ms=1e3 * np.sqrt(np.mean(e[:, 0] ** 2)),
                     onset_z_sd=float(np.std(e[:, 0] / np.maximum(e[:, 1], 1e-9))),
                     onset_se_med_ms=1e3 * np.median(e[:, 1]),
                     drift_bias=float(np.median(e[:, 2])), drift_rmse=float(np.sqrt(np.mean(e[:, 2] ** 2))),
                     drift_z_sd=float(np.std(e[:, 2] / np.maximum(e[:, 3], 1e-9))), drift_se_med=float(np.median(e[:, 3])),
                     frac_onset_off_100ms=float(np.mean(np.abs(e[:, 0]) > 0.1)))
            res.append(r)
            print(' '.join(f'{k} {v:.3g}' if isinstance(v, float) else f'{k} {v}' for k, v in r.items()), flush=True)

# pooled drift over several chapters of one session (different onsets, same drift)
pool = []
for snr in (0.05, 0.1, 0.2):
    for rep in range(30):
        drift = rng.uniform(-60, 60)
        fits = [joint_fit(*synth(d, rng.uniform(-0.7, -0.4), drift, snr), LAGS, FS, SEG) for d in (300, 420, 600, 250, 500)]
        p = pooled_drift(fits, FS)
        pool.append((snr, p['drift_ppm'] - drift, p['drift_se']))
p = np.array(pool)
for snr in (0.05, 0.1, 0.2):
    q = p[p[:, 0] == snr]
    print(f'pooled 5 chapters snr {snr}: drift bias {np.median(q[:, 1]):+.1f} rmse {np.sqrt(np.mean(q[:, 1] ** 2)):.1f} ppm, '
          f'median se {np.median(q[:, 2]):.1f}, z sd {np.std(q[:, 1] / q[:, 2]):.2f}')
json.dump(res, open(f'{out}/joint_fit_synth.json', 'w'), indent=1)
