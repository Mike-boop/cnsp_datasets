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

# cEEGrid (OpenNeuro ds004015, registry holtze2021_ceegrid): one around-ear file per trial (notes 12-14)
GRID_TASK = "AttendedSpeakerParadigmcEEGridAttention"
GRID_NS_TYPE = "around-ear-eeg"
GRID_ONSETS = os.path.join(os.path.dirname(__file__), "ceegrid_onsets.csv")  # Holtze half: lag vs the scalp file
# Jaeger half: Holtze-half median lag + (88 - 54) - (102 - 70) ms (cap delays and the authors' cEEGrid shifts, notes 13)
JAEGER_EXTRA_MS = (88 - 54) - (102 - 70)
# block-onset jitter (ms): scalp markers ~7 (notes 7); Jaeger half adds the between-session SD of the transferred lag
JITTER_MS = {"holtze2021": 7, "jaeger2020": 9}
JAEGER_BASE = 100  # Jaeger subjects: subject = 100 + maj number (maj_s07 -> 107); Holtze: bjh number = ds003516 id
GRID_BLOCKS = 5  # Jaeger block 6 has no stimulus (notes 12)
GRID_NOTES = ("cEEGrid (2 x 10 around-ear electrodes, 18 channels, reference R04b, ground R04a) on a separate "
              "SMARTING (mBrainTrain) Bluetooth amplifier, recorded with the scalp BrainAmp in one LSL/XDF file. "
              "{onset} Drift not corrected (cEEGrid vs scalp +4 ppm, <= 1.3 ms within a block; vs audio unknown). "
              "Stimuli as in the scalp files (dry narratives).")
GRID_ONSET_HOLTZE = ("Onset = ds004015 StartTrigger + this block's lag of the cEEGrid behind the concurrent ds003516 "
                     "scalp recording (whole-block cross-correlation of the two files), i.e. the scalp onset carried "
                     "over to the cEEGrid clock.")
GRID_ONSET_JAEGER = ("Jaeger et al. (2020) session (free-field loudspeakers at +-45 deg; no scalp data shared). "
                     "Onset = ds004015 StartTrigger {offset:+.1f} ms: the median cEEGrid-vs-scalp lag of the Holtze "
                     "sessions (same amplifiers and recorder) {extra:+d} ms for the studies' different cap delays and "
                     "author shifts.")
GRID_ONSET_SHIPPED = ("Onset = ds004015 StartTrigger as shipped (contains the authors' N1-matching shift of the "
                      "cEEGrid to the cap; ~37 ms late relative to the concurrent scalp recording, notes 13).")
GRID_VALIDATION_TIER = "low"  # notes 16
# ds004015 subject -> block -> cEEGrid channels flat (1-40 Hz SD < 0.5 uV) or > 5x the subject's median SD (notes 14)
GRID_BADS = {
    "sub-002": {b: ["R05"] for b in range(1, 5)}, "sub-010": {b: ["R05", "R04"] for b in range(1, 6)},
    "sub-018": {1: ["R05"], 2: ["R07"], 3: ["R07", "R05"], 4: ["R07"]}, "sub-020": {1: ["R05"]},
    "sub-028": {3: ["R07", "L02"]}, "sub-029": {5: ["R01"]}, "sub-031": {b: ["L03"] for b in range(1, 6)},
    "sub-032": {3: ["R05", "R04", "L04b", "L03"], 5: ["L02"]}, "sub-033": {b: ["R01"] for b in range(2, 5)},
}
PRESENTATION = {"holtze2021": "earphones, HRIR-spatialised at +-30 deg (beamformer in beam blocks)",
                "jaeger2020": "free-field loudspeakers at +-45 deg, 1.1 m, 70 dB SPL, equal level"}


class Holtze2021Adaptor:
    """
    Holtze et al. 2021 (OpenNeuro ds003516): attend one of two talkers (left/right, the same side throughout);
    the participant's own name is inserted 10 times per block in the ignored talker in blocks 2-5.
    25 subjects x 5 blocks of ~10 min, BrainAmp 500 Hz, 47 scalp channels + E19/E20 (EOG), nose reference.
    Plus the concurrent cEEGrid of 21 of them and of 15 Jaeger et al. (2020) participants (OpenNeuro ds004015,
    `ns_type` `around-ear-eeg`, SMARTING 500 Hz, 18 channels, reference R04b).

    Trial = block b (onset = b-th StartTrigger). Stimuli: `story1_block<b>` (left) and `story2_block<b>` (right),
    each as the matching channel of the v1.1.1 `Block_<b>_32k.wav` (`audio`, 32 kHz) and the authors' onset
    envelope `sig<s>_<b>.mat` (`onset_envelope_authors`, 500 Hz). Condition `attend-<side>-<omni-noname|omni|beam>`
    (Jaeger: `attend-<side>-freefield`, blocks 1-5; subject = 100 + maj number). Name onsets are `own_name`
    annotations. See notes.md.

    ceegrid_dir: the ds004015 download (None: `<download_dir>/ds004015` if it exists, else scalp only).
    ceegrid_onset: 'scalp' (default: cEEGrid onsets carried over from the concurrent scalp recording, notes 13) or
    'shipped' (ds004015's StartTriggers, which contain the authors' N1-based shift).
    """

    def __init__(self, download_dir: str, ceegrid_dir: str | None = None, ceegrid_onset: str = "scalp"):
        self.root = download_dir
        with open(os.path.join(download_dir, "participants.tsv"), newline="") as f:
            self.participants = list(csv.DictReader(f, delimiter="\t"))
        quest = read_mat(os.path.join(download_dir, "stimuli", "name_quest.mat"))["name_quest"]
        self.name_len = dict(zip(np.ravel(quest["subj"]).astype(int), np.ravel(quest["len"]) / 1000))
        self.duration = {b: _block_duration(download_dir, b) for b in range(1, 6)}
        if ceegrid_onset not in ("scalp", "shipped"):
            raise ValueError(f"ceegrid_onset {ceegrid_onset!r} is not 'scalp' or 'shipped'")
        if ceegrid_dir is None:
            ceegrid_dir = os.path.join(download_dir, "ds004015")
            ceegrid_dir = ceegrid_dir if os.path.isdir(ceegrid_dir) else None
        elif not os.path.isdir(ceegrid_dir):
            raise FileNotFoundError(f"ceegrid_dir {ceegrid_dir} does not exist")
        self.grid = _GridSource(ceegrid_dir, ceegrid_onset == "shipped") if ceegrid_dir else None

    def parse(self) -> Iterable[TrialRecord]:
        for p in self.participants:
            sub, side = int(p["participant_id"][4:]), p["attended_ch"]
            set_path = os.path.join(self.root, p["participant_id"], "eeg", f"{p['participant_id']}_task-{TASK}_eeg.set")
            ann = mne.io.read_raw_eeglab(set_path, preload=False, verbose="ERROR").annotations
            starts = ann.onset[ann.description == "StartTrigger"]
            if len(starts) != 5:
                raise ValueError(f"{set_path}: {len(starts)} StartTrigger events")
            grid = self.grid.holtze(sub, p) if self.grid else None
            for b, start in enumerate(starts, 1):
                inside, names = _names(ann, start, self.duration[b], b, set_path)
                cond = "omni-noname" if b == 1 else NAME_EVENTS[p["cond_order"][b - 2]]
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
                stimuli = self._stimuli(b, side)
                yield TrialRecord(
                    subject=sub, session=1, trial=b, condition=f"attend-{side}-{cond}", ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=_eeg_loader(set_path, start, self.duration[b], names, self.name_len[sub],
                                               description, highpass=0.0159),  # recording filter (eeg.json)
                )
                if grid:
                    yield self.grid.record(grid, sub, b, f"attend-{side}-{cond}", stimuli, self.duration[b],
                                           self.name_len[sub], incl=p["incl"] == "incl",
                                           condition_order=p["cond_order"])
        if self.grid:
            for g in self.grid.jaeger():
                for b in range(1, len(g["starts"]) + 1):
                    side = g["attended_ch"]
                    yield self.grid.record(g, JAEGER_BASE + g["number"], b, f"attend-{side}-freefield",
                                           self._stimuli(b, side), self.duration[b], None)

    def _stimuli(self, b: int, side: str) -> list[StimulusRecord]:
        stimuli = []
        for s, stim_side in enumerate(SIDES, 1):
            name, attended = f"story{s}_block{b}", stim_side == side
            stimuli += [StimulusRecord("audio", name, _audio_loader(_wav(self.root, b), s - 1),
                                       is_attended=attended, feature_name="audio"),
                        StimulusRecord("audio", name, _env_loader(_env(self.root, s, b), s),
                                       is_attended=attended, feature_name=ENVELOPE)]
        return stimuli


class _GridSource:
    """The ds004015 cEEGrid files: subject map, block onsets and TrialRecords (ns_type `around-ear-eeg`)."""

    def __init__(self, root: str, shipped: bool):
        self.root, self.shipped = root, shipped
        with open(os.path.join(root, "participants.tsv"), newline="") as f:
            self.participants = list(csv.DictReader(f, delimiter="\t"))
        ids = read_mat(os.path.join(root, "sourcedata", "subj_info.mat"))["subj_info"]["subj_id"]
        for p, orig in zip(self.participants, ids, strict=True):  # same order (sub-001 .. sub-036)
            p["orig_id"], p["number"] = orig, int(orig.split("_s")[1])
            if p["orig_study"] != {"bjh": "holtze2021", "maj": "jaeger2020"}[orig[:3]]:
                raise ValueError(f"{p['participant_id']}: {orig} does not match orig_study {p['orig_study']}")
        with open(GRID_ONSETS, newline="") as f:
            self.lags = {(r["ds004015"], int(r["block"])): float(r["lag_ms"]) for r in csv.DictReader(f)}
        self.jaeger_offset_ms = round(float(np.median(list(self.lags.values()))) + JAEGER_EXTRA_MS, 1)

    def _session(self, p: dict) -> dict:
        pid = p["participant_id"]
        set_path = os.path.join(self.root, pid, "eeg", f"{pid}_task-{GRID_TASK}_eeg.set")
        ann = mne.io.read_raw_eeglab(set_path, preload=False, verbose="ERROR").annotations
        # block 6 has no stimulus; MNE already drops the markers past the file end (lost blocks)
        starts = ann.onset[ann.description == "StartTrigger"][:GRID_BLOCKS]
        return dict(p, path=set_path, ann=ann, starts=starts)

    def holtze(self, sub: int, p16: dict) -> dict | None:
        """The ds004015 session of ds003516 subject `sub` (= bjh number), checked against its participants row."""
        p = next((q for q in self.participants if q["orig_id"] == f"bjh_s{sub:02d}"), None)
        if p is None:
            return None  # the authors' 4 excluded subjects are not in ds004015
        if (p["attended_ch"], p["gender"].lower(), p["age"], p["con_order"]) != (
                p16["attended_ch"], p16["gender"].lower(), p16["age"], p16["cond_order"]):
            raise ValueError(f"{p['participant_id']} does not match ds003516 sub-{sub:03d}")
        g = self._session(p)
        if len(g["starts"]) != 5:
            raise ValueError(f"{g['path']}: {len(g['starts'])} StartTrigger events")
        return g

    def jaeger(self) -> Iterable[dict]:
        """The Jaeger et al. (2020) sessions (cEEGrid only)."""
        for p in self.participants:
            if p["orig_study"] == "jaeger2020":
                yield self._session(p)

    def record(self, g: dict, sub: int, b: int, condition: str, stimuli: list[StimulusRecord], duration: float,
               name_len: float | None, **extra) -> TrialRecord:
        """cEEGrid block `b`; onset = StartTrigger + the scalp lag (Holtze) or the Jaeger offset (notes 13)."""
        start = float(g["starts"][b - 1])
        holtze = g["orig_study"] == "holtze2021"
        shift_ms = 0.0 if self.shipped else self.lags[(g["participant_id"], b)] if holtze else self.jaeger_offset_ms
        onset = start + shift_ms / 1000
        names = np.array([])
        if holtze:  # name onsets relative to the StartTrigger = the same table times as in the scalp file
            names = _names(g["ann"], start, duration, b, g["path"])[1]
        onset_note = (GRID_ONSET_SHIPPED if self.shipped else GRID_ONSET_HOLTZE if holtze
                      else GRID_ONSET_JAEGER.format(offset=self.jaeger_offset_ms, extra=JAEGER_EXTRA_MS))
        description = provenance(
            "sw_trigger", "software (LSL marker stream; paper, XDF header)", GRID_NOTES.format(onset=onset_note),
            jitter_ms=JITTER_MS[g["orig_study"]], validation_tier=GRID_VALIDATION_TIER,
            block=b, attended_side=g["attended_ch"], sex=g["gender"].upper(), age=int(g["age"]),
            start_trigger_s=start, onset_shift_ms=shift_ms, onset_s=onset,
            ds004015_id=g["participant_id"], ds003516_id=f"sub-{sub:03d}" if holtze else None,
            original_id=g["orig_id"], original_study=g["orig_study"], presentation=PRESENTATION[g["orig_study"]],
            blocks_analysed_2022=[int(g[k]) for k in ("first_bl", "second_bl", "third_bl")],
            name_length_s=name_len, reference="R04b", ground="R04a", amplifier="SMARTING (mBrainTrain)",
            montage="cEEGrid (around-ear)", positions="template (EEGLAB, ds004015 electrodes.tsv)", **extra,
        )
        return TrialRecord(
            subject=sub, session=1, trial=b, condition=condition, ns_type=GRID_NS_TYPE, stimulus=stimuli,
            neural_data_fn=_eeg_loader(g["path"], onset, duration, names, name_len or 0.0, description,
                                       bads=GRID_BADS.get(g["participant_id"], {}).get(b, [])),
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


def _names(ann: mne.Annotations, start: float, duration: float, b: int, path: str) -> tuple[np.ndarray, np.ndarray]:
    """Events inside block `b` (mask) and its name onsets relative to `start` (0 in block 1, 10 in blocks 2-5)."""
    inside = (ann.onset > start) & (ann.onset < start + duration)
    names = ann.onset[inside & np.isin(ann.description, list(NAME_EVENTS.values()))] - start
    if len(names) != (0 if b == 1 else 10):
        raise ValueError(f"{path}: block {b} has {len(names)} name events")
    return inside, names


def _eeg_loader(path: str, start: float, duration: float, names: np.ndarray, name_len: float, description: str,
                highpass: float | None = None, bads: list[str] = ()) -> Callable[[], BaseRaw]:
    def _loader() -> BaseRaw:
        raw = mne.io.read_raw_eeglab(path, preload=False, verbose="ERROR")  # uV -> V by MNE
        sfreq = raw.info["sfreq"]
        i0, n = int(round(start * sfreq)), int(round(duration * sfreq))
        if i0 < 0 or i0 + n > raw.n_times:
            raise ValueError(f"{path}: block at {start:.3f} s runs past the recording")
        raw.crop(i0 / sfreq, (i0 + n) / sfreq, include_tmax=False).load_data(verbose="ERROR")
        raw.set_annotations(mne.Annotations(names, name_len, "own_name"))
        if highpass is not None:
            with raw.info._unlock():
                raw.info["highpass"] = highpass
        raw.info["bads"] = list(bads)
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
