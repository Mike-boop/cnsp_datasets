"""
Per-segment alignment for the LibriBrain Sherlock sessions whose wav does not follow the events' time axis linearly
(Sherlock3, and the sessions whose linear map breaks part-way; notes.md section 5b). Writes segmap.csv next to this
file, which the adaptor prefers over wavmap.csv: for every playback segment (adaptor.segments), the wav time where
it starts.

1. Lag curve: the events' 100 Hz word mask (timechapter axis) against the wav's 100 Hz log-energy envelope in 30 s
   windows every 10 s; each window is searched within +-1.5 s of the previous good lag (+-30 s for the first; good:
   r >= 0.3). wav_time = timechapter + L(timechapter).
2. Per segment: L interpolated from the good windows at the segment start, refined by the best lag within
   +-150 ms in a 10 s window centred on the segment (parabolic peak); a refinement more than 150 ms off a 5-segment
   running median is replaced by that median. Segments in stretches without good windows (> 30 s from one) get no
   audio. Sessions whose median local r is below 0.5 are left out.

    python -m cnsp_datasets.datasets.libribrain100.alignment.segalign <download dir>
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np
import pandas as pd

from cnsp_datasets.datasets.libribrain100.adaptor import SEGMAP_CSV as OUT, read_wavmap, segments
from cnsp_datasets.datasets.libribrain100.alignment.wavmap import BOOKS, FS, envelope, word_mask
WIN, HOP, SEARCH, R_MIN = 30, 10, 1.5, 0.3
SESSION_R_MIN = 0.5  # sessions whose median local r is lower are left out (wrong or missing wav)
LOCAL, FINE = 10, 0.15


def _r(env: np.ndarray, w: np.ndarray, start: int) -> float:
    if start < 0 or start + len(w) > len(env):
        return -1.0
    e = env[start:start + len(w)]
    return float(np.mean((e - e.mean()) * (w - w.mean())) / (e.std() * w.std() + 1e-9))


def lag_curve(m: np.ndarray, env: np.ndarray, first: tuple = (-30, 30)) -> pd.DataFrame:
    """Windowed lags (s) of env relative to m, tracked from window to window."""
    rows, prev = [], None
    for a in range(0, len(m) - WIN * FS, HOP * FS):
        w = m[a:a + WIN * FS]
        lo, hi = first if prev is None else (prev - SEARCH, prev + SEARCH)
        r, L = max((_r(env, w, a + L), L) for L in range(int(lo * FS), int(hi * FS) + 1))
        rows.append(dict(t=a / FS + WIN / 2, lag=L / FS, r=r))
        if r >= R_MIN:
            prev = L / FS
    return pd.DataFrame(rows)


def refine(m: np.ndarray, env: np.ndarray, t: float, lag: float) -> tuple[float, float]:
    """Best lag within +-FINE s of `lag` for a LOCAL s window centred on t (parabolic peak), and its r."""
    a = max(int((t - LOCAL / 2) * FS), 0)
    w = m[a:a + LOCAL * FS]
    if w.std() == 0:
        return lag, 0.0
    lags = np.arange(int((lag - FINE) * FS), int((lag + FINE) * FS) + 1)
    c = np.array([_r(env, w, a + L) for L in lags])
    k = int(np.argmax(c))
    d = 0.0
    if 0 < k < len(c) - 1 and c[k - 1] > -1 and c[k + 1] > -1:
        d = 0.5 * (c[k - 1] - c[k + 1]) / (c[k - 1] - 2 * c[k] + c[k + 1])
    return (lags[k] + d) / FS, float(c[k])


def align_session(events: pd.DataFrame, wav: str) -> pd.DataFrame:
    m, env = word_mask(events), envelope(wav)
    curve = lag_curve(m, env)
    good = curve[curve.r >= R_MIN]
    segs = segments(events, "timechapter")
    rows = []
    for s in segs.itertuples():
        near = (good.t - s.src_start).abs().min() if len(good) else np.inf
        if near > WIN:
            rows.append(dict(src_start=s.src_start, wav_start_s=np.nan, lag_s=np.nan, r_local=np.nan))
            continue
        lag0 = float(np.interp(s.src_start, good.t, good.lag))
        lag, r = refine(m, env, (s.src_start + s.src_end) / 2, lag0)
        rows.append(dict(src_start=s.src_start, lag_curve_s=lag0, lag_s=lag, r_local=r))
    d = pd.DataFrame(rows)
    med = d.lag_s.rolling(5, center=True, min_periods=1).median()
    off = (d.lag_s - med).abs() > FINE
    d.loc[off, "lag_s"] = med[off]
    d["replaced"] = off
    d["wav_start_s"] = d.src_start + d.lag_s
    return d


def main(download_dir: str) -> None:
    linear = read_wavmap()
    rows = []
    for book in BOOKS:
        task = book.split("/")[1]
        wavs = sorted(glob.glob(f"{download_dir}/{book}/stimuli/audio/*.wav"))
        for f in sorted(glob.glob(f"{download_dir}/{book}/derivatives/events/sub-0_*.tsv")):
            ses = int(re.search(r"ses-(\d+)", f)[1])
            if (task, ses) in linear.index:
                row = linear.loc[(task, ses)]
                if row.valid_until_s >= row.source_end_s:
                    continue  # the linear map holds throughout
                wav = row.wav
            else:
                wav = next((w for w in wavs if re.search(rf"_{ses:02d}_doyle", w)), None)  # same-numbered story
                if wav is None:
                    continue
                wav = os.path.basename(wav)
            d = align_session(pd.read_csv(f, sep="\t"), f"{download_dir}/{book}/stimuli/audio/{wav}")
            if not d.r_local.median() >= SESSION_R_MIN:
                print(task, ses, wav, f"left out: median local r {d.r_local.median():.2f}", flush=True)
                continue
            d.insert(0, "wav", wav)
            d.insert(0, "session", ses)
            d.insert(0, "task", task)
            rows.append(d)
            print(task, ses, wav, f"{d.wav_start_s.notna().mean():.0%} of segments aligned, "
                  f"median local r {d.r_local.median():.2f}", flush=True)
    pd.concat(rows).to_csv(OUT, index=False, float_format="%.4f")
    print(f"wrote {OUT}")



if __name__ == "__main__":
    main(sys.argv[1])
