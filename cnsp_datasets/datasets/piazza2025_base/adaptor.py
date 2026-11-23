from __future__ import annotations

import itertools
import os
from functools import lru_cache
from typing import Callable, Iterable

import numpy as np
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray
from pymatreader import read_mat
from scipy.io import wavfile

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 100
AUDIO_FS = 44100
N_SUBJECTS = 25
# stim.condNames FDS, NDS, Slow_NDS; FDS is called L2A in the paper
REGISTERS = {1: "L2A", 2: "NDS", 3: "Slow_NDS"}
STORIES = {1: "HOLE", 2: "Love", 3: "Guerrilla"}  # stim.stimNames
PARTS = 5
EXCESS = (85, 110)  # EEG trial length minus envelope length, samples (epochs end ~1 s after the audio)
STUB = 500  # samples; shorter EEG trials are empty placeholders for failed recordings
RENAME = {"T7 (T3)": "T7", "T8 (T4)": "T8", "Iz (inion)": "Iz", "Afz": "AFz"}
UNKNOWN_ORDER = [f"E{i:02d}" for i in range(1, 65)]
GROUPS = {
    "l1l": dict(folder="L1L", chanlocs="BioSchanlocs64.mat", labelled=range(1, N_SUBJECTS + 1),
                reference="unknown (BioSemi; a left-earlobe electrode was recorded for offline referencing but is "
                          "not shipped)",
                notes="Experiment 2: native English listeners, Trinity College Dublin, BioSemi ActiveTwo 64 ch "
                      "recorded at 1024 Hz."),
    "l2l": dict(folder="L2L", chanlocs="chanlocs64Brain.mat", labelled=range(1, 6),
                reference="left earlobe (online, hardware; paper)",
                notes="Experiment 1: Spanish L1 learners of English, BCBL, BrainVision actiCAP/BrainAmp 64 ch "
                      "recorded at 1000 Hz. Channel order from chanlocs64Brain.mat, which fits subjects 1-5 only."),
}
NOTES = ("Shipped preprocessed by the authors (CND): 1-8 Hz band-pass, 100 Hz, microvolts (scaled to V); the readme "
         "says bad channels were interpolated. Epoched by the authors at the PsychoPy start trigger: EEG sample 0 = "
         "audio onset, EEG runs ~1 s past the audio end. Stories in +16 dB multi-talker babble; NDS/Slow-NDS stimuli "
         "are the shipped wavs (speech + babble as played), L2A only the authors' 100 Hz envelope.")
ORDER_UNKNOWN = ("Channel order unknown: no shipped labelling fits this subject's data (notes.md), so channels are "
                 "named E01-E64 in file order, without positions.")


class Piazza2025Adaptor:
    """
    Piazza et al. 2025 (OSF ba3p4, CND): three stories, each in five ~3 min parts, heard once per participant in one
    of three speech registers (L2A, NDS, Slow-NDS; Latin square). Two groups with different EEG systems, standardised
    as separate datasets (`group` 'l1l' or 'l2l'). 100 Hz preprocessed EEG.

    Trials are assigned to (story, register, part) from the EEG trial lengths, which fit exactly one of the nine
    designs per subject; the stim files' labels are checked against it and are wrong for L1L 13-15 (notes.md). Trial
    number = presentation position (1-15). Placeholder trials of failed recordings and the parts missing in L2L 16
    are skipped.
    """

    def __init__(self, download_dir: str, group: str):
        self.group = GROUPS[group]
        self.root = os.path.join(download_dir, "data_CND", self.group["folder"])
        self.audio_dir = os.path.join(download_dir, "STIMULI", "Audio")
        self.subjects = [s for s in range(1, N_SUBJECTS + 1) if os.path.exists(self._eeg_path(s))]
        labels = read_mat(os.path.join(self.root, self.group["chanlocs"]))["chanlocs"]["labels"]
        self.names = [RENAME.get(c, c) for c in labels]

    def parse(self) -> Iterable[TrialRecord]:
        eeg_len = {s: [len(t) for t in _read_eeg(self._eeg_path(s))["data"]] for s in self.subjects}
        envelopes = self._envelopes(eeg_len)
        lengths = {key: len(env) for key, env in envelopes.items()}
        for sub in self.subjects:
            slots, assigned = _design(eeg_len[sub], lengths)
            mismatch = _labelled_slots(_read_stim(self._stim_path(sub))) != slots
            labelled = sub in self.group["labelled"]
            for idx, (slot, key) in enumerate(assigned):
                if key is None:
                    continue
                story, register, part = key
                notes = " ".join([NOTES, self.group["notes"]] + ([] if labelled else [ORDER_UNKNOWN]))
                description = provenance(
                    "sw_trigger", "software (paper: PsychoPy start trigger; epoched by the authors)", notes,
                    validation_tier="low", reference=self.group["reference"], story=story, register=register,
                    part=part, shipped_trial_index=idx, stim_file_mismatch=mismatch, channel_order_known=labelled,
                )
                yield TrialRecord(
                    subject=sub, session=1, trial=slot + 1, condition=register, ns_type="eeg",
                    stimulus=[self._stimulus(key, envelopes)],
                    neural_data_fn=self._eeg_loader(sub, idx, labelled, description),
                )

    def _eeg_path(self, sub: int) -> str:
        return os.path.join(self.root, f"pre_dataSub{sub}.mat")

    def _stim_path(self, sub: int) -> str:
        return os.path.join(self.root, f"dataStim{sub}.mat")

    def _envelopes(self, eeg_len: dict[int, list[int]]) -> dict[tuple, np.ndarray]:
        """(story, register, part) -> the authors' 100 Hz envelope, from subjects whose stim labels fit their EEG."""
        envelopes = {}
        for sub in self.subjects:
            stim = _read_stim(self._stim_path(sub))
            env = stim["data"][0]
            if len(eeg_len[sub]) == len(env) and all(_fits(n, len(e)) for n, e in zip(eeg_len[sub], env)):
                for col, key in enumerate(_labelled_slots(stim)):
                    envelopes.setdefault(key, np.asarray(env[col], dtype=np.float32))
            if len(envelopes) == 3 * 3 * PARTS:
                return envelopes
        raise ValueError(f"envelopes found for {len(envelopes)} of {3 * 3 * PARTS} parts")

    def _stimulus(self, key: tuple, envelopes: dict) -> StimulusRecord:
        story, register, part = key
        if register == "L2A":  # no wav shipped
            env = envelopes[key]
            return StimulusRecord("audio", f"{story}_{register}_p{part}", lambda: {"fs": FS, "data": env[None, :]},
                                  is_attended=True, feature_name="envelope")
        name = f"{story}_{register}_p{part}_16dB"
        return StimulusRecord("audio", name, _audio_loader(os.path.join(self.audio_dir, name + ".wav")),
                              is_attended=True, feature_name="audio")

    def _eeg_loader(self, sub: int, idx: int, labelled: bool, description: str) -> Callable[[], BaseRaw]:
        path, names = self._eeg_path(sub), self.names if labelled else UNKNOWN_ORDER

        def _loader() -> BaseRaw:
            eeg = _read_eeg(path)
            info = create_info(names, FS, "eeg")
            raw = RawArray(1e-6 * np.asarray(eeg["data"][idx], dtype=float).T, info, verbose="ERROR")  # µV
            if labelled:
                raw.set_montage(make_standard_montage("standard_1005"))  # template positions
            raw.info["description"] = description
            return raw
        return _loader


def _fits(n: int, length: int) -> bool:
    """Whether an EEG trial of n samples can hold a stimulus part of `length` samples (or is a placeholder)."""
    return n < STUB or EXCESS[0] <= n - length <= EXCESS[1]


def _labelled_slots(stim: dict) -> list[tuple]:
    """(story, register, part) of each column of a stim file, from condIdxs / stimIdxs (blocks of five parts)."""
    cond, story = np.ravel(stim["condIdxs"]), np.ravel(stim["stimIdxs"])
    return [(STORIES[s], REGISTERS[c], i % PARTS + 1) for i, (c, s) in enumerate(zip(cond, story))]


def _design(eeg_len: list[int], lengths: dict[tuple, int]) -> tuple[list[tuple], list[tuple]]:
    """
    The one design (register order x story order) the EEG trial lengths fit: its 15 slots and, per EEG trial,
    (slot index, key), key None for placeholders. Each trial takes the next slot its length fits (missing parts are
    skipped greedily; placeholders take a slot unchecked); requiring a unique fit over all 36 orders guards this.
    """
    fits = []
    for registers in itertools.permutations(REGISTERS):
        for stories in itertools.permutations(STORIES):
            slots = [(STORIES[s], REGISTERS[c], p) for c, s in zip(registers, stories) for p in range(1, PARTS + 1)]
            assigned, j = [], 0
            for n in eeg_len:
                while j < len(slots) and not _fits(n, lengths[slots[j]]):
                    j += 1
                if j == len(slots):
                    break
                assigned.append((j, None if n < STUB else slots[j]))
                j += 1
            else:
                fits.append((slots, assigned))
    if len(fits) != 1:
        raise ValueError(f"EEG trial lengths fit {len(fits)} designs")
    return fits[0]


def _audio_loader(path: str) -> Callable[[], dict]:
    def _loader() -> dict:
        fs, x = wavfile.read(path)
        if fs != AUDIO_FS or x.dtype != np.int16 or x.ndim != 1:
            raise ValueError(f"{path}: expected 44.1 kHz mono int16")
        return {"fs": AUDIO_FS, "data": (x / 32768.0).astype(np.float32)[None, :]}
    return _loader


@lru_cache(maxsize=1)
def _read_stim(path: str) -> dict:
    stim = read_mat(path)["stim"]
    if stim["fs"] != FS:
        raise ValueError(f"{path}: stimulus features at {stim['fs']} Hz, expected {FS}")
    return stim


@lru_cache(maxsize=1)
def _read_eeg(path: str) -> dict:
    eeg = read_mat(path)["eeg"]
    if eeg["fs"] != FS:
        raise ValueError(f"{path}: EEG at {eeg['fs']} Hz, expected {FS}")
    return eeg
