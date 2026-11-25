"""
Sound onset after the trigger and audio vs MEG clock drift of every piece, from the audio copy UADC002 (the played
wav channel 0, inverted, low-passed at 300 Hz; notes.md sections 6-7). Writes audio_fit.csv next to this file, one
row per UPPT001 trigger, which the adaptor reads (it imports torch through align.scan; the adaptor does not).

Pieces (codes 101-119): coarse Theil-Sen fit of the 1-20 Hz envelope of the 30-290 Hz band, then of the inverted
30-290 Hz waveform on the coarse clock (`jehn2025_base.alignment.xcorr.window_fit`, 10000-sample windows). Test
snippets (codes 1-3, too short for windows): one cross-correlation of the whole waveform. Columns: `delay_ms`
(sound onset after the trigger), `drift_ppm` (> 0: MEG clock fast), `band_frac` (share of the wav's power in
30-290 Hz; only pieces with band_frac >= MIN_BAND_FRAC are `reliable`), `xcorr_r` (test snippets).

    python -m cnsp_datasets.datasets.kern2022.alignment.drift <kern2022 download dir>
"""
from __future__ import annotations

import os
import sys

import mne
import numpy as np
import pandas as pd
from scipy.interpolate import make_interp_spline
from scipy.io import wavfile
from scipy.signal import butter, correlate, hilbert, resample_poly, sosfiltfilt

from cnsp_datasets.align.scan import peak_offset
from cnsp_datasets.datasets.jehn2025_base.alignment.xcorr import window_fit
from cnsp_datasets.datasets.kern2022.adaptor import AUDIO_FIT as OUT, FS, recording, wav_path

COARSE_LAG, MIN_R_ENV, MIN_COARSE = 360, 0.5, 3  # +-300 ms; envelope r; windows needed for the fine fit
FINE_LAG, MIN_R, MIN_WINDOWS = 12, 0.3, 5  # +-10 ms; waveform r; windows needed to report a fit
MIN_BAND_FRAC = 0.005
_SOS = butter(4, [30, 290], "bp", fs=FS, output="sos")
_SOS_ENV = butter(4, [1, 20], "bp", fs=FS, output="sos")


def piece_onsets(trig: np.ndarray) -> list[tuple[int, int]]:
    """(sample, code) of every piece (101-119) and test snippet (1-3) on UPPT001."""
    starts = np.flatnonzero(np.diff(trig) != 0) + 1
    return [(int(s), int(trig[s])) for s in starts if 101 <= trig[s] <= 119 or 1 <= trig[s] <= 3]


def _whole_xcorr(y: np.ndarray, w: np.ndarray, s: int) -> tuple[float, float]:
    """Sub-sample lag (samples after s) and r of the positive peak of w in y, within -0.5 to +1.5 s."""
    seg = y[s - FS // 2:s + 3 * FS // 2 + len(w)]
    energy = np.cumsum(np.r_[0, seg ** 2])
    c = correlate(seg, w, "valid", method="fft") / np.sqrt(
        (energy[len(w):] - energy[:-len(w)]) * (w ** 2).sum() + 1e-30)
    return peak_offset(c) - FS // 2, c.max()


def _envelope(x: np.ndarray) -> np.ndarray:
    return sosfiltfilt(_SOS_ENV, np.abs(hilbert(x)))


def piece_fits(uadc: np.ndarray, trig: np.ndarray, download_dir: str) -> list[dict]:
    """Delay and drift of every piece and test snippet of one recording (uadc: UADC002; trig: UPPT001)."""
    y = sosfiltfilt(_SOS, uadc)
    y_env = _envelope(y)
    rows = []
    for s, code in piece_onsets(trig):
        fs, x = wavfile.read(wav_path(download_dir, code))
        played = x[:, 0].astype(float)
        w = -sosfiltfilt(_SOS, resample_poly(played, 2 * FS, 2 * fs))  # the audio copy is inverted
        band_frac = (w ** 2).mean() / (played ** 2).mean()
        row = dict(code=code, trigger_samp=s, dur_s=len(x) / fs, band_frac=band_frac,
                   reliable=bool(band_frac >= MIN_BAND_FRAC), n_coarse=0, n_windows=0, delay_ms=np.nan,
                   drift_ppm=np.nan, xcorr_r=np.nan)
        if code < 100:
            lag, r = _whole_xcorr(y, w, s)
            row.update(delay_ms=lag / FS * 1e3, xcorr_r=r)
        else:
            ic, d0, row["n_coarse"] = window_fit(y_env, _envelope(w), s, COARSE_LAG, MIN_R_ENV)
            if row["n_coarse"] >= MIN_COARSE:
                start = int(s + round(ic))
                n = int(len(w) * (1 + d0))
                on_meg_clock = make_interp_spline(np.arange(len(w)), w, k=3)(np.arange(n) / (1 + d0))
                onset, resid, n_win = window_fit(y, on_meg_clock, start, FINE_LAG, MIN_R)
                if n_win >= MIN_WINDOWS:
                    row.update(n_windows=n_win, delay_ms=(start + onset - s) / FS * 1e3,
                               drift_ppm=((1 + d0) * (1 + resid) - 1) * 1e6)
        rows.append(row)
    return rows


def main(download_dir: str) -> None:
    rows = []
    for sub in sorted(d for d in os.listdir(os.path.join(download_dir, "MEGData")) if d.startswith("sub0")):
        raw = mne.io.read_raw_ctf(recording(download_dir, sub), preload=False, verbose="ERROR")
        uadc, trig = raw.get_data(picks=["UADC002-4302", "UPPT001"])  # same channel suffix in all 35 recordings
        rows += [dict(subject=sub, **r) for r in piece_fits(uadc, trig.astype(int), download_dir)]
        print(sub, flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False, float_format="%.4f")


if __name__ == "__main__":
    main(sys.argv[1])
