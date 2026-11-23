from __future__ import annotations

import math
import os
from functools import lru_cache
from typing import Iterable

import mne
import numpy as np
import pandas as pd
from scipy.io import wavfile

from cnsp_datasets.datasets.chen2023.triggers import read_fif
from cnsp_datasets.datasets.chen2023.vocoder import vocode
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

TRIGGERS_CSV = os.path.join(os.path.dirname(__file__), "triggers.csv")  # from triggers.py (STI101 codes)
SFREQ = 1000.0
SOUND_DELAY_MS = 16.0  # trigger-to-sound delay measured by the authors (Black Box Toolkit v2; paper section 2.2)
# EOG001, EOG002, ECG003, EEG010; sub-5551a7b45438 and sub-400fb1b90f57: EOG002, EOG004, ECG003, EEG010, EEG060
OTHER_SETUP = {"sub-5551a7b45438", "sub-400fb1b90f57"}
LICENCE = ("ANC Data Use Agreement 1.0.2: use for scientific or educational purposes; no redistribution of the "
           "dataset in whole or in part, in any form (section 2.2); cite with the commit hash")
NOTES = ("MEGIN TRIUX, MaxFilter 2.2.15 SSS applied by the authors (as shipped). Trial = one stimulus trigger on "
         "STI101 (code = condition base + stimulus number, authors' code); events.tsv misses some trials. Onset = "
         "trigger + 16 ms trigger-to-sound delay measured by the authors. No audio copy in the recording; no drift "
         "correction. EOG channels: direction unknown; EEG010 (and EEG060): EEG electrodes of unknown placement, kept "
         "as misc. Vocoded trials: the vocoded sounds are not shipped; the stimulus is the clean source wav or "
         "(option 'rebuild') a rebuild with fresh noise. " + LICENCE)


class Chen2023Adaptor:
    """
    Chen et al. (2023, NeuroImage), ANC dataset yc_audiobook_vocoding: 24 subjects, MEGIN TRIUX 306-channel MEG at
    1000 Hz (SSS applied), Goethe's "Das Maerchen" in 24 excerpts (16-194 s), each heard at most once per subject in
    one of six conditions (original, 7/5/3/2/1-channel noise vocoded); 24, 21 or 3 trials per subject (missing runs,
    notes.md). Subjects are numbered 1-24 in the order of their sorted BIDS ids; the original id is in the
    provenance. Trial = 3 * (run - 1) + position in the run.

    vocoded: what the vocoded trials carry as their stimulus.
      "clean" (default): the clean source wav (what was vocoded; its envelope is close to the vocoded one).
      "rebuild": an n-channel vocoded rebuild (vocoder.py, fixed seed per stimulus and n). Only the band envelopes
                 match the presented sound, not the noise fine structure (notes.md, section 4).
      None: vocoded trials are skipped.
    """

    def __init__(self, download_dir: str, vocoded: str | None = "clean", sound_delay_ms: float = SOUND_DELAY_MS):
        if vocoded not in ("clean", "rebuild", None):
            raise ValueError(f"vocoded must be 'clean', 'rebuild' or None, not {vocoded!r}")
        self.download_dir = download_dir
        self.vocoded = vocoded
        self.sound_delay_ms = sound_delay_ms
        self.table = pd.read_csv(TRIGGERS_CSV)

    def parse(self) -> Iterable[TrialRecord]:
        subjects = {s: i for i, s in enumerate(sorted(self.table.subject.unique()), 1)}
        for t in self.table.itertuples():
            n = None if t.condition == "original" else int(t.condition[0])  # "7chan" -> 7
            if n is not None and self.vocoded is None:
                continue
            fif = os.path.join(self.download_dir, t.subject, "ses-1", "meg",
                               f"{t.subject}_ses-1_task-audiobook_run-{t.run:02d}_meg.fif")
            wav = os.path.join(self.download_dir, "stimuli", f"{t.stim:02d}.wav")
            rebuilt = n is not None and self.vocoded == "rebuild"
            name = f"{t.stim:02d}_{n}ch_rebuilt" if rebuilt else f"{t.stim:02d}"
            onset = t.sample + self.sound_delay_ms * SFREQ / 1000  # samples from the first sample of the file
            eeg = ["EEG010", "EEG060"] if t.subject in OTHER_SETUP else ["EEG010"]
            description = provenance(
                "hw_trigger", "unknown (VPixx presentation; trigger-to-sound delay measured by the authors)", NOTES,
                validation_tier=None, original_subject=t.subject, run=int(t.run), position=int(t.position),
                trigger_code=int(t.code), stim_file=f"stimuli/{t.stim:02d}.wav", trigger_sample=int(t.sample),
                sound_delay_ms=self.sound_delay_ms, vocoder_channels=n,
                stimulus=("rebuilt vocoded (envelopes only)" if rebuilt else
                          "clean source wav (vocoded sound not shipped)" if n else "as played"),
                sss="MaxFilter 2.2.15 SSS (authors)", reference="none (MEG)", licence=LICENCE,
                external_sensors={c: "EEG electrode, placement unknown (type misc)" for c in eeg})
            yield TrialRecord(
                subject=subjects[t.subject], session=1, trial=3 * (t.run - 1) + t.position, condition=t.condition,
                ns_type="meg",
                stimulus=StimulusRecord("audio", name, _audio_loader(wav, n if rebuilt else None, t.stim),
                                        is_attended=True),
                neural_data_fn=_meg_loader(fif, onset, wav, description),
            )


@lru_cache(maxsize=1)
def _read(fif: str) -> mne.io.BaseRaw:
    """The run with MEG, EOG, ECG and EEG channels (EEG retyped misc), cached for the run's three trials."""
    raw = read_fif(fif)
    if raw.info["sfreq"] != SFREQ:
        raise ValueError(f"{fif}: {raw.info['sfreq']} Hz, expected {SFREQ}")
    raw.pick(np.concatenate([mne.pick_types(raw.info, meg=True),  # MEG first, then the peripherals
                             mne.pick_types(raw.info, meg=False, eog=True, ecg=True, eeg=True)]))
    eeg = [raw.ch_names[i] for i in mne.pick_types(raw.info, meg=False, eeg=True)]
    raw.set_channel_types(dict.fromkeys(eeg, "misc"), on_unit_change="ignore")
    return raw


@lru_cache(maxsize=1)
def _wav(path: str) -> tuple[int, np.ndarray]:
    """Sample rate and first channel of a stimulus wav (dual mono: L = R in every file)."""
    fs, x = wavfile.read(path)
    return fs, x[:, 0]


def _meg_loader(fif: str, onset: float, wav: str, description: str):
    """The trial: as many samples as the wav lasts, from the sound onset."""
    def _loader():
        fs, x = _wav(wav)
        n_out = math.ceil(len(x) * SFREQ / fs)
        out = crop_on_audio_clock(_read(fif), onset, n_out)
        if out.n_times != n_out:
            raise ValueError(f"{fif}: recording ends {n_out - out.n_times} samples before the stimulus")
        out.info["description"] = description
        return out

    return _loader


def _audio_loader(path: str, n: int | None, stim: int):
    """The clean wav, or its n-channel vocoded rebuild."""
    def _loader():
        fs, x = _wav(path)
        if n is not None:
            x = vocode(x, fs, n, seed=100 * stim + n).astype(np.float32)
        return {"fs": fs, "data": x[None, :]}

    return _loader


ADAPTOR = Chen2023Adaptor
