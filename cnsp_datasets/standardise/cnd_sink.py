"""
CND (Continuous-event Neural Data) sink — di Liberto et al. format.

Data are accumulated in memory as `save_record` is called, then written to
disk when `finalize()` is called (or on __exit__ when used as a context manager).

Output — one file per subject:
    dataSub{n:03d}.mat
        eeg.data            {1 x T}  each cell (nTime x nChan)
        eeg.fs              scalar
        eeg.label           {1 x nChan} cellstr
        eeg.nbchan          scalar
        eeg.origTrialPosition  [1 x T] trial numbers in the original dataset
        eeg.conditionLabel  {1 x T} cellstr
        eeg.condNames       {1 x C} cellstr, unique conditions
        eeg.condIdxs        [1 x T] 1-based indices into condNames
        stim(k)             1 x K struct array, one element per feature
            .data           {1 x S} cell of unique stimulus waveforms (nTime x nFeatureDims)
            .fs             scalar
            .name           feature name string
            .stimIds        {1 x S} cellstr, unique stimulus IDs
            .stimIdxs       [1 x T] 1-based index of each trial's stimulus into .data / .stimIds
            .condNames      {1 x C} cellstr
            .condIdxs       [1 x T] 1-based condition index for each trial
        cndVersion          '1.0'

Usage:
    with CNDSinkV1(save_directory) as sink:
        for record in adaptor.parse():
            sink.save_record(record)
    # or call sink.finalize() manually
"""

from __future__ import annotations

import traceback
import numpy as np

from dataclasses import dataclass, field
from pathlib import Path
from scipy.io import savemat
from typing import Any, Dict, List, Optional

from cnsp_datasets.standardise.trial_record import TrialRecord

CND_VERSION = "1.0"

# ──────────────────────────────────────────────────────────────────────────────
# Internal buffers
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _FeatureBuf:
    fs: float
    unique_data: List[np.ndarray] = field(default_factory=list)   # (nTime, nDim) each
    unique_ids: List[str] = field(default_factory=list)
    trial_stim_idxs: List[int] = field(default_factory=list)      # 1-based
    trial_cond_idxs: List[int] = field(default_factory=list)      # 1-based
    cond_names: List[str] = field(default_factory=list)

    def add_trial(self, stim_id: str, data: np.ndarray, cond: str):
        if stim_id not in self.unique_ids:
            self.unique_ids.append(stim_id)
            self.unique_data.append(data)
        self.trial_stim_idxs.append(self.unique_ids.index(stim_id) + 1)

        if cond not in self.cond_names:
            self.cond_names.append(cond)
        self.trial_cond_idxs.append(self.cond_names.index(cond) + 1)


@dataclass
class _SubjectBuf:
    eeg_data: List[np.ndarray] = field(default_factory=list)      # (nTime, nChan) each
    fs: Optional[float] = None
    labels: Optional[List[str]] = None
    orig_trial_positions: List[int] = field(default_factory=list)
    cond_labels: List[str] = field(default_factory=list)
    cond_names: List[str] = field(default_factory=list)
    cond_idxs: List[int] = field(default_factory=list)
    features: Dict[str, _FeatureBuf] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_cell(arrays: List[np.ndarray]) -> np.ndarray:
    """Pack a list of arrays into a (1, N) MATLAB-compatible object array."""
    cell = np.empty((1, len(arrays)), dtype=object)
    for i, a in enumerate(arrays):
        cell[0, i] = np.asarray(a)
    return cell


def _make_cellstr(strings: List[str]) -> np.ndarray:
    """Pack a list of strings into a (1, N) MATLAB-compatible object array."""
    cell = np.empty((1, len(strings)), dtype=object)
    for i, s in enumerate(strings):
        cell[0, i] = str(s)
    return cell


def _row_vec(ints: List[int]) -> np.ndarray:
    """Return a (1, N) float64 row vector."""
    return np.array(ints, dtype=np.float64).reshape(1, -1)


def _extract_waveform(data: Any) -> Optional[tuple[np.ndarray, float]]:
    """
    Pull (waveform_2d, fs) from the dict a stimulus data_fn returns.

    Adaptors consistently use {"waveform": (1, T) array, "fs": scalar}.
    Falls back to the first ndarray value found, under any key name.
    Returns None if no numeric array can be found.
    """
    if not isinstance(data, dict):
        return None

    fs = float(data.get("fs", 0.0))
    for key in ("waveform", "data", "env", "envelope", "audio"):
        if key in data and isinstance(data[key], np.ndarray):
            arr = data[key]
            # Normalise to (nTime, nFeatureDims)
            arr = np.asarray(arr, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr[:, None]
            elif arr.ndim == 2 and arr.shape[0] < arr.shape[1]:
                # (1, T) → (T, 1)
                arr = arr.T
            return arr, fs

    # Last resort: first array value in dict
    for v in data.values():
        if isinstance(v, np.ndarray) and v.ndim >= 1:
            arr = np.asarray(v, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr[:, None]
            elif arr.ndim == 2 and arr.shape[0] < arr.shape[1]:
                arr = arr.T
            return arr, fs

    return None


def _build_stim_struct_array(features: Dict[str, _FeatureBuf]) -> np.ndarray:
    """
    Build a (1, K) numpy structured array that scipy.io.savemat converts into a
    MATLAB struct array  stim(k).data, stim(k).fs, …
    """
    fields = ("data", "fs", "name", "stimIds", "stimIdxs", "condNames", "condIdxs")
    dt = np.dtype([(f, "O") for f in fields])
    arr = np.empty((1, len(features)), dtype=dt)

    for k, (feat_name, buf) in enumerate(features.items()):
        arr[0, k]["data"] = _make_cell(buf.unique_data)
        arr[0, k]["fs"] = np.atleast_2d(np.float64(buf.fs))
        arr[0, k]["name"] = feat_name
        arr[0, k]["stimIds"] = _make_cellstr(buf.unique_ids)
        arr[0, k]["stimIdxs"] = _row_vec(buf.trial_stim_idxs)
        arr[0, k]["condNames"] = _make_cellstr(buf.cond_names)
        arr[0, k]["condIdxs"] = _row_vec(buf.trial_cond_idxs)

    return arr


def _build_eeg_struct(buf: _SubjectBuf) -> dict:
    return {
        "data": _make_cell(buf.eeg_data),
        "fs": np.atleast_2d(np.float64(buf.fs)),
        "label": _make_cellstr(buf.labels or []),
        "nbchan": np.atleast_2d(np.float64(len(buf.labels or []))),
        "origTrialPosition": _row_vec(buf.orig_trial_positions),
        "conditionLabel": _make_cellstr(buf.cond_labels),
        "condNames": _make_cellstr(buf.cond_names),
        "condIdxs": _row_vec(buf.cond_idxs),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Sink
# ──────────────────────────────────────────────────────────────────────────────

class CNDSinkV1:

    def __init__(self, save_directory: str | Path):
        self.save_directory = Path(save_directory)
        self.save_directory.mkdir(parents=True, exist_ok=True)
        self._subjects: Dict[int, _SubjectBuf] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def save_record(self, record: TrialRecord):
        try:
            self._accumulate(record)
        except Exception as e:
            print(f"[CNDSinkV1] Error buffering record (sub={record.subject}, "
                  f"trial={record.trial}): {e}")
            traceback.print_exc()

    def finalize(self):
        """Write all buffered data to disk. Call once after all records have been added."""
        for subject, buf in self._subjects.items():
            try:
                self._write_subject(subject, buf)
            except Exception as e:
                print(f"[CNDSinkV1] Error writing subject {subject}: {e}")
                traceback.print_exc()
        self._subjects.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.finalize()

    # ── Accumulation ───────────────────────────────────────────────────────────

    def _accumulate(self, record: TrialRecord):
        sub = record.subject
        if sub not in self._subjects:
            self._subjects[sub] = _SubjectBuf()
        buf = self._subjects[sub]

        # EEG: (nChan, nTime) → (nTime, nChan)
        raw = record.neural_data
        eeg = raw.get_data().T.astype(np.float64)
        buf.eeg_data.append(eeg)

        if buf.fs is None:
            buf.fs = float(raw.info["sfreq"])
            buf.labels = list(raw.info["ch_names"])

        buf.orig_trial_positions.append(record.trial)
        buf.cond_labels.append(record.condition)
        if record.condition not in buf.cond_names:
            buf.cond_names.append(record.condition)
        buf.cond_idxs.append(buf.cond_names.index(record.condition) + 1)

        # Stimuli
        for stim in record.stimulus:
            data = stim.data_fn()
            if isinstance(data, str):
                continue  # TextGrid / plain text — not representable in CND
            result = _extract_waveform(data)
            if result is None:
                continue
            waveform, fs = result

            feat = stim.feature_name
            if feat not in buf.features:
                buf.features[feat] = _FeatureBuf(fs=fs)
            buf.features[feat].add_trial(stim.name, waveform, record.condition)

    # ── Writing ────────────────────────────────────────────────────────────────

    def _write_subject(self, subject: int, buf: _SubjectBuf):
        out: dict = {"cndVersion": CND_VERSION}
        out["eeg"] = _build_eeg_struct(buf)
        if buf.features:
            out["stim"] = _build_stim_struct_array(buf.features)
        path = self.save_directory / f"dataSub{subject:03d}.mat"
        savemat(str(path), out)
        print(f"[CNDSinkV1] Wrote {path} "
              f"({len(buf.eeg_data)} trials, {len(buf.features)} feature(s))")
