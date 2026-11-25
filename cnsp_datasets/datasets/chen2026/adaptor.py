from __future__ import annotations

import json
import logging
import math
import os
from functools import lru_cache
from typing import Iterable

import mne
import pandas as pd
import soundfile

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.iohelpers import audio_loader, mark_bads
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

log = logging.getLogger(__name__)

HERE = os.path.dirname(__file__)
TIMING_CSV = os.path.join(HERE, "alignment", "timing.csv")  # alignment/README.md: how it was made
BADS_JSON = os.path.join(HERE, "bads.json")  # from bads.py
FS = 1000
AUDIO_FS = 12000
SESSIONS = {"garnettdream": 1, "littleprince": 2}  # BIDS sessions (one story each); listening order not recoverable
LATENCY = {"chapter": "latency_s", "option_b": "latency_optionB_s", "listener_median": "listener_median_s"}
DRIFT_ESTIMATE_PPM = 16.0  # pooled EEG estimate (decoder windows), documented, not applied by default (notes 6b)
ABSENT = "sub-05 littleprince 14 and 27, sub-06 garnettdream 4"  # EEG not in the release (notes 6b), not in timing.csv
TRIGGER = ("software (code: PsychoPy/sounddevice -> zmq -> egi-pynetstation; the paper says hardware). ROWS/ROWE "
           "replay the reader's line timeline from the sd.play() request, so they give the request time t0, not "
           "the sound")
REFERENCE = "Cz (EGI VREF, the recording reference; dropped by the authors, added back here as a zero channel)"
NOTES = ("PassiveListening only (ReadingAloud and the practice prefaces excluded). Trial = one chapter wav, played "
         "whole. t0 = intercept of a fit of the ROWS/ROWE triggers to the reader's json timeline (residual SD ~3 ms; "
         "alignment/trigger_fit.py); onset = t0 + sound latency (~0.5 s, varying per sd.play() call). The latency is "
         "estimated from this EEG (listener-specific leave-one-chapter-out backward decoder, z >= 2 against "
         "mismatched envelopes, else the accou2023 DNN, else the listener median; alignment/timing.csv `rule`), so "
         "validation scores on these onsets are optimistic (circular); `latency_option` says which column was used "
         "(default option B: listener median unless the chapter's estimate deviates by > max(40 ms, 3 SE); "
         "alignment/onsets_optionB.csv). Drift: ~+16 ppm EEG estimate (alignment/drift.csv), not reliable (every "
         "listener's CI includes 0) and not applied (user decision). Bad channels per participant (bads.json): SD "
         "(1-40 Hz) > 5x or < 1/5 of the median in >= 20% of the chapters. Positions: GSN-HydroCel-129 template (the "
         "shipped CapTrak files are the same template).")


def reader_of(sub: str) -> str:
    """Listeners 01-04 heard reader f1, 05-08 reader m1 (notes.md section 3)."""
    return "f1" if int(sub) <= 4 else "m1"


class Chen2026Adaptor(BaseAdaptor):
    """
    ChineseEEG-2 (Chen et al. 2026, Science Data Bank 10.57760/sciencedb.CHNNeuro.00001 V5), PassiveListening: 8
    Mandarin listeners, 128-ch EGI HydroCel at 1000 Hz (BrainVision files cut per chapter by the authors), hearing
    one reader's recordings of Garnett Dream (01-04: reader f1, 9 sections; 05-08: reader m1, 8) and The Little Prince
    (27 chapters). 281 trials (sub-05 LP 14/27 and sub-06 GD 4 are absent from the release).

    Condition = story, session = BIDS session (1 garnettdream, 2 littleprince), trial = chapter. Onset = t0 (trigger
    fit) + latency from alignment/timing.csv, where `latency` picks the column: "option_b" (default, user
    2026-11-23; listener median unless the chapter's estimate deviates by more than max(40 ms, 3 SE); logged in
    alignment/onsets_optionB.csv), "chapter" (per-chapter EEG estimate under the z >= 2 rule, else the listener
    median) or "listener_median" (one latency per listener). drift_ppm: default 0; the ~+16 ppm EEG estimate
    (alignment/drift.csv) is not applied. Stimulus: the 12 kHz wav (first channel, float32). Bad channels
    (bads.json) are kept and listed in info["bads"]. audio_dir: registry entry chen2026_audio, by default
    <download_dir>/ChineseEEG-2_audio.
    """

    def __init__(self, download_dir: str, latency: str = "option_b", drift_ppm: float = 0.0,
                 audio_dir: str | None = None):
        super().__init__(download_dir)
        self.choice("latency", latency, LATENCY)
        self.root = os.path.join(download_dir, "PassiveListening")
        self.audio_dir = audio_dir or os.path.join(download_dir, "ChineseEEG-2_audio")
        self.latency = latency
        self.drift = float(drift_ppm)
        self.table = pd.read_csv(TIMING_CSV, dtype={"sub": str})
        with open(BADS_JSON) as f:
            self.bads = json.load(f)

    def parse(self) -> Iterable[TrialRecord]:
        log.info("chen2026: absent from the release: %s", ABSENT)
        for r in self.table.itertuples(index=False):
            reader = reader_of(r.sub)
            wav = os.path.join(self.audio_dir, f"{r.story}_{reader}", f"audio_{r.chapter}.wav")
            latency = float(getattr(r, LATENCY[self.latency]))
            own = {"chapter": r.rule != "listener median", "option_b": bool(r.optionB_per_chapter),
                   "listener_median": False}[self.latency]  # a per-chapter EEG estimate is used
            onset = (r.t0_s + latency) * FS
            if self.drift == 0:
                onset = round(onset)
            vhdr = os.path.join(self.root, f"sub-{r.sub}", f"ses-{r.story}", "eeg", r.file)
            halves = [_num(r.halves_A_ms), _num(r.halves_B_ms)]
            halves_agree = None if pd.isna(r.halves_agree) else bool(r.halves_agree)
            description = provenance(
                "dnn" if own else "sw_trigger", TRIGGER, NOTES, drift_ppm=DRIFT_ESTIMATE_PPM,
                jitter_ms=_num(r.latency_se_ms) if own else _num(r.listener_latency_rsd_ms),
                drift_corrected_ppm=self.drift, latency_option=self.latency,
                latency_source=("per-chapter EEG estimate" if own else
                                "listener median of the EEG latency estimates (constant per listener)"),
                t0_s=_num(r.t0_s), latency_s=latency, onset_sample=float(onset),
                listener_median_s=_num(r.listener_median_s), listener_latency_rsd_ms=_num(r.listener_latency_rsd_ms),
                rule=r.rule, rule_z=_num(r.rule_z), latency_se_ms=_num(r.latency_se_ms),
                halves_ms=halves, halves_agree=halves_agree, peak_ratio=_num(r.peak_ratio),
                decoder_latency_ms=_num(r.decoder_latency_ms), decoder_z=_num(r.decoder_z),
                decoder_se_ms=_num(r.decoder_se_ms), trigger_events=int(r.trig_n_events),
                trigger_rows_found=r.trig_rows_found, trigger_residual_sd_ms=_num(r.trig_res_sd_ms),
                participant=f"sub-{r.sub}", reader=reader, story=r.story, chapter=int(r.chapter), file=r.file,
                reference=REFERENCE, units_as_shipped="uV (float32 BrainVision written by pybv), read into V",
                montage="GSN-HydroCel-129 template", validation_tier=None)
            name = f"{r.story}_{reader}_ch{r.chapter:02d}"
            yield TrialRecord(
                subject=int(r.sub), session=SESSIONS[r.story], trial=int(r.chapter), condition=r.story, ns_type="eeg",
                stimulus=[StimulusRecord("audio", name, audio_loader(wav, channel=0), True, "audio")],
                neural_data_fn=_eeg_loader(vhdr, onset, math.ceil(_wav_length(wav) * FS / AUDIO_FS),
                                           self.drift * 1e-6, self.bads[r.sub], description))


def _num(x) -> float | None:
    """Float, or None for a missing value (JSON has no NaN)."""
    return None if pd.isna(x) else float(x)


@lru_cache(maxsize=None)
def _wav_length(path: str) -> int:
    """Samples of a chapter wav, checking the shipped format (12 kHz int16, two identical channels)."""
    info = soundfile.info(path)
    if info.samplerate != AUDIO_FS or info.subtype != "PCM_16" or info.channels != 2:
        raise ValueError(f"{path}: expected {AUDIO_FS} Hz int16 stereo, got {info.samplerate} Hz {info.subtype} "
                         f"{info.channels} channels")
    return info.frames


@lru_cache(maxsize=1)
def _read(vhdr: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_brainvision(vhdr, preload=False, verbose="ERROR")


@lru_cache(maxsize=1)
def _montage() -> mne.channels.DigMontage:
    montage = mne.channels.make_standard_montage("GSN-HydroCel-129")
    montage.rename_channels({"Cz": "VREF"})
    return montage


def _eeg_loader(vhdr: str, onset: float, n_out: int, drift: float, bads: list[str],
                description: str):
    def _loader() -> mne.io.BaseRaw:
        raw = _read(vhdr)
        if raw.info["sfreq"] != FS or len(raw.ch_names) != 128:
            raise ValueError(f"{vhdr}: expected 128 channels at {FS} Hz")
        out = crop_on_audio_clock(raw, onset, n_out, drift)
        if out.n_times != n_out:
            raise ValueError(f"{vhdr}: recording ends {n_out - out.n_times} samples before the end of the wav")
        out = mne.add_reference_channels(out, "VREF", copy=False)
        out.set_montage(_montage(), verbose="ERROR")
        out.set_meas_date(None)
        mark_bads(out, bads)
        out.info["description"] = description
        return out

    return _loader


ADAPTOR = Chen2026Adaptor
