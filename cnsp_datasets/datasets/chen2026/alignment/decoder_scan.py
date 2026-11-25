"""Per-chapter sound latency (and within-chapter drift data) from a listener-specific backward decoder, trained
leave-one-chapter-out (LOCO) so a chapter's estimate never uses its own EEG for training.

Inputs: align/cache (eeg50: 129 ch avg ref, 1-8 Hz, 50 Hz, sample 0 = floor(t0*50); env50: |audio| 1-8 Hz from audio
sample 0). Decoder: ridge, EEG lags 0..240 ms after the target sample (crossdec.py). Target at shift s: env[t - s],
i.e. the sound s seconds after EEG sample 0. Rows t in [SMAX, wav end) for every shift.
Shift range 0..4 s (some sd.play() calls start > 1.5 s late). Pass 1 (unanchored): training shift S0 on 0.2..1.0 s chosen by mean held-out r at S0. Pass 2: training chapters
shifted by their own pass-1 latency (only chapters with z >= 5; others at S0*). Per held-out chapter: r vs shift on
0..4 s (20 ms grid, parabolic peak), jackknife SE over 10 contiguous chunks, z against 10 mismatched envelopes
(max over shifts), window curves (30 s windows, 10 s hop) for drift, and odd/even 30-s block halves for validation.
Latency L (s after t0) = peak shift + (te50 - t0) (te50 = floor(t0*50)/50 <= t0).
usage: decoder_scan.py <sub>  -> align/decoder/sub-<sub>.npz + .csv"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 1)
import csv, glob, os, sys
import numpy as np
from scipy.linalg import cho_factor, cho_solve
C = settings.ALIGN
FS = 50; LAGS = np.arange(13); SMAX = 200; SH = np.arange(SMAX + 1); WIN, HOPW = 30 * FS, 10 * FS
sub = sys.argv[1]
os.makedirs(f'{C}/decoder', exist_ok=True)
files = sorted(glob.glob(f'{C}/cache/sub-{sub}_*.npz'))
keys, X, E, meta = [], [], [], []
for f in files:
    d = np.load(f)
    x, e = d['eeg50'].T, d['env50']
    n = min(len(e), x.shape[0] - LAGS[-1])
    Xk = np.concatenate([x[l:l + n] for l in LAGS], 1)[SMAX:n]       # rows t = SMAX..n-1
    Xk = (Xk - Xk.mean(0)) / Xk.std(0)
    Yk = np.stack([e[SMAX - s:n - s] for s in SH], 1)                # column s: env[t - s]
    Yk = (Yk - Yk.mean(0)) / Yk.std(0)
    keys.append(os.path.basename(f)[len(f'sub-{sub}_'):-4]); X.append(Xk.astype(np.float32)); E.append(Yk)
    meta.append(dict(t0=float(d['t0']), te=float(d['te50']), wav=float(d['wav_s']), env=e))
K = len(keys)
G = [Xk.T.astype(np.float64) @ Xk for Xk in X]
XtY = [Xk.T.astype(np.float64) @ Yk for Xk, Yk in zip(X, E)]
Gt = sum(G)
lam = 1e-2 * np.trace(Gt) / Gt.shape[0] / K * (K - 1)
chol = [cho_factor(Gt - G[k] + lam * np.eye(len(Gt))) for k in range(K)]
print(f'sub-{sub}: {K} chapters loaded', flush=True)


def corr_curve(rec, Y):
    r = (rec - rec.mean()) / rec.std()
    return (r[:, None] * Y).mean(0)


def peak(c):
    i = int(np.argmax(c))
    if 0 < i < len(c) - 1:
        den = c[i - 1] - 2 * c[i] + c[i + 1]
        return i + (0.5 * (c[i - 1] - c[i + 1]) / den if den < 0 else 0.0)
    return float(i)


def heldout(k, shifts_train):
    rhs = sum(XtY[j][:, shifts_train[j]] for j in range(K) if j != k)
    return X[k] @ cho_solve(chol[k], rhs).astype(np.float32)


# pass 1: S0 grid
S0s = np.arange(10, 51, 2)
score = []
for S0 in S0s:
    rs = [corr_curve(heldout(k, [S0] * K), E[k][:, S0:S0 + 1])[0] for k in range(K)]
    score.append(np.mean(rs))
S0 = int(S0s[int(np.argmax(score))])
print(f'sub-{sub}: S0 scan {dict(zip((S0s / FS).round(2).tolist(), np.round(score, 3).tolist()))} -> S0 {S0 / FS:.2f} s', flush=True)
rng = np.random.default_rng(0)


def analyse(shifts_train):
    out = []
    for k in range(K):
        rec = heldout(k, shifts_train)
        c = corr_curve(rec, E[k]); pk = peak(c)
        n = len(rec); ch = np.minimum(np.arange(n) * 10 // n, 9)
        loo = np.array([peak(corr_curve(rec[ch != q], E[k][ch != q])) for q in range(10)])
        se = np.sqrt(9 / 10 * ((loo - loo.mean()) ** 2).sum()) / FS
        others = [j for j in range(K) if j != k]
        nulls = []
        for j in rng.choice(others, min(10, len(others)), replace=False):
            e = np.resize(meta[j]['env'], len(meta[k]['env']))
            m = len(e); nn = min(m, len(rec) + SMAX)
            Yn = np.stack([e[SMAX - s:nn - s] for s in SH], 1)[:len(rec)]
            Yn = (Yn - Yn.mean(0)) / Yn.std(0)
            nulls.append(corr_curve(rec[:len(Yn)], Yn).max())
        z = (c.max() - np.mean(nulls)) / (np.std(nulls) + 1e-9)
        starts = np.arange(0, n - WIN + 1, HOPW)
        W = np.stack([corr_curve(rec[s:s + WIN], E[k][s:s + WIN]) for s in starts], 1) if len(starts) else np.zeros((len(SH), 0))
        blk = (np.arange(n) // (30 * FS)) % 2
        ha = [peak(corr_curve(rec[blk == h], E[k][blk == h])) for h in (0, 1)]
        cb = [corr_curve(rec[blk == h], E[k][blk == h]) for h in (0, 1)]
        off = meta[k]['te'] - meta[k]['t0']
        out.append(dict(key=keys[k], L=pk / FS + off, se=se, r=float(c.max()), z=float(z), curve=c, W=W,
                        wstarts=starts + SMAX, LA=ha[0] / FS + off, LB=ha[1] / FS + off, cA=cb[0], cB=cb[1], off=off))
    return out


p1 = analyse([S0] * K)
good = [o['z'] >= 5 for o in p1]
sh2 = [int(round((o['L'] - o['off']) * FS)) if g else S0 for o, g in zip(p1, good)]
p2 = analyse(sh2)
for o1, o2 in zip(p1, p2):
    print(f"sub-{sub} {o2['key']:18s} pass1 L {o1['L'] * 1e3:5.0f} ms z {o1['z']:5.1f} | pass2 L {o2['L'] * 1e3:5.0f} +- {o2['se'] * 1e3:4.0f} ms "
          f"r {o2['r']:.3f} z {o2['z']:5.1f} | halves {o2['LA'] * 1e3:5.0f} / {o2['LB'] * 1e3:5.0f}", flush=True)
np.savez(f'{C}/decoder/sub-{sub}.npz', keys=keys, S0=S0, S0s=S0s, S0score=score, shifts=SH / FS,
         **{f'{nm}_{o["key"]}': o[nm] for o in p2 for nm in ('curve', 'W', 'wstarts', 'cA', 'cB')},
         **{f'p1curve_{o["key"]}': o['curve'] for o in p1})
with open(f'{C}/decoder/sub-{sub}.csv', 'w') as f:
    w = csv.writer(f); w.writerow(['sub', 'key', 'L1_ms', 'z1', 'L_ms', 'se_ms', 'r', 'z', 'LA_ms', 'LB_ms', 'off_ms', 'wav_s'])
    for o1, o2, m in zip(p1, p2, meta):
        w.writerow([sub, o2['key'], round(o1['L'] * 1e3, 1), round(o1['z'], 2), round(o2['L'] * 1e3, 1), round(o2['se'] * 1e3, 1),
                    round(o2['r'], 4), round(o2['z'], 2), round(o2['LA'] * 1e3, 1), round(o2['LB'] * 1e3, 1), round(o2['off'] * 1e3, 2),
                    round(m['wav'], 2)])
