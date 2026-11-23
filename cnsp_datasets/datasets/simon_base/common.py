"""
Shared code for the UMD Simon-lab KIT-MEG datasets (presacco2016, brodbeck2018, brodbeck2022, karunathilake2023,
karunathilake2025, kulasingham2021).

All were recorded on the lab's KIT 157-channel system: MEG 001-157 axial gradiometers (MNE type `mag`) and
MEG 158-160 reference magnetometers (`ref_meg`), in T, plus MISC TTL/idle lines and STI 014, which the adaptors
drop. Participants are R-numbers (R2262); R2262 -> subject 2262. Stimuli are mono int16 wavs.

- Shipped epochs (brodbeck2018, kulasingham2021): `read_epochs`, `epoch_raw` (one epoch as Raw, shipped bads plus
  zero-variance channels).
- Continuous recordings (brodbeck2022, karunathilake2023/2025): `read_raw`, `stim_events`, `rms_bads` (flat or
  saturated gradiometers), `crop_meg`.
"""
from __future__ import annotations

import glob
import re
from collections import Counter
from functools import lru_cache
from typing import Callable, Iterable, Sequence

import mne
import numpy as np
from scipy.io import wavfile

from cnsp_datasets.standardise.clock import crop_on_audio_clock

REFERENCE = "not applicable (MEG)"


def find_one(pattern: str) -> str:
    """The single match of a recursive glob."""
    hits = sorted(glob.glob(pattern, recursive=True))
    if len(hits) != 1:
        raise FileNotFoundError(f"expected one match for {pattern}, found {hits}")
    return hits[0]


def subject_number(pid: str) -> int:
    """The full R-number (R2262 -> 2262)."""
    if not re.fullmatch(r"R\d+", pid):
        raise ValueError(f"not an R-number: {pid}")
    return int(pid[1:])


def check_unique_subjects(pids: Iterable[str]) -> None:
    """Raise if a subject number occurs twice (e.g. the same R-number in two folders)."""
    counts = Counter(map(subject_number, pids))
    duplicates = sorted(n for n, k in counts.items() if k > 1)
    if duplicates:
        raise ValueError(f"subject numbers are not unique: {duplicates}")


def read_wav(path: str, fs: int) -> np.ndarray:
    """Mono int16 wav at `fs` as float32 in [-1, 1)."""
    rate, x = wavfile.read(path)
    if rate != fs or x.dtype != np.int16 or x.ndim != 1:
        raise ValueError(f"{path}: expected {fs} Hz mono int16")
    return (x / 32768.0).astype(np.float32)


def audio_loader(path: str, fs: int, mute: int = 0) -> Callable[[], dict]:
    """Stimulus loader of `read_wav(path, fs)`, samples before `mute` set to 0."""
    def _load() -> dict:
        x = read_wav(path, fs)
        x[:mute] = 0
        return {"fs": fs, "data": x[None, :]}

    return _load


@lru_cache(maxsize=None)
def wav_samples(path: str, audio_fs: int, fs: int) -> int:
    """Length of a wav at `audio_fs` in samples at `fs`."""
    rate, x = wavfile.read(path, mmap=True)
    if rate != audio_fs:
        raise ValueError(f"{path}: expected {audio_fs} Hz")
    return round(len(x) * fs / audio_fs)


def meg_picks(info: mne.Info) -> np.ndarray:
    """Gradiometers and reference magnetometers, bads included (MISC and STI dropped)."""
    return mne.pick_types(info, meg=True, ref_meg=True, exclude=[])


@lru_cache(maxsize=2)
def read_epochs(fname: str, sfreq: float, n_times: int) -> mne.Epochs:
    """Shipped epochs, checked for `sfreq` and `n_times` samples from t = 0 (cached: do not modify)."""
    epochs = mne.read_epochs(fname, preload=True, verbose="ERROR")
    if epochs.info["sfreq"] != sfreq or len(epochs.times) != n_times or epochs.tmin != 0:
        raise ValueError(f"{fname}: unexpected rate or epoch length")
    return epochs


def epoch_raw(epochs: mne.Epochs, idx: int) -> mne.io.RawArray:
    """Epoch `idx` as Raw (`meg_picks`); bads = shipped bads plus any zero-variance channel."""
    picks = meg_picks(epochs.info)
    info = mne.pick_info(epochs.info, picks)
    data = epochs.get_data(picks=picks, item=idx)[0]
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    flat = [raw.ch_names[i] for i in np.flatnonzero(data.std(axis=1) == 0)]
    raw.info["bads"] = sorted(set(info["bads"]) | set(flat))
    return raw


@lru_cache(maxsize=1)
def read_raw(path: str, sfreq: float) -> mne.io.BaseRaw:
    """Continuous recording (opening the first file joins its splits), checked for `sfreq` (cached: do not modify)."""
    raw = mne.io.read_raw_fif(path, preload=False, verbose="ERROR")
    if raw.info["sfreq"] != sfreq:
        raise ValueError(f"{path}: sfreq {raw.info['sfreq']}, expected {sfreq}")
    return raw


def stim_events(raw: mne.io.BaseRaw, codes: Iterable[int]) -> np.ndarray:
    """STI 014 events (every onset, 1-sample events kept) with a code in `codes`."""
    events = mne.find_events(raw, stim_channel="STI 014", shortest_event=1, verbose="ERROR")
    return events[np.isin(events[:, 2], list(codes))]


@lru_cache(maxsize=4)
def rms_bads(path: str, sfreq: float, flat_ratio: float, saturated_ratio: float | None = None) -> tuple[str, ...]:
    """
    Gradiometers of `read_raw(path, sfreq)` whose median rms over 10 x 10 s windows (starts spread evenly from 60 s
    to 70 s before the end; recordings of >= 130 s) is below the across-channel median / `flat_ratio` or, if given,
    above the median x `saturated_ratio`.
    """
    raw = read_raw(path, sfreq)
    meg = mne.pick_types(raw.info, meg=True, ref_meg=False, exclude=[])
    starts = np.linspace(60, raw.n_times / sfreq - 70, 10)
    rms = np.median([raw.get_data(picks=meg, start=int(t * sfreq), stop=int((t + 10) * sfreq)).std(axis=1)
                     for t in starts], axis=0)
    bad = rms < np.median(rms) / flat_ratio
    if saturated_ratio is not None:
        bad |= rms > np.median(rms) * saturated_ratio
    return tuple(raw.ch_names[meg[j]] for j in np.where(bad)[0])


def crop_meg(raw: mne.io.BaseRaw, onset: float, n_out: int, description: str,
             bads: Sequence[str] | None = None) -> mne.io.BaseRaw:
    """
    `n_out` samples of `meg_picks` from `onset` (samples from the first sample, may be fractional;
    `crop_on_audio_clock`); bads replaced if given.
    """
    out = crop_on_audio_clock(raw, onset, n_out, picks=meg_picks(raw.info))
    if bads is not None:
        out.info["bads"] = list(bads)
    out.info["description"] = description
    return out
