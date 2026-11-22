from __future__ import annotations

import csv
import math
import os
from typing import Callable, Iterable

import mne
import numpy as np
from mne.io import BaseRaw
from pymatreader import read_mat
from scipy.io import wavfile

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

TASK = "AttendedSpeakerParadigmOwnName"
AUDIO_DIR = os.path.join("stimuli_v1.1.1", "stimuli")  # holtze2021_audio (v1.1.1; removed upstream later)
AUDIO_FS, ENV_FS = 32000, 500
ENVELOPE = "onset_envelope_authors"
SIDES = ("left", "right")  # wav channel 0 = story 1 = sig1 = left, channel 1 = story 2 = sig2 = right (notes 4)
NAME_EVENTS = {"O": "omni", "B": "beam"}
NOTES = ("Onset = StartTrigger as shipped (LSL marker stream, the authors' constant 102 ms marker delay already "
         "applied); trial = block, EEG as long as the longer story. Drift not corrected (pooled -5.6 ppm, not "
         "resolvable per subject); block-onset jitter ~7 ms SD (from the EEG). Original nose reference. The audio "
         "is the dry narratives (no HRIR, no beamformer, no names: the ignored story still has the replaced verbs); "
         "own_name annotations mark the name onsets (duration = name length).")


class Holtze2021Adaptor:
    """
    Holtze et al. 2021 (OpenNeuro ds003516): attend one of two talkers (left/right, the same side throughout);
    the participant's own name is inserted 10 times per block in the ignored talker in blocks 2-5.
    25 subjects x 5 blocks of ~10 min, BrainAmp 500 Hz, 47 scalp channels + E19/E20 (EOG), nose reference.

    Trial = block b (onset = b-th StartTrigger). Stimuli: `story1_block<b>` (left) and `story2_block<b>` (right),
    each as the matching channel of the v1.1.1 `Block_<b>_32k.wav` (`audio`, 32 kHz) and the authors' onset
    envelope `sig<s>_<b>.mat` (`onset_envelope_authors`, 500 Hz). Condition `attend-<side>-<omni-noname|omni|beam>`.
    Name onsets are `own_name` annotations. See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        with open(os.path.join(download_dir, "participants.tsv"), newline="") as f:
            self.participants = list(csv.DictReader(f, delimiter="\t"))
        quest = read_mat(os.path.join(download_dir, "stimuli", "name_quest.mat"))["name_quest"]
        self.name_len = dict(zip(np.ravel(quest["subj"]).astype(int), np.ravel(quest["len"]) / 1000))
        self.duration = {b: _block_duration(download_dir, b) for b in range(1, 6)}

    def parse(self) -> Iterable[TrialRecord]:
        for p in self.participants:
            sub, side = int(p["participant_id"][4:]), p["attended_ch"]
            set_path = os.path.join(self.root, p["participant_id"], "eeg", f"{p['participant_id']}_task-{TASK}_eeg.set")
            ann = mne.io.read_raw_eeglab(set_path, preload=False, verbose="ERROR").annotations
            starts = ann.onset[ann.description == "StartTrigger"]
            if len(starts) != 5:
                raise ValueError(f"{set_path}: {len(starts)} StartTrigger events")
            for b, start in enumerate(starts, 1):
                inside = (ann.onset > start) & (ann.onset < start + self.duration[b])
                names = ann.onset[inside & np.isin(ann.description, list(NAME_EVENTS.values()))] - start
                cond = "omni-noname" if b == 1 else NAME_EVENTS[p["cond_order"][b - 2]]
                if len(names) != (0 if b == 1 else 10):
                    raise ValueError(f"{set_path}: block {b} has {len(names)} name events")
                if b > 1 and set(ann.description[inside]) - {cond}:
                    raise ValueError(f"{set_path}: block {b} events {set(ann.description[inside])} do not match "
                                     f"cond_order {p['cond_order']}")
                description = provenance(
                    "sw_trigger", "software (inferred: LSL marker stream; paper, XDF header)", NOTES, jitter_ms=7,
                    validation_tier="low",
                    block=b, condition_order=p["cond_order"], attended_side=side,
                    incl=p["incl"] == "incl", sex=p["gender"], age=int(p["age"]),
                    start_trigger_s=float(start), name_length_s=self.name_len[sub],
                    reference="nose", eog=["E19", "E20"], positions="template (EEGLAB chanlocs)",
                )
                stimuli = []
                for s, stim_side in enumerate(SIDES, 1):
                    name, attended = f"story{s}_block{b}", stim_side == side
                    stimuli += [StimulusRecord("audio", name, _audio_loader(_wav(self.root, b), s - 1),
                                               is_attended=attended, feature_name="audio"),
                                StimulusRecord("audio", name, _env_loader(_env(self.root, s, b), s),
                                               is_attended=attended, feature_name=ENVELOPE)]
                yield TrialRecord(
                    subject=sub, session=1, trial=b, condition=f"attend-{side}-{cond}", ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=_eeg_loader(set_path, start, self.duration[b], names, self.name_len[sub],
                                               description),
                )


def _wav(root: str, b: int) -> str:
    return os.path.join(root, AUDIO_DIR, f"Block_{b}_32k.wav")


def _env(root: str, s: int, b: int) -> str:
    return os.path.join(root, "stimuli", f"sig{s}_{b}.mat")


def _block_duration(root: str, b: int) -> float:
    """Block duration (s): the envelope length (= wav duration rounded up to whole 500 Hz samples)."""
    n_env = {len(_read_env(_env(root, s, b), s)) for s in (1, 2)}
    n_wav = len(wavfile.read(_wav(root, b), mmap=True)[1])
    if n_env != {math.ceil(n_wav * ENV_FS / AUDIO_FS)}:
        raise ValueError(f"block {b}: envelope lengths {n_env} do not match the wav ({n_wav} samples)")
    return n_env.pop() / ENV_FS


def _eeg_loader(path: str, start: float, duration: float, names: np.ndarray, name_len: float,
                description: str) -> Callable[[], BaseRaw]:
    def _loader() -> BaseRaw:
        raw = mne.io.read_raw_eeglab(path, preload=False, verbose="ERROR")  # uV -> V by MNE
        sfreq = raw.info["sfreq"]
        i0, n = int(round(start * sfreq)), int(round(duration * sfreq))
        raw.crop(i0 / sfreq, (i0 + n) / sfreq, include_tmax=False).load_data(verbose="ERROR")
        raw.set_annotations(mne.Annotations(names, name_len, "own_name"))
        with raw.info._unlock():
            raw.info["highpass"] = 0.0159  # recording filter (eeg.json)
        raw.info["description"] = description
        return raw
    return _loader


def _audio_loader(path: str, channel: int) -> Callable[[], dict]:
    def _loader() -> dict:
        fs, x = wavfile.read(path, mmap=True)
        if fs != AUDIO_FS or x.dtype != np.int16 or x.shape[1] != 2:
            raise ValueError(f"{path}: expected 32 kHz stereo int16")
        return {"fs": fs, "data": (x[:, channel] / 32768.0).astype(np.float32)[None, :]}
    return _loader


def _env_loader(path: str, s: int) -> Callable[[], dict]:
    return lambda: {"fs": ENV_FS, "data": _read_env(path, s)[None, :]}


def _read_env(path: str, s: int) -> np.ndarray:
    return np.ravel(read_mat(path)[f"sig{s}"])


ADAPTOR = Holtze2021Adaptor
