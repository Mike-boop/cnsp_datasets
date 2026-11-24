"""TRF from the authors' onset annotations (TextGrid on the trial axis) to the envelope of the trial's audio.

usage: annot_trf.py <dataset> <download dir> <out png> <condition:subject:session[:trial]> ...

Per trial and 120 s window: ridge TRF (lags -200..+400 ms, 200 Hz) from a phoneme-onset (and word-onset) impulse
train to the audio's Hilbert envelope (< 50 Hz). Correct timing: the same kernel, peaking at the same small
positive latency, in every window. Prints the peak latency per window; plots all windows' kernels.
"""
import re, sys, warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, hilbert, resample_poly, sosfiltfilt
warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/gu08wuvu/cnsp_datasets")
from cnsp_datasets.standardise.format_dataset import get_adaptor_class

FS, WIN = 200, 120
LAGS = np.arange(-40, 81)


def tier(tg, name):
    part = re.split(r'name = "', tg)
    body = next(p for p in part if p.startswith(name + '"'))
    return [float(a) for a, b, t in re.findall(r'xmin = ([\d.]+)\s+xmax = ([\d.]+)\s+text = "(.*?)"', body)
            if t.strip() and t.strip().lower() not in ("sp", "sil", "")]


def trf(x, y, lam=1.0):
    X = np.stack([np.roll(x, L) for L in LAGS], 1)
    X[:LAGS.max()] = 0
    X[len(X) + LAGS.min():] = 0
    A = X.T @ X
    return np.linalg.solve(A + lam * np.trace(A) / len(A) * np.eye(len(A)), X.T @ y)


name, ddir, out, want = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
recs = [r for r in get_adaptor_class(name)(download_dir=ddir).parse()
        if f"{r.condition}:{r.subject}:{r.session}" in want or f"{r.condition}:{r.subject}:{r.session}:{r.trial}" in want]
fig, axes = plt.subplots(len(recs), 2, figsize=(11, 2.4 * len(recs)), squeeze=False)
sos = butter(4, 50, fs=FS * 10, output="sos")
for row, r in enumerate(recs):
    st = {s.feature_name: s for s in r.stimulus}
    if "audio" not in st:
        continue
    a = st["audio"].data_fn()
    x = a["data"][0].astype(np.float32)
    env = np.abs(hilbert(resample_poly(x, FS * 10, a["fs"])))
    env = resample_poly(sosfiltfilt(sos, env), 1, 10)
    tg = st["textgrid"].data_fn()
    lab = f"{r.condition} sub {r.subject} ses {r.session} trial {r.trial}"
    for col, tname in enumerate(("phones", "words")):
        on = np.zeros(len(env))
        for t in tier(tg, tname):
            if t * FS < len(env):
                on[int(round(t * FS))] = 1
        peaks = []
        for w0 in range(0, len(env) - WIN * FS + 1, WIN * FS):
            e = env[w0:w0 + WIN * FS]
            o = on[w0:w0 + WIN * FS]
            if o.sum() < 20:
                continue
            k = trf(o - o.mean(), (e - e.mean()) / e.std())
            peaks.append(LAGS[np.argmax(k)] * 1000 / FS)
            axes[row, col].plot(LAGS * 1000 / FS, k, lw=0.8, alpha=0.6)
        axes[row, col].set_title(f"{lab}: {tname} -> envelope", fontsize=8)
        axes[row, col].axvline(0, c="k", lw=0.5)
        print(f"{lab} {tname}: {len(peaks)} windows, peak latency median {np.median(peaks):.0f} ms, "
              f"range {min(peaks):.0f}..{max(peaks):.0f} ms", flush=True)
axes[-1, 0].set_xlabel("lag (ms)")
axes[-1, 1].set_xlabel("lag (ms)")
fig.tight_layout()
fig.savefig(out, dpi=90)
