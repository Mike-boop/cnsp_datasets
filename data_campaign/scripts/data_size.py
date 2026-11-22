"""Data size per dataset and condition, estimated from the stimuli ("soft"): each trial counts the duration of its
longest stimulus (simultaneous streams, e.g. target + distractor or speech + babble, are counted once), summed per
participant. Stimulus durations come from the array headers inside the flat-format stimulus files (each read once);
the trial list comes from the neural file names. No neural data is read.

Scans tmp/review/**/standardised and /data_storage/gu08wuvu/datasets/<dataset>/standardised-flat (or the folders
given as arguments). Writes tmp/review/data_size.csv (one row per subject x condition, merged with earlier rows of
other datasets) and prints participants and hours per participant (mean, min, max) per dataset and per condition.
    python data_size.py [folder ...]
"""
import glob
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd

REVIEW = "/data_storage/gu08wuvu/datasets/tmp/review"
OUT = f"{REVIEW}/data_size.csv"
NEURAL = ("eeg", "meg", "ieeg")


def roots():
    found = sorted(glob.glob(f"{REVIEW}/**/standardised", recursive=True))
    return found + sorted(glob.glob("/data_storage/gu08wuvu/datasets/*/standardised-flat"))


def name_of(root):
    if root.startswith(REVIEW):
        sub = os.path.basename(root).removeprefix("standardised").lstrip("_")  # standardised_en -> yang2026_en
        return os.path.basename(os.path.dirname(root)) + (f"_{sub}" if sub else "")
    return os.path.basename(os.path.dirname(root)) + " (user copy)"


def npz_seconds(path):
    """Duration of the 'data' array in a flat-format stimulus .npz (last axis / fs), from headers only."""
    with zipfile.ZipFile(path) as z:
        with z.open("fs.npy") as f:
            fs = float(np.load(f))
        with z.open("data.npy") as f:
            version = np.lib.format.read_magic(f)
            shape, _, _ = np.lib.format._read_array_header(f, version)
    return shape[-1] / fs


def stimulus_seconds(root):
    """{stimulus name: seconds}: the longest feature file of each name (some features are shorter, e.g. onsets)."""
    out = {}
    for path in glob.glob(f"{root}/*/*_-_*.npz"):
        name = os.path.basename(path).split("_-_")[0]
        try:
            sec = npz_seconds(path)
        except (KeyError, ValueError, zipfile.BadZipFile):
            continue
        out[name] = max(out.get(name, 0.0), sec)
    return out


def scan(root):
    durations = stimulus_seconds(root)
    rows, missing = [], set()
    for kind in NEURAL:
        for path in glob.glob(f"{root}/{kind}/*_-_{kind}.fif"):
            parts = os.path.basename(path)[:-4].split("_-_")
            sub = parts[0].removeprefix("sub-")
            cond = next((p.removeprefix("cond-") for p in parts if p.startswith("cond-")), "n/a")
            names = [re.sub(r"^[a-z]+\d+-", "", p) for p in parts if re.match(r"^[a-z]+\d+-", p)]
            secs = [durations[n] for n in names if n in durations]
            missing.update(n for n in names if n not in durations)
            if secs:
                rows.append(dict(dataset=name_of(root), subject=sub, condition=cond, seconds=max(secs)))
    if missing:
        print(f"  {name_of(root)}: no stimulus file for {len(missing)} names, e.g. {sorted(missing)[:3]}")
    d = pd.DataFrame(rows)
    return d.groupby(["dataset", "subject", "condition"], as_index=False).agg(seconds=("seconds", "sum"),
                                                                              trials=("seconds", "size")) if len(d) else d


def summary(d):
    per_sub = d.groupby(["dataset", "subject"]).seconds.sum() / 3600
    s = per_sub.groupby("dataset").agg(participants="count", hours_mean="mean", hours_min="min", hours_max="max",
                                       hours_total="sum")
    s["trials"] = d.groupby("dataset").trials.sum()
    return s.round(2)


def per_condition(d):
    per = d.groupby(["dataset", "condition", "subject"]).seconds.sum() / 3600
    s = per.groupby(["dataset", "condition"]).agg(participants="count", hours_mean="mean")
    return s.round(3)


if __name__ == "__main__":
    frames = []
    for r in sys.argv[1:] or roots():
        d = scan(r)
        print(f"{name_of(r)}: {int(d.trials.sum()) if len(d) else 0} trials", flush=True)
        if len(d):
            frames.append(d)
    new = pd.concat(frames)
    if os.path.exists(OUT):
        old = pd.read_csv(OUT, dtype={"subject": str})
        new = pd.concat([old[~old.dataset.isin(new.dataset.unique())], new])
    new.to_csv(OUT, index=False)
    print(summary(new).to_string())
    print(per_condition(new).to_string())
