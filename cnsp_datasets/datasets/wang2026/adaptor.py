from __future__ import annotations

import os
from collections import Counter
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
import openpyxl
from mne.channels import make_standard_montage
from scipy.io import wavfile

from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

EEG_FS, AUDIO_FS, TRIAL_S = 500.0, 16000, 60
N_EEG = int(TRIAL_S * EEG_FS)
VALIDATION_TIER = "low"  # validation.json: low passes, mlr and brainstem fail (notes.md 9)
STEP_MAX = 100  # samples searched after the event-table sample
KEYS = {"179": "left", "184": "right"}  # response keys: attention now on the left / right stream (Zenodo record)
DROP = ["HEO", "EMG", "Trigger"]  # HEO and EMG unused (railed or noise only; no HEOG/EMG in the paper); trigger word
BADS = {2: ["CB2"], 3: ["M2"], 4: ["T8"], 5: ["M2"], 12: ["T7"]}  # 40-200 Hz noise > 5x median (notes.md 5)
REFERENCE = ("unknown: paper names mastoids and nose tip, but M1/M2 are recorded live channels; lowest variance at "
             "CZ/C1/C2/CPZ suggests the Quik-Cap vertex REF (inferred)")
TRIGGER_TYPE = ("software (E-Prime 3.0 port code at the start of each wav; paper: 'synchronized trigger signals'; "
                "sound latency undocumented)")
NOTES = ("Trial = one 60-s presentation, cut at its E-Prime trial code (11-70 attention-switching, 71/72 practice, "
         "73-82 passive block), timed by the code's first sample on the recorded Trigger channel (the CNT event "
         "table is 1 sample earlier, 24 in S14). Stimuli: the shipped 16 kHz stereo wav as played (left channel = "
         "left talker only, right = right talker only; channels independent) plus each channel as `<wav>_left` / "
         "`<wav>_right`; none is flagged attended because attention switches within the trial. Annotations: "
         "`key/left`, `key/right` at each button press (codes 179/184) and `attend/left`, `attend/right` spans "
         "from each press to the next press or the trial end (attention-switching and practice trials; "
         "unlabelled before the first press); passive-block presses are motor control and get no attend spans. "
         "No drift estimate (60-s trials, no end marker or audio copy). VEOG carries no blink signal in any "
         "subject (railed or noise) and is marked bad. Many neighbouring electrodes are gel-bridged (notes.md 5). "
         "Positions: standard_1005 template (CB1/CB2 have none).")
PASSIVE_NOTE = (" Passive block: the audio played is not listed in StimList.xlsx and could not be identified from "
                "the EEG among the shipped wavs (notes.md 3), so no stimulus is attached.")


class Wang2026Adaptor:
    """
    Wang et al. 2026 AASD (Zenodo 17413336): 18 Mandarin listeners (S1-S18), one Neuroscan Curry CNT each (64 EEG
    incl. M1/M2, 500 Hz kept, original reference). Two AISHELL-1 talkers (one male, one female), one per ear;
    listeners switch attention at will and press a left/right key at each switch.

    Trial = presentation in recording order; condition `switching` (6 blocks x 10), `practice` (codes 71/72) or
    `passive` (block 7, key presses without a task, audio unknown: no stimulus). Onset = the trial code on the
    Trigger channel; no drift correction. Attention labels are MNE annotations on each trial. See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = os.path.join(download_dir, "Original EEG")
        self.wav_dir = os.path.join(download_dir, "Stimuli Audio")
        wb = openpyxl.load_workbook(os.path.join(self.root, "StimList.xlsx"), read_only=True)
        header, *rows = wb.active.iter_rows(values_only=True)
        wb.close()
        col = {h.strip(): i for i, h in enumerate(header)}
        # code -> (wav stem, ear condition); MixFile mix_NNN.wav is shipped as mixed_NNN.wav
        self.stim = {int(r[col["Trigger"]]): (r[col["MixFile"]].replace("mix_", "mixed_")[:-4], r[col["EarCondition"]])
                     for r in rows}

    def parse(self) -> Iterable[TrialRecord]:
        for subject in range(1, 19):
            cnt = os.path.join(self.root, f"S{subject}", f"S{subject}.cnt")
            events = _events(cnt)
            keys = [(s, KEYS[d]) for s, _, d in events if d in KEYS]
            trials = [(s, a, int(d)) for s, a, d in events if d not in KEYS]
            n_switch, seen = 0, Counter()
            for trial, (onset, ann_sample, code) in enumerate(trials, 1):
                n_switch += 11 <= code <= 70
                condition = "switching" if code <= 70 else "practice" if code <= 72 else "passive"
                block = 0 if condition == "practice" else 7 if condition == "passive" else (n_switch - 1) // 10 + 1
                presses = [((s - onset) / EEG_FS, side) for s, side in keys if 0 <= s - onset < N_EEG]
                extra = dict(participant=f"S{subject}", trial_code=code, block=block, onset_sample=onset,
                             onset_source="Trigger channel step (0xFF00 + code)",
                             event_table_offset_ms=(onset - ann_sample) * 1000 / EEG_FS, n_key_presses=len(presses),
                             bad_channels=["VEOG"] + BADS.get(subject, []), reference=REFERENCE,
                             units_as_shipped="CNT calibrated to uV by the header, read into V",
                             external_sensors={"M1": "left mastoid", "M2": "right mastoid"},
                             montage="standard_1005 template (no digitisation)")
                stimuli, notes = [], NOTES + PASSIVE_NOTE * (condition == "passive")
                if condition != "passive":
                    wav, ear = self.stim[code]
                    seen[wav] += 1
                    left, right = ("male", "female") if ear.startswith("Left male") else ("female", "male")
                    extra.update(stimulus=wav, ear_condition=ear, left_talker=left, right_talker=right,
                                 presentation=seen[wav], attention_s=_attention_seconds(presses))
                    path = os.path.join(self.wav_dir, f"{wav}.wav")
                    stimuli = [StimulusRecord("audio", name, _audio_loader(path, ch), False, "audio")
                               for name, ch in ((wav, None), (f"{wav}_left", 0), (f"{wav}_right", 1))]
                description = provenance("sw_trigger", TRIGGER_TYPE, notes, validation_tier=VALIDATION_TIER, **extra)
                yield TrialRecord(subject=subject, session=1, trial=trial, condition=condition, ns_type="eeg",
                                  stimulus=stimuli,
                                  neural_data_fn=_eeg_loader(cnt, onset, presses, condition != "passive",
                                                             extra["bad_channels"], description))


def _spans(presses: list) -> list:
    """(onset, duration, side) from each press to the next press or the trial end."""
    ends = [t for t, _ in presses[1:]] + [float(TRIAL_S)]
    return [(t, end - t, side) for (t, side), end in zip(presses, ends)]


def _attention_seconds(presses: list) -> dict:
    """Seconds labelled left / right / unlabelled (before the first press) in one trial."""
    out = {"left": 0.0, "right": 0.0, "unlabelled": presses[0][0] if presses else float(TRIAL_S)}
    for _, duration, side in _spans(presses):
        out[side] += duration
    return {k: round(v, 3) for k, v in out.items()}


def _annotations(presses: list, spans: bool) -> mne.Annotations:
    """Key presses (zero duration) and, if spans, attention spans from each press to the next or the trial end."""
    onset = [t for t, _ in presses]
    duration = [0.0] * len(presses)
    label = [f"key/{side}" for _, side in presses]
    if spans:
        for t, d, side in _spans(presses):
            onset.append(t)
            duration.append(d)
            label.append(f"attend/{side}")
    return mne.Annotations(onset, duration, label)


def _events(cnt: str) -> list:
    """
    (sample, event-table sample, code) of the trial codes (11-82) and key presses, timed by the code's first sample
    on the Trigger channel (0xFF00 + code): 1 sample after the event table, 24 in S14 (notes.md 6).
    """
    raw = mne.io.read_raw_cnt(cnt, preload=False, verbose="ERROR")
    word = np.round(raw.get_data(picks=["Trigger"])[0] * 1e6).astype(int) - 0xFF00
    out = []
    for onset, code in zip(raw.annotations.onset, raw.annotations.description):
        if not (code in KEYS or (code.isdigit() and 11 <= int(code) <= 82)):
            continue
        i = round(onset * EEG_FS)
        hit = np.flatnonzero(word[i:i + STEP_MAX] == int(code))
        if not hit.size:
            raise ValueError(f"{cnt}: code {code} at sample {i} not on the Trigger channel")
        out.append((i + int(hit[0]), i, code))
    return out


@lru_cache(maxsize=1)
def _read(cnt: str) -> mne.io.BaseRaw:
    """Lazy CNT reader with the standard channel types and names (VEO -> VEOG, mastoids misc)."""
    raw = mne.io.read_raw_cnt(cnt, preload=False, verbose="ERROR")
    if raw.info["sfreq"] != EEG_FS or len(raw.ch_names) != 68 or raw.ch_names[-4:] != ["HEO", "VEO", "EMG", "Trigger"]:
        raise ValueError(f"{cnt}: expected 68 channels at 500 Hz ending HEO, VEO, EMG, Trigger")
    raw.drop_channels(DROP)
    raw.rename_channels({"VEO": "VEOG"})
    raw.set_channel_types({"VEOG": "eog", "M1": "misc", "M2": "misc"}, on_unit_change="ignore")
    return raw


def _eeg_loader(cnt: str, onset: int, presses: list, spans: bool, bads: list,
                description: str) -> Callable[[], mne.io.BaseRaw]:
    """Loader of one 60-s trial with its key (and, if spans, attention) annotations, bads and sidecar."""
    def _loader() -> mne.io.BaseRaw:
        raw = _read(cnt)
        out = crop_on_audio_clock(raw, onset, N_EEG)
        if out.n_times != N_EEG:
            raise ValueError(f"{cnt}: trial at sample {onset} runs past the end of the recording")
        out.set_montage(make_standard_montage("standard_1005"), match_case=False, on_missing="ignore",
                        verbose="ERROR")
        out.set_annotations(_annotations(presses, spans))
        out.info["bads"] = list(bads)
        out.info["description"] = description
        return out

    return _loader


def _audio_loader(path: str, channel: int | None) -> Callable[[], dict]:
    """The stereo wav (channel None) or one of its channels, as float32 at 16 kHz."""
    def _loader() -> dict:
        fs, x = wavfile.read(path)
        if fs != AUDIO_FS or x.dtype != np.int16 or x.shape != (TRIAL_S * AUDIO_FS, 2):
            raise ValueError(f"{path}: expected 60 s of 16 kHz stereo int16")
        x = (x.T / 32768.0).astype(np.float32)
        return {"fs": AUDIO_FS, "data": x if channel is None else x[channel:channel + 1]}

    return _loader


ADAPTOR = Wang2026Adaptor
