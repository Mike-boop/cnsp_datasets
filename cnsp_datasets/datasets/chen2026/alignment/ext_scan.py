"""Extended-range latency search (-1..+8 s after t0) for chapters that fail the z >= 2 decoder rule (align/z2/fail_z2.csv).
(a) decoder: LOCO ridge decoder of the listener (same features and pass-2 training shifts as decoder_scan.py: own
    latency for chapters with z >= 5, else S0), held-out r vs shift on -1..+8 s (20 ms), parabolic peak, jackknife SE
    over 10 chunks, z against 10 mismatched envelopes (max over the same range);
(b) DNN: lag_scores (fs128_1020-64) on latency -1..+8 s, 5 mismatched nulls; z/SE as analyse_timing.dnn_chapter.
Caches reused (align/cache); results to align/ext/sub-XX_<key>.npz.  usage: ext_scan.py <sub>"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 1)
import csv, os, sys
import numpy as np
import torch
from scipy.stats import zscore
from cnsp_datasets.align.scan import lag_scores
from cnsp_datasets.align.specs import load_classifier
torch.set_num_threads(4)
A = settings.ALIGN
os.makedirs(f'{A}/ext', exist_ok=True)
FS = 50; LAGS = np.arange(13); NEG, POS = 50, 400                  # shifts -1 s .. +8 s at 50 Hz
SH = np.arange(-NEG, POS + 1)
sub = sys.argv[1]
fails = [r['key'] for r in csv.DictReader(open(f'{A}/z2/fail_z2.csv')) if r['sub'] == sub]
rows = {r['key']: r for r in csv.DictReader(open(f'{A}/decoder/sub-{sub}.csv'))}
S0 = int(round(float(np.load(f'{A}/decoder/sub-{sub}.npz')['S0'])))
keys = sorted(rows)


def design(k):
    d = np.load(f'{A}/cache/sub-{sub}_{k}.npz')
    x, e = d['eeg50'].T, d['env50']
    n = min(len(e), x.shape[0] - LAGS[-1])
    X = np.concatenate([x[l:l + n] for l in LAGS], 1)[POS:n - NEG]
    return ((X - X.mean(0)) / X.std(0)).astype(np.float32), e, n, d


def ycol(e, n, s):
    y = e[POS - s:n - NEG - s]; return (y - y.mean()) / y.std()


# decoder training sums (streamed, as inject_drift.py)
G = None; parts = {}
for k in keys:
    X, e, n, _ = design(k)
    s = int(round((float(rows[k]['L_ms']) - float(rows[k]['off_ms'])) / 1e3 * FS)) if float(rows[k]['z']) >= 5 else S0
    g = X.T.astype(np.float64) @ X; xy = X.T.astype(np.float64) @ ycol(e, n, s)
    G = g if G is None else G + g; parts[k] = (g, xy)
lam = 1e-2 * np.trace(G) / G.shape[0]
envs = {k: np.load(f'{A}/cache/sub-{sub}_{k}.npz')['env50'] for k in keys}
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
model, spec, _ = load_classifier(settings.MODEL, dev)
DL = np.arange(-8 * 128, 1 * 128 + 1)                              # DNN lags: latency -1 .. +8 s
rng = np.random.default_rng(0)


def peak(c):
    i = int(np.argmax(c))
    if 0 < i < len(c) - 1:
        den = c[i - 1] - 2 * c[i] + c[i + 1]
        return i + (0.5 * (c[i - 1] - c[i + 1]) / den if den < 0 else 0.0)
    return float(i)


def curve(rec, Y):
    r = (rec - rec.mean()) / rec.std(); return (r[:, None] * Y).mean(0)


for k in fails:
    out = f'{A}/ext/sub-{sub}_{k}.npz'
    if os.path.exists(out):
        continue
    w = np.linalg.solve(G - parts[k][0] + lam * np.eye(len(G)), sum(v[1] for j, v in parts.items() if j != k))
    X, e, n, d = design(k)
    rec = X @ w.astype(np.float32); del X
    Y = np.stack([ycol(e, n, s) for s in SH], 1)
    c = curve(rec, Y)
    ch = np.minimum(np.arange(len(rec)) * 10 // len(rec), 9)
    loo = np.array([peak(curve(rec[ch != q], Y[ch != q])) for q in range(10)])
    se = np.sqrt(0.9 * ((loo - loo.mean()) ** 2).sum()) / FS
    nulls = []
    for j in rng.choice([j for j in keys if j != k], 10, replace=False):
        en = np.resize(envs[j], len(e))
        Yn = np.stack([ycol(en, n, s) for s in SH], 1)
        nulls.append(curve(rec, Yn).max())
    zdec = (c.max() - np.mean(nulls)) / (np.std(nulls) + 1e-9)
    off50 = float(d['te50']) - float(d['t0'])
    # DNN
    eeg, env = d['eeg128'], d['env128'].mean(0, keepdims=True)
    m = min(eeg.shape[1], env.shape[1] - DL.min())
    eeg = zscore(eeg[:, :m], axis=-1).astype(np.float32)
    stim = np.concatenate([zscore(env, axis=-1), np.zeros((1, max(0, m - env.shape[1])))], 1)[:, :m].astype(np.float32)
    sc, st = lag_scores(model, eeg, stim, DL, 640, 128, device=dev)
    nl = []
    for j in rng.choice([j for j in keys if j != k], 5, replace=False):
        g = np.load(f'{A}/cache/sub-{sub}_{j}.npz')['env128'].mean(0, keepdims=True)
        g = zscore(np.resize(g, (1, m)), axis=-1).astype(np.float32)
        nl.append(lag_scores(model, eeg, g, DL, 640, 128, device=dev)[0].mean(1))
    np.savez(out, dec_lat=SH / FS + off50, dec_curve=c, dec_L=(SH[0] + peak(c)) / FS + off50, dec_se=se, dec_z=zdec,
             dnn_lat=-DL / 128 - (float(d['t0']) - float(d['te128'])), dnn_scores=sc.astype(np.float32), dnn_null=np.stack(nl, 1))
    print(f'sub-{sub} {k}: decoder L {((SH[0] + peak(c)) / FS + off50) * 1e3:.0f} ms z {zdec:.1f} SE {se * 1e3:.0f}', flush=True)
