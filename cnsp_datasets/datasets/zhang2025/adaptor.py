from __future__ import annotations

import csv
import json
import os
import pickle
from typing import Callable, Iterable

import mne
import numpy as np
import soundfile as sf
from mne.io import BaseRaw
from pymatreader import read_mat

from cnsp_datasets.datasets.zhang2025.trialinfo import read_trial_info, stem
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS, N = 125, 3750  # 30-s trials at 125 Hz
MAPPING = os.path.join(os.path.dirname(__file__), "mapping.csv")
BADS_JSON = os.path.join(os.path.dirname(__file__), "bads.json")
CHANNELS = ["R1", "R2", "R3", "R4", "R7", "R8", "R9", "R10", "L10", "L9", "L8", "L7", "L4", "L3", "L2", "L1"]
TASKS = {1: "sustained", 2: "cued-switch", 3: "free-switch", 4: "stop-attending", 5: "switch-to-new",
         6: "switch-on-silence", 7: "ignore-new"}
# Event times (s from trial onset) as annotations: the switch cue (tasks 2-4), the onset of the third talker
# (tasks 5, 7); task 6 stores the end of the attended talker as interfere_time too (named attended_silent).
EVENTS = {"switch_time": "switch_cue", "interfere_time": "interferer_onset"}
TRIGGER = ("hardware (screen photodiode, separate LSL stream; the authors' cut lies a fixed 1.02 s after its first "
           "rise, paper II.A/C); sound latency relative to the flash unknown (no audio copy)")
NOTES = ("Raw OpenBCI EEG (uV -> V), original reference (unused left-ear cEEGrid electrode). Trial = the 30-s segment "
         "of the trialinfo recording that the authors cut for their shipped (preprocessed) trial, located by EEG "
         "cross-correlation (mapping.csv); that cut lies 1.02 s (IQR 1.01-1.03 s) after the first photodiode rise "
         "(paper II.C: cut at the trigger). Stimuli are the dry 30-s wavs played from the loudspeakers (attended "
         "first); onsets of an appearing talker (task 5, 7) or the attended talker's silence (task 6) are "
         "annotations, not applied to the audio. Bad (dead) channels per participant in info['bads'] (bads.json).")


class Zhang2025Adaptor:
    """
    Zhang et al. 2025 (Zenodo 17393865, NJU cEEGrid dataset): two cEEGrids (8 channels per ear, R1-R10/L1-L10
    subset), OpenBCI Cyton+Daisy at 125 Hz, 30-s trials, three (task 6: two) Mandarin news talkers from loudspeakers
    at +-60/+-120/0 deg (subject 1: +-30/+-90/0), seven attention tasks. Yields the 3287 trials of 66 of the 79
    released subjects that have a raw recording (notes.md 3).

    Trial ids are those of the authors' shipped trials (`dataset-001-subject-SSS-trial-TTT`,
    `meta/publish_metadata.pkl`). The raw EEG comes from `trialinfo/*.mat`, whose file names do not follow the
    subject and trial numbers; `mapping.csv` gives the file and the start sample of every trial.
    Condition `task<k>-<name>`; per-second attended direction (`label`) and task timing in the provenance.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        with open(os.path.join(download_dir, "meta", "publish_metadata.pkl"), "rb") as f:
            self.meta = _NumpyUnpickler(f).load()
        if any([c["name"] for c in m["channel_infos"].values()] != CHANNELS for m in self.meta.values()):
            raise ValueError("publish_metadata.pkl: unexpected channel list")
        with open(MAPPING, newline="") as f:
            self.mapping = list(csv.DictReader(f))
        with open(BADS_JSON) as f:
            self.bads = json.load(f)

    def parse(self) -> Iterable[TrialRecord]:
        for row in self.mapping:
            sub, trial = int(row["subject"]), int(row["trial"])
            meta = self.meta[f"dataset-001-subject-{sub:03d}-trial-{trial:03d}"]
            mat = os.path.join(self.root, "trialinfo", row["file"])
            info = read_trial_info(mat)
            task = meta["task_id"]
            if info["class"] != f"task{task}info":
                raise ValueError(f"{mat}: {info['class']} does not match task {task}")
            n_spk = int(info["num_speaker"].item())
            att = int(info["attended_speaker"].item()) - 1
            order = [att] + [i for i in range(n_spk) if i != att]
            stems = [stem(info["audio_paths"][i]) for i in order]
            dirs = np.ravel(info["speaker_directions"])
            events = {}
            for key, name in EVENTS.items():
                if key in info:
                    events["attended_silent" if task == 6 else name] = float(info[key].item())
            switch_to = stem(info["audio_paths"][int(info["switch_speaker"].item()) - 1]) if task == 2 else None
            description = provenance(
                "onset_only", TRIGGER, NOTES, validation_tier="low", task=task, task_name=TASKS[task],
                speaker_directions_deg=[float(dirs[i]) for i in order], attended_direction_deg=float(dirs[att]),
                switch_to=switch_to, events_s=events, label_per_second=[int(v) for v in meta["label"]],
                source_file=row["file"], source_start_sample=int(row["start"]), match_r=float(row["r"]),
                units_as_shipped="µV (OpenBCI); scaled to V", reference="unused left-ear cEEGrid electrode (OpenBCI "
                "SRB)", external_sensors={})
            yield TrialRecord(
                subject=sub, session=1, trial=trial, condition=f"task{task}-{TASKS[task]}", ns_type="eeg",
                stimulus=[StimulusRecord("audio", s, _audio_loader(os.path.join(self.root, "stimuli", f"{s}.wav")),
                                         is_attended=k == 0) for k, s in enumerate(stems)],
                neural_data_fn=_eeg_loader(mat, int(row["start"]), self.bads[f"{sub:03d}"], events, description),
            )


class _NumpyUnpickler(pickle.Unpickler):
    """The metadata pickle holds dicts of numpy arrays; refuse anything else (the file is untrusted)."""

    def find_class(self, module, name):
        if (module.replace("numpy.core", "numpy._core"), name) not in {
                ("numpy._core.multiarray", "_reconstruct"), ("numpy", "ndarray"), ("numpy", "dtype")}:
            raise pickle.UnpicklingError(f"{module}.{name} not allowed")
        return super().find_class(module, name)


def _eeg_loader(mat: str, start: int, bads: list[str], events: dict, description: str) -> Callable[[], BaseRaw]:
    def _loader() -> BaseRaw:
        eeg = read_mat(mat, variable_names=["eeg"])["eeg"][start:start + N].T * 1e-6
        if eeg.shape[1] != N:
            raise ValueError(f"{mat}: only {eeg.shape[1]} samples from {start}")
        raw = mne.io.RawArray(eeg, mne.create_info(CHANNELS, FS, "eeg"), verbose="ERROR")
        raw.info["bads"] = list(bads)
        raw.set_annotations(mne.Annotations(list(events.values()), 0.0, list(events)))
        raw.info["description"] = description
        return raw
    return _loader


def _audio_loader(path: str) -> Callable[[], dict]:
    def _loader() -> dict:
        x, fs = sf.read(path, dtype="float32")
        if x.ndim != 1:
            raise ValueError(f"{path}: expected mono")
        return {"fs": int(fs), "data": x[None, :]}
    return _loader


ADAPTOR = Zhang2025Adaptor
