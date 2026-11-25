"""
Readers shared by the Broderick et al. (2019) adaptors (natural, av, cocktail): the same Dryad package and CND layout.

EEG .mat files hold 128 BioSemi channels (key `eegData`, or `EEG` in the speech-in-noise folder) and, in most files,
the two mastoids (`mastoids`), all in microvolts at 128 Hz. Word timings are `Run<k>.mat` files (`wordVec`,
`onset_time`, `offset_time`, s).
"""
from __future__ import annotations

import numpy as np
from mne import create_info
from mne.io import RawArray
from pymatreader import read_mat

from cnsp_datasets.standardise.iohelpers import textgrid

FS = 128.0
N_EEG = 128
CHANNELS = [f"{bank}{k}" for bank in "ABCD" for k in range(1, 33)]  # BioSemi 128 (A1..D32)
MASTOIDS = ["M1", "M2"]


def channels_first(x: np.ndarray, n_channels: int, what: str) -> np.ndarray:
    """
    A 2-D array as (n_channels, n_times). The files store (n_times, n_channels); an array already channels-first is
    kept. The channel count decides, so a short recording cannot be mis-oriented; any other shape raises.
    """
    x = np.asarray(x)
    if x.ndim != 2:
        raise ValueError(f"{what}: expected 2-D, got {x.shape}")
    if x.shape[1] == n_channels and x.shape[0] != n_channels:
        return x.T
    if x.shape[0] == n_channels:
        return x
    raise ValueError(f"{what}: no axis of {x.shape} has {n_channels} channels")


def read_eeg(mat_path: str, key: str = "eegData") -> RawArray:
    """One run: 128 EEG channels (+ M1/M2 as misc when the file has `mastoids`) in V, original reference."""
    m = read_mat(mat_path)
    if key not in m:
        raise KeyError(f"{key!r} not found in {mat_path}")
    data = [channels_first(m[key], N_EEG, f"{mat_path} {key}")]
    names, types = list(CHANNELS), ["eeg"] * N_EEG
    if "mastoids" in m:
        data.append(channels_first(m["mastoids"], len(MASTOIDS), f"{mat_path} mastoids"))
        names += MASTOIDS
        types += ["misc"] * len(MASTOIDS)
    raw = RawArray(1e-6 * np.concatenate(data, axis=0).astype(float), create_info(names, FS, types),
                   verbose="ERROR")  # shipped in microvolts
    raw.set_montage("biosemi128")
    return raw


def words_textgrid(mat_path: str, reverse_duration: float | None = None) -> str:
    """
    TextGrid (tier `words`, lower case) of a Run<k>.mat. reverse_duration: the words of the time-reversed audio of
    this duration (s), i.e. in reverse order at duration - offset .. duration - onset.
    """
    m = read_mat(mat_path)
    words = [str(w).lower() for w in np.atleast_1d(m["wordVec"])]
    onsets, offsets = np.ravel(m["onset_time"]).astype(float), np.ravel(m["offset_time"]).astype(float)
    if not len(words) == len(onsets) == len(offsets):
        raise ValueError(f"{mat_path}: {len(words)} words, {len(onsets)} onsets, {len(offsets)} offsets")
    if reverse_duration is not None:
        words = words[::-1]
        onsets, offsets = reverse_duration - offsets[::-1], reverse_duration - onsets[::-1]
    # xmin 0, or the first onset if earlier (a last word ending after the reversed envelope's end)
    xmin = min(0.0, float(onsets.min())) if len(onsets) else 0.0
    return textgrid({"words": list(zip(onsets, offsets, words))}, xmin=xmin)
