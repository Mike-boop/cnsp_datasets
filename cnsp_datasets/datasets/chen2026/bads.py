"""
Bad channels per participant (notes.md section 6d): in every chapter file of alignment/timing.csv, a channel is
flagged when its 1-40 Hz SD is more than BAD_RATIO times or less than 1/BAD_RATIO of the median SD over E1-E128;
a participant's bad channels are those flagged in >= MIN_FRAC of their chapters (flags in single chapters come and
go with the impedances, and the validator needs one channel set per participant). Writes bads.json next to this
file, which the adaptor reads.

    python -m cnsp_datasets.datasets.chen2026.bads <chen2026 download dir>
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import mne
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

from cnsp_datasets.datasets.chen2026.adaptor import BADS_JSON, TIMING_CSV

BAD_RATIO, MIN_FRAC = 5.0, 0.2


def flagged(vhdr: str) -> list[str]:
    """Channels of one file whose 1-40 Hz SD is > BAD_RATIO x or < 1/BAD_RATIO of the median SD."""
    raw = mne.io.read_raw_brainvision(vhdr, preload=True, verbose="ERROR")
    sos = butter(4, [1, 40], "bandpass", fs=raw.info["sfreq"], output="sos")
    sd = np.array([sosfiltfilt(sos, x).std() for x in raw.get_data()])  # per channel: bounded memory
    ratio = sd / np.median(sd)
    return [c for c, q in zip(raw.ch_names, ratio) if q > BAD_RATIO or q < 1 / BAD_RATIO]


def main(download_dir: str) -> None:
    table = pd.read_csv(TIMING_CSV, dtype={"sub": str})
    out = {}
    for sub, rows in table.groupby("sub"):
        counts = Counter()
        for r in rows.itertuples():
            counts.update(flagged(os.path.join(download_dir, "PassiveListening", f"sub-{sub}", f"ses-{r.story}", "eeg",
                                               r.file)))
        out[sub] = sorted((c for c, n in counts.items() if n >= MIN_FRAC * len(rows)), key=lambda c: int(c[1:]))
        print(f"sub-{sub}: {out[sub]} (flagged in >= {MIN_FRAC:.0%} of {len(rows)} chapters; "
              f"{len(counts)} channels flagged at least once)", flush=True)
    with open(BADS_JSON, "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
