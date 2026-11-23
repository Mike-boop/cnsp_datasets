"""
Build triggers.csv: one row per stimulus trigger on STI101 (codes 51-224 = condition base + stimulus number 1-24,
authors' code c02_sens_coh_vocoding.m), read from the recordings rather than events.tsv, which misses some trials
(notes.md, section 4). Run once on a download: python triggers.py <download dir>.
"""
from __future__ import annotations

import glob
import io
import os
import sys

import mne
import pandas as pd

BASES = {50: "original", 80: "7chan", 110: "5chan", 140: "3chan", 170: "2chan", 200: "1chan"}
CSV = os.path.join(os.path.dirname(__file__), "triggers.csv")


def run_triggers(fif: str) -> list[dict]:
    """Stimulus triggers of one run; sample counted from the first sample of the file."""
    with open(fif, "rb") as f:  # one sequential read: MNE's small reads are slow on network storage
        raw = mne.io.read_raw_fif(io.BytesIO(f.read()), preload=True, verbose="ERROR")
    # min_duration skips 1-sample transition values (e.g. 48 on the way to 53)
    events = mne.find_events(raw, stim_channel="STI101", min_duration=0.002, consecutive=True, verbose="ERROR")
    return [dict(sample=int(s - raw.first_samp), code=int(c), condition=BASES[b], stim=int(c - b),
                 n_times=int(raw.n_times)) for s, _, c in events for b in BASES if b < c <= b + 24]


def main(download_dir: str) -> None:
    rows = []
    for fif in sorted(glob.glob(os.path.join(download_dir, "sub-*", "ses-1", "meg", "*_meg.fif"))):
        name = os.path.basename(fif)
        for position, row in enumerate(run_triggers(fif), 1):
            rows.append(dict(subject=name.split("_")[0], run=int(name.split("run-")[1][:2]), position=position,
                             **row))
    pd.DataFrame(rows).to_csv(CSV, index=False)


if __name__ == "__main__":
    main(sys.argv[1])
