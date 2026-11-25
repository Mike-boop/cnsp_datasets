"""
Rebuild mapping.csv: which trialinfo recording, and which 30-s segment of it, each shipped trial was cut from.

The trialinfo file names (S<ss>_T<tt>.mat) do not follow the shipped subject/trial ids, so every shipped
(preprocessed) trial `eeg/dataset-001-subject-SSS-trial-TTT.npy` is located in the raw recordings by sliding
correlation (1-8 Hz, mean over the 16 channels). Candidates: recordings with the same task, attended speaker and
initial attended direction (`meta/publish_metadata.pkl` vs the trialinfo object). A trial is kept when the best
r > 0.3 and beats the runner-up by >= 0.15, and no other trial claims the same recording.
Takes ~1 h on 2 threads.

    python -m cnsp_datasets.datasets.zhang2025.alignment.make_mapping DOWNLOAD_DIR [OUT_CSV]
"""
import csv
import glob
import os
import sys
from collections import defaultdict

import numpy as np
from pymatreader import read_mat
from scipy.signal import butter, fftconvolve, sosfiltfilt

from cnsp_datasets.datasets.zhang2025.adaptor import FS, MAPPING, _NumpyUnpickler
from cnsp_datasets.datasets.zhang2025.trialinfo import read_trial_info, stem

SOS = butter(4, [1, 8], "bandpass", fs=FS, output="sos")
R_MIN, MARGIN = 0.3, 0.15


def _filt(x):
    return sosfiltfilt(SOS, x - x.mean(0), axis=0)


def sliding_r(raw: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Mean-over-channels Pearson r of template x (n, C) at every start in raw (L, C); flat stretches score 0."""
    n = len(x)
    xz = (x - x.mean(0)) / x.std(0)
    num = np.stack([fftconvolve(raw[:, c], xz[::-1, c], mode="valid") for c in range(raw.shape[1])], 1)
    cs = np.cumsum(np.vstack([np.zeros((1, raw.shape[1])), raw]), 0)
    cs2 = np.cumsum(np.vstack([np.zeros((1, raw.shape[1])), raw ** 2]), 0)
    s, s2 = cs[n:] - cs[:-n], cs2[n:] - cs2[:-n]
    sd = np.sqrt(np.maximum(s2 - s ** 2 / n, 0))
    ok = sd > 1e-3 * np.median(sd, 0)
    return np.where(ok, num / (np.maximum(sd, 1e-12) * np.sqrt(n)), 0).mean(1)


def main(root: str, out: str = MAPPING) -> None:
    with open(os.path.join(root, "meta", "publish_metadata.pkl"), "rb") as f:
        meta = _NumpyUnpickler(f).load()
    raws, by_sig = {}, defaultdict(list)
    for path in sorted(glob.glob(os.path.join(root, "trialinfo", "*.mat"))):
        name, info = os.path.basename(path), read_trial_info(path)
        att = int(info["attended_speaker"].item()) - 1
        speaker = int(stem(info["audio_paths"][att]).split("_")[1])
        by_sig[(int(info["class"][4]), speaker, int(np.ravel(info["speaker_directions"])[att]))].append(name)
        raws[name] = _filt(read_mat(path, variable_names=["eeg"])["eeg"]).astype(np.float32)
    best = {}
    for key, m in sorted(meta.items()):
        x = _filt(np.load(os.path.join(root, "eeg", key + ".npy")))
        scores = []
        for name in by_sig[(m["task_id"], m["speaker_id"], int(m["label"][0]))]:
            if len(raws[name]) >= len(x):
                sc = sliding_r(raws[name].astype(np.float64), x)
                scores.append((float(sc.max()), name, int(sc.argmax())))
        top, second = (sorted(scores, reverse=True) + [(0, None, 0)] * 2)[:2]
        if top[0] > R_MIN and top[0] - second[0] >= MARGIN:
            best[key] = top + (second[0],)
    claims = defaultdict(int)
    for v in best.values():
        claims[v[1]] += 1
    rows = sorted((int(k.split("-")[3]), int(k.split("-")[5]), v[1], v[2], round(v[0], 3), round(v[3], 3))
                  for k, v in best.items() if claims[v[1]] == 1)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject", "trial", "file", "start", "r", "r_second"])
        w.writerows(rows)


if __name__ == "__main__":
    main(*sys.argv[1:])
