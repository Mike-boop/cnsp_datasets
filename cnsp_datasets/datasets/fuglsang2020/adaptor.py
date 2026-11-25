from __future__ import annotations

import csv
import os
import re
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
from mne.channels import make_standard_montage
from pymatreader import read_mat

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import mark_bads
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 512  # BioSemi rate and envelope rate, kept
MONTAGE = make_standard_montage("biosemi64")
# channels.tsv description of the EXG channels -> (name, type, montage file)
EXG = {"left_mastoid": ("M1", "misc", "eeg"), "right_mastoid": ("M2", "misc", "eeg"),
       **{f"{side}_eog_{k}": (name, "eog", "eeg") for side, s in (("left", "L"), ("right", "R"))
          for k, name in ((1, f"VEOG_{s}_low"), (2, f"HEOG_{s}"), (3, f"VEOG_{s}_high"))},
       **{f"{side}_eareeg_{k}": (f"E{side[0].upper()}{k}", "eeg", "ear-eeg")
          for side in ("left", "right") for k in (1, 2, 3)}}
# (participant, ns_type) -> bad channels: 45-200 Hz SD within trials > 5x the montage median (a recurring P2/PO4/POz
# fault), flat (1-40 Hz SD < 0.5 uV: right EOG of sub-010/034), near-dead ear channels (45-200 Hz < 0.2x), sub-039 CP6
# (1-40 Hz 5.8x, not blinks); notes.md 5b
BADS = {(1, 'eeg'): ['POz'], (2, 'eeg'): ['P2'], (3, 'eeg'): ['P2', 'PO4'], (4, 'eeg'): ['P2', 'POz'],
        (5, 'ear-eeg'): ['ER3'], (7, 'eeg'): ['P2', 'PO4', 'POz'], (8, 'ear-eeg'): ['EL3', 'ER2'],
        (10, 'eeg'): ['HEOG_R', 'P2', 'VEOG_R_high', 'VEOG_R_low'], (12, 'eeg'): ['PO4'],
        (14, 'eeg'): ['C6', 'F8', 'FC6', 'FT8', 'PO4'], (16, 'eeg'): ['P2'], (17, 'eeg'): ['FC6', 'PO4'],
        (18, 'eeg'): ['Fp1'], (21, 'ear-eeg'): ['EL2', 'ER3'], (21, 'eeg'): ['PO4', 'POz', 'Pz'],
        (22, 'ear-eeg'): ['EL1'], (22, 'eeg'): ['P2', 'PO4'], (24, 'ear-eeg'): ['ER2', 'ER3'],
        (24, 'eeg'): ['P2', 'PO4'], (25, 'eeg'): ['P2', 'PO4'], (26, 'eeg'): ['P2'], (27, 'eeg'): ['PO4', 'POz'],
        (28, 'eeg'): ['P2', 'POz'], (29, 'eeg'): ['P2'], (30, 'ear-eeg'): ['EL1', 'ER3'], (30, 'eeg'): ['P2'],
        (31, 'eeg'): ['P2'], (33, 'eeg'): ['C2', 'P2', 'P4', 'P6', 'P8', 'PO4', 'Pz'],
        (34, 'eeg'): ['HEOG_R', 'P2', 'POz', 'VEOG_R_high', 'VEOG_R_low'], (35, 'eeg'): ['O2', 'PO4'],
        (36, 'eeg'): ['AF7', 'P2', 'PO4'], (38, 'eeg'): ['P2'], (39, 'eeg'): ['CP6', 'POz'], (40, 'eeg'): ['PO4'],
        (42, 'eeg'): ['P2'], (43, 'eeg'): ['P2']}
# validation.json per montage (notes.md 9): scalp low + mlr pass (brainstem: no wave V, envelope at 512 Hz); ear low
VALIDATION_TIER = {"eeg": "mlr", "ear-eeg": "low"}
TRIGGER_TYPE = ("unknown (BioSemi Status triggers; how the stimulus PC generated them relative to the sound is not "
                "documented)")
NOTES = ("Trial = target-onset trigger (Status, = events.tsv sample - 1) for the length of the shipped target "
         "envelope; the trial-end trigger comes 5-7 samples (~12 ms) before that end in every trial, constant over "
         "50-57 s trials (no drift). No audio is shipped: stimuli are the authors' envelopes (gammatone, 24 bands "
         "100-4000 Hz, |.|^0.3, 512 Hz; derivatives/README), as presented ('envelope': CamEQ-equalised for "
         "hearing-impaired listeners) and, for them, without CamEQ ('envelope-no-cameq', used in the paper). Masker "
         "(distractor) onsets are jittered per listener and trial (uniform 3-5 s after the target; shipped t[0] = "
         "the masker trigger): each masker is stored per listener and trial with that delay built in (zero-padded), "
         "so t = 0 is the target onset for every stream (`masker_delay_s`); maskers run past the trial end (cut at "
         "the point of use). Audio segments shared across listeners: `target_segment`/`masker_segment` "
         "(shared_segments.csv, None = heard by this listener only; envelopes of one segment differ slightly "
         "between listeners: loudness matching, side, CamEQ). ER-3 insert earphones (tube delay not corrected).")


class Fuglsang2020Adaptor(BaseAdaptor):
    """
    Fuglsang et al. 2020 (Zenodo 3618205, ds-eeg-snhl): selective attention to one of two audiobooks (male/female,
    +-90 deg HRTF, insert earphones) or one talker in quiet; 44 older listeners (22 hearing-impaired, 22
    normal-hearing), 48 ~50-s trials each, BioSemi 64 + EXG at 512 Hz. Scalp EEG (+ EOG, mastoids) is ns_type
    'eeg'; the in-ear EEG of 19 participants is ns_type 'ear-eeg'. Envelopes only (see NOTES).
    """

    def __init__(self, download_dir: str, subjects: list | None = None):
        super().__init__(download_dir)
        self.subjects = subjects  # participant numbers to yield (all if None)
        nested = os.path.join(download_dir, "ds-eeg-snhl")
        self.root = nested if os.path.isdir(nested) else download_dir
        with open(os.path.join(self.root, "participants.tsv"), newline="", encoding="utf-8") as f:
            self.participants = {r["participant_id"]: r for r in csv.DictReader(f, delimiter="\t")}
        with open(os.path.join(os.path.dirname(__file__), "shared_segments.csv"), newline="", encoding="utf-8") as f:
            self.segments = {(r["participant"], r["role"], int(r["trial"])): r["shared_segment"]
                             for r in csv.DictReader(f)}

    def parse(self) -> Iterable[TrialRecord]:
        for bdf in self.sorted_glob(self.root, "sub-*/eeg/*_task-selectiveattention*_eeg.bdf"):
            participant = os.path.basename(bdf)[:7]
            if self.subjects is not None and int(participant[4:]) not in self.subjects:
                continue
            info = self.participants[participant]
            run = re.search(r"_run-(\d+)_", bdf)
            channels = _channels(bdf.replace("_eeg.bdf", "_channels.tsv"))
            with open(bdf.replace("_eeg.bdf", "_events.tsv"), newline="", encoding="utf-8") as f:
                events = [e for e in csv.DictReader(f, delimiter="\t") if e["type"] == "STATUS"]
            subject = int(participant[4:])
            for i, ev in enumerate(events):
                if ev["trigger_type"] != "targetonset":
                    continue
                nxt = events[i + 1] if i + 1 < len(events) else {}
                masker = nxt if nxt.get("trigger_type") == "maskeronset" else None
                two = ev["single_talker_two_talker"] == "twotalker"
                if (masker is not None) != two:
                    raise ValueError(f"{bdf}: masker trigger does not match the condition at event {i}")
                trial = int(re.search(r"t(\d+)\.wav", ev["stim_file"]).group(1))
                stimuli = self._stimuli(ev, True) + (self._stimuli(masker, False) if masker else [])
                n_times = _read_envelope(self._mat(ev["stim_file"])).shape[1]
                onset, end = int(ev["sample"]) - 1, _next_end(events, i)
                extra = dict(participant=participant, hearing_status=info["hearing_status"], age=int(info["age"]),
                             file=os.path.relpath(bdf, self.root), run=int(run.group(1)) if run else 1,
                             trigger_code=int(ev["value"]), onset_sample=onset,
                             attended_talker=ev["attend_male_female"].removeprefix("attend"),
                             attended_side=ev["attend_left_right"].removeprefix("attend"),
                             masker_delay_s=(int(masker["sample"]) - int(ev["sample"])) / FS if masker else None,
                             target_segment=self.segments.get((participant, "target", trial)),
                             masker_segment=self.segments.get((participant, "masker", trial)) if masker else None,
                             difficulty_rating=_number(end.get("diffulty_ratings")),  # sic, shipped column name
                             questionnaire_score=_number(end.get("questionnaire_scores")),
                             reference="BioSemi CMS/DRL (reference-free recording, not re-referenced)",
                             units_as_shipped="BDF, read into V",
                             stimulus_files=[f"{s.name}_{s.feature_name}" for s in stimuli])
                for ns_type in sorted({c[3] for c in channels}):
                    yield TrialRecord(
                        subject=subject, session=1, trial=trial,
                        condition="two-talker" if two else "single-talker", ns_type=ns_type, stimulus=stimuli,
                        neural_data_fn=_eeg_loader(bdf, onset, n_times, ns_type,
                                                   [c for c in channels if c[3] == ns_type],
                                                   BADS.get((subject, ns_type), []), extra))

    def _mat(self, wav: str) -> str:
        """Envelope file of a stimulus named in events.tsv."""
        return os.path.join(self.root, "derivatives", "stimuli", wav[:-4] + ".mat")

    def _stimuli(self, ev: dict, attended: bool) -> list:
        """Envelope as presented, plus the envelope without CamEQ when that differs (hearing-impaired listeners)."""
        files = [("envelope", ev["stim_file"])]
        if ev["stim_file_without_cambridge_eq"] != ev["stim_file"]:
            files.append(("envelope-no-cameq", ev["stim_file_without_cambridge_eq"]))
        name = ev["stim_file"][:-4].replace("/", "-")  # e.g. sub001-masker-m004
        return [StimulusRecord("audio", name, _envelope(self._mat(f)), is_attended=attended, feature_name=feature)
                for feature, f in files]


def _channels(tsv: str) -> list:
    """(BDF name, stored name, type, ns_type) per channel, from channels.tsv (Status dropped)."""
    with open(tsv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    out = []
    for r in rows:
        if r["name"] == "Status":
            continue
        name, kind, ns_type = EXG[r["description"]] if r["name"].startswith("EXG") else (r["name"], "eeg", "eeg")
        out.append((r["name"], name, kind, ns_type))
    return out


def _next_end(events: list, i: int) -> dict:
    """The trial-end event after event i (empty if none before the next onset)."""
    for e in events[i + 1:]:
        if e["trigger_type"] == "targetonset":
            break
        if e["trigger_type"] == "trialend":
            return e
    return {}


def _number(value: str | None) -> float | None:
    """events.tsv value as float, None for n/a."""
    return None if value in (None, "n/a") else float(value)


@lru_cache(maxsize=256)
def _read_envelope(path: str) -> np.ndarray:
    """Shipped envelope (1, n) at 512 Hz, zero-padded before its first time stamp (masker onset): t = 0 is onset."""
    d = read_mat(path)["dat"]
    if float(d["fs"]) != FS:
        raise ValueError(f"{path}: envelope at {d['fs']} Hz")
    x = np.ravel(d["feat"]).astype(np.float32)
    pad = round(float(np.ravel(d["t"])[0]) * FS)
    return np.concatenate([np.zeros(pad, np.float32), x])[None]


def _envelope(path: str) -> Callable[[], dict]:
    return lambda: {"fs": FS, "data": _read_envelope(path)}


def _eeg_loader(bdf: str, onset: int, n_times: int, ns_type: str, channels: list, bads: list,
                extra: dict) -> Callable[[], mne.io.BaseRaw]:
    """n_times samples of the channels from the onset sample, in volts, with stored names and types (header kept)."""
    def _loader() -> mne.io.BaseRaw:
        raw = mne.io.read_raw_bdf(bdf, preload=False, verbose="ERROR")
        if raw.info["sfreq"] != FS or onset + n_times > raw.n_times:
            raise ValueError(f"{bdf}: not {FS} Hz, or trial at sample {onset} runs past the end of the recording")
        raw.pick([c[0] for c in channels]).crop(onset / FS, (onset + n_times) / FS, include_tmax=False)
        raw.load_data(verbose="ERROR").set_annotations(None)
        raw.rename_channels({c[0]: c[1] for c in channels})
        raw.set_channel_types({c[1]: c[2] for c in channels}, verbose="ERROR")
        if ns_type == "eeg":
            raw.set_montage(MONTAGE, on_missing="ignore", verbose="ERROR")
        mark_bads(raw, bads)
        raw.info["description"] = provenance(
            "sw_trigger", TRIGGER_TYPE, NOTES, drift_ppm=0.0, jitter_ms=1.2, validation_tier=VALIDATION_TIER[ns_type],
            bad_channels=bads, montage="biosemi64 template (no digitisation)" if ns_type == "eeg" else
            "in-ear (individual earpieces, Eriksholm; no positions)", **extra)
        return raw

    return _loader


ADAPTOR = Fuglsang2020Adaptor
