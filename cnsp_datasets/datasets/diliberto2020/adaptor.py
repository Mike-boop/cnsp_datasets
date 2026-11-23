from __future__ import annotations

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

ROOT = "diliBach_4dryad_CND"
EEG_FS = 512
STIM_FS = 64
PAD = 512  # leading padding samples; the stimulus starts at EEG sample PAD + 1 (readme)
LSB = 31.25e-9  # shipped values are BioSemi ADC counts (notes section 5)
FEATURES = {0: "envelope", 1: "note_onsets", 2: "note_pitch"}  # rows of stim.data
RENAME = {"T7 (T3)": "T7", "T8 (T4)": "T8", "Iz (inion)": "Iz", "Afz": "AFz"}
MASTOIDS = ["M1", "M2"]  # extChan columns: left, right (readme)
BADS = {8: ["C4"], 12: ["Fpz"]}  # noise without EEG, notes section 5
TRIGGER = "unknown (Presentation; trigger route not documented, triggers not shared)"
NOTES = ("CND release: raw BioSemi EEG at 512 Hz (ADC counts scaled by 31.25 nV to V; CMS/DRL, no reference, no "
         "filter). Trials cut by the authors; onset = EEG sample 513 as documented, the leading 1 s padding is "
         "dropped and ~1 s of EEG after the stimulus kept. Presentation order not shipped: trial = shipped index. "
         "Stimuli = authors' 64 Hz features (no audio). Drift not measurable.")


class DiLiberto2020Adaptor:
    """
    Di Liberto et al. 2020 (Dryad g1jwstqmh, CND): 20 subjects (1-10 non-musicians, 11-20 pianists) x 30 trials =
    10 MIDI-synthesised Bach piano pieces x 3 repetitions. 64 BioSemi channels + mastoids at 512 Hz. Stimulus
    `piece<kk>` = the authors' 64 Hz envelope (plus note-onset features with `note_features=True`), starting at
    trial sample 0. Trial = shipped index + 1 (presentation order not shipped). See notes.md.
    """

    def __init__(self, download_dir: str, note_features: bool = False):
        self.root = os.path.join(download_dir, ROOT)
        self.features = FEATURES if note_features else {0: FEATURES[0]}
        self.subjects = [s for s in range(1, 21) if os.path.exists(self._path(f"Sub{s}"))]

    def parse(self) -> Iterable[TrialRecord]:
        stim = read_mat(self._path("Stim"))["stim"]
        if stim["fs"] != STIM_FS:
            raise ValueError(f"stimuli at {stim['fs']} Hz, expected {STIM_FS}")
        pieces = np.asarray(stim["stimIdxs"], int)
        reps = np.asarray(stim["repIdxs"], int)
        for sub in self.subjects:
            for idx, (piece, rep) in enumerate(zip(pieces, reps)):
                name, n_stim = f"piece{piece:02d}", len(stim["data"][0][idx])
                description = provenance(
                    "onset_only", TRIGGER, NOTES, validation_tier="low", piece=int(piece), repetition=int(rep),
                    group="musician" if sub > 10 else "non-musician", shipped_trial_index=idx,
                    stimulus_samples=n_stim,
                )
                stimuli = [StimulusRecord("audio", name, _feature_loader(stim["data"][row][idx]), is_attended=True,
                                          feature_name=feature) for row, feature in self.features.items()]
                yield TrialRecord(
                    subject=sub, session=1, trial=idx + 1, condition="listening", ns_type="eeg", stimulus=stimuli,
                    neural_data_fn=self._eeg_loader(sub, idx, n_stim, description),
                )

    def _path(self, kind: str) -> str:
        return os.path.join(self.root, f"data{kind}.mat")

    def _eeg_loader(self, sub: int, idx: int, stim_len: int, description: str) -> Callable[[], BaseRaw]:
        """
        Loader of one trial from the stimulus onset: 64 EEG channels + mastoids in V, original reference. Checks fs,
        padding and that the cropped EEG covers the stimulus (the only guard on the crop).
        """
        path = self._path(f"Sub{sub}")

        def _loader() -> BaseRaw:
            eeg = _read_eeg(path)
            if eeg["fs"] != EEG_FS or eeg["paddingStartSample"] != PAD:
                raise ValueError(f"subject {sub}: fs {eeg['fs']}, padding {eeg['paddingStartSample']}")
            data = np.concatenate([eeg["data"][idx], eeg["extChan"]["data"][idx]], axis=1)[PAD:].T
            if data.shape[1] < stim_len * EEG_FS // STIM_FS:
                raise ValueError(f"subject {sub}, trial {idx}: EEG shorter than the stimulus")
            labels = [RENAME.get(ch, ch) for ch in eeg["chanlocs"]["labels"]]
            info = create_info(labels + MASTOIDS, float(EEG_FS), ["eeg"] * len(labels) + ["misc"] * 2)
            raw = RawArray(LSB * data, info, verbose="ERROR")
            raw.set_montage(make_standard_montage("biosemi64"))  # template positions
            raw.info["bads"] = list(BADS.get(sub, []))
            raw.info["description"] = description
            return raw
        return _loader


def _feature_loader(x) -> Callable[[], dict]:
    """Loader of one 64 Hz feature as a 1 x n float32 array."""
    data = np.asarray(x, dtype=np.float32)[None, :]
    return lambda: {"fs": STIM_FS, "data": data}


@lru_cache(maxsize=1)
def _read_eeg(path: str) -> dict:
    """One subject's CND `eeg` struct; cached because a subject's trials are loaded one after another."""
    return read_mat(path)["eeg"]


ADAPTOR = DiLiberto2020Adaptor
