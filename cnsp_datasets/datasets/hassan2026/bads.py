"""
Bad channels per participant (notes.md section 5): the authors' list (metadata/bad_channels.csv), plus channels at
the ADC clip (|x| >= CLIP) in more than CLIP_FRAC of the samples, plus flat channels whose median 1-40 Hz SD over
the participant's trials is below FLAT_RATIO x the participant's median over channels. Writes bads.json next to
this file, which the adaptor reads.

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
CLIP, CLIP_FRAC, FLAT_RATIO = 0.0838, 0.1, 0.1


def authors_bads(root: str) -> dict[str, list[str]]:
    """metadata/bad_channels.csv as {subject: [channels]}."""
    table = pd.read_csv(os.path.join(root, "metadata", "bad_channels.csv")).fillna("")
    return {r.subject_id: [c for c in r.bad_channels.split(";") if c] for r in table.itertuples()}


def main(download_dir: str) -> None:
    root = os.path.join(download_dir, "maestro-eeg-dataset")
    sos = butter(4, [1, 40], "bandpass", fs=500, output="sos")
    out = {}
    for subject, bads in authors_bads(root).items():
        clip, sd = [], []
        for path in sorted(glob.glob(os.path.join(root, "data", "eeg", f"subject={subject}", "*.parquet"))):
            x = pd.read_parquet(path).filter(like="ch_")
            clip.append((x.abs() >= CLIP).mean().to_numpy())
            sd.append(sosfiltfilt(sos, x.to_numpy(float), axis=0).std(0))
        names = [c[3:] for c in x.columns]
        clip, sd = np.mean(clip, 0), np.median(sd, 0)
        extra = {c for c, f, s in zip(names, clip, sd) if f > CLIP_FRAC or s < FLAT_RATIO * np.median(sd)}
        out[subject] = [c for c in names if c in set(bads) | extra]
    with open(BADS_JSON, "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
