"""
Audio onset and audio vs MEG clock drift of every presentation, from the audio copy (English MISC006, Russian
MISC005). Writes drift.csv next to this file, which the adaptor reads (notes.md section 6).

Per run: code 3 (STI101 & 0xFF) locates each presentation. Coarse: the wav's 1-20 Hz envelope is cross-correlated
with the audio copy's in 10 s windows every 5 s (+-600 ms around code 3; the English clocks differ by ~540 ppm, i.e.
216 ms at the end), Theil-Sen line -> coarse onset and drift. Fine: the wav (1 kHz, 2-200 Hz) is put on the coarse
clock and cross-correlated with the audio copy (10 s windows, +-30 ms, r > 0.3; jehn2025_base.alignment.xcorr).
Both use the positive xcorr peak: the |xcorr| peak of jehn2025_base.alignment.drift.trial_drift picks the inverted
side lobe (~2.4 ms off) in some windows.
`onset_samp` = MEG sample (from the first stored sample, fractional) of wav sample 0; `drift_ppm` > 0: the MEG
clock runs fast relative to the audio clock. FIT_END_S limits the fit (sub-E12 run-1 presentation 2).

    python -m cnsp_datasets.datasets.yang2026_base.alignment.drift <yang2026 download dir>
"""
from __future__ import annotations

import os
import sys

import mne
import numpy as np
import pandas as pd
from scipy.interpolate import make_interp_spline
from scipy.io import wavfile
from scipy.signal import butter, hilbert, resample_poly, sosfiltfilt

from cnsp_datasets.datasets.jehn2025_base.alignment.xcorr import MAX_LAG, SOS as _SOS, window_fit
from cnsp_datasets.datasets.yang2026_base.adaptor import DRIFT_CSV as OUT, FIT_END_S, SITES, code3_samples, run_files

COARSE_LAG, MIN_R_ENV, MIN_R = 600, 0.5, 0.3
_SOS_ENV = butter(4, [1, 20], "bp", fs=1000, output="sos")


def _envelope(x: np.ndarray) -> np.ndarray:
    return sosfiltfilt(_SOS_ENV, np.abs(hilbert(x)))


def presentation_fits(fif: str, wav: np.ndarray, env_wav: np.ndarray, channel: str) -> list[dict]:
    raw = mne.io.read_raw_fif(fif, preload=False, verbose="ERROR")
    y = raw.get_data(picks=channel)[0]
    yf, env = sosfiltfilt(_SOS, y), _envelope(y)
    code3 = code3_samples(raw)
    if len(code3) != 2:
        raise ValueError(f"{fif}: {len(code3)} code-3 onsets, expected 2")
    rows = []
    for pres, ref in enumerate(code3, 1):
        fit_end = FIT_END_S.get((os.path.basename(fif), pres))
        n = len(wav) if fit_end is None else round(fit_end * 1000)
        ic, d0, _ = window_fit(env, env_wav[:n], int(ref), COARSE_LAG, MIN_R_ENV)
        start = int(ref + round(ic))
        on_meg_clock = make_interp_spline(np.arange(n), wav[:n], k=3)(np.arange(int(n * (1 + d0))) / (1 + d0))
        onset, resid, n_windows = window_fit(yf, on_meg_clock, start, MAX_LAG, MIN_R)
        rows.append(dict(file=os.path.basename(fif), pres=pres, code3=int(ref), coarse_ppm=d0 * 1e6,
                         n_windows=n_windows, onset_samp=start + onset, drift_ppm=((1 + d0) * (1 + resid) - 1) * 1e6,
                         end_margin_s=(raw.n_times - start - onset - len(on_meg_clock)) / 1000))
    return rows


def main(download_dir: str) -> None:
    rows = []
    for site, cfg in SITES.items():
        root = os.path.join(download_dir, cfg["folder"])
        fs, x = wavfile.read(os.path.join(root, "stimuli", "audio", "stimulus.wav"), mmap=True)
        w = resample_poly(np.asarray(x[:, 0], float), 1000, fs)
        wav, env_wav = sosfiltfilt(_SOS, w), _envelope(w)
        for fif in run_files(root, cfg["task"]):
            for row in presentation_fits(fif, wav, env_wav, next(iter(cfg["audio_copy"]))):
                rows.append(dict(site=site, **row))
                print(rows[-1], flush=True)
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, float_format="%.5f")
    d["after_code3_ms"] = d.onset_samp - d.code3
    print(f"wrote {OUT}: {len(d)} presentations")
    print(d.groupby("site")[["after_code3_ms", "drift_ppm", "n_windows", "end_margin_s"]].describe().T.round(3)
          .to_string())


if __name__ == "__main__":
    main(sys.argv[1])
