"""
Which wav each LibriBrain Sherlock session played, and where: wav_time = k * timechapter + c, valid up to
valid_until_s (notes.md section 5). Writes wavmap.csv next to this file, which the adaptor reads.

For every candidate wav of the book, the 100 Hz log-energy envelope of the wav, read on the timechapter axis, is
correlated with the events' word mask (first 300 s, offsets up to +-30 s). For the best wav, 60 s windows every 30 s
give lags; the map is valid up to the first of three consecutive windows whose lag is > 50 ms off (or r < 0.3), and
a Theil-Sen line through the valid windows gives k and c. Sessions without a match, or with a scale k != 1 (a
spurious match), are left out.

    python -m cnsp_datasets.datasets.libribrain100.alignment.wavmap <download dir>
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.stats import theilslopes

from cnsp_datasets.datasets.libribrain100.adaptor import WAVMAP_CSV as OUT
FS = 100
SCALES = (1.0,)
BOOKS = [f"LibriBrain/Sherlock{i}" for i in range(1, 8)] + ["LibriBrain2/Sherlock9"]


def envelope(path: str) -> np.ndarray:
    """100 Hz log energy. Frame edges are exact multiples of fs / FS (an integer hop of fs // FS would put 22.05 kHz
    files on a 100.227 Hz grid, i.e. stretch them by 0.227%)."""
    fs, x = wavfile.read(path, mmap=True)
    x = np.asarray(x, dtype=np.float32)
    x = x[:, 0] if x.ndim == 2 else x
    edges = np.round(np.arange(int(len(x) * FS / fs) + 1) * fs / FS).astype(np.int64)
    e = np.log(np.add.reduceat(x[:edges[-1]] ** 2, edges[:-1]) / np.diff(edges) + 1e-3)
    return (e - e.mean()) / e.std()


def word_mask(events: pd.DataFrame) -> np.ndarray:
    m = np.zeros(int(((events.timechapter + events.duration).max() + 1) * FS))
    w = events[events.kind == "word"]
    for t, d in zip(w.timechapter, w.duration):
        m[int(t * FS):int((t + d) * FS)] = 1
    return (m - m.mean()) / (m.std() + 1e-9)


def on_source(env: np.ndarray, k: float, c: float, n: int) -> np.ndarray:
    """Envelope at wav time k * t + c for source times t = 0, 1/FS, ... (n samples)."""
    return np.interp((k * np.arange(n) / FS + c) * FS, np.arange(len(env)), env, left=0, right=0)


def best_lag(a: np.ndarray, b: np.ndarray, maxlag: int):
    """Lag L (s) and r such that a(t + L) best matches b(t), |L| <= maxlag samples."""
    n = min(len(a), len(b))
    c = np.correlate(np.pad(a[:n], maxlag), b[:n], "valid") / n
    i = int(np.argmax(c))
    return (i - maxlag) / FS, c[i]


def fit_session(m: np.ndarray, env: dict) -> dict | None:
    n, head = len(m), min(len(m), 300 * FS)
    (lag0, r0), name, k0 = max(((best_lag(on_source(e, k0, 0, head + 30 * FS), m[:head], 30 * FS), name, k0)
                                for name, e in env.items() for k0 in SCALES), key=lambda x: x[0][1])
    es = on_source(env[name], k0, k0 * lag0, n)
    win = [(a / FS + 30, *best_lag(es[a:a + 60 * FS], m[a:a + 60 * FS], 2 * FS))
           for a in range(0, n - 60 * FS, 30 * FS)]
    tt, ll, rr = (np.array(x) for x in zip(*win))
    good = (rr >= 0.3) & (np.abs(ll - np.median(ll[:5])) < 0.05)
    bad_run = np.convolve(~good, np.ones(3), "valid") == 3
    stop = int(np.argmax(bad_run)) if bad_run.any() else len(tt)
    ok = good[:stop]
    if ok.sum() < 3:
        return None
    slope, icpt = theilslopes(ll[:stop][ok], tt[:stop][ok])[:2]
    if abs(k0 * (1 + slope) - 1) > 1e-4:
        return None  # a spurious match: the audio plays at its own rate (k = 1) wherever it matches
    resid = ll[:stop][ok] - (slope * tt[:stop][ok] + icpt)
    return dict(wav=name, k=k0 * (1 + slope), c_s=k0 * (lag0 + icpt), r=r0, resid_sd_ms=1e3 * resid.std(),
                valid_until_s=float(tt[stop] - 30) if stop < len(tt) else n / FS, source_end_s=n / FS)


def main(download_dir: str) -> None:
    rows = []
    for book in BOOKS:
        env = {os.path.basename(w): envelope(w) for w in sorted(glob.glob(f"{download_dir}/{book}/stimuli/audio/*.wav"))}
        for f in sorted(glob.glob(f"{download_dir}/{book}/derivatives/events/sub-0_*.tsv")):
            fit = fit_session(word_mask(pd.read_csv(f, sep="\t")), env)
            if fit:
                rows.append(dict(task=book.split("/")[1], session=int(re.search(r"ses-(\d+)", f)[1]), **fit))
    d = pd.DataFrame(rows).sort_values(["task", "session"])
    d.to_csv(OUT, index=False, float_format="%.8g")
    print(f"wrote {OUT}: {len(d)} sessions")



if __name__ == "__main__":
    main(sys.argv[1])
