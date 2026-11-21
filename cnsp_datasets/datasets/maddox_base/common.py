"""
Shared code for the Maddox / Polonenko lab datasets (polonenko2021/2024/2025/2026, stoll2025, shan2024).

All were recorded with the same setup: expyfun with sound-card triggers (sample-locked to the audio), BrainVision
(actiCHamp, EP-PreAmp for the subcortical montage) and ER-2 insert earphones with ~11-inch tubes. Stimuli are
expyfun hdf5 files (`read_hdf5`: datasets under `expyfun/key_<name>`).

Timing used here:
- onset = start marker + acoustic tube delay (sound at the eardrum);
- drift = mean over a recording's trials of (end - start marker) / nominal - 1 (> 0: the EEG counts more samples
  per audio second; same convention as bentum2023.drift.to_audio_clock);
- trials are skipped when a recording pause (New Segment) falls inside them or the recording ends before them;
- one resample per trial: zero-phase anti-alias FIR at the native rate, then one quintic-spline evaluation on the
  drift-corrected output grid (plain decimation for integer factors without drift).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Sequence, Tuple

import h5py
import mne
import numpy as np
from scipy.interpolate import make_interp_spline
from scipy.signal import firwin, oaconvolve

TUBE_DELAY = 11 * 25.4e-3 / 343.0  # s, 11-inch ER-2 tubes (authors' code: 0.81 ms)
SPLINE_ORDER = 5
PAD = 0.05  # s of EEG kept on both sides of a trial while filtering (filter edges)


@dataclass
class MarkedTrial:
    start: int                # 0-based sample of the start marker (S 1)
    bits: Tuple[int, ...]     # trial ID stamped after the start marker (S 4 = 0, S 8 = 1)
    end: int | None = None    # the next end marker (S 2), if any before the next start


@dataclass
class Recording:
    trials: List[MarkedTrial]
    boundaries: List[int]     # samples where a new segment starts (recording paused; MNE joins without a gap)
    n_times: int
    sfreq: float

    def usable(self, trial: MarkedTrial, n: int) -> bool:
        """Whether n samples from the trial's start are recorded without a pause and before the end."""
        return trial.start + n + int(PAD * self.sfreq) < self.n_times and not any(
            trial.start < b <= trial.start + n for b in self.boundaries)

    def drift(self, nominal: float) -> float:
        """
        Clock drift from the start/end pairs that span `nominal` EEG samples (+-0.1%) without a pause:
        mean((end - start) / nominal) - 1.
        """
        ratios = [(t.end - t.start) / nominal for t in self.trials
                  if t.end is not None and abs(t.end - t.start - nominal) < 1e-3 * nominal
                  and self.usable(t, t.end - t.start)]
        return float(np.mean(ratios) - 1)


def read_recording(vhdr: str, ids_before_start: bool = False) -> Recording:
    """
    Start/end markers, trial-ID bits and segment boundaries of a BrainVision recording (.vmrk text only).

    ids_before_start: the ID bits are stamped before each start marker (stoll2025 exp2) instead of after it.
    """
    trials, boundaries, pending = [], [], ()
    with open(vhdr[:-5] + ".vmrk", encoding="utf-8") as f:
        markers = [line.split("=", 1)[1].split(",")[:3] for line in f if line.startswith("Mk")]
    for kind, desc, sample in markers:
        sample = int(sample) - 1
        if kind == "New Segment" and sample > 0:
            boundaries.append(sample)
        elif desc == "S  1":
            trials.append(MarkedTrial(sample, pending))
            pending = ()
        elif desc in ("S  4", "S  8"):
            bit = (int(desc == "S  8"),)
            if ids_before_start:
                pending += bit
            elif trials:
                trials[-1].bits += bit
        elif desc == "S  2" and trials and trials[-1].end is None:
            trials[-1].end = sample
    raw = _raw(vhdr)
    return Recording(trials, boundaries, raw.n_times, raw.info["sfreq"])


def bits_to_ints(bits: Sequence[int], widths: Sequence[int]) -> List[int]:
    """Split a bit sequence (most significant first, as expyfun.decimals_to_binary) into integers."""
    out, i = [], 0
    for w in widths:
        out.append(int("".join(map(str, bits[i:i + w])) or "0", 2))
        i += w
    return out


def read_expyfun(path: str, key: str) -> np.ndarray:
    """One entry of an expyfun hdf5 file (written by expyfun.io.write_hdf5)."""
    with h5py.File(path, "r") as f:
        return f[f"expyfun/key_{key}"][()]


@lru_cache(maxsize=4)
def _raw(vhdr: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_brainvision(vhdr, preload=False, verbose="ERROR")


def recording_sfreq(vhdr: str) -> float:
    """Sample rate of a BrainVision recording (header only)."""
    return _raw(vhdr).info["sfreq"]


def _antialias(sfreq: float, sfreq_out: float) -> np.ndarray:
    """Low-pass FIR (Kaiser, as scipy.signal.resample_poly) for decimating sfreq -> sfreq_out."""
    factor = sfreq / sfreq_out
    half = int(np.ceil(10 * factor))
    return firwin(2 * half + 1, 1 / factor, window=("kaiser", 5.0))


def load_trial(vhdr: str, onset: float, duration: float, sfreq_out: float | None = None, drift: float = 0.0,
               picks: List[str] | None = None) -> mne.io.RawArray:
    """
    One trial of a BrainVision recording on the audio clock.

    onset: trial start in EEG samples (may be fractional, e.g. marker + tube delay); duration: seconds.
    sfreq_out: output rate (None keeps the native rate; never upsampled). drift: see module docstring (0 = off).
    """
    raw = _raw(vhdr)
    sfreq = raw.info["sfreq"]
    sfreq_out = sfreq if sfreq_out is None else min(sfreq_out, sfreq)
    step = sfreq / sfreq_out
    n_out = int(np.ceil(round(duration * sfreq_out, 6)))
    pad = int(np.ceil(PAD * sfreq)) if sfreq_out < sfreq else SPLINE_ORDER + 1
    first = int(np.floor(onset)) - pad
    last = int(np.ceil(onset + (n_out - 1) * step * (1 + drift))) + pad + 1
    if first < 0 or last > raw.n_times:
        raise ValueError(f"trial [{first}, {last}) runs outside {vhdr} ({raw.n_times} samples)")
    picks = raw.ch_names if picks is None else picks
    data = raw.get_data(picks=picks, start=first, stop=last)
    if sfreq_out < sfreq:
        data = oaconvolve(data, _antialias(sfreq, sfreq_out)[None, :], mode="same", axes=1)
    positions = onset - first + np.arange(n_out) * step * (1 + drift)
    if np.allclose(positions, np.round(positions)):
        data = data[:, np.round(positions).astype(int)]
    else:
        data = make_interp_spline(np.arange(data.shape[1]), data, k=SPLINE_ORDER, axis=1)(positions)
    info = mne.create_info(picks, sfreq_out, "eeg")
    return mne.io.RawArray(data.astype(np.float32), info, verbose="ERROR")


def expyfun_loader(path: str, key: str, fs_key: str | None = "fs", fs: int | None = None, invert: bool = False):
    """
    data_fn returning {'fs', 'data' (n_channels, n_times) float32} for one hdf5 entry. invert: the stimulus was
    played with inverted polarity (audio negated; for 'anm', whose rows are the two polarities, rows swapped).
    """

    def _loader() -> Dict:
        data = np.atleast_2d(read_expyfun(path, key)).astype(np.float32)
        if invert:
            data = data[::-1].copy() if key == "anm" else -data
        rate = fs if fs is not None else int(np.ravel(read_expyfun(path, fs_key))[0])
        return {"fs": rate, "data": data}

    return _loader


def pulse_loader(path: str, n_times: int, fs: int, key: str = "pinds"):
    """data_fn for a pulse train (uint8: 1 at each pulse index, else 0) at the audio rate."""

    def _loader() -> Dict:
        train = np.zeros((1, n_times), np.uint8)  # 0/1: 4x smaller than float32
        train[0, np.ravel(read_expyfun(path, key)).astype(int)] = 1
        return {"fs": fs, "data": train}

    return _loader
