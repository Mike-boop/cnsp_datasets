"""
Bad channels per participant (notes.md section 5): 1-40 Hz SD per channel in each trial window (shipped onset to
+126 s); a channel is bad if its SD is > 5x or < 1/5 of the median over channels in >= 20% of the participant's 25
trials (the chen2026 rule), except that the periocular channels (PERIOCULAR: blinks and eye movements) are only
tested for low SD. VREF (the reference, zero) is not tested. Writes bads.json next to this file, which the adaptor
reads.

    python -m cnsp_datasets.datasets.peng2026.bads <peng2026 download dir>
"""
from __future__ import annotations

import glob
import json
import os
import sys

import mne
import numpy as np
import pandas as pd

BADS_JSON = os.path.join(os.path.dirname(__file__), "bads.json")
RATIO, FRACTION, TRIAL_S = 5.0, 0.2, 126.0
PERIOCULAR = {"E1", "E8", "E14", "E17", "E21", "E25", "E32", "E125", "E126", "E127", "E128"}  # HydroCel 128


def trial_flags(mff: str) -> np.ndarray:
    """Outlier flags (trials x E1-E128) of one run."""
    raw = mne.io.read_raw_egi(mff, preload=True, verbose="ERROR").pick([f"E{i}" for i in range(1, 129)])
    raw.filter(1, 40, verbose="ERROR")
    onsets = pd.read_csv(mff.replace("_eeg.mff", "_events.tsv"), sep="\t")["onset"]
    sfreq, x = raw.info["sfreq"], raw.get_data()
    sd = np.array([x[:, int(o * sfreq):int((o + TRIAL_S) * sfreq)].std(1) for o in onsets])
    med = np.median(sd, 1, keepdims=True)
    high = (sd > RATIO * med) & ~np.isin(raw.ch_names, list(PERIOCULAR))
    return high | (sd < med / RATIO)


def main(download_dir: str) -> None:
    out = {}
    for sub_dir in sorted(glob.glob(os.path.join(download_dir, "sub-*", ""))):
        flags = np.vstack([trial_flags(m) for m in sorted(glob.glob(os.path.join(sub_dir, "eeg", "*_eeg.mff")))])
        sub = os.path.basename(sub_dir[:-1])
        out[sub] = [f"E{i + 1}" for i in np.flatnonzero(flags.mean(0) >= FRACTION)]
        print(sub, out[sub], flush=True)
    with open(BADS_JSON, "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
