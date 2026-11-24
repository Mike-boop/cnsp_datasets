"""
Bad channels per participant (notes.md section 5): 1-40 Hz SD per channel in each mapped 30-s trial; a channel is
bad if its SD is > 5x or < 1/5 of the median over channels in >= 20% of the participant's trials (the chen2026
rule). Writes bads.json next to this file, which the adaptor reads.

    python -m cnsp_datasets.datasets.zhang2025.bads <zhang2025 download dir>
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict

import numpy as np
from pymatreader import read_mat
from scipy.signal import butter, sosfiltfilt

from cnsp_datasets.datasets.zhang2025.adaptor import BADS_JSON, CHANNELS, FS, MAPPING, N

RATIO, FRACTION = 5.0, 0.2
SOS = butter(4, [1, 40], "bandpass", fs=FS, output="sos")


def main(download_dir: str) -> None:
    flags = defaultdict(list)
    with open(MAPPING, newline="") as f:
        for row in csv.DictReader(f):
            eeg = read_mat(os.path.join(download_dir, "trialinfo", row["file"]), variable_names=["eeg"])["eeg"]
            sd = sosfiltfilt(SOS, eeg - eeg.mean(0), axis=0)[int(row["start"]):int(row["start"]) + N].std(0)
            med = np.median(sd)
            flags[int(row["subject"])].append((sd > RATIO * med) | (sd < med / RATIO))
    out = {f"{sub:03d}": [CHANNELS[i] for i in np.flatnonzero(np.mean(fl, 0) >= FRACTION)]
           for sub, fl in sorted(flags.items())}
    with open(BADS_JSON, "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
