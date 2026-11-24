from __future__ import annotations

import glob
import os
from functools import lru_cache
from typing import Callable, Iterable

import soundfile as sf
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray
from pymatreader import read_mat

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 500
AUDIO_FS = 44100
N_CHANNELS = 31
# (stimIdxs, trial length in samples) -> story; index 3 is "The Golden Duck" or, for the first children, the wombats.
# The length alone identifies the story; stimIdxs is a cross-check (a mismatch raises KeyError)
STORIES = {(1, 146088): "HG_audio", (2, 91114): "BW_audio", (3, 168838): "GD_audio", (3, 150395): "WB_audio"}
TRIGGER = "software (paper: Presentation event marker at each story start; epoched by the authors)"
REFERENCE = "average of the 31 shipped channels (re-referenced by the authors; online reference FCz not restored)"
LICENCE = "none stated (public OSF project c3agw)"
NOTES = ("Shipped preprocessed by the authors (CND, MNE 1.5): 1-15 Hz zero-phase band-pass, bad channels interpolated "
         "(0-5 per recording), 1-3 ocular ICA components removed, average reference; 500 Hz (recorded at 500 Hz or at "
         "50 kHz and downsampled by the authors), microvolts scaled to V. Trials cut by the authors at the story-start "
         "marker to the story length: EEG sample 0 = wav sample 0. Presentation order unknown (trial = shipped index). "
         "Channel positions are standard_1020 templates.")


class Rogachev2024Adaptor:
    """
    Rogachev & Sysoeva 2024 (OSF c3agw, CND): 52 Russian-speaking children aged 3-8 hear three stories (hedgehogs,
    "Brick and Wax", "The Golden Duck", or the wombat story instead of the last for the first 7 children); 8 children
    heard only the first two. 32-ch actiCHamp, shipped as 31 channels at 500 Hz. Stories are told apart by stimIdxs
    and the trial length, which equals the wav length (notes.md). Trial number = shipped index (presentation order
    unknown).
    """

    def __init__(self, download_dir: str):
        self.root = os.path.join(download_dir, "dataCND")
        self.audio_dir = os.path.join(download_dir, "stimuli")
        files = glob.glob(f"{self.root}/dataParticipant_NP*.mat")
        self.subjects = sorted(os.path.basename(f).removeprefix("dataParticipant_").removesuffix(".mat") for f in files)

    def parse(self) -> Iterable[TrialRecord]:
        for sid in self.subjects:
            stim = read_mat(os.path.join(self.root, f"dataStim_{sid}.mat"))["stim"]
            path = os.path.join(self.root, f"dataParticipant_{sid}.mat")
            for idx, (k, x) in enumerate(zip(stim["stimIdxs"], _read_eeg(path)["data"], strict=True)):
                name = STORIES[(int(k), len(x))]
                description = provenance("onset_only", TRIGGER, NOTES, validation_tier="low", subject_id=sid,
                                         reference=REFERENCE, licence=LICENCE, shipped_trial_index=idx)
                yield TrialRecord(
                    subject=int(sid[2:]), session=1, trial=idx + 1, condition="story", ns_type="eeg",
                    stimulus=StimulusRecord("audio", name, _audio_loader(os.path.join(self.audio_dir, f"{name}.wav")),
                                            is_attended=True),
                    neural_data_fn=_eeg_loader(path, idx, description),
                )


def _audio_loader(path: str) -> Callable[[], dict]:
    """44.1 kHz stereo wav as 2 x n float32, as shipped."""
    def _loader() -> dict:
        x, fs = sf.read(path, dtype="float32")
        if fs != AUDIO_FS:
            raise ValueError(f"{path}: expected {AUDIO_FS} Hz")
        return {"fs": AUDIO_FS, "data": x.T}
    return _loader


def _eeg_loader(path: str, idx: int, description: str) -> Callable[[], BaseRaw]:
    """Loader of one trial: 31 EEG channels at 500 Hz in V, average reference."""
    def _loader() -> BaseRaw:
        eeg = _read_eeg(path)
        info = create_info(eeg["chanlocs"]["labels"], float(FS), "eeg")
        raw = RawArray(1e-6 * eeg["data"][idx].T, info, verbose="ERROR")  # shipped in µV
        raw.set_montage(make_standard_montage("standard_1020"))  # template positions
        raw.info["description"] = description
        return raw
    return _loader


@lru_cache(maxsize=1)
def _read_eeg(path: str) -> dict:
    """CND `eeg` struct of one child; checks 500 Hz and 31 channels."""
    eeg = read_mat(path)["eeg"]
    if eeg["fs"] != FS or eeg["data"][0].shape[1] != N_CHANNELS:
        raise ValueError(f"{path}: expected {N_CHANNELS} channels at {FS} Hz")
    return eeg


ADAPTOR = Rogachev2024Adaptor
