from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from typing import Callable, Iterable

import numpy as np
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray
from pymatreader import read_mat

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 100
FEATURE = "envelope"  # the authors' 100 Hz broadband envelope (no audio shared); same name as broderick2019
REFERENCE_SUBJECTS = {"A": 1, "B": 2}  # complete 41-trial sequences of the two counterbalancing groups
FIRST_LECTURE = {"A": "L1", "B": "L2"}  # target lecture of the first half
GROUP = {lec: group for group, lec in FIRST_LECTURE.items()}
RENAME = {"T7 (T3)": "T7", "T8 (T4)": "T8", "Iz (inion)": "Iz", "Afz": "AFz"}
HALVES = {1: "first_half", 2: "second_half"}
NOTES = ("Shipped preprocessed by the authors: linked-mastoid reference, ICA, interpolated channels, 1-20 Hz, "
         "100 Hz, microvolts (scaled to V). Trial sample 0 is ~5 s after the target onset and ~2 s after the "
         "non-target onset (inferred); EEG and envelopes are cut to the same window by the authors.")
POST_SWITCH = "First trial after the talker switch; excluded in the paper."


class HarshaiYahav2025Adaptor:
    """
    Har-shai Yahav et al. 2025 (OSF bzean, CND): attend an audiovisual lecture (front) and ignore a competing
    audio-only lecture (left); target and non-target lectures swap at half-time. 23 subjects x 40-41 trials at
    100 Hz, already preprocessed (1-20 Hz, ICA, linked mastoids). Only the authors' 100 Hz envelopes are shipped.

    Trials are identified by the target envelope's content, not by position (`stimIdxs` is the trial position and
    four subjects miss one trial). Segment names: `L<l>s<k>` = k-th target segment of lecture l, paired with
    the non-target `L<other>e<k>` (from the end of the other lecture). Trial number = experiment trial (1 = the
    first trial, dropped by the authors; 22 = first trial after the switch, kept here). Envelopes start at trial
    sample 0 (authors' alignment). See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = os.path.join(download_dir, "dataCND")
        self.subjects = [s for s in range(1, 25) if os.path.exists(self._sub_path(s))]

    def parse(self) -> Iterable[TrialRecord]:
        segments = self._segment_table()
        for sub in self.subjects:
            stim = _read_stim(self._stim_path(sub))
            if stim["fs"] != FS:
                raise ValueError(f"subject {sub}: envelopes at {stim['fs']} Hz, expected {FS}")
            segs = [segments[_pair_digest(stim, i)] for i in range(len(stim["data"][0]))]
            # half from content: the first trial's lecture is the first-half target (condIdxs is one entry short
            # in subjects 13, 14 and 24, notes section 3)
            halves = [1 if lec == segs[0][0] else 2 for lec, _ in segs]
            if halves != sorted(halves) or any(h == 1 and k == 1 for (_, k), h in zip(segs, halves)):
                raise ValueError(f"subject {sub}: halves out of order or segment 1 (dropped) in the first half")
            cond = np.ravel(stim["condIdxs"]).tolist()
            if len(cond) == len(halves) and cond != halves:  # condIdxs checked where complete
                raise ValueError(f"subject {sub}: condIdxs disagrees with the halves from content")
            group = GROUP[segs[0][0]]
            for idx, ((lec, k), half) in enumerate(zip(segs, halves)):
                trial = k if half == 1 else 21 + k
                target, nontarget = f"{lec}s{k:02d}", f"{_other(lec)}e{k:02d}"
                description = provenance(
                    "none", "unknown (not described; OpenSesame)", NOTES + (" " + POST_SWITCH if trial == 22 else ""),
                    validation_tier="low", group=group, target_lecture=lec, target=target, nontarget=nontarget,
                    shipped_trial_index=idx,
                )
                yield TrialRecord(
                    subject=sub, session=1, trial=trial, condition=HALVES[half], ns_type="eeg",
                    stimulus=[
                        StimulusRecord("audio", target, self._env_loader(sub, 0, idx), is_attended=True,
                                       feature_name=FEATURE),
                        StimulusRecord("audio", nontarget, self._env_loader(sub, 1, idx), is_attended=False,
                                       feature_name=FEATURE),
                    ],
                    neural_data_fn=self._eeg_loader(sub, idx, description),
                )

    def _sub_path(self, sub: int) -> str:
        return os.path.join(self.root, f"dataSub{sub}.mat")

    def _stim_path(self, sub: int) -> str:
        return os.path.join(self.root, f"dataStim{sub}.mat")

    def _segment_table(self) -> dict[str, tuple]:
        """(target, non-target) envelope digest -> (lecture, k), from the groups' reference subjects (notes 3)."""
        table = {}
        for group, sub in REFERENCE_SUBJECTS.items():
            stim = _read_stim(self._stim_path(sub))
            lec = FIRST_LECTURE[group]
            design = [(lec, k) for k in range(2, 22)] + [(_other(lec), k) for k in range(1, 22)]
            if len(stim["data"][0]) != len(design):
                raise ValueError(f"reference subject {sub} does not have {len(design)} trials")
            for i, seg in enumerate(design):
                if table.setdefault(_pair_digest(stim, i), seg) != seg:
                    raise ValueError(f"reference subjects disagree on segment {seg}")
        if len(table) != 42:
            raise ValueError(f"expected 42 target segments, found {len(table)}")
        return table

    def _env_loader(self, sub: int, row: int, idx: int) -> Callable[[], dict]:
        path = self._stim_path(sub)

        def _loader() -> dict:
            env = np.asarray(_read_stim(path)["data"][row][idx], dtype=np.float32)
            return {"fs": FS, "data": env[None, :]}
        return _loader

    def _eeg_loader(self, sub: int, idx: int, description: str) -> Callable[[], BaseRaw]:
        path = self._sub_path(sub)

        def _loader() -> BaseRaw:
            eeg = _read_eeg(path)
            names = [RENAME.get(c, c) for c in eeg["chanlocs"]["labels"]]
            info = create_info(names, float(eeg["fs"]), "eeg")
            raw = RawArray(1e-6 * np.asarray(eeg["data"][idx]).T, info, verbose="ERROR")  # shipped in µV
            raw.set_montage(make_standard_montage("standard_1005"))  # template positions
            raw.info["description"] = description
            return raw
        return _loader


def _other(lec: str) -> str:
    return "L2" if lec == "L1" else "L1"


def _pair_digest(stim: dict, idx: int) -> str:
    """Digest of a trial's target and non-target envelopes (identical across subjects)."""
    pair = [np.ascontiguousarray(stim["data"][row][idx], dtype=np.float64).tobytes() for row in (0, 1)]
    return hashlib.md5(b"".join(pair)).hexdigest()


@lru_cache(maxsize=2)
def _read_stim(path: str) -> dict:
    return read_mat(path)["stim"]


@lru_cache(maxsize=1)
def _read_eeg(path: str) -> dict:
    return read_mat(path)["eeg"]


ADAPTOR = HarshaiYahav2025Adaptor
