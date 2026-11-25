from __future__ import annotations

import os
from typing import Callable, Iterable

import h5py
import mne
from mne.io import BaseRaw

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import read_wav
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

ROOT = "upload_folder"
FS = 256
SCALE = 1e-6  # shipped EEG is z-scored per trial (dimensionless); stored so that 1 SD reads as 1 uV
NOTES = ("EEG and audio cut by the authors so that sample 0 of both coincides (offline cross-correlation of the "
         "ear-module microphones with the audio; paper II.B); the microphone recordings are not shipped. EEG "
         "z-scored per trial by the authors (dimensionless), stored x 1e-6. Each in-ear electrode is referenced "
         "to FT7 (lower left forehead), ground on the right earlobe. Drift not estimated.")


class Thornton2025Adaptor(BaseAdaptor):
    """
    Thornton, Mandic & Reichenbach 2025 (IEEE Access; Zenodo 10260082): dry-contact in-ear EEG (two channels,
    `left_ear` and `right_ear`, each referenced to FT7), 256 Hz, 19 subjects (sub-000..sub-018) x 16 trials of
    134-240 s. Two audiobook talkers (male, female) presented diotically over headphones; the listener attends
    the male talker in trials 1-4 and 9-12 and the female talker in trials 5-8 and 13-16 (same for everyone).

    One trial per h5 dataset `eeg/sub-NNN/trial_TT` (sub-002 trial 1 is empty and skipped). Stimuli
    `trial_TT_attended` / `trial_TT_ignored` (44.1 kHz float32 wavs as shipped). Condition `attend-<sex>`.
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self.root = os.path.join(download_dir, ROOT)

    def parse(self) -> Iterable[TrialRecord]:
        h5 = os.path.join(self.root, "eeg_data.h5")
        with h5py.File(h5, "r") as f:
            names = [c.decode() for c in f["channels"][()]]
            trials = [(s, t, f["eeg"][s][t].shape[1]) for s in sorted(f["eeg"]) for t in sorted(f["eeg"][s])]
        for sub, key, n in trials:
            if n == 0:
                continue
            trial = int(key.split("_")[1])
            story = (trial - 1) // 4 + 1
            # Attended talker from the f0 of the attended/ignored wavs (notes.md 3); the same for every subject.
            talker = "male" if story % 2 else "female"
            stimuli = [StimulusRecord("audio", f"trial_{trial:02d}_{role}",
                                      _audio_loader(os.path.join(self.root, "audio", f"trial_{trial:02d}_{role}.wav")),
                                      is_attended=role == "attended") for role in ("attended", "ignored")]
            description = provenance(
                "stimtrack_xcorr", "hardware (authors' microphone-to-audio cross-correlation; paper II.B)", NOTES,
                validation_tier="low", story=story, attended_talker=talker,
                reference="FT7", ground="right earlobe", units_as_shipped="z-scored per trial (dimensionless)")
            yield TrialRecord(
                subject=int(sub.split("-")[1]), session=1, trial=trial, condition=f"attend-{talker}",
                ns_type="eeg", stimulus=stimuli,
                neural_data_fn=_eeg_loader(h5, f"eeg/{sub}/{key}", names, description),
            )


def _eeg_loader(h5: str, key: str, names: list[str], description: str) -> Callable[[], BaseRaw]:
    def _loader() -> BaseRaw:
        with h5py.File(h5, "r") as f:
            data = f[key][()] * SCALE
        raw = mne.io.RawArray(data, mne.create_info(names, FS, "eeg"), verbose="ERROR")
        raw.info["description"] = description
        return raw
    return _loader


def _audio_loader(path: str) -> Callable[[], dict]:
    def _loader() -> dict:
        x, fs = read_wav(path)  # float32 as stored
        if x.shape[0] != 1:
            raise ValueError(f"{path}: expected mono, got {x.shape[0]} channels")
        return {"fs": fs, "data": x}
    return _loader


ADAPTOR = Thornton2025Adaptor
