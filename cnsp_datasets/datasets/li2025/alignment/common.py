"""
Shared pieces of the li2025 onset/drift scripts: the speech envelope and the preprocessed MEG, read from the download
through the adaptor without onset correction, the lagged design of a ridge forward TRF, the saved TRF weights, the
cached wide-lag TRFs whose delays are estimated and the template match that turns a TRF into a delay.

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

from cnsp_datasets.align.scan import peak_offset
from cnsp_datasets.datasets.li2025.adaptor import N_TIMES, VIDEO, Li2025Adaptor, _decode, group  # noqa: F401

FS = 64
ALPHA = 1.0  # ridge, relative to the mean eigenvalue of X'X
SOS = butter(4, [0.5, 8], "bandpass", fs=FS, output="sos")
LAGS = np.arange(round(-1.5 * FS), round(1.5 * FS) + 1)  # TRF lags of trf_weights.py (the template) and poptrf.py
MATCH_LAGS = np.arange(round(-1.5 * FS), round(2.5 * FS) + 1)  # lags of the TRFs whose delay is estimated
N = N_TIMES * FS // 1000
N_PARTS = 5  # parts per recording for the delays' consistency check
PART_WINDOW = 0.3  # s: each part is matched within this of its recording's whole-recording delay
# template lags -0.2..+0.6 s; the same indices in LAGS and MATCH_LAGS (both grids start at -1.5 s)
WIN = np.where((LAGS >= -0.2 * FS) & (LAGS <= 0.6 * FS))[0]
CANDS = np.arange(0, len(MATCH_LAGS) - WIN[-1])  # shifts that keep the window within the fitted lags (0..1.9 s)


def envelope(download_dir: str) -> np.ndarray:
    """0.5-8 Hz z-scored envelope at FS, cut to the recording (N samples)."""
    x = _decode(os.path.join(download_dir, VIDEO)).astype(float).mean(0)
    env = np.abs(hilbert(x, N=next_fast_len(len(x))))[:len(x)]
    env = sosfiltfilt(SOS, resample_poly(env, FS, 44100))[:N]
    return (env - env.mean()) / env.std()


def meg(download_dir: str, skip=(54,)):
    """Yield (subject, raw info, Y (samples x channels)) per participant; sub-54 (truncated) skipped by default."""
    for rec in Li2025Adaptor(download_dir, onset="none").parse():
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


def design(e: np.ndarray, lags: np.ndarray = LAGS) -> np.ndarray:
    """X[t, j] = e[t - lags[j]] (zeros outside): lag > 0 = MEG after the sound."""
    n = len(e)
    X = np.zeros((n, len(lags)))
    for j, lag in enumerate(lags):
        if lag >= 0:
            X[lag:, j] = e[:n - lag]
        else:
            X[:lag, j] = e[-lag:]
    return X


def regularised(X: np.ndarray) -> np.ndarray:
    """X'X plus ridge ALPHA x its mean eigenvalue."""
    xx = X.T @ X
    return xx + ALPHA * np.trace(xx) / len(xx) * np.eye(len(xx))


def weight_files(src: str) -> list[str]:
    """trf_weights.py output files (sub-XX.npz), sorted by subject."""
    return sorted(glob.glob(os.path.join(src, "sub-*.npz")))


def load_weights(src: str):
    """
    trf_weights.py output: (list of npz, channels good in all subjects, stack(group, key) -> subj x lags x ch);
    stack(None, key) stacks all subjects, in weight_files order.
    """
    data = [np.load(f) for f in weight_files(src)]
    common = sorted(set.intersection(*[set(d["ch_names"]) for d in data]))

    def stack(g, key):
        return np.array([d[key][:, [list(d["ch_names"]).index(c) for c in common]]
                         for d in data if g is None or str(d["group"]) == g])

    return data, common, stack


def match_trfs(src: str, common: list[str], cache: str) -> dict:
    """
    Uncorrected TRFs over MATCH_LAGS (common channels) per subject: {subject: (whole recording, parts, part centres
    in s)}. N_PARTS equal parts (sub-54, truncated: two halves of its 698 s); cached in cache/sub-XX.npz.
    """
    os.makedirs(cache, exist_ok=True)

    def path(s):
        return os.path.join(cache, f"sub-{s:02d}.npz")

    def cached(s):
        if not os.path.exists(path(s)):
            return False
        d = np.load(path(s))
        return list(d["common"]) == common and d["whole"].shape[0] == len(MATCH_LAGS)

    done = {s for s in range(31, 61) if cached(s)}
    env = full = None
    for sub, info, Y in meg(src, skip=done):
        if env is None:
            env = envelope(src)
            full = design(env, MATCH_LAGS)
        X = full if len(Y) == N else design(env[:len(Y)], MATCH_LAGS)
        Y = Y[:, [info["ch_names"].index(c) for c in common]]
        idx = np.array_split(np.arange(len(Y)), N_PARTS if len(Y) == N else 2)
        w = [np.linalg.solve(regularised(X[i]), X[i].T @ Y[i]) for i in [slice(None)] + idx]
        np.savez(path(sub), whole=w[0], parts=np.array(w[1:]), centres_s=[i.mean() / FS for i in idx],
                 common=np.array(common))
        print(sub, flush=True)
    return {s: (d["whole"], d["parts"], d["centres_s"]) for s in range(31, 61) for d in [np.load(path(s))]}


def match_curve(template: np.ndarray, W: np.ndarray) -> np.ndarray:
    """
    Space-time r between the template (WIN lags of a LAGS TRF, raveled) and the lags WIN + k of W (a MATCH_LAGS TRF,
    lags x channels), for every shift k in CANDS.
    """
    return np.array([np.corrcoef(template, W[WIN + k].ravel())[0, 1] for k in CANDS])


def match_delay(curve: np.ndarray, near: float | None = None) -> float:
    """
    Best-matching delay (s) of a match curve, parabolic refinement; only within PART_WINDOW of near (s) if given (a
    maximum on that window's edge is returned unrefined).
    """
    lo, hi = 0, len(curve)
    if near is not None:
        lo = max(lo, int(np.ceil((near - PART_WINDOW) * FS)))
        hi = min(hi, int(np.floor((near + PART_WINDOW) * FS)) + 1)
    return (lo + peak_offset(curve[lo:hi])) / FS
