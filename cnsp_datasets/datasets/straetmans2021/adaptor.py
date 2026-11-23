from __future__ import annotations

import csv
import os
from typing import Callable, Iterable

import mne
from mne.io import BaseRaw
from pymatreader import read_mat

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import TrialRecord

TASK = "NeuralTrackingToGo"
N_NARRATIVES = 6
BADS = {"sub-018": ["P4"]}  # broken in 4/6 narratives (notes 5)
JITTER_MS = 15  # ~SD(duration residual) / sqrt(2) plus a one-sided tail (notes 7)
STIMULUS_UNAVAILABLE = ("not shared: commercial audiobook (Kling 2009, Die Känguru-Chroniken); the release has no "
                        "audio, envelope, attended side or salient-event markers")
REFERENCE = "common reference electrode not in the data (paper: Fz, contradicted by the data; probably FCz)"
NOTES = ("Trial = narrative, from its start to its stop marker as shipped (software LSL markers sent by Presentation "
         "for Android on the phone that also played the audio; sound latency after the marker unknown). Drift not "
         "corrected: drift_ppm is the amplifier vs phone LSL clock rate (effective_srate), not the audio clock. "
         "No stimulus: see stimulus_unavailable; validation_tier null = untestable. Raw DC data.")


class Straetmans2021Adaptor:
    """
    Straetmans et al. 2021 (OpenNeuro ds003801): mobile EEG, attend one of two talkers while sitting or walking.
    20 subjects x 6 narratives (~5 min), SMARTING 24 channels at 250 Hz.

    Trial = narrative in presentation order; condition `sit` or `walk`; the narrative id is in the sidecar. The
    audio is not shared, so trials have no stimulus. See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        with open(os.path.join(download_dir, "participants.tsv"), newline="") as f:
            self.participants = list(csv.DictReader(f, delimiter="\t"))

    def parse(self) -> Iterable[TrialRecord]:
        for p in self.participants:
            sub = p["participant_id"]
            set_path = os.path.join(self.root, sub, "eeg", f"{sub}_task-{TASK}_eeg.set")
            spans = _narratives(mne.read_annotations(set_path), set_path)
            lsl = read_mat(set_path)["EEG"]["etc"]["info"]
            drift_ppm = round((lsl["effective_srate"] / float(lsl["nominal_srate"]) - 1) * 1e6, 2)
            for trial, (start, stop, narrative, cond) in enumerate(spans, 1):
                description = provenance(
                    "sw_trigger", "software (paper: Presentation for Android markers via LSL)", NOTES,
                    drift_ppm=drift_ppm, jitter_ms=JITTER_MS, validation_tier=None, drift_corrected_ppm=0.0,
                    narrative=narrative, start_marker_s=start, stop_marker_s=stop,
                    stimulus_unavailable=STIMULUS_UNAVAILABLE, sex=p["gender"], age=int(p["age"]),
                    reference=REFERENCE,
                    positions="template (EEGLAB smarting-24channels.locs)",
                )
                yield TrialRecord(
                    subject=int(sub[4:]), session=1, trial=trial, condition=cond, ns_type="eeg", stimulus=[],
                    neural_data_fn=_eeg_loader(set_path, start, stop, BADS.get(sub, []), description),
                )


def _narratives(ann: mne.Annotations, path: str) -> list[tuple[float, float, int, str]]:
    """(start s, stop s, narrative, condition) per narrative, in presentation order."""
    marks = {d: float(o) for d, o in zip(ann.description, ann.onset) if d.startswith(("start_sound", "stop_sound"))}
    starts = sorted((o, d) for d, o in marks.items() if d.startswith("start"))
    if len(marks) != 2 * N_NARRATIVES or len(starts) != N_NARRATIVES:
        raise ValueError(f"{path}: expected {N_NARRATIVES} start/stop marker pairs, got {sorted(marks)}")
    if sorted(int(d.removeprefix("start_sound").split("_")[0]) for _, d in starts) != list(range(1, N_NARRATIVES + 1)):
        raise ValueError(f"{path}: narratives {[d for _, d in starts]} are not 1..{N_NARRATIVES}")
    spans = []
    for start, d in starts:
        narrative, cond = d.removeprefix("start_sound").split("_")
        stop = marks.get(d.replace("start", "stop"))
        if stop is None or stop <= start:
            raise ValueError(f"{path}: no stop marker after {d}")
        spans.append((start, stop, int(narrative), cond))
    return spans


def _eeg_loader(path: str, start: float, stop: float, bads: list[str], description: str) -> Callable[[], BaseRaw]:
    def _loader() -> BaseRaw:
        raw = mne.io.read_raw_eeglab(path, preload=False, verbose="ERROR")  # uV -> V by MNE
        sfreq = raw.info["sfreq"]
        i0, i1 = round(start * sfreq), round(stop * sfreq)
        raw.crop(i0 / sfreq, i1 / sfreq, include_tmax=False).load_data(verbose="ERROR")
        raw.set_annotations(None)  # marker times are in the sidecar
        raw.info["bads"] = bads
        raw.info["description"] = description
        return raw
    return _loader


ADAPTOR = Straetmans2021Adaptor
