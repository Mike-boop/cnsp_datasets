"""
Drift of the Jehn 2025 EEG relative to the stimuli, from the two aux channels (rows 32-33: recordings of the left and
right loudspeaker signals on the EEG amplifier). Writes drift.csv next to this file, which the adaptor reads.

Per trial: the aux row carrying the attended stream is cross-correlated with the stimulus (both 2-200 Hz at 1 kHz)
in 10 s windows every 5 s; a Theil-Sen line through the window lags (sub-sample peaks, |lag| <= 30 ms, windows with
r >= 0.1) gives the onset (intercept) and drift (slope, ppm; > 0: the EEG clock runs fast). Per subject, the median
over trials with at least 10 valid windows is used for correction.

    python -m cnsp_datasets.datasets.jehn2025_base.drift <dir with jehn2025_nh, jehn2025_hi, jehn2025_ci downloads>
"""
from __future__ import annotations

import os
import sys

import h5py
import numpy as np
import pandas as pd
from scipy.signal import butter, correlate, resample_poly, sosfiltfilt
from scipy.stats import theilslopes

OUT = os.path.join(os.path.dirname(__file__), "drift.csv")
GROUPS = {"nh": "nh_dataset_1kHz.hdf5", "hi": "hi_dataset_1kHz.hdf5", "ci": "ci_dataset_1kHz.hdf5"}
WIN, HOP, MAX_LAG, MIN_R, MIN_WINDOWS = 10_000, 5_000, 30, 0.1, 10
_SOS = butter(4, [2, 200], "bp", fs=1000, output="sos")


def _lag(y: np.ndarray, s: np.ndarray) -> tuple[float, float]:
    """Sub-sample lag (samples) of s in y within +-MAX_LAG, and the normalised peak correlation."""
    c = np.abs(correlate(y, s, "full")[len(s) - 1 - MAX_LAG:len(s) + MAX_LAG])
    k = int(np.argmax(c))
    d = 0.5 * (c[k - 1] - c[k + 1]) / (c[k - 1] - 2 * c[k] + c[k + 1]) if 0 < k < len(c) - 1 else 0.0
    return k - MAX_LAG + d, c[k] / np.sqrt((y ** 2).sum() * (s ** 2).sum() + 1e-30)


def trial_drift(aux: np.ndarray, stim: np.ndarray) -> dict:
    """Onset (ms) and drift (ppm) of the stimulus on one aux channel (both filtered, 1 kHz)."""
    n = min(len(aux), len(stim))
    t, lags = [], []
    for a in range(0, n - WIN + 1, HOP):
        lag, r = _lag(aux[a:a + WIN], stim[a:a + WIN])
        if r >= MIN_R:
            t.append((a + WIN / 2) / 1000)
            lags.append(lag)
    if len(t) < 2:
        return dict(n_windows=len(t), onset_ms=np.nan, drift_ppm=np.nan)
    slope, intercept, _, _ = theilslopes(lags, t)
    return dict(n_windows=len(t), onset_ms=intercept, drift_ppm=1e3 * slope)


def main(root: str) -> None:
    rows = []
    for group, fname in GROUPS.items():
        with h5py.File(os.path.join(root, f"jehn2025_{group}", "download", fname), "r") as f:
            stims = {}
            for sub in f["eeg"]:
                for trial in f["eeg"][sub]:
                    if trial == "taken_out_indices":
                        continue
                    node = f["eeg"][sub][trial]
                    code = str(node.attrs["stimulus"])
                    if code not in stims:
                        stims[code] = sosfiltfilt(_SOS, resample_poly(f[f"stimulus_files/{code}/attended_wav"][:], 1, 48))
                    aux = [sosfiltfilt(_SOS, x) for x in node[31:33]]
                    n = min(len(aux[0]), len(stims[code]))
                    row = int(np.argmax([_lag(a[:n], stims[code][:n])[1] for a in aux]))  # full-trial best aux row
                    rows.append(dict(group=group, subject=sub, trial=int(trial), code=code, aux_row=row + 32,
                                     **trial_drift(aux[row], stims[code])))
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, float_format="%.3f")
    ok = d[d.n_windows >= MIN_WINDOWS]
    print(f"wrote {OUT}: {len(d)} trials, {len(ok)} with >= {MIN_WINDOWS} windows")
    print(ok.groupby("group")[["drift_ppm", "onset_ms"]].describe().round(2).T.to_string())


def subject_drift(table: str = OUT) -> dict[str, float]:
    """Median drift (as a fraction, not ppm) per subject code over trials with enough valid windows."""
    d = pd.read_csv(table, dtype={"subject": str})
    d = d[d.n_windows >= MIN_WINDOWS]
    return (d.groupby("subject").drift_ppm.median() * 1e-6).to_dict()


if __name__ == "__main__":
    main(sys.argv[1])
