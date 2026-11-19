"""Helpers for building BIDS datasets from BrainVision recordings (used by the datasets' make_bids.py)."""
from __future__ import annotations

import json
import os
import re
import shutil

import pandas as pd


def link(src: str, dst: str) -> None:
    """Hard-link src to dst (copy if the file systems differ)."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_tsv(path: str, df: pd.DataFrame) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, sep="\t", index=False, na_rep="n/a")


def channels_of(vhdr: str) -> list[tuple[str, str]]:
    """(name, unit) per channel from the [Channel Infos] section of a BrainVision header."""
    text = open(vhdr, encoding="utf-8").read()
    section = text.split("[Channel Infos]")[1].split("[")[0]
    return [(m.group(1), m.group(4).strip() or "µV")
            for m in re.finditer(r"^Ch\d+=([^,]*),([^,]*),([^,]*),(.*)$", section, re.M)]


def copy_brainvision(vhdr: str, stem: str) -> None:
    """<stem>.vhdr/.vmrk rewritten to point at the renamed files; the .eeg hard-linked."""
    src = os.path.dirname(vhdr)
    head = open(vhdr, encoding="utf-8").read()
    data_file = re.search(r"^DataFile=(.*)$", head, re.M).group(1).strip()
    marker_file = re.search(r"^MarkerFile=(.*)$", head, re.M).group(1).strip()
    name = os.path.basename(stem)
    head = re.sub(r"^DataFile=.*$", f"DataFile={name}.eeg", head, flags=re.M)
    head = re.sub(r"^MarkerFile=.*$", f"MarkerFile={name}.vmrk", head, flags=re.M)
    os.makedirs(os.path.dirname(stem), exist_ok=True)
    open(f"{stem}.vhdr", "w", encoding="utf-8").write(head)
    mrk = open(os.path.join(src, marker_file), encoding="utf-8").read()
    open(f"{stem}.vmrk", "w", encoding="utf-8").write(re.sub(r"^DataFile=.*$", f"DataFile={name}.eeg", mrk, flags=re.M))
    link(os.path.join(src, data_file), f"{stem}.eeg")


def markers(vmrk: str) -> list[tuple[str, str, int]]:
    """(type, description, 0-based sample) of every marker in a BrainVision marker file."""
    text = open(vmrk, encoding="utf-8").read()
    return [(m.group(1), m.group(2).strip(), int(m.group(3)) - 1)
            for m in re.finditer(r"^Mk\d+=([^,]*),([^,]*),(\d+)", text, re.M)]
