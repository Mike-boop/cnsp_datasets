from __future__ import annotations

import glob
import math
import os
from functools import lru_cache
from typing import Iterable

import mne
import pandas as pd
from scipy.io import wavfile

from cnsp_datasets.datasets.broderick2019_natural.utils import multi_tier_dict_to_textgrid
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

DRIFT_PPM = 5.7      # MEG clock vs audio clock, median over all story parts (notes.md section 7)
REPEAT_CODES = (100, 150)  # noise-ceiling passage (stimuli/noise_ceiling.wav)
KEEP = ("UADC003",)  # audio copy, kept next to MEG, reference sensors and EEG057-064


class Armeni2022Adaptor:
    """
    Armeni et al. 2022 (Donders DSC_3011085.05_995_v1): 3 participants x 10 sessions, CTF-275 MEG (269 axial
    gradiometers, 29 reference sensors) at 1200 Hz, resampled to sfreq=1000 (default; None keeps 1200 Hz).
    Each session plays 7-8 parts of The Adventures of Sherlock Holmes (`stimuli/<session>_<part>.wav`, wav_onset
    codes 10, 20, ...), each followed by two repeats of a 29 s noise-ceiling passage (codes 100/150).

    One trial per wav_onset event (condition `story` or `repeat`). Onsets as shipped: the authors already corrected
    each part's audio delay from the UADC003 audio channel (checked: within +-2 ms). drift_correction=True (default)
    resamples onto the audio clock (+5.7 ppm), in the same interpolation as the resampling. Stimuli: the wav as
    shipped and, for story parts, a TextGrid (words, phones) from the events. See notes.md.
    """

    def __init__(self, download_dir: str, sfreq: float | None = 1000, drift_correction: bool = True):
        self.download_dir = download_dir
        self.sfreq = sfreq
        self.drift = DRIFT_PPM * 1e-6 if drift_correction else 0.0

    def parse(self) -> Iterable[TrialRecord]:
        for ds in sorted(glob.glob(os.path.join(self.download_dir, "sub-*", "ses-*", "meg", "*_task-compr_meg.ds"))):
            sub, ses = (int(p.split("-")[1]) for p in os.path.basename(ds).split("_")[:2])
            events = pd.read_csv(ds.replace("_meg.ds", "_events.tsv"), sep="\t")
            for trial, e in enumerate(events[events.type == "wav_onset"].itertuples(), 1):
                code = int(e.value)
                repeat = code in REPEAT_CODES
                name = "noise_ceiling" if repeat else f"{ses:02d}_{code // 10}"
                if e.onset < 0:
                    continue  # sub-003 ses-001 part 1: recording started after the audio (notes.md section 6)
                stimuli = [StimulusRecord("audio", name, _wav_loader(self._wav(name)), True, "audio")]
                if not repeat:
                    stimuli.append(StimulusRecord("audio", name, _textgrid_loader(events, code // 10, e.onset), True,
                                                  "textgrid"))
                yield TrialRecord(subject=sub, session=ses, trial=trial, condition="repeat" if repeat else "story",
                                  ns_type="meg", stimulus=stimuli,
                                  neural_data_fn=self._meg_loader(ds, e.onset, self._wav(name)))

    def _wav(self, name: str) -> str:
        return os.path.join(self.download_dir, "stimuli", f"{name}.wav")

    def _meg_loader(self, ds: str, onset: float, wav: str):
        def _loader():
            raw = _read(ds)
            sf = raw.info["sfreq"]
            sf_out = sf if self.sfreq is None else min(self.sfreq, sf)
            fs, x = wavfile.read(wav, mmap=True)
            picks = mne.pick_types(raw.info, meg=True, ref_meg=True, eeg=True).tolist() + \
                [i for i, c in enumerate(raw.ch_names) if c.startswith(KEEP)]
            return crop_on_audio_clock(raw, onset * sf, math.ceil(len(x) / fs * sf_out), self.drift, picks, sf_out)

        return _loader


def _wav_loader(path: str):
    def _loader():
        fs, x = wavfile.read(path)
        return {"fs": fs, "data": x[None, :]}

    return _loader


def _textgrid_loader(events: pd.DataFrame, part: int, onset: float):
    def _loader():
        tiers = {}
        for kind, tier in (("word_onset", "words"), ("phoneme_onset", "phones")):
            r = events[events.type == f"{kind}_{part:02d}"]
            tiers[tier] = dict(item=r.value.str.strip('"').tolist(), onset_s=(r.onset - onset).round(5).tolist(),
                               offset_s=(r.onset - onset + r.duration.astype(float)).round(5).tolist())
        return multi_tier_dict_to_textgrid(tiers)

    return _loader


@lru_cache(maxsize=1)
def _read(ds: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_ctf(ds, preload=False, verbose="ERROR")


ADAPTOR = Armeni2022Adaptor
