from __future__ import annotations

import glob
import math
import os
from functools import lru_cache
from typing import Iterable

import mne
import pandas as pd
from scipy.io import wavfile

from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

RUNS = [("audiobook1", 1), ("audiobook1", 2), ("audiobook2", 1), ("audiobook2", 2)]  # presentation order
STORIES = {"audiobook1": "Das schwatzende Herz (Poe)", "audiobook2": "Die Maske des roten Todes (Poe)"}
DRIFT_CSV = os.path.join(os.path.dirname(__file__), "drift.csv")  # from drift.py (MISC001 vs wav, per run)
ACOUSTIC_DELAY_MS = 0.4  # authors' 3 ms after the trigger minus the 2.6 ms of MISC001 (notes.md, open question 3)
BADS = ["MEG2143", "MEG1112"]  # always marked bad by the authors (scan protocols)
AUDIO_COPY = {"MISC001": "audio copy, left channel (V)", "MISC002": "audio copy, right channel (V)"}
NOTES = ("Raw MEGIN TRIUX data as shipped: no SSS/MaxFilter (the authors' tSSS + movement-compensated files are "
         "on OpenNeuro, derivatives/sub-XX/maxfilter); fine-calibration and cross-talk files ship with the raw "
         "data. Onset = first 1 s audiobook trigger (events.tsv; hardware TTL from the sound card) + the run's "
         "audio-copy (MISC001) onset from cross-correlation with the wav + 0.4 ms assumed acoustic delay. "
         "Sound-card vs MEG clock drift (~+485 ppm) measured per run on MISC001. cHPI lines (261-328 Hz) remain "
         "in the data. MISC001/MISC002 = audio copy (diotic).")
VALIDATION_NOTE = ("brainstem tier with tSSS (Maxwell filtering, applied by the user; standardised data are raw); "
                   "raw data reach mlr")


class Habersetzer2025Adaptor:
    """
    MEG-SCANS (Habersetzer et al. 2025, OpenNeuro ds006468): 24 subjects, MEGIN TRIUX 306-channel MEG at 1000 Hz,
    raw (no SSS). Two German Poe audiobooks (conditions audiobook1, audiobook2), two runs each; one trial per run
    (trial = presentation order 1-4), starting at the audio onset and as long as the wav. sub-01 (pilot) heard
    preliminary audiobook1 versions (stimuli `pilot_audiobook1_run-0N`) and no audiobook2. OLSA, chirps and
    empty-room runs are not used.

    Onset: first audiobook trigger + the run's audio-copy onset (drift.csv) + 0.4 ms acoustic delay. drift_correction:
    "run" (default; the run's drift from drift.csv), "dataset" (median over runs, +485.07 ppm) or None; corrected
    by resampling onto the audio clock. Channels: MEG, EOG, ECG, MISC001/002 (audio copy); MEG2143 and MEG1112 bad.
    Stimuli: wav as shipped (44.1 kHz) and the shipped TextGrid (words, phones). See notes.md.
    """

    def __init__(self, download_dir: str, drift_correction: str | None = "run"):
        if drift_correction not in ("run", "dataset", None):
            raise ValueError(f"drift_correction must be 'run', 'dataset' or None, not {drift_correction!r}")
        self.download_dir = download_dir
        self.drift_correction = drift_correction
        self.table = pd.read_csv(DRIFT_CSV).set_index("file")

    def parse(self) -> Iterable[TrialRecord]:
        for sub_dir in sorted(glob.glob(os.path.join(self.download_dir, "sub-*"))):
            sub = os.path.basename(sub_dir)
            for trial, (task, run) in enumerate(RUNS, 1):
                fif = os.path.join(sub_dir, "meg", f"{sub}_task-{task}_run-{run:02d}_meg.fif")
                if not os.path.exists(fif):
                    continue
                m = self.table.loc[os.path.basename(fif)]
                stim_file = audiobook_events(fif).stim_file.iloc[0]
                if stim_file != m.stim_file:
                    raise ValueError(f"{fif}: events.tsv names {stim_file}, drift.csv {m.stim_file}")
                name = ("pilot_" if "/pilot/" in stim_file else "") + f"{task}_run-{run:02d}"
                wav = os.path.join(self.download_dir, "stimuli", stim_file)
                drift = {"run": m.drift_ppm, "dataset": self.table.drift_ppm.median(), None: 0.0}[
                    self.drift_correction]
                onset = m.first_trig_sample + m.onset_ms + ACOUSTIC_DELAY_MS  # samples at 1000 Hz
                description = provenance(
                    "stimtrack_xcorr", "hardware (paper: sound-card trigger channel -> FPGA box -> TTL)", NOTES,
                    drift_ppm=round(float(m.drift_ppm), 3), jitter_ms=0.01, validation_tier="brainstem",
                    validation_note=VALIDATION_NOTE,
                    drift_corrected_ppm=round(float(drift), 3), story=STORIES[task], run=run,
                    stim_file=stim_file, first_trigger_sample=int(m.first_trig_sample),
                    audio_copy_onset_ms=round(float(m.onset_ms), 4), acoustic_delay_ms=ACOUSTIC_DELAY_MS,
                    onset_sample=round(float(onset), 4), sss="none (raw as shipped)", bads=BADS,
                    reference="none (MEG)", external_sensors=AUDIO_COPY,
                    chpi="continuous HPI, 5 coils at 261, 278, 295, 311, 328 Hz, not removed")
                yield TrialRecord(
                    subject=int(sub[4:]), session=1, trial=trial, condition=task, ns_type="meg",
                    stimulus=[StimulusRecord("audio", name, _audio_loader(wav), True, "audio"),
                              StimulusRecord("audio", name, _text_loader(wav[:-4] + ".TextGrid"), True, "textgrid")],
                    neural_data_fn=_meg_loader(fif, onset, wav, drift * 1e-6, description),
                )


def audiobook_events(fif: str) -> pd.DataFrame:
    """The run's 1 s audiobook triggers from events.tsv (STI101 has glitches, notes.md section 5)."""
    ev = pd.read_csv(fif.replace("_meg.fif", "_events.tsv"), sep="\t", encoding="utf-8-sig")
    return ev[ev.trial_type == "audiobook 1s"]


@lru_cache(maxsize=1)
def _read(fif: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_fif(fif, preload=False, verbose="ERROR")


def _meg_loader(fif: str, onset: float, wav: str, drift: float, description: str):
    def _loader():
        raw = _read(fif)
        fs, x = wavfile.read(wav, mmap=True)
        n_out = math.ceil(len(x) * 1000 / fs)
        picks = mne.pick_types(raw.info, meg=True, eog=True, ecg=True).tolist() + \
            [raw.ch_names.index(c) for c in AUDIO_COPY]
        out = crop_on_audio_clock(raw, onset, n_out, drift, picks=picks, sfreq_out=1000)
        if out.n_times != n_out:
            raise ValueError(f"{fif}: recording ends {n_out - out.n_times} samples before the stimulus")
        out.info["bads"] = BADS
        out.info["description"] = description
        return out

    return _loader


def _audio_loader(path: str):
    def _loader():
        fs, x = wavfile.read(path)
        return {"fs": fs, "data": x[None, :]}

    return _loader


def _text_loader(path: str):
    def _loader() -> str:
        with open(path, encoding="utf-8") as f:
            return f.read()

    return _loader


ADAPTOR = Habersetzer2025Adaptor
