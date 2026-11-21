from __future__ import annotations

import glob
import math
import os
from functools import lru_cache
from typing import Iterable

import mne
import numpy as np
from scipy.io import wavfile

from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS_MEG = 1000
TUBE_DELAY = 0.006  # 2 m tubes from the loudspeakers (Zenodo description)
N_CHAPTERS = 5
# attended speaker -> (attended audiobook, ignored audiobook); verified by duration and f0 (notes.md section 3)
BOOKS = {"LP": (1, 4), "HP": (3, 2)}


class Schueller2024Adaptor:
    """
    Schüller et al. 2023/2024 (Zenodo 12793944, 12794769, 12794808: Set1-3, participants 1-19, 20-38, 39-58):
    248-channel 4D magnetometer MEG, 1000 Hz (resampled by the authors from 1017.25 Hz, 50 Hz harmonics notched),
    two German audiobooks played diotically at once (LP and HP narrator), attention switched every chapter.

    Each subject has one run per attended speaker, the authors' concatenation of that speaker's 5 chapters (no
    gaps): chapter k fills ceil(n_k * 1000 / 44100) samples, so trials are cut at the cumulative boundaries. One
    trial per chapter; trials numbered in presentation order (LP chapter 1, HP chapter 1, LP chapter 2, ...).
    tube_delay=True starts each trial 6 ms after its boundary (acoustic delay of the tubes); the trial ends at the
    next boundary. Stimuli: attended and ignored audio as shipped (44.1 kHz; the ignored track already holds its
    ~5 s delayed start). See notes.md.
    """

    def __init__(self, download_dir: str, tube_delay: bool = True):
        self.download_dir = download_dir
        self.delay = round(TUBE_DELAY * FS_MEG) if tube_delay else 0
        self.audio_dir = os.path.join(download_dir, "Set1", "Audio")

    def parse(self) -> Iterable[TrialRecord]:
        runs = glob.glob(os.path.join(self.download_dir, "Set*", "*", "*_speaker_attended", "data_meg.fif"))
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
                    neural_data_fn=_meg_loader(fif, bounds[k - 1] + self.delay, bounds[k]),
                )

    def wav(self, book: int, chapter: int) -> str:
        stream = "attended_speech" if book in (1, 3) else "ignored_speech"
        return os.path.join(self.audio_dir, stream, f"audiobook{book}_{chapter}.wav")

    def n_meg(self, book: int, chapter: int) -> int:
        """MEG samples the authors gave a chapter: its audio resampled to 1000 Hz, rounded up."""
        fs, x = wavfile.read(self.wav(book, chapter), mmap=True)
        return math.ceil(len(x) * FS_MEG / fs)

    def _stimulus(self, book: int, chapter: int, attended: bool) -> StimulusRecord:
        path = self.wav(book, chapter)

        def _loader():
            fs, x = wavfile.read(path)
            x = x[:, 0] if x.ndim == 2 else x  # ignored tracks: two identical channels
            return {"fs": fs, "data": x[None, :]}

        return StimulusRecord("audio", f"audiobook{book}_{chapter}", _loader, attended, feature_name="audio")


@lru_cache(maxsize=1)
def _read(fif: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_fif(fif, preload=False, verbose="ERROR")


def _meg_loader(fif: str, start: int, stop: int):
    def _loader():
        raw = _read(fif)
        stop_ = min(stop, raw.n_times)
        return raw.copy().crop(start / FS_MEG, (stop_ - 1) / FS_MEG).load_data()

    return _loader


ADAPTOR = Schueller2024Adaptor
