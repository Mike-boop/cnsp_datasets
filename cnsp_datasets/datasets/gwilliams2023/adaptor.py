from __future__ import annotations

import ast
import glob
import math
import os
from functools import lru_cache
from typing import Iterable

import mne
import numpy as np
import pandas as pd
import soundfile
from scipy.signal import butter, correlate, hilbert, resample_poly, sosfiltfilt

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.iohelpers import audio_loader, read_wav, textgrid
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS_MEG = 1000
AUDIO_CH = "MISC 009"  # copy of the sound on the MEG system (notes.md section 6)
DRIFT_PPM = -46.0      # MEG clock vs audio clock, median over all 1470 sounds (notes.md section 7)
SEARCH = 0.5           # s: onset search around the trigger
_ENV = butter(4, [2, 40], "bandpass", fs=FS_MEG, output="sos")


class Gwilliams2023Adaptor(BaseAdaptor):
    """
    MEG-MASC (Gwilliams et al. 2023, OSF ag3kj + hqvm3 + u5327 + dr4wy): 27 subjects, 1-2 sessions, four
    synthesised stories (task 0-3), each split into ~3 min wavs. KIT 208-channel MEG (+16 reference sensors),
    1000 Hz. One trial per wav, numbered in presentation order (participants.tsv task_order).

    onset="audio" (default): each sound's onset is measured on the audio copy (MISC 009) by envelope
    cross-correlation within +-0.5 s of its trigger; the shipped `sound` events (trigger) are ~44 ms early.
    onset="trigger" uses the events as shipped. drift_correction=True (default) resamples the MEG onto the audio
    clock (-46 ppm). Channels: MEG, reference sensors (bads kept and listed), MISC 009. Stimuli: the wav as shipped
    (float32) and a TextGrid (words, phones) from the events. See notes.md.
    """

    def __init__(self, download_dir: str, onset: str = "audio", drift_correction: bool = True):
        super().__init__(download_dir)
        self.onset = self.choice("onset", onset, ("audio", "trigger"))
        self.drift = DRIFT_PPM * 1e-6 if drift_correction else 0.0

    def parse(self) -> Iterable[TrialRecord]:
        participants = pd.read_csv(self.path("participants.tsv"), sep="\t")
        order = {r.participant_id: ast.literal_eval(r.task_order) for r in participants.itertuples()}
        for sub in sorted(order):
            for ses_dir in sorted(glob.glob(os.path.join(self.download_dir, sub, "ses-*"))):
                session = int(ses_dir.rsplit("-", 1)[1])
                trial = 0
                for task in order[sub]:
                    con = os.path.join(ses_dir, "meg", f"{sub}_ses-{session}_task-{task}_meg.con")
                    if not os.path.exists(con):
                        continue
                    for onset, name, words in self._sounds(con):
                        trial += 1
                        yield TrialRecord(
                            subject=int(sub[4:]),
                            session=session,
                            trial=trial,
                            condition=name.rsplit("_", 1)[0].replace("_", "-"),
                            ns_type="meg",
                            stimulus=self._stimuli(name, words),
                            neural_data_fn=self._meg_loader(con, onset, name),
                        )

    def _sounds(self, con: str):
        """(trigger onset in s, wav name, word/phoneme rows) per sound of one recording."""
        events = pd.read_csv(con.replace("_meg.con", "_events.tsv"), sep="\t")
        rows = [dict(ast.literal_eval(t), onset=o, duration=d)
                for t, o, d in zip(events.trial_type, events.onset, events.duration)]
        sounds = [r for r in rows if r["kind"] == "sound"]
        for s in sounds:
            name = os.path.basename(s["sound"]).replace(".0.wav", "").replace(".wav", "").lower()
            words = [r for r in rows if r["kind"] in ("word", "phoneme")
                     and os.path.basename(r["sound"]).replace(".wav", "").lower() == name]
            yield s["onset"], name, words

    def _wav(self, name: str) -> str:
        return os.path.join(self.download_dir, "stimuli", "audio", f"{name}.wav")

    def _stimuli(self, name: str, words: list) -> list:
        def _textgrid():
            return textgrid({tier: [(r["start"], r["start"] + r["duration"], str(r[key]))
                                    for r in words if r["kind"] == kind]
                             for kind, tier, key in (("word", "words", "word"), ("phoneme", "phones", "phoneme"))})

        return [StimulusRecord("audio", name, audio_loader(self._wav(name)), True, feature_name="audio"),
                StimulusRecord("audio", name, _textgrid, True, feature_name="textgrid")]

    def _meg_loader(self, con: str, trigger: float, name: str):
        def _loader():
            raw = _read(con)
            fs, n = _wav_info(self._wav(name))
            onset = trigger * FS_MEG
            if self.onset == "audio":
                onset += measure_lag(con, trigger, self._wav(name)) * FS_MEG
            n_out = math.ceil(n * FS_MEG / fs)
            picks = mne.pick_types(raw.info, meg=True, ref_meg=True, misc=False, exclude=[]).tolist() + \
                [raw.ch_names.index(AUDIO_CH)]
            return crop_on_audio_clock(raw, onset, n_out, self.drift, picks=picks)

        return _loader


@lru_cache(maxsize=1)
def _read(con: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_kit(con, preload=False, verbose="ERROR")


@lru_cache(maxsize=1)
def _audio_channel_envelope(con: str) -> np.ndarray:
    return sosfiltfilt(_ENV, np.abs(hilbert(_read(con).get_data(picks=AUDIO_CH)[0])))


@lru_cache(maxsize=64)
def _wav_envelope(path: str) -> np.ndarray:
    x, fs = read_wav(path, channel=0)  # scaled to [-1, 1): the lag (argmax) is unchanged
    return sosfiltfilt(_ENV, np.abs(hilbert(resample_poly(x[0].astype(float), FS_MEG, fs))))


def _wav_info(path: str):
    info = soundfile.info(path)
    return info.samplerate, info.frames


def measure_lag(con: str, trigger: float, wav: str) -> float:
    """Delay (s) of the sound on the audio channel after its trigger: envelope cross-correlation, sub-sample."""
    env, ref = _audio_channel_envelope(con), _wav_envelope(wav)
    s0 = int(round(trigger * FS_MEG))
    lo, hi = max(0, s0 - int(SEARCH * FS_MEG)), s0 + int(SEARCH * FS_MEG)
    ref = ref[:min(len(ref), len(env) - hi)]
    c = correlate(env[lo:hi + len(ref)], ref, "valid")
    k = int(np.argmax(c))
    d = 0.0
    if 0 < k < len(c) - 1:
        d = 0.5 * (c[k - 1] - c[k + 1]) / (c[k - 1] - 2 * c[k] + c[k + 1])
    return (lo + k + d - s0) / FS_MEG


ADAPTOR = Gwilliams2023Adaptor
