"""
Audio onset and sound-card vs MEG clock drift of every audiobook run, from the audio copy MISC001. Writes drift.csv
next to this file, which the adaptor reads (notes.md section 6).

Per run: the 1 s triggers (events.tsv, sent on the sound-card clock) give the trigger clock (Theil-Sen slope of the
trigger samples, `trig_ppm`). The wav (1 kHz, 2-200 Hz) is put on that clock and jehn2025_base.alignment.drift.trial_drift
cross-correlates it with MISC001 from the first trigger on (10 s windows every 5 s, Theil-Sen): intercept =
`onset_ms` (audio copy after the first trigger, MEG samples), slope = residual drift. `drift_ppm` = trig_ppm +
residual: > 0, the MEG clock runs fast relative to the audio clock.

    python -m cnsp_datasets.datasets.habersetzer2025.alignment.drift <download dir>
"""
from __future__ import annotations

import glob
import os
import sys

import mne
import numpy as np
import pandas as pd
from scipy.interpolate import make_interp_spline
from scipy.io import wavfile
from scipy.signal import resample_poly, sosfiltfilt
from scipy.stats import theilslopes

from cnsp_datasets.datasets.habersetzer2025.adaptor import DRIFT_CSV as OUT, audiobook_events
from cnsp_datasets.datasets.jehn2025_base.alignment.drift import trial_drift
from cnsp_datasets.datasets.jehn2025_base.alignment.xcorr import SOS as _SOS


def run_drift(fif: str, download_dir: str) -> dict:
    ev = audiobook_events(fif)
    trig = ev["sample"].to_numpy(float)
    slope = theilslopes(trig, np.arange(len(trig)))[0]  # MEG samples per audio second
    fs, x = wavfile.read(os.path.join(download_dir, "stimuli", ev.stim_file.iloc[0]))
    wav = sosfiltfilt(_SOS, resample_poly(x.astype(float), 1000, fs))
    on_trig_clock = make_interp_spline(np.arange(len(wav)), wav, k=3)(
        np.arange(int(len(wav) * slope / 1000)) * 1000 / slope)
    raw = mne.io.read_raw_fif(fif, preload=False, verbose="ERROR")
    misc = sosfiltfilt(_SOS, raw.get_data(picks="MISC001")[0])
    fit = trial_drift(misc[int(trig[0]):], on_trig_clock)
    trig_ppm = (slope / 1000 - 1) * 1e6
    return dict(file=os.path.basename(fif), stim_file=ev.stim_file.iloc[0], n_trig=len(trig),
                first_trig_sample=int(trig[0]), trig_ppm=trig_ppm, n_windows=fit["n_windows"],
                onset_ms=fit["onset_ms"], resid_ppm=fit["drift_ppm"], drift_ppm=trig_ppm + fit["drift_ppm"])


def main(download_dir: str) -> None:
    rows = []
    for fif in sorted(glob.glob(os.path.join(download_dir, "sub-*", "meg", "sub-*_task-audiobook*_meg.fif"))):
        rows.append(run_drift(fif, download_dir))
        print(rows[-1], flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, float_format="%.5f")
    print(f"wrote {OUT}: {len(d)} runs")
    print(d[["onset_ms", "drift_ppm", "resid_ppm"]].describe().round(3).to_string())


if __name__ == "__main__":
    main(sys.argv[1])
