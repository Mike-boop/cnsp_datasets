"""
Shared pieces of the li2025 onset/drift scripts: the speech envelope and the preprocessed MEG, read from the download
through the adaptor without onset correction, the lagged design of a ridge forward TRF, and the saved TRF weights.

Preprocessing (analysis only; the standardised data stay raw): magnetometers without bads and MEG062 (on the z-axis,
undefined HFC basis), homogeneous field correction (order 1), 0.1 Hz high-pass of the whole recording; envelope
(|hilbert| of the mean audio channel) and MEG band-passed 0.5-8 Hz at 64 Hz and z-scored.
"""
import glob
import os

import mne
import numpy as np
from scipy.fft import next_fast_len
from scipy.signal import butter, hilbert, resample_poly, sosfiltfilt

from cnsp_datasets.datasets.li2025.adaptor import N_TIMES, VIDEO, Li2025Adaptor, _decode, group  # noqa: F401

FS = 64
ALPHA = 1.0  # ridge, relative to the mean eigenvalue of X'X
SOS = butter(4, [0.5, 8], "bandpass", fs=FS, output="sos")
LAGS = np.arange(round(-1.5 * FS), round(1.5 * FS) + 1)
N = N_TIMES * FS // 1000


def envelope(download_dir: str) -> np.ndarray:
    """0.5-8 Hz z-scored envelope at FS, cut to the recording (N samples)."""
    x = _decode(os.path.join(download_dir, VIDEO)).astype(float).mean(0)
    env = np.abs(hilbert(x, N=next_fast_len(len(x))))[:len(x)]
    env = sosfiltfilt(SOS, resample_poly(env, FS, 44100))[:N]
    return (env - env.mean()) / env.std()


def meg(download_dir: str, skip=(54,)):
    """Yield (subject, raw info, Y (samples x channels)) per participant; sub-54 (truncated) skipped by default."""
    for rec in Li2025Adaptor(download_dir, onset_correction=False).parse():
        if rec.subject in skip:
            continue
        raw = rec.neural_data_fn()
        raw.pick("mag", exclude=raw.info["bads"] + ["MEG062"])
        raw.add_proj(mne.preprocessing.compute_proj_hfc(raw.info, order=1, verbose="ERROR"))
        raw.apply_proj(verbose="ERROR")
        raw.filter(0.1, None, verbose="ERROR")
        Y = sosfiltfilt(SOS, resample_poly(raw.get_data(), FS, 1000, axis=1), axis=1)[:, :N].T
        yield rec.subject, raw.info, (Y - Y.mean(0)) / Y.std(0)


def delayed(e: np.ndarray, d: float) -> np.ndarray:
    """Envelope delayed by d s (zeros in front), same length."""
    k = round(d * FS)
    return np.concatenate([np.zeros(k), e[:len(e) - k]])


def design(e: np.ndarray) -> np.ndarray:
    """X[t, j] = e[t - LAGS[j]] (zeros outside): lag > 0 = MEG after the sound."""
    n = len(e)
    X = np.zeros((n, len(LAGS)))
    for j, lag in enumerate(LAGS):
        if lag >= 0:
            X[lag:, j] = e[:n - lag]
        else:
            X[:lag, j] = e[-lag:]
    return X


def regularised(X: np.ndarray) -> np.ndarray:
    """X'X plus ridge ALPHA x its mean eigenvalue."""
    xx = X.T @ X
    return xx + ALPHA * np.trace(xx) / len(LAGS) * np.eye(len(LAGS))


def load_weights(src: str):
    """trf_weights.py output: (list of npz, channels good in all subjects, stack(group, key) -> subj x lags x ch)."""
    data = [np.load(f) for f in sorted(glob.glob(os.path.join(src, "sub-*.npz")))]
    common = sorted(set.intersection(*[set(d["ch_names"]) for d in data]))

    def stack(g, key):
        return np.array([d[key][:, [list(d["ch_names"]).index(c) for c in common]]
                         for d in data if str(d["group"]) == g])

    return data, common, stack
