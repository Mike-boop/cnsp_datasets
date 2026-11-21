"""
Sound-card vs MEG clock drift of the Schüller recordings, per chapter (trial), from the raw recordings' audio
channel. Writes drift.csv next to this file, which the adaptor reads (notes.md section 7).

The public release has no audio channel; the non-public raw recordings (BTi `c,rfhp1.0Hz`, branch `internal`
dataset schuller2022full) record the sound-card output on `EXT 004`. Per raw recording and chapter: the stimtrack is
resampled 1017.25 -> 1000 Hz (as the authors resampled the MEG), the chapter onset is found by cross-correlating the
first 60 s of its audio (attended + ignored, each normalised) with the whole stimtrack, and jehn2025_base.drift
.trial_drift (2-200 Hz, 10 s windows every 5 s, Theil-Sen) gives onset (ms) and drift (ppm; > 0: MEG clock fast).
Rows carry the recording's meas_date, which equals the meas_date of the participant's runs in the release.

    python -m cnsp_datasets.datasets.schueller2024.drift <raw dir with P*/raw/c,rfhp1.0Hz> <release download dir>
"""
from __future__ import annotations

import glob
import os
import sys

import mne
import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.signal import correlate, resample_poly, sosfiltfilt

from cnsp_datasets.datasets.jehn2025_base.drift import _SOS, trial_drift
from cnsp_datasets.datasets.schueller2024.adaptor import BOOKS, N_CHAPTERS, Schueller2024Adaptor

OUT = os.path.join(os.path.dirname(__file__), "drift.csv")


def chapter_audio(download_dir: str) -> dict:
    """(speaker, chapter) -> attended + ignored audio at 1 kHz, 2-200 Hz."""
    a = Schueller2024Adaptor(download_dir)
    audio = {}
    for speaker, (att, ign) in BOOKS.items():
        for k in range(1, N_CHAPTERS + 1):
            _, xa = wavfile.read(a.wav(att, k))
            _, xi = wavfile.read(a.wav(ign, k))
            xi = xi[:, 0] if xi.ndim == 2 else xi
            audio[(speaker, k)] = sosfiltfilt(_SOS, resample_poly(xa / np.abs(xa).max() + xi / np.abs(xi).max(), 10, 441))
    return audio


def main(raw_dir: str, download_dir: str) -> None:
    audio = chapter_audio(download_dir)
    rows = []
    for path in sorted(glob.glob(os.path.join(raw_dir, "*", "raw", "c,rfhp1.0Hz"))):
        raw = mne.io.read_raw_bti(path, convert=True, preload=False, verbose="ERROR")
        st = sosfiltfilt(_SOS, resample_poly(raw.get_data(picks="EXT 004")[0], 4000, 4069))
        for (speaker, k), au in audio.items():
            c = correlate(st, au[:60000], "valid", method="fft")
            i = int(np.argmax(np.abs(c)))
            r = np.abs(c[i]) / np.sqrt(np.sum(au[:60000] ** 2) * np.sum(st[i:i + 60000] ** 2))
            rows.append(dict(folder=path.split(os.sep)[-3], meas_date=str(raw.info["meas_date"]), speaker=speaker,
                             chapter=k, trial=2 * k - (speaker == "LP"), onset_s=i / 1000, r60=round(float(r), 3),
                             dur_s=len(au) / 1000, **trial_drift(st[i:i + len(au)], au)))
        print(path, flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False, float_format="%.4f")
    print(f"wrote {OUT}: {len(rows)} chapters")


if __name__ == "__main__":
    main(*sys.argv[1:3])
