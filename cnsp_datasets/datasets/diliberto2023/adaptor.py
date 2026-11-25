from __future__ import annotations

import os
from functools import lru_cache
from typing import Callable, Iterable

import numpy as np
from mne import create_info
from mne.channels import make_dig_montage
from mne.io import BaseRaw, RawArray
from pymatreader import read_mat

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

ROOT = "eegCND"
FS = 50
N_RHYMES = 18
UV = 1e-6  # shipped in µV (assumed, notes section 5)
# age folder -> (session, subject offset); infants dataSub<k> are the same child at every age (notes section 3)
GROUPS = {"4mo": (1, 0), "7mo": (2, 0), "11mo": (3, 0), "adults": (1, 100)}
N_SUBJECTS = {"4mo": 47, "7mo": 47, "11mo": 47, "adults": 17}
MASTOIDS = ("E29", "E47")  # extChan columns: left, right (EEGLAB Y > 0 = left)
TRIGGER = "unknown (paper: synchronisation triggers, route not documented; trials cut by the authors)"
REFERENCE = "linked mastoids (E29, E47), as shipped; M1/M2 stored in the same reference"
LICENCE = "none stated ('copyright 2021', public OSF project mdnwg)"
NOTES = ("REPETITION-AVERAGED: each trial is the authors' average of the 2-3 presentations of one rhyme, not a single "
         "presentation. Shipped preprocessed (CND, 0.1-8 Hz copy): 0.1-8 Hz zero-phase Butterworth, 50 Hz, ASR, noisy "
         "channels interpolated (which ones unknown), linked-mastoid reference; µV (assumed) scaled to V, absolute "
         "amplitudes unreliable. Adults' 128 channels were spline-interpolated to the infant 64-channel layout. "
         "Trials cut by the authors at the stimulus onset to the stimulus length (EEG sample 0 = feature sample 0); "
         "no audio shipped, stimuli are the authors' 50 Hz features. Drift not measurable.")
# dataStim rows -> feature_name; row 3 (visual motion) is not standardised
FEATURES = {0: "spectrogram", 1: "envelope_derivative", 2: "phonetic_features"}


class DiLiberto2023Adaptor(BaseAdaptor):
    """
    Di Liberto et al. 2023 (OSF mdnwg, CND): 47 infants at 4, 7 and 11 months (subjects 1-47, sessions 1-3) and 17
    adults (subjects 101-117) watch 18 audio-visual nursery rhymes. 58 EGI channels at 50 Hz, preprocessed and
    averaged over the repetitions of each rhyme by the authors: one trial per rhyme. Stimuli `rhymeNN` are the
    shipped 50 Hz features: `envelope` (sum of the 8 spectrogram bands, the paper's definition), `spectrogram`,
    `envelope_derivative` and the 19 annotation-derived `phonetic_features` (`phonetic_features=False` drops
    them). Empty trials are skipped. See notes.md.
    """

    def __init__(self, download_dir: str, phonetic_features: bool = True):
        super().__init__(download_dir)
        self.root = os.path.join(download_dir, ROOT)
        self.rows = [0, 1, 2] if phonetic_features else [0, 1]

    def parse(self) -> Iterable[TrialRecord]:
        stim = read_mat(os.path.join(self.root, "dataStim.mat"))["stim"]
        if (stim["fs"] != FS or list(stim["stimIdxs"]) != list(range(1, N_RHYMES + 1))
                or list(stim["names"][:3]) != ["Sgram", "Envelope derivative", "Phonetic Features (step)"]):
            raise ValueError("unexpected dataStim layout")
        stimuli = [self._stimuli(stim, idx) for idx in range(N_RHYMES)]
        for age, (session, offset) in GROUPS.items():
            for k in range(1, N_SUBJECTS[age] + 1):
                path = os.path.join(self.root, age, f"dataSub{k}_pre01_8Hz.mat")
                for idx in np.flatnonzero(_read_eeg(path)["nonemptyTrials"]):
                    description = provenance(
                        "onset_only", TRIGGER, NOTES, validation_tier="low", age_group=age,
                        original_subject=f"{age}/dataSub{k}", rhyme=int(idx) + 1, repetition_averaged=True,
                        reference=REFERENCE, licence=LICENCE, units_as_shipped="uV (assumed)",
                    )
                    yield TrialRecord(
                        subject=offset + k, session=session, trial=int(idx) + 1, condition=age, ns_type="eeg",
                        stimulus=stimuli[idx], neural_data_fn=_eeg_loader(path, int(idx), description),
                    )

    def _stimuli(self, stim: dict, idx: int) -> list[StimulusRecord]:
        """The 50 Hz features of rhyme idx + 1; the envelope is the sum of the spectrogram bands."""
        name, details = f"rhyme{idx + 1:02d}", dict(stim["additionalDetails"])  # list of [name, value] pairs
        sgram = np.asarray(stim["data"][0][idx], np.float32).T
        extra = {0: {"band_edges_hz": np.asarray(details["Sgram Frequency-bands"])},
                 2: {"labels": np.asarray(details["Phonetic feature labels"])}}
        records = [StimulusRecord("audio", name, _const({"fs": FS, "data": sgram.sum(0, keepdims=True)}),
                                  is_attended=True, feature_name="envelope")]
        for row in self.rows:
            data = np.asarray(stim["data"][row][idx], np.float32).reshape(sgram.shape[1], -1).T
            records.append(StimulusRecord("audio", name, _const({"fs": FS, "data": data, **extra.get(row, {})}),
                                          is_attended=True, feature_name=FEATURES[row]))
        return records


def _const(value: dict) -> Callable[[], dict]:
    return lambda: value


def _eeg_loader(path: str, idx: int, description: str) -> Callable[[], BaseRaw]:
    """
    Loader of one trial: 58 EEG channels + M1/M2 in V, linked-mastoid reference. The shipped mastoids are in an
    earlier reference, so M1 = (E29 - E47) / 2 and M2 = -M1 put them in the EEG's reference (notes section 5).
    """
    def _loader() -> BaseRaw:
        eeg = _read_eeg(path)
        if eeg["fs"] != FS or eeg["reRef"] != "Mastoids" or eeg["extChan"]["chanlocs"]["labels"] != list(MASTOIDS):
            raise ValueError(f"{path}: unexpected CND header")
        x, m = np.asarray(eeg["data"][idx]), np.asarray(eeg["extChan"]["data"][idx])
        half = (m[:, 0] - m[:, 1])[:, None] / 2
        locs = eeg["chanlocs"]
        info = create_info(locs["labels"] + ["M1", "M2"], float(FS), ["eeg"] * len(locs["labels"]) + ["misc"] * 2)
        raw = RawArray(UV * np.concatenate([x, half, -half], axis=1).T, info, verbose="ERROR")
        # EEGLAB axes (X nose, Y left, Z up, cm) -> MNE head coordinates (x right, y nose, z up, m)
        pos = np.c_[-np.asarray(locs["Y"]), locs["X"], locs["Z"]] / 100
        raw.set_montage(make_dig_montage(dict(zip(locs["labels"], pos)), coord_frame="head"))
        raw.info["description"] = description
        return raw
    return _loader


@lru_cache(maxsize=1)
def _read_eeg(path: str) -> dict:
    """One subject-age CND `eeg` struct; cached because its trials are loaded one after another."""
    return read_mat(path)["eeg"]


ADAPTOR = DiLiberto2023Adaptor
