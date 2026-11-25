"""Validate the decoder drift path with a known drift: for long strong chapters of one listener, train the LOCO
decoder (pass-2 shifts from decoder/sub-<sub>.csv), warp the held-out chapter's EEG so that the sound slides later by
b * t (EEG'(t) = EEG(t (1 - b)), linear interpolation), and recover b with the analysis' window method (30-s windows,
10-s hop, peak within L +- 0.25 s, Theil-Sen). Expected: recovered(b) - recovered(0) = b.
usage: inject_drift.py <sub> <chapter key> ...   (e.g. 01 garnettdream_ch01)"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 2)
import csv, sys
import numpy as np
from scipy.stats import theilslopes
C = settings.ALIGN
FS = 50; LAGS = np.arange(13); SMAX = 200; SH = np.arange(SMAX + 1); WIN, HOP = 30 * FS, 10 * FS
sub, targets = sys.argv[1], sys.argv[2:]
rows = {r['key']: r for r in csv.DictReader(open(f'{C}/decoder/sub-{sub}.csv'))}
keys = sorted(rows)


def design(x, e):
    n = min(len(e), x.shape[0] - LAGS[-1])
    X = np.concatenate([x[l:l + n] for l in LAGS], 1)[SMAX:n]
    return ((X - X.mean(0)) / X.std(0)).astype(np.float32), e, n


def target(e, n, s):
    y = e[SMAX - s:n - s]; return (y - y.mean()) / y.std()


G = np.zeros((129 * 13, 129 * 13)); XtY = {}
data = {}
for k in keys:
    d = np.load(f'{C}/cache/sub-{sub}_{k}.npz')
    X, e, n = design(d['eeg50'].T, d['env50'])
    s = int(round((float(rows[k]['L_ms']) - float(rows[k]['off_ms'])) / 1e3 * FS)) if float(rows[k]['z']) >= 5 else 26
    s = min(max(s, 0), SMAX)
    g = X.T.astype(np.float64) @ X; xy = X.T.astype(np.float64) @ target(e, n, s)
    G += g; XtY[k] = (g, xy)
    if k in targets:
        data[k] = (d['eeg50'].T, d['env50'])
    del X
lam = 1e-2 * np.trace(G) / G.shape[0]
for k in targets:
    w = np.linalg.solve(G - XtY[k][0] + lam * np.eye(len(G)), sum(v[1] for j, v in XtY.items() if j != k))
    x, e = data[k]
    L = (float(rows[k]['L_ms']) - float(rows[k]['off_ms'])) / 1e3
    out = []
    for b_ppm in (-50, 0, 50):
        b = b_ppm * 1e-6; t = np.arange(len(x))
        xw = np.stack([np.interp(t * (1 - b), t, x[:, c]) for c in range(x.shape[1])], 1)
        X, e_, n = design(xw, e)
        rec = X @ w.astype(np.float32); rec = (rec - rec.mean()) / rec.std()
        Y = np.stack([target(e_, n, s) for s in SH], 1)
        sel = np.flatnonzero(np.abs(SH / FS - L) <= 0.25)
        tc, pk = [], []
        for s0 in range(0, len(rec) - WIN + 1, HOP):
            r_ = rec[s0:s0 + WIN]; Yw = Y[s0:s0 + WIN]
            c = ((r_ - r_.mean())[:, None] * (Yw - Yw.mean(0))).sum(0) / (r_.std() * Yw.std(0) * WIN)
            cs = c[sel]; i = int(np.argmax(cs))
            dd = 0.5 * (cs[i - 1] - cs[i + 1]) / (cs[i - 1] - 2 * cs[i] + cs[i + 1]) if 0 < i < len(cs) - 1 else 0
            pk.append((sel[0] + i + dd) / FS); tc.append((s0 + SMAX + WIN / 2) / FS)
        out.append((b_ppm, theilslopes(pk, tc)[0] * 1e6))
    base = out[1][1]
    print(f'sub-{sub} {k} ({len(x) / FS:.0f} s): ' + ', '.join(f'injected {bp:+d} -> recovered {r:+.1f} ppm (diff {r - base:+.1f})' for bp, r in out), flush=True)
