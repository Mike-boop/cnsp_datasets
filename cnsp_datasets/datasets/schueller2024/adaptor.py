from __future__ import annotations

import glob
import logging
import math
import os
from functools import lru_cache
from typing import Iterable

import mne
import numpy as np
import pandas as pd
import soundfile

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.iohelpers import audio_loader
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS_MEG = 1000
TUBE_DELAY = 0.006  # 2 m tubes from the loudspeakers (Zenodo description)
N_CHAPTERS = 5
# attended speaker -> (attended audiobook, ignored audiobook); verified by duration and f0 (notes.md section 3)
BOOKS = {"LP": (1, 4), "HP": (3, 2)}
DRIFT_CSV = os.path.join(os.path.dirname(__file__), "alignment", "drift.csv")  # from alignment/drift.py (raw data)
MIN_WINDOWS = 10  # chapters with fewer valid drift windows are not used

log = logging.getLogger(__name__)


class Schueller2024Adaptor(BaseAdaptor):
    """
    Schüller et al. 2023/2024 (Zenodo 12793944, 12794769, 12794808: Set1-3, participants 1-19, 20-38, 39-58):
    248-channel 4D magnetometer MEG, 1000 Hz (resampled by the authors from 1017.25 Hz, 50 Hz harmonics notched),
    two German audiobooks played diotically at once (LP and HP narrator), attention switched every chapter.

    Each subject has one run per attended speaker, the authors' concatenation of that speaker's 5 chapters (no
    gaps): chapter k fills ceil(n_k * 1000 / 44100) samples, so trials are cut at the cumulative boundaries. One
    trial per chapter; trials numbered in presentation order (LP chapter 1, HP chapter 1, LP chapter 2, ...).
    tube_delay=True starts each trial 6 ms after its boundary (acoustic delay of the tubes); the trial ends at the
    next boundary. drift: sound-card vs MEG clock drift measured on the raw recordings (drift.csv, per chapter;
    matched to the release by meas_date), corrected by resampling each trial onto the audio clock: "subject"
    (default: the participant's median; participants without raw data get the dataset median), "dataset" (median
    over all chapters, +8.5 ppm) or None; a participant without raw data is logged. Stimuli: attended and ignored
    audio as shipped (44.1 kHz, float32, first channel; the ignored track already holds its ~5 s delayed start).
    See notes.md.
    """

    def __init__(self, download_dir: str, tube_delay: bool = True, drift: str | None = "subject"):
        super().__init__(download_dir)
        self.choice("drift", drift, ("subject", "dataset", None))
        self.delay = round(TUBE_DELAY * FS_MEG) if tube_delay else 0
        self.drift = drift
        self.audio_dir = os.path.join(download_dir, "Set1", "Audio")

    def parse(self) -> Iterable[TrialRecord]:
        runs = sorted(glob.glob(os.path.join(self.download_dir, "Set*", "*", "*_speaker_attended", "data_meg.fif")))
        for fif in sorted(runs, key=lambda p: (int(p.split(os.sep)[-3]), p)):
            subject = int(fif.split(os.sep)[-3])
            speaker = os.path.basename(os.path.dirname(fif))[:2]
            att, ign = BOOKS[speaker]
            bounds = np.cumsum([0] + [self.n_meg(att, k) for k in range(1, N_CHAPTERS + 1)])
            for k in range(1, N_CHAPTERS + 1):
                yield TrialRecord(
                    subject=subject,
                    session=1,
                    trial=2 * k - (speaker == "LP"),
                    condition=f"{speaker.lower()}-attended",
                    ns_type="meg",
                    stimulus=[self._stimulus(att, k, True), self._stimulus(ign, k, False)],
                    neural_data_fn=self._meg_loader(fif, bounds[k - 1] + self.delay, bounds[k]),
                )

    def drift_of(self, raw: mne.io.BaseRaw) -> float:
        """Drift (fraction, > 0: MEG clock fast) for one run, following self.drift."""
        if self.drift is None:
            return 0.0
        table = _drift_table()
        if self.drift == "subject":
            rows = subject_rows(table, raw.info["meas_date"])
            if len(rows):
                return float(rows.drift_ppm.median()) * 1e-6
            _log_fallback(str(raw.info["meas_date"]))
        return float(table.drift_ppm.median()) * 1e-6

    def _meg_loader(self, fif: str, start: int, stop: int):
        def _loader():
            raw = _read(fif)
            return crop_on_audio_clock(raw, start, min(stop, raw.n_times) - start, self.drift_of(raw))

        return _loader

    def wav(self, book: int, chapter: int) -> str:
        stream = "attended_speech" if book in (1, 3) else "ignored_speech"
        return os.path.join(self.audio_dir, stream, f"audiobook{book}_{chapter}.wav")

    def n_meg(self, book: int, chapter: int) -> int:
        """MEG samples the authors gave a chapter: its audio resampled to 1000 Hz, rounded up."""
        info = soundfile.info(self.wav(book, chapter))
        return math.ceil(info.frames * FS_MEG / info.samplerate)

    def _stimulus(self, book: int, chapter: int, attended: bool) -> StimulusRecord:
        # first channel (as before; the ignored tracks hold two identical channels)
        loader = audio_loader(self.wav(book, chapter), channel=0)
        return StimulusRecord("audio", f"audiobook{book}_{chapter}", loader, attended, feature_name="audio")


@lru_cache(maxsize=1)
def _read(fif: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_fif(fif, preload=False, verbose="ERROR")


@lru_cache(maxsize=1)
def _drift_table() -> pd.DataFrame:
    d = pd.read_csv(DRIFT_CSV)
    d["meas_date"] = pd.to_datetime(d.meas_date, utc=True)
    return d[d.n_windows >= MIN_WINDOWS]


def subject_rows(table: pd.DataFrame, meas_date) -> pd.DataFrame:
    """
    Rows of the drift table whose raw recording has this meas_date (compared as UTC timestamps). Raw folders with
    the same date must hold the same fits (P42 is in the raw data twice, as P42 and P42_zweiter Versuch); one is
    kept. Different fits for one date raise.
    """
    if meas_date is None:
        return table.iloc[:0]
    rows = table[table.meas_date == pd.Timestamp(meas_date).tz_convert("UTC")]
    folders = sorted(rows.folder.unique())
    if len(folders) > 1:
        cols = ["speaker", "chapter", "drift_ppm"]
        fits = [rows[rows.folder == f][cols].reset_index(drop=True) for f in folders]
        if not all(f.equals(fits[0]) for f in fits[1:]):
            raise ValueError(f"meas_date {meas_date} matches raw recordings {folders} with different drifts")
        rows = rows[rows.folder == folders[0]]
    return rows


@lru_cache(maxsize=None)
def _log_fallback(meas_date: str) -> None:
    """Logged once per recording date."""
    log.warning("schueller2024: no raw-data drift for the run recorded %s; using the dataset median", meas_date)


ADAPTOR = Schueller2024Adaptor
