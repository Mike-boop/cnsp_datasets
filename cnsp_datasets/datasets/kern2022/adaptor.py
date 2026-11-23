from __future__ import annotations

import math
import os
from functools import lru_cache
from typing import Iterable

import mne
import numpy as np
import pandas as pd
from scipy.io import wavfile

from cnsp_datasets.datasets.kern2022.drift import FS, OUT as AUDIO_FIT, recording, wav_path
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

# sound onset after the UPPT001 trigger of a piece and MEG vs audio clock drift: medians over the 210 reliable piece
# fits (6 pieces x 35 participants) in audio_fit.csv (UADC002 audio copy; notes.md sections 6-7)
MUSIC_DELAY_MS = 4.1
DRIFT_PPM = 6.5
# SD of the sound onset around the trigger: pieces, within-participant SD of the piece delays (median 0.4 ms);
# test snippets, SD of each snippet's delay across runs (2.1-2.5 ms; notes.md section 6)
JITTER_MS = {"music": 0.4, "test": 2.5}
# kept next to MEG and reference sensors: audio copy, EyeLink x, y, pupil. UADC001 (same audio), UADC003/004 (audio
# in sub001 only), UADC008-013 and EEG057-064 (unconnected inputs) are dropped (notes.md section 5)
KEEP = ("UADC002", "UADC005", "UADC006", "UADC007")
TRIGGER = "software (BITSI trigger sent by Psychtoolbox after PsychPortAudio('Start'); RunSingleTrial.m)"


class Kern2022Adaptor:
    """
    Kern, Heilbron, de Lange & Spaak 2022 (Donders DSC_3018045.02_116_v1): 35 participants, one CTF-275 MEG session
    each (269 axial gradiometers, 29 reference sensors) at 1200 Hz, resampled to sfreq=1000 (default; None keeps
    1200 Hz). 19 monophonic pieces (codes 101-119, condition `music`) and the volume-setting test snippets (codes 1-3,
    condition `test`), one trial per UPPT001 trigger as listed in audio_fit.csv (drift.py). Stimulus: wav channel 0,
    the one played to both ears. audio_delay=True starts each trial at the sound onset measured on the UADC002 audio
    copy (pieces: +MUSIC_DELAY_MS; test snippets: the trial's own delay, which for snippet 2 rests on a weak fit that
    agrees with snippet 3); drift_correction=True resamples onto the audio clock (+DRIFT_PPM) in the same resample.
    Both are hardware-derived and on by default (user, 2026-11-23). Channels: MEG, reference sensors, UADC002 (audio
    copy), UADC005-007 (EyeLink x, y, pupil). `subjects` limits the participants (e.g. [1, 10]; pilots). See notes.md.
    """

    def __init__(self, download_dir: str, sfreq: float | None = 1000, audio_delay: bool = True,
                 drift_correction: bool = True, subjects: Iterable[int] | None = None):
        self.download_dir = download_dir
        self.sfreq = sfreq
        self.audio_delay = audio_delay
        self.drift = DRIFT_PPM * 1e-6 if drift_correction else 0.0
        self.subjects = None if subjects is None else set(subjects)
        overview = pd.read_csv(os.path.join(download_dir, "MusicData", "MusicMEG", "OverviewMusicMEG.csv"),
                               encoding="utf-8-sig")
        self.names = dict(zip(overview.ID, overview.Filename))

    def parse(self) -> Iterable[TrialRecord]:
        fits = pd.read_csv(AUDIO_FIT)
        for sub, rows in fits.groupby("subject"):
            subject = int(sub[3:])
            if self.subjects is not None and subject not in self.subjects:
                continue
            ds = recording(self.download_dir, sub)
            for trial, row in enumerate(rows.itertuples(), 1):
                condition = "music" if row.code > 100 else "test"
                name = self.names[row.code] if condition == "music" else f"test{row.code}"
                delay = MUSIC_DELAY_MS if condition == "music" else row.delay_ms
                onset = row.trigger_samp + (delay * 1e-3 * FS if self.audio_delay else 0)
                wav = wav_path(self.download_dir, row.code)
                # pieces get the dataset-median delay (trigger-based); test snippets their own measured delay
                method = "stimtrack_xcorr" if self.audio_delay and condition == "test" else "sw_trigger"
                description = provenance(
                    method, TRIGGER,
                    f"Sound {delay:.1f} ms after the trigger ({'corrected' if self.audio_delay else 'not corrected'})"
                    f" and drift {'corrected' if self.drift else 'not corrected'}: hardware-derived (UADC002 audio"
                    " copy), corrected by default (user, 2026-11-23). See notes.md.",
                    drift_ppm=DRIFT_PPM, jitter_ms=JITTER_MS[condition], piece_code=int(row.code),
                    onset_corrected=self.audio_delay, drift_corrected=bool(self.drift))
                yield TrialRecord(subject=subject, session=1, trial=trial, condition=condition,
                                  ns_type="meg",
                                  stimulus=StimulusRecord("audio", name, _wav_loader(wav), True, "audio"),
                                  neural_data_fn=self._meg_loader(ds, onset, wav, description))

    def _meg_loader(self, ds: str, onset: float, wav: str, description: str):
        def _loader():
            raw = _read(ds)
            sf = raw.info["sfreq"]
            sf_out = sf if self.sfreq is None else min(self.sfreq, sf)
            fs, x = wavfile.read(wav, mmap=True)
            picks = mne.pick_types(raw.info, meg=True, ref_meg=True, eeg=False).tolist() + \
                [i for i, c in enumerate(raw.ch_names) if c.startswith(KEEP)]
            out = crop_on_audio_clock(raw, onset, math.ceil(len(x) / fs * sf_out), self.drift, picks, sf_out)
            out.info["description"] = description
            return out

        return _loader


def _wav_loader(path: str):
    """Channel 0 of the stereo wav: the channel played to both ears (RunSingleTrial.m)."""
    def _loader():
        fs, x = wavfile.read(path)
        return {"fs": fs, "data": np.ascontiguousarray(x[:, 0])[None, :]}

    return _loader


@lru_cache(maxsize=1)
def _read(ds: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_ctf(ds, preload=False, verbose="ERROR")


ADAPTOR = Kern2022Adaptor
