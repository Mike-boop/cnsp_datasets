"""
Bad channels per participant (notes.md section 5): the authors' list (metadata/bad_channels.csv), plus channels at
the ADC clip in more than CLIP_FRAC of the samples, plus flat channels whose median 1-40 Hz SD over the
participant's trials is below FLAT_RATIO x the participant's median over channels. No upper variance threshold:
the only high-variance channels (Fp in S10/S16) carry blinks. Writes bads.json next to this file, which the adaptor
reads.

    python -m cnsp_datasets.datasets.hassan2026.bads <hassan2026 download dir>
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

BADS_JSON = os.path.join(os.path.dirname(__file__), "bads.json")
FS = 500
CLIP = 0.0838  # just inside the ADC clip at +-2^23 x 1e-8 V (notes 5)
CLIP_FRAC, FLAT_RATIO = 0.1, 0.1


def main(download_dir: str) -> None:
    root = os.path.join(download_dir, "maestro-eeg-dataset")
    with open(os.path.join(root, "metadata", "eeg_channels.json")) as f:
        names = json.load(f)["channels"]
    authors = pd.read_csv(os.path.join(root, "metadata", "bad_channels.csv")).fillna("")
    sos = butter(4, [1, 40], "bandpass", fs=FS, output="sos")
    out = {}
    for r in authors.itertuples():
        clip_frac, sd = [], []
        for path in sorted(glob.glob(os.path.join(root, "data", "eeg", f"subject={r.subject_id}", "*.parquet"))):
            x = pd.read_parquet(path)[[f"ch_{c}" for c in names]].to_numpy(float)
            clip_frac.append((np.abs(x) >= CLIP).mean(0))
            sd.append(sosfiltfilt(sos, x, axis=0).std(0))
        clip_frac, sd_med = np.mean(clip_frac, 0), np.median(sd, 0)
        listed = {c for c in r.bad_channels.split(";") if c}
        extra = {c for c, f, s in zip(names, clip_frac, sd_med)
                 if f > CLIP_FRAC or s < FLAT_RATIO * np.median(sd_med)} - listed
        out[r.subject_id] = [c for c in names if c in listed | extra]
        print(r.subject_id, "authors:", sorted(listed), "extra:", sorted(extra))
    with open(BADS_JSON, "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
