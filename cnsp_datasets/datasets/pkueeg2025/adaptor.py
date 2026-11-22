from __future__ import annotations

import glob
import io
import math
import os
import subprocess
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
import pandas as pd
import textgrid
from mne.channels import make_standard_montage

from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS_AUDIO = 48000
ONSET_SHIFT_S = 1105 / FS_AUDIO  # leading mp3 encoder + decoder delay, played before the gapless audio (inferred)
# pooled marker-interval drift per EEG system (notes.md section 7, scripts/drift_fit.py) and the default correction
DRIFT_PPM = {"NeuroScan": 76.8, "Neuracle": 27.1}
DRIFT_APPLIED_PPM = {"NeuroScan": 76.8, "Neuracle": 0.0}  # Neuracle: CI includes 0, not corrected
JITTER_MS = 2.1  # per marker (residual SD 3.0 ms per start-to-end interval)
SYSTEM = {1: "NeuroScan", 2: "NeuroScan", 3: "Neuracle"}  # by day
AMPLIFIER = {"NeuroScan": "NeuroScan SynAmps2 (CNT)", "Neuracle": "Neuracle NeuSen Wireless (BDF)"}
REFERENCE = {"NeuroScan": "unknown (undocumented; possibly mastoid/ear, unverified)",
             "Neuracle": "unknown (undocumented; CPz inferred from channel amplitudes)"}
LOWPASS = {"NeuroScan": "undocumented online low-pass, steep roll-off above ~200 Hz (-30 to -40 dB at 400 Hz)",
           "Neuracle": "undocumented, gentle roll-off (-15 to -21 dB at 400 Hz)"}
TYPES = {"EEG": "eeg", "EOG": "eog", "ECG": "ecg"}
# (subject, day, story): earlier play of the selected (last) trial, notes.md section 3
REPEATED = {(9, 3, 39): "complete", (9, 3, 50): "complete", (13, 2, 25): "complete", (16, 1, 3): "complete",
            (19, 2, 33): "complete", (20, 3, 47): "complete", (3, 1, 14): "partial (restarted after 171 s)"}
# (subject, day): onset correction; the stories start this long before their markers in the EEG (constant over the
# session; envelope reconstruction with a subject-independent decoder, notes.md section 14)
SESSION_OFFSET_S = {(1, 3): -12.660, (11, 3): -10.443}
SUSPECT = {(25, 3): "suspect: recording failure (from ~400 s all channels incl. ECG/EOG carry the same ~1.5-10 uV "
                    "common signal, no ECG; no envelope tracking at any lag within +-30 min; notes.md section 14)"}
NOTES = ("Onset = start marker (events.tsv) + onset_shift_ms: the player kept the mp3 encoder padding, so the first "
         "gapless sample is assumed to be heard 1105 samples (23.02 ms) after the marker (inferred, not measured; "
         "no stimtrack). Marker source and presentation software undocumented. Drift estimated across subjects "
         "per EEG system from marker intervals vs mp3 lengths. Stimulus: gapless mp3 decode, left channel (L == R). "
         "Channel positions: standard_1005 template, not measured. Bad channels from the authors' "
         "code/preprocessing/config/bad_channels.tsv.")


class Pkueeg2025Adaptor:
    """
    PKUEEG (OpenNeuro ds008834): 25 Mandarin listeners, 50 synthesised Three Kingdoms stories (1-25 female voice,
    26-50 male) over three days (17/16/17 stories), one continuous BrainVision file per day at 1000 Hz: NeuroScan
    SynAmps2 on days 1-2, Neuracle NeuSen on day 3. One trial per speech row of events.tsv (session = day, trial =
    presentation order, condition = voice); rest intervals are skipped. Repeated stories use the last play.

    Onset = start marker + onset_shift_s (default: 1105/48000 s mp3 delay) + a measured offset in two sessions whose
    EEG is offset from its markers (SESSION_OFFSET_S); sub-25 day 3 is flagged suspect. drift_correction "system"
    (default: 76.8 ppm NeuroScan, none Neuracle) or None; applied with the onset in one interpolation. Channels as
    recorded (Day-3 upper-case labels mapped to 10-10 case), EOG/ECG kept, original reference. Stimuli: gapless mp3
    decode (ffmpeg, one channel, 48 kHz), TextGrid (words from the legacy segmentation timed by the MFA syllables,
    syllables, phones) and transcript. See notes.md.
    """

    def __init__(self, download_dir: str, onset_shift_s: float = ONSET_SHIFT_S,
                 drift_correction: str | None = "system"):
        if drift_correction not in ("system", None):
            raise ValueError(f"drift_correction must be 'system' or None, not {drift_correction!r}")
        self.root = download_dir
        self.onset_shift_s = onset_shift_s
        self.drift_correction = drift_correction
        bads = pd.read_csv(os.path.join(download_dir, "code", "preprocessing", "config", "bad_channels.tsv"),
                           sep="\t", keep_default_na=False)
        self.bads = {(r.participant_id, r.session_id): [] if r.bad_channels == "n/a" else r.bad_channels.split()
                     for r in bads.itertuples()}
        stimuli = os.path.join(download_dir, "stimuli", "stimuli.tsv")
        self.stimuli = pd.read_csv(stimuli, sep="\t").set_index("story_id")

    def parse(self) -> Iterable[TrialRecord]:
        for vhdr in sorted(glob.glob(os.path.join(self.root, "sub-*", "ses-day*", "eeg", "*_eeg.vhdr"))):
            sub, ses = os.path.basename(vhdr).split("_")[:2]
            subject, day = int(sub[4:]), int(ses[7:])
            system = SYSTEM[day]
            events = pd.read_csv(vhdr.replace("_eeg.vhdr", "_events.tsv"), sep="\t").sort_values("onset")
            labels = pd.read_csv(vhdr.replace("_eeg.vhdr", "_channels.tsv"), sep="\t").name.tolist()
            speech = events[events.trial_type == "speech"]
            for trial, ev in enumerate(speech.itertuples(), 1):
                story = int(ev.story_id)
                info = self.stimuli.loc[story]
                if f"ses-day{day}" != info.session_id or ev.stim_file != info.audio_file:
                    raise ValueError(f"{vhdr}: story {story} ({ev.stim_file}) does not belong to {ses}")
                name = f"story-{story:02d}"
                mp3 = os.path.join(self.root, "stimuli", info.audio_file)
                drift = DRIFT_APPLIED_PPM[system] if self.drift_correction else 0.0
                offset_s = SESSION_OFFSET_S.get((subject, day), 0.0)
                onset = ev.sample + (self.onset_shift_s + offset_s) * 1000
                quality = SUSPECT.get((subject, day))
                if offset_s:
                    quality = (f"corrected: onset moved by {offset_s:+.3f} s, the EEG response to every story of the "
                               "session precedes its marker by this constant (measured by envelope reconstruction, "
                               "+-~10 ms; not a story/marker mapping error)")
                description = provenance(
                    "sw_trigger", "unknown (README: hardware markers; source and presentation software "
                    "undocumented; ~2 ms jitter per marker, not sample-locked to the audio)", NOTES,
                    drift_ppm=DRIFT_PPM[system], jitter_ms=JITTER_MS, validation_tier="low",
                    drift_corrected_ppm=drift,
                    onset_shift_ms=round(self.onset_shift_s * 1000, 4), session_offset_ms=offset_s * 1000,
                    quality=quality, marker_sample=int(ev.sample),
                    marker_duration_s=float(ev.duration), story_id=story, presentation_order=trial, day=day,
                    eeg_system=AMPLIFIER[system], voice=info.voice_gender, voice_name=info.voice_name,
                    repeated_presentation=REPEATED.get((subject, day, story)),
                    candidate_pair_count=int(ev.candidate_pair_count), reference=REFERENCE[system],
                    online_filters=LOWPASS[system], units_as_shipped="V (BrainVision float32, header uV)",
                    montage="standard_1005 template (no digitisation)", original_labels=labels,
                    bads_source="authors' bad_channels.tsv")
                stimuli = [StimulusRecord("audio", name, _audio_loader(mp3, self._tg(story)), True, "audio"),
                           StimulusRecord("audio", name, self._textgrid_loader(story), True, "textgrid"),
                           StimulusRecord("audio", name, _text_loader(os.path.join(
                               self.root, "stimuli", info.transcript_file)), True, "transcript")]
                yield TrialRecord(subject=subject, session=day, trial=trial, condition=info.voice_gender,
                                  ns_type="eeg", stimulus=stimuli,
                                  neural_data_fn=_eeg_loader(vhdr, onset, mp3, self._tg(story), drift * 1e-6,
                                                             self.bads[(sub, ses)], description))

    def _tg(self, story: int) -> str:
        return os.path.join(self.root, "derivatives", "stimulus_annotations", "textgrid",
                            f"story-{story:02d}_alignment.TextGrid")

    def _textgrid_loader(self, story: int) -> Callable[[], str]:
        """Words (Hanzi, legacy segmentation, MFA syllable times), syllables (Pinyin, MFA) and phones (MFA)."""
        ann = os.path.join(self.root, "derivatives", "stimulus_annotations")

        def _loader() -> str:
            mfa = _read_tg(self._tg(story))
            syl, phones = mfa.getFirst("words"), mfa.getFirst("phones")
            syl = [s for s in syl if s.mark]
            hanzi = pd.read_csv(os.path.join(ann, "pinyin", "boundaries", f"story-{story:02d}_pinyin.tsv"),
                                sep="\t", dtype=str, keep_default_na=False)
            legacy = pd.read_csv(os.path.join(ann, "word_boundaries", "legacy", f"story-{story:02d}_words.tsv"),
                                 sep="\t", dtype=str, keep_default_na=False)
            if [s.mark for s in syl] != hanzi.pinyin.tolist():
                raise ValueError(f"story {story}: MFA syllables differ from the Pinyin boundary table")
            out = textgrid.TextGrid(maxTime=mfa.maxTime)
            for tier, items in (("words", _words(syl, hanzi.hanzi.tolist(), legacy.word.tolist())),
                                ("syllables", [(s.minTime, s.maxTime, s.mark) for s in syl]),
                                ("phones", [(p.minTime, p.maxTime, p.mark) for p in phones if p.mark])):
                t = textgrid.IntervalTier(tier, 0, mfa.maxTime)
                for a, b, mark in items:
                    t.add(a, b, mark)
                out.append(t)
            f = _Buffer()
            out.write(f)
            return f.getvalue()

        return _loader


class _Buffer(io.StringIO):
    """StringIO that survives TextGrid.write closing it."""

    def close(self):
        pass


def _words(syl: list, hanzi: list, words: list) -> list:
    """Legacy words timed by their MFA syllables (one Hanzi each); numerals (absent from the legacy words) kept."""
    out, i = [], 0
    for w in words + [None]:
        while i < len(syl) and hanzi[i].isdigit():
            out.append((syl[i].minTime, syl[i].maxTime, hanzi[i]))
            i += 1
        if w is None:
            break
        j = i + len(w)
        if "".join(hanzi[i:j]) != w:
            raise ValueError(f"legacy word {w!r} does not match syllables {hanzi[i:j]}")
        out.append((syl[i].minTime, syl[j - 1].maxTime, w))
        i = j
    if i != len(syl):
        raise ValueError(f"{len(syl) - i} syllables left after the last legacy word")
    return out


def _read_tg(path: str) -> textgrid.TextGrid:
    """MFA TextGrid at full precision (the package rounds to 4 digits by default)."""
    tg = textgrid.TextGrid()
    tg.read(path, round_digits=6)
    return tg


def _decode(mp3: str) -> np.ndarray:
    """Gapless decode (ffmpeg honours the LAME header), 48 kHz, left channel (L == R in every file)."""
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-c:a", "mp3float", "-i", mp3, "-map", "0:a:0",
                          "-f", "f32le", "-c:a", "pcm_f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, dtype="<f4").reshape(-1, 2)
    if not np.array_equal(x[:, 0], x[:, 1]):
        raise ValueError(f"{mp3}: left and right channels differ")
    return x[:, 0].copy()


@lru_cache(maxsize=None)
def _n_audio(mp3: str, tg: str) -> int:
    """Gapless length in samples; must equal the MFA TextGrid end (same time base)."""
    n = len(_decode(mp3))
    n_tg = round(_read_tg(tg).maxTime * FS_AUDIO)
    if n != n_tg:
        raise ValueError(f"{mp3}: {n} decoded samples, TextGrid ends at {n_tg}")
    return n


def _audio_loader(mp3: str, tg: str) -> Callable[[], dict]:
    def _loader() -> dict:
        x = _decode(mp3)
        if len(x) != _n_audio(mp3, tg):
            raise ValueError(f"{mp3}: decoded length changed")
        return {"fs": FS_AUDIO, "data": x[None, :]}

    return _loader


def _text_loader(path: str) -> Callable[[], str]:
    def _loader() -> str:
        with open(path, encoding="utf-8") as f:
            return f.read()

    return _loader


@lru_cache(maxsize=1)
def _read(vhdr: str) -> mne.io.BaseRaw:
    """Lazy BrainVision reader; channel types from channels.tsv, Day-3 upper-case labels in 10-10 case."""
    raw = mne.io.read_raw_brainvision(vhdr, preload=False, verbose="ERROR")
    ch = pd.read_csv(vhdr.replace("_eeg.vhdr", "_channels.tsv"), sep="\t")
    if ch.name.tolist() != raw.ch_names:
        raise ValueError(f"{vhdr}: channels.tsv does not match the header")
    raw.set_channel_types(dict(zip(ch.name, ch.type.map(TYPES))), verbose="ERROR")
    standard = {c.upper(): c for c in make_standard_montage("standard_1005").ch_names}
    raw.rename_channels({c: standard[c.upper()] for c, t in zip(ch.name, ch.type) if t == "EEG"})
    return raw


def _eeg_loader(vhdr: str, onset: float, mp3: str, tg: str, drift: float, bads: list, description: str):
    def _loader() -> mne.io.BaseRaw:
        raw = _read(vhdr)
        n_out = math.ceil(_n_audio(mp3, tg) * raw.info["sfreq"] / FS_AUDIO)
        out = crop_on_audio_clock(raw, onset, n_out, drift)
        if out.n_times != n_out:
            raise ValueError(f"{vhdr}: recording ends {n_out - out.n_times} samples before the stimulus")
        out.set_montage(make_standard_montage("standard_1005"), verbose="ERROR")
        upper = {c.upper(): c for c in out.ch_names}
        out.info["bads"] = [upper[b.upper()] for b in bads]
        out.info["description"] = description
        return out

    return _loader


ADAPTOR = Pkueeg2025Adaptor
