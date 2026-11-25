from __future__ import annotations

import logging
import math
import os
import re
import tempfile
from functools import lru_cache
from typing import Callable, Iterable

import mne
import pandas as pd
import soundfile
from mne.channels import make_standard_montage

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.iohelpers import mark_bads, read_wav, textgrid
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

log = logging.getLogger(__name__)

AUDIO_FS = 44100
ONSETS = os.path.join(os.path.dirname(__file__), "alignment", "onsets.csv")  # notes.md sections 3 and 6
DRIFT = 164e-6  # pooled within-section EEG lag slope, 32 sections / 18 subjects (notes.md section 7)
JITTER_MS = 4.1  # residual SD of the S 31-S 33 timeline fit (notes.md section 7)
TIMELINE_SD_MS = {2: 19.3, 3: 31.4, 4: 40.2}  # cross-subject SD of the trigger timeline per position
CONDITIONS = {"mixed": "mixed", "single_f": "single-female", "single_m": "single-male"}
STIMULI = {"mixed": ("mix", "single_female", "single_male"), "single_f": ("single_female",),
           "single_m": ("single_male",)}
TRIGGERED = {"S11", "S31", "S32", "S33"}
DEAD = ["C3", "C4", "CP1", "CP2", "CP5", "CP6", "F3", "F4", "F7", "F8", "Fz", "FC1", "FC2", "FC5", "FC6", "Fp1",
        "Fp2", "FT10", "FT9", "O1", "O2", "Oz", "P3", "P4", "P7", "P8", "Pz", "T7", "T8", "TP10", "TP9"]
DEAD_SUBJECTS = {10, 11, 12, 13, 14, 22, 23, 24, 25, 26}  # upstream: first actiCAP 32-set except Cz (notes 5)
LOW_VARIANCE = {17: ["FC1"], 21: ["C1", "Pz"]}  # ~1 uV 1-40 Hz SD, not marked bad
GROUP_CONFIDENCE = {5: "low", 9: "medium", 10: "medium", 23: "medium"}  # notes.md section 3; others high
SHORT_PAUSE = {16, 18}  # 615-s section spacing, offsets from the authors' derivatives (notes.md section 6)
TRUNCATED = {15}  # .eeg truncated upstream within section 1
BROKEN_HEADER = {26}  # .vhdr DataFile/MarkerFile point to the original lab file names
REFERENCE = ("unknown: JSON says Cz (a live channel), paper says nose; data indicate an online FCz reference "
             "(inferred, actiCAP default; FCz not recorded)")
NOTES = ("Continuous playback, one wav per ~10-min section, four sections per recording: positions 1-2 mixed "
         "(female + male at 0.5 each, diotic), 3-4 single talker in group order A (male, female) or B (female, male). "
         "Group and labels from EEG envelope tracking; the paper's Table S2 run order does not match the EEG. "
         "Attended talker in mixed sections unknown (instructed, not recoverable). Section 1 onset = S 11/S 31; "
         "sections 2-3 = S 32/S 33 where present, else the trigger timeline from the first marker (735.07 / "
         "1470.14 s); section 4 = first marker + 2192.2 s (A) or 2196.2 s (B), S 34 (~0.95 s late) ignored. "
         "Drift: EEG lag slides +164 ppm within sections (pooled EEG estimate); drift_corrected_ppm says what was "
         "applied (onset and drift in one quintic-spline interpolation). Positions: standard_1005 template.")
SHORT_NOTE = " Short-pause session: offsets 615.06 / 1230.12 / 1832.2 (A) or 1836.2 (B) s from the authors' epochs."
TRUNC_NOTE = " Recording truncated upstream: 455 s of section 1 only; the stimulus is longer than the EEG."
DEAD_NOTE = " 31 channels dead upstream (first actiCAP 32-set except Cz), marked bad."
CONF_NOTE = " Group A/B call has {} confidence (weak single-talker tracking)."
WORDS_NOTE = "words: upstream word_information.csv (centiseconds, 10 ms precision), relative to the wav start"


class Wang2025Adaptor(BaseAdaptor):
    """
    Wang et al. 2025, Le Petit Prince multi-talker, EEG part (OpenNeuro ds005345 v1.0.1): 26 Mandarin listeners,
    one BrainAmp recording each (64 EEG channels, 500 Hz kept, original reference) with four continuously played
    ~10-min sections: two mixed-talker (`mixed`), then `single-female` and `single-male` in group order.

    Trial = section (1-4, presentation position). Onsets from `alignment/onsets.csv` (triggers or trigger timeline);
    drift_correction (default +164 ppm, None = off) is applied with the onset in one interpolation. Stimuli: the
    shipped 44.1 kHz wavs (mixed: `mix` as played plus `single_female` and `single_male`, none attended; single:
    the talker's wav, attended; float32) and `words` TextGrids for the single wavs. See notes.md.
    """

    def __init__(self, download_dir: str, drift_correction: float | None = DRIFT):
        super().__init__(download_dir)
        self.root = download_dir
        self.drift = drift_correction or 0.0
        self.onsets = pd.read_csv(ONSETS, keep_default_na=False)
        self.n_audio = {s: soundfile.info(self._wav(s)).frames for s in ("mix", "single_female", "single_male")}
        part = pd.read_csv(self.path("participants.tsv"), sep="\t")
        self.participants = part.set_index("participant_id").to_dict("index")

    def parse(self) -> Iterable[TrialRecord]:
        for sub, rows in self.onsets.groupby("sub"):
            subject = int(sub[4:])
            vhdr = os.path.join(self.root, sub, "eeg", f"{sub}_task-multitalker_eeg.vhdr")
            code, first = _first_marker(vhdr.replace(".vhdr", ".vmrk"))
            if code != rows.source.iloc[0] or abs(first / 500 - rows.onset_s.iloc[0]) > 1e-6:
                raise ValueError(f"{sub}: first marker {code} at {first / 500} s does not match onsets.csv")
            p = self.participants[sub]
            for r in rows.itertuples():
                if r.condition == "n/a":
                    log.info("wang2025: %s position %s skipped (recording truncated upstream)", sub, r.pos)
                    continue
                method = "sw_trigger" if r.source in TRIGGERED else "onset_only"
                n_out = math.ceil(max(self.n_audio[s] for s in STIMULI[r.condition]) * 500 / AUDIO_FS)
                notes = (NOTES + SHORT_NOTE * (subject in SHORT_PAUSE) + TRUNC_NOTE * (subject in TRUNCATED)
                         + DEAD_NOTE * (subject in DEAD_SUBJECTS)
                         + (CONF_NOTE.format(GROUP_CONFIDENCE[subject]) if subject in GROUP_CONFIDENCE else ""))
                description = provenance(
                    method, "software (inferred: S 31-S 33 intervals on a 60 Hz frame grid; undocumented)", notes,
                    drift_ppm=164.0, jitter_ms=JITTER_MS, validation_tier="low",
                    drift_corrected_ppm=round(self.drift * 1e6, 3),
                    participant=sub, position=int(r.pos), group=r.group if r.group != "-" else "unknown",
                    group_confidence=GROUP_CONFIDENCE.get(subject, "high") if r.group != "-" else "n/a",
                    condition_source="EEG envelope tracking (Table S2 run order does not match the EEG)",
                    attended="unknown" if r.condition == "mixed" else STIMULI[r.condition][0],
                    onset_s=float(r.onset_s), onset_source=r.source,
                    timeline_sd_ms=None if method == "sw_trigger" else TIMELINE_SD_MS[r.pos],
                    first_marker=code, first_marker_s=first / 500, short_pause_session=subject in SHORT_PAUSE,
                    truncated_upstream=subject in TRUNCATED, bad_channels=DEAD if subject in DEAD_SUBJECTS else [],
                    low_variance_channels=LOW_VARIANCE.get(subject, []), age=int(p["age"]), sex=p["sex"],
                    eeg_acq_date=p["eeg_acq_time"], reference=REFERENCE, ground="unknown (JSON AFz, paper forehead)",
                    units_as_shipped="0.1 uV INT_16 (BrainVision), read into V",
                    montage="standard_1005 template (no digitisation)", annotation=WORDS_NOTE)
                stimuli = []
                for s in STIMULI[r.condition]:
                    attended = r.condition != "mixed"
                    stimuli.append(StimulusRecord("audio", s, _audio_loader(self._wav(s)), attended, "audio"))
                    if s != "mix":
                        stimuli.append(StimulusRecord("audio", s, self._textgrid_loader(s), attended, "textgrid"))
                yield TrialRecord(
                    subject=subject, session=1, trial=int(r.pos), condition=CONDITIONS[r.condition], ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=_eeg_loader(vhdr, r.onset_s * 500, n_out, self.drift, subject in TRUNCATED,
                                               DEAD if subject in DEAD_SUBJECTS else [], description))

    def _wav(self, name: str) -> str:
        return os.path.join(self.root, "stimuli", f"{name}.wav")

    def _textgrid_loader(self, name: str) -> Callable[[], str]:
        """`words` tier from the upstream centisecond word timings."""
        path = os.path.join(self.root, "annotation", f"{name}_word_information.csv")
        xmax = self.n_audio[name] / AUDIO_FS

        def _loader() -> str:
            w = pd.read_csv(path)
            return textgrid({"words": [(on, min(off, xmax), str(word))
                                       for on, off, word in zip(w.onset / 100, w.offset / 100, w.word)]}, xmax=xmax)

        return _loader


def _first_marker(vmrk: str) -> tuple[str, int]:
    """Code and 0-based sample of the first S 11/S 31 marker."""
    with open(vmrk, encoding="utf-8") as f:
        m = re.search(r"Stimulus,S (11|31),(\d+),", f.read())
    return f"S{m.group(1)}", int(m.group(2)) - 1


def _audio_loader(path: str) -> Callable[[], dict]:
    def _loader() -> dict:
        info = soundfile.info(path)
        if info.samplerate != AUDIO_FS or info.subtype != "PCM_16" or info.channels != 1:
            raise ValueError(f"{path}: expected 44.1 kHz mono int16")
        return {"fs": AUDIO_FS, "data": read_wav(path)[0]}

    return _loader


_PATCHED: dict = {}  # vhdr -> TemporaryDirectory holding its patched copy, kept for the life of the process


def patched_header(vhdr: str) -> str:
    """A copy of a broken header (sub-26) whose DataFile/MarkerFile point to the files next to it (absolute)."""
    if vhdr not in _PATCHED:
        with open(vhdr, encoding="utf-8") as f:
            text = f.read()
        stem = os.path.abspath(vhdr)[:-5]
        text = re.sub(r"(?m)^DataFile=.*$", lambda _: f"DataFile={stem}.eeg", text)
        text = re.sub(r"(?m)^MarkerFile=.*$", lambda _: f"MarkerFile={stem}.vmrk", text)
        tmp = tempfile.TemporaryDirectory(prefix="wang2025_")
        with open(os.path.join(tmp.name, os.path.basename(vhdr)), "w", encoding="utf-8") as f:
            f.write(text)
        _PATCHED[vhdr] = tmp
    return os.path.join(_PATCHED[vhdr].name, os.path.basename(vhdr))


@lru_cache(maxsize=1)
def _read(vhdr: str) -> mne.io.BaseRaw:
    """Lazy BrainVision reader; a broken header (sub-26) is read through a patched copy (patched_header)."""
    if int(os.path.basename(vhdr)[4:6]) in BROKEN_HEADER:
        vhdr = patched_header(vhdr)
    return mne.io.read_raw_brainvision(vhdr, preload=False, verbose="ERROR")


def _eeg_loader(vhdr: str, onset: float, n_out: int, drift: float, truncated: bool, bads: list,
                description: str) -> Callable[[], mne.io.BaseRaw]:
    def _loader() -> mne.io.BaseRaw:
        raw = _read(vhdr)
        if raw.info["sfreq"] != 500 or len(raw.ch_names) != 64:
            raise ValueError(f"{vhdr}: expected 64 channels at 500 Hz")
        out = crop_on_audio_clock(raw, onset, n_out, drift)
        if out.n_times != n_out and not truncated:
            raise ValueError(f"{vhdr}: recording ends {n_out - out.n_times} samples before the stimulus")
        out.set_montage(make_standard_montage("standard_1005"), verbose="ERROR")
        out.set_meas_date(None)  # recording PC clock wrong (2010); date in the metadata
        mark_bads(out, bads)
        out.info["description"] = description
        return out

    return _loader


ADAPTOR = Wang2025Adaptor
