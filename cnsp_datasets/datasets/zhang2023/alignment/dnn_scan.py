"""
Per-trial DNN lag scan against the rebuilt sources (accou2023 match-mismatch classifier fs128_1020-32_broadband).

EEG: the shipped trial (Emotiv 32 at template standard_1020 positions) through the classifier's own steps (0.5 Hz
high-pass, spherical-spline interpolation onto the BioSemi-32 layout, average reference), z-scored per channel.
Stimulus: Hilbert envelope of the rebuilt 115 s source at 128 Hz, z-scored. 5 s windows (1 s hop) inside each
splice piece (pieces.csv); the window at trial EEG sample j is scored against source position map[j] + lag for
lags of +-12 s. Stimuli: attended, ignored and two mismatched sources (null; chosen by a crc32 seed per trial).
Sign: negative lag = the EEG is later than the shipped pairing. One cache file per trial (resumable).
Usage: ZHANG2023_DNN=<classifier.pt> python -m cnsp_datasets.datasets.zhang2023.alignment.dnn_scan <download_dir> \
    <out_dir>
"""
import os
import sys
import zlib

import h5py
import numpy as np
import torch
import torch.nn.functional as F

from cnsp_datasets.align.specs import load_classifier
from cnsp_datasets.datasets.zhang2023.expinfo import channel_names, read_expinfo
from cnsp_datasets.datasets.zhang2023.adaptor import _eeg_loader
from cnsp_datasets.datasets.zhang2023.alignment.splices import (FS_AUDIO, mat_files, read_csv, source_audio,
                                                                trial_lengths)

MODEL_ENV = "ZHANG2023_DNN"  # path of the accou2023 classifier fs128_1020-32_broadband.pt (no default)
LAG_S, HOP = 12.0, 128


@torch.no_grad()
def tower(model, x, eeg, device):
    x = torch.as_tensor(x, dtype=torch.float32, device=device)[None]
    if eeg:
        x = model.eeg_spatial_filter(x)
    for p in model.eeg_projections if eeg else model.stimfeat_projections:
        x = model.activation(p(x))
    return x[0]


@torch.no_grad()
def scan(model, ew, u, s_windows, lags, device):
    """Scores (n_lags, n_windows) of normalised EEG windows ew against source windows at u + lag; NaN outside."""
    out = np.full((len(lags), len(u)), np.nan, np.float32)
    n = s_windows.shape[1]
    ut = torch.as_tensor(u, device=device)
    for b in range(0, len(lags), 64):
        idx = ut[None] + torch.as_tensor(lags[b:b + 64], device=device)[:, None]
        ok = (idx >= 0) & (idx < n)
        s = F.normalize(s_windows[:, idx.clamp(0, n - 1)].permute(1, 2, 0, 3), dim=-1)
        sc = model.linear(torch.einsum("wfk,lwgk->lwfg", ew, s).flatten(start_dim=2)).squeeze(-1)
        sc[~ok] = float("nan")
        out[b:b + 64] = sc.cpu().numpy()
    return out


def model_path() -> str:
    """The classifier's path from $ZHANG2023_DNN; a clear error if it is not set."""
    path = os.environ.get(MODEL_ENV)
    if not path:
        raise RuntimeError(f"set {MODEL_ENV} to the accou2023 classifier fs128_1020-32_broadband.pt "
                           "(cnsp_datasets.align.train_cli)")
    return path


def main(root, out):
    model_file = model_path()
    os.makedirs(out, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, spec, _ = load_classifier(model_file, device)
    fs, seg = spec.fs, round(spec.segment_length * spec.fs)
    lags = np.arange(-round(LAG_S * fs), round(LAG_S * fs) + 1)
    win = tower(model, np.zeros((1, seg)), False, device).shape[-1]  # feature samples per segment
    pieces, cover = read_csv("pieces.csv"), read_csv("source_cover.csv")
    windows = {}
    for name in sorted({r["source"] for r in cover}):
        d = {"fs": FS_AUDIO, "data": source_audio(root, name, cover).astype(float)[None]}
        for step in spec.stim_steps():
            d = step.run(d)
        e = np.asarray(d["data"]).ravel()
        windows[name] = tower(model, ((e - e.mean()) / e.std())[None], False, device).unfold(1, win, 1)
    names = sorted(windows)
    for path in mat_files(root):
        s = os.path.basename(path)[:-4]
        with h5py.File(path, "r") as f:
            info, ch, lengths = read_expinfo(f), channel_names(f), trial_lengths(f)
        for t, n_eeg in enumerate(lengths):
            key = f"{s}_t{t + 1:02d}"
            cache = os.path.join(out, f"{key}.npz")
            if os.path.exists(cache) or not n_eeg:
                continue
            rows = [p for p in pieces if p["subject"] == s and p["trial"] == t + 1 and p["n"] >= seg]
            raw = _eeg_loader(path, t + 1, ch, "")()
            for step in spec.eeg_steps():
                raw = step.run(raw)
            e = raw.get_data()
            e = (e - e.mean(1, keepdims=True)) / e.std(1, keepdims=True)
            ew, u, j = [], [], []
            for p in rows:
                feat = tower(model, e[:, p["eeg_start"]:p["eeg_start"] + p["n"]], True, device)
                for w0 in range(0, p["n"] - seg + 1, HOP):
                    ew.append(feat[:, w0:w0 + win])
                    u.append(p["source_start"] + w0)
                    j.append(p["eeg_start"] + w0)
            if not ew:
                np.savez(cache, n=0)
                continue
            ew = F.normalize(torch.stack(ew), dim=-1)
            left = info["attended_lr"][t] == "left"
            att = info["l_audio" if left else "r_audio"][t].removesuffix(".wav")
            ign = info["r_audio" if left else "l_audio"][t].removesuffix(".wav")
            rng = np.random.default_rng(zlib.crc32(key.encode()))
            nulls = list(rng.choice([n for n in names if n not in (att, ign)], 2, replace=False))
            res = {k: scan(model, ew, np.array(u), windows[k], lags, device) for k in [att, ign] + nulls}
            np.savez(cache, n=len(u), lags=lags, att=res[att].astype(np.float16), ign=np.nanmean(res[ign], 1),
                     null0=res[nulls[0]].astype(np.float16), null1=res[nulls[1]].astype(np.float16),
                     j=np.array(j), u=np.array(u), n_eeg=e.shape[1], names=np.array([att, ign] + nulls))
            print(key, len(u), "windows", flush=True)
    print("=== done", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])
