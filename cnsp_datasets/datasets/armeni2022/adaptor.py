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
# kept next to MEG and reference sensors: audio copy, EyeLink x, y, pupil (paper, Table 5); EEG057-064 carry no
# signal and are dropped (notes.md section 5)
KEEP = ("UADC003", "UADC005", "UADC006", "UADC007")
# (participant, session): run 3 of sub-003 ses-008 crashed and was restarted; the restart has no wav_onset event.
# Its onset was measured on UADC003 (08_3.wav, r = 0.98; ends at the run-3 offset marker; notes.md section 6).
EXTRA_ONSETS = {(3, 8): [(30, 2022.901)]}
# unstable channels listed in the paper ("MRP5" is MRP55: 24x the median SD; notes.md section 5)
BADS = {(3, 4): ["MRC23", "MLO22", "MRP55", "MLC23"]}


class Armeni2022Adaptor:
    """
    Armeni et al. 2022 (Donders DSC_3011085.05_995_v1): 3 participants x 10 sessions, CTF-275 MEG (269 axial
    gradiometers, 29 reference sensors) at 1200 Hz, resampled to sfreq=1000 (default; None keeps 1200 Hz).
    Each session plays 7-8 parts of The Adventures of Sherlock Holmes (`stimuli/<session>_<part>.wav`, wav_onset
    codes 10, 20, ...), each followed by two repeats of a 29 s noise-ceiling passage (codes 100/150).

    One trial per wav_onset event (condition `story` or `repeat`), plus the restarted run 3 of sub-003 ses-008 (no
    event; onset measured). Onsets as shipped: the authors already corrected each part's audio delay from the UADC003
    audio channel (checked: within +-2 ms). Channels: MEG, reference sensors, UADC003 (audio), UADC005-007 (EyeLink
    x, y, pupil); the paper's unstable channels of sub-003 ses-004 are marked bad. drift_correction=True (default)
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
            onsets = [(int(v), o) for v, o in zip(events.value[events.type == "wav_onset"],
                                                  events.onset[events.type == "wav_onset"])]
            onsets = sorted(onsets + EXTRA_ONSETS.get((sub, ses), []), key=lambda x: x[1])
            for trial, (code, onset) in enumerate(onsets, 1):
                repeat = code in REPEAT_CODES
                name = "noise_ceiling" if repeat else f"{ses:02d}_{code // 10}"
                if onset < 0:
                    continue  # sub-003 ses-001 part 1: recording started after the audio (notes.md section 6)
                stimuli = [StimulusRecord("audio", name, _wav_loader(self._wav(name)), True, "audio")]
                if not repeat:
                    stimuli.append(StimulusRecord("audio", name, self._textgrid_loader(ses, code // 10), True,
                                                  "textgrid"))
                yield TrialRecord(subject=sub, session=ses, trial=trial, condition="repeat" if repeat else "story",
                                  ns_type="meg", stimulus=stimuli,
                                  neural_data_fn=self._meg_loader(ds, onset, self._wav(name), BADS.get((sub, ses), [])))

    def _textgrid_loader(self, ses: int, part: int):
        """
        Words and phones of one story part, relative to its onset. Taken from the first participant whose annotations
        of the part start at its own wav_onset (within 0.1 s): in sub-003 ses-008 they are shifted by one part after
        the crashed run (notes.md section 3). Within a wav the timings are the same for every participant.
        """
        def _loader():
            for ev_path in sorted(glob.glob(os.path.join(self.download_dir, "sub-*", f"ses-{ses:03d}", "meg",
                                                         "*_task-compr_events.tsv"))):
                ev = pd.read_csv(ev_path, sep="\t")
                onset = ev.onset[(ev.type == "wav_onset") & (ev.value.astype(str) == str(part * 10))]
                words = ev[ev.type == f"word_onset_{part:02d}"]
                if len(onset) == 1 and len(words) and 0 <= words.onset.min() - onset.iloc[0] < 0.1:
                    return _textgrid_text(ev, part, onset.iloc[0])
            raise ValueError(f"no consistent annotations for session {ses} part {part}")

        return _loader

    def _wav(self, name: str) -> str:
        return os.path.join(self.download_dir, "stimuli", f"{name}.wav")

    def _meg_loader(self, ds: str, onset: float, wav: str, bads: list):
        def _loader():
            raw = _read(ds)
            sf = raw.info["sfreq"]
            sf_out = sf if self.sfreq is None else min(self.sfreq, sf)
            fs, x = wavfile.read(wav, mmap=True)
            picks = mne.pick_types(raw.info, meg=True, ref_meg=True, eeg=False).tolist() + \
                [i for i, c in enumerate(raw.ch_names) if c.startswith(KEEP)]
            out = crop_on_audio_clock(raw, onset * sf, math.ceil(len(x) / fs * sf_out), self.drift, picks, sf_out)
            out.info["bads"] = [c for c in out.ch_names if c.split("-")[0] in bads]
            return out

        return _loader


def _wav_loader(path: str):
    def _loader():
        fs, x = wavfile.read(path)
        return {"fs": fs, "data": x[None, :]}

    return _loader


def _textgrid_text(events: pd.DataFrame, part: int, onset: float) -> str:
    tiers = {}
    for kind, tier in (("word_onset", "words"), ("phoneme_onset", "phones")):
        r = events[events.type == f"{kind}_{part:02d}"]
        tiers[tier] = dict(item=r.value.str.strip('"').tolist(), onset_s=(r.onset - onset).round(5).tolist(),
                           offset_s=(r.onset - onset + r.duration.astype(float)).round(5).tolist())
    return multi_tier_dict_to_textgrid(tiers)


@lru_cache(maxsize=1)
def _read(ds: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_ctf(ds, preload=False, verbose="ERROR")


ADAPTOR = Armeni2022Adaptor
