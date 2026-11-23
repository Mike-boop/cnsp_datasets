"""
Playback-request time t0 of every PassiveListening chapter, from the ROWS/ROWE triggers, and a check of the t0
column of timing.csv (notes.md sections 6 and 6b).

The listening script replayed each reader's EEG line timeline (events_data.json in the audio repo) as ROWS/ROWE
triggers from the moment sd.play() was requested. Per run file and json chapter: offset = mode of all (EEG ROWS - json
ROWS) differences (5 ms bins); json events with an EEG event of the same type within 30 ms are inliers; the chapter is
in the file if >= 50% of its ROWS are found. EEG_t = t0 + (1 + d) a is fitted on the inliers (two refits, tolerance
max(15 ms, 4 SD)). CH markers are not used (missing or renumbered in many runs). Per listener and chapter the
best-covered match (>= 80% of the ROWS) in the shortest file is kept; prefaces (chapter 0) and json chapters with < 10
rows (ReadingAloud-only) are dropped.

The sound latency after t0 (latency_s, latency_optionB_s, listener_median_s in timing.csv) is estimated from the EEG
(decoder and DNN scans; notes.md 6b-6c) and is not recomputed here.

    python -m cnsp_datasets.datasets.chen2026.timing <chen2026 download dir> [audio dir]
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd

TIMING_CSV = os.path.join(os.path.dirname(__file__), "timing.csv")
TOL, MIN_FRAC, KEEP_FRAC, MIN_ROWS = 0.030, 0.5, 0.8, 10


def reader_of(sub: str) -> str:
    """Listeners 01-04 heard reader f1, 05-08 reader m1 (notes.md section 3)."""
    return "f1" if int(sub) <= 4 else "m1"


def json_chapters(audio_dir: str, story: str, reader: str) -> list[tuple[np.ndarray, np.ndarray]]:
    """Per chapter: ROWS and ROWE times (s) relative to the chapter's audio sample 0 (250 Hz reader EEG indices)."""
    with open(os.path.join(audio_dir, f"{story}_{reader}", "events_data.json")) as f:
        e = json.load(f)
    begin, rows, rowe = (np.array(e[k]) for k in ("begn_nonzero_indices", "ROWS_times", "ROWE_times"))
    out = []
    for k, b in enumerate(begin):
        hi = begin[k + 1] if k + 1 < len(begin) else np.inf
        out.append(((rows[(rows >= b) & (rows < hi)] - b) / 250, (rowe[(rowe >= b) & (rowe < hi)] - b) / 250))
    return out


def _nearest(x: np.ndarray, ref: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Distance from each ref value to the nearest x (sorted), and its index."""
    if len(x) == 0:
        return np.full(len(ref), np.inf), np.zeros(len(ref), int)
    if len(x) == 1:
        return np.abs(x[0] - ref), np.zeros(len(ref), int)
    i = np.clip(np.searchsorted(x, ref), 1, len(x) - 1)
    i = np.where(np.abs(x[i - 1] - ref) < np.abs(x[i] - ref), i - 1, i)
    return np.abs(x[i] - ref), i


def fit_chapter(rows: np.ndarray, rowe: np.ndarray, a_rows: np.ndarray, a_rowe: np.ndarray) -> dict | None:
    """t0, drift and residuals of one json chapter in one file's ROWS/ROWE times (s), or None if not there."""
    diff = (rows[:, None] - a_rows[None, :]).ravel()
    if len(diff) == 0:
        return None
    hist, edges = np.histogram(diff, bins=np.arange(diff.min(), diff.max() + 0.01, 0.005))
    c = np.array([edges[int(np.argmax(hist))] + 0.0025, 1.0])
    if (_nearest(rows, c[0] + a_rows)[0] < TOL).mean() < MIN_FRAC:
        return None
    tol = TOL
    for _ in range(3):
        d_s, i_s = _nearest(rows, c[0] + c[1] * a_rows)
        d_e, i_e = _nearest(rowe, c[0] + c[1] * a_rowe)
        m_s, m_e = d_s < tol, d_e < tol
        a = np.r_[a_rows[m_s], a_rowe[m_e]]
        t = np.r_[rows[i_s[m_s]], rowe[i_e[m_e]]]
        c, *_ = np.linalg.lstsq(np.c_[np.ones_like(a), a], t, rcond=None)
        res = t - np.c_[np.ones_like(a), a] @ c
        tol = max(0.015, 4 * res.std())
    return dict(t0_s=c[0], drift_ppm=(c[1] - 1) * 1e6, res_sd_ms=res.std() * 1e3, rows_found=int(m_s.sum()),
                rows_json=len(a_rows), n_events=int(m_s.sum() + m_e.sum()))


def t0_table(download_dir: str, audio_dir: str) -> pd.DataFrame:
    """One row per listener and chapter: the file and t0 (s from the file's first sample) of the best match."""
    found = []
    for events in sorted(glob.glob(os.path.join(download_dir, "PassiveListening", "sub-*", "ses-*", "eeg",
                                                "*_task-lis_run-*_events.tsv"))):
        name = os.path.basename(events)
        sub, story = re.match(r"sub-(\d+)_ses-(\w+?)_", name).groups()
        ev = pd.read_csv(events, sep="\t")
        rows = np.sort(ev.onset[ev.trial_type == "ROWS"].to_numpy(float))
        rowe = np.sort(ev.onset[ev.trial_type == "ROWE"].to_numpy(float))
        with open(events.replace("_events.tsv", "_eeg.json")) as f:
            duration = json.load(f)["RecordingDuration"]
        for k, (a_rows, a_rowe) in enumerate(json_chapters(audio_dir, story, reader_of(sub))):
            if k == 0 or len(a_rows) < MIN_ROWS:
                continue
            fit = fit_chapter(rows, rowe, a_rows, a_rowe)
            if fit and fit["rows_found"] >= KEEP_FRAC * fit["rows_json"]:
                found.append(dict(sub=sub, story=story, chapter=k, file=name.replace("_events.tsv", "_eeg.vhdr"),
                                  file_s=duration, **fit))
    if not found:
        raise ValueError(f"no PassiveListening events files under {download_dir}")
    df = pd.DataFrame(found)
    df["frac"] = df.rows_found / df.rows_json
    df = df.sort_values(["frac", "file_s"], ascending=[False, True]).drop_duplicates(["sub", "story", "chapter"])
    return df.sort_values(["sub", "story", "chapter"]).reset_index(drop=True)


def main(download_dir: str, audio_dir: str | None = None) -> None:
    """Recompute the trigger fit and compare it with timing.csv; exit 1 on any mismatch."""
    audio_dir = audio_dir or os.path.join(download_dir, "ChineseEEG-2_audio")
    new = t0_table(download_dir, audio_dir)
    old = pd.read_csv(TIMING_CSV, dtype={"sub": str})
    m = old.merge(new, on=["sub", "story", "chapter"], how="outer", suffixes=("", "_new"), indicator=True)
    both = m[m._merge == "both"]
    checks = {
        "chapters only in one table": (m._merge != "both").sum() == 0,
        "same file": (both.file == both.file_new).all(),
        "t0 within 0.01 ms": ((both.t0_s - both.t0_s_new).abs() < 1e-5).all(),
        "same ROWS found": (both.trig_rows_found
                            == both.rows_found.astype(str) + "/" + both.rows_json.astype(str)).all(),
        "same event count": (both.trig_n_events == both.n_events).all(),
        "residual SD within 0.01 ms": ((both.trig_res_sd_ms - both.res_sd_ms).abs() < 0.01).all(),
    }
    for name, ok in checks.items():
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
    long = new.file_s > 120  # the trigger slope says nothing about sound-card drift (same clock; notes 6)
    print(f"trigger slope, chapters > 2 min: max |d| {new.drift_ppm[long].abs().max():.1f} ppm")
    if not all(checks.values()):
        sys.exit(1)


if __name__ == "__main__":
    main(*sys.argv[1:])
