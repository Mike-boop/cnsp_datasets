"""
Sound onsets on the EEG clock (notes.md section 6). Every onset is E-Prime's SoundOut1.OnsetTime plus a per-run
offset c (E-Prime clock -> amplifier samples, the mapping Net Station applies to the ECI events):
- runs with valid ECI TBEG markers (sub-10..30, sub-09): c = median(marker - OnsetTime);
- runs whose TBEG markers carry timestamp 0 (sub-01..08; E-Prime bug): c from the TBEG arrival times in the Net
  Station log, arrival = (1 + eps) * (OnsetTime + c) + L, with eps (Mac log clock vs marker clock) and L (arrival
  latency) per run calibrated on sub-10..30 (CALIBRATION, from `python -m cnsp_datasets.datasets.peng2026.onsets
  <dir>`, which also prints the leave-one-subject-out error).
"""
from __future__ import annotations

import glob
import re
import sys

import mne
import numpy as np
import pandas as pd

# run -> (eps, L s): medians over sub-10..30 of per-subject fits of arrival on marker (notes 6c)
CALIBRATION = {1: (64.8e-6, -0.0183), 2: (65.8e-6, -0.0266), 3: (32.2e-6, -0.0047)}
MARKER_TOL_S = 0.005  # markers within 5 ms of the run's median offset count as valid (spread ~1 ms)
_TS = re.compile(r"^(\d\d):(\d\d):(\d\d)\.(\d{3})\.(\d{3}):")


def _seconds(line: str) -> float:
    h, m, s, ms, us = map(int, _TS.match(line).groups())
    return h * 3600 + m * 60 + s + ms / 1e3 + us / 1e6


def log_arrivals(mff: str) -> np.ndarray:
    """Net Station log times (s since EEG START, Mac clock) at which TBEG events arrived from E-Prime."""
    logs = sorted(glob.glob(f"{glob.escape(mff)}/log_*.txt"))
    if not logs:
        raise FileNotFoundError(f"{mff}: no Net Station log_*.txt")
    with open(logs[0], encoding="utf-8", errors="ignore") as f:
        lines = f.read().splitlines()
    start = next(_seconds(ln) for ln in lines if "EEG START RECORDING" in ln)
    return np.array([_seconds(ln) - start for ln in lines
                     if "PLTECIEvents:eventData" in ln and ln.split(": ")[-1].startswith("TBEG")])


def eci_offset(markers: np.ndarray, t_ep: np.ndarray) -> float | None:
    """c from the ECI TBEG markers (s), or None if fewer than 3 are consistent with the E-Prime onsets."""
    d = (np.unique(markers)[:, None] - t_ep[None, :]).ravel()  # collapsed markers (all one time) count once
    if d.size == 0:
        return None
    mode = d[np.argmax([np.sum(np.abs(d - x) < MARKER_TOL_S) for x in d])]  # the offset most pairs share
    ok = np.abs(d - mode) < MARKER_TOL_S
    return float(np.median(d[ok])) if ok.sum() >= 3 else None


def match_arrivals(arrivals: np.ndarray, t_ep: np.ndarray) -> np.ndarray:
    """Arrival per E-Prime onset (NaN if none within 0.5 s of the run's dominant offset; the authors' histogram)."""
    d = (arrivals[:, None] - t_ep[None, :]).ravel()
    h, e = np.histogram(d, np.arange(d.min(), d.max() + 0.1, 0.1))
    off = e[np.argmax(h)] + 0.05
    nearest = arrivals[[np.argmin(np.abs(arrivals - t - off)) for t in t_ep]]
    return np.where(np.abs(nearest - t_ep - off) < 0.5, nearest, np.nan)


def log_offset(arrivals: np.ndarray, t_ep: np.ndarray, run: int, calibration: dict = CALIBRATION) -> float:
    """c from the log arrival times (s)."""
    eps, lat = calibration[run]
    return float(np.nanmedian((match_arrivals(arrivals, t_ep) - lat) / (1 + eps) - t_ep))


def tbeg_markers(raw: mne.io.BaseRaw) -> np.ndarray:
    """ECI TBEG marker times (s since the first sample)."""
    return raw.annotations.onset[raw.annotations.description == "TBEG"]


def _calibrate(root: str) -> None:
    """Print CALIBRATION from sub-10..30 and the leave-one-subject-out error of log_offset against the markers."""
    rows = []
    for mff in sorted(glob.glob(f"{root}/sub-*/eeg/*_eeg.mff")):
        sub, run = int(mff.split("sub-")[1][:2]), int(mff.split("_run-")[1][:2])
        if sub < 10:
            continue
        ev = pd.read_csv(mff.replace("_eeg.mff", "_events.tsv"), sep="\t")
        t_ep = ev["SoundOut1.OnsetTime"].to_numpy() / 1000
        c = eci_offset(tbeg_markers(mne.io.read_raw_egi(mff, verbose="ERROR")), t_ep)
        arrivals = log_arrivals(mff)
        arr = match_arrivals(arrivals, t_ep)
        ok = ~np.isnan(arr)
        p = np.polyfit(t_ep[ok] + c, arr[ok], 1)
        rows.append(dict(sub=sub, run=run, eps=p[0] - 1, lat=p[1], c=c, t_ep=t_ep, arr=arrivals))
    df = pd.DataFrame(rows)
    print({r: (round(g.eps.median() * 1e6, 1), round(g.lat.median(), 4)) for r, g in df.groupby("run")})
    err = []
    for s in df["sub"].unique():
        cal = {r: (g.eps.median(), g.lat.median()) for r, g in df[df["sub"] != s].groupby("run")}
        err += [(log_offset(x.arr, x.t_ep, x.run, cal) - x.c) * 1e3 for x in df[df["sub"] == s].itertuples()]
    err = np.array(err)
    print("runs with |e| > 30 ms:",
          [(int(x.sub), int(x.run), round(e)) for x, e in zip(df.itertuples(), err) if abs(e) > 30])
    print(f"LOSO run-offset error (ms): mean {err.mean():.1f}, SD {err.std():.1f}, max |e| {np.abs(err).max():.1f}")


if __name__ == "__main__":
    _calibrate(sys.argv[1])
