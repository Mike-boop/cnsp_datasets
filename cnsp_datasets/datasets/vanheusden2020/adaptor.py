from __future__ import annotations

import glob
import math
import os
import re
import warnings
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
from mne.io import BaseRaw
from scipy.io import wavfile

from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 1024  # recorded at 2048 Hz, decimated by 2
AUDIO_FS = 44100
TRIGGER_BIT = 2  # Status bit 1, one pulse at each segment onset (notes.md 6)
SCALP = [f"A{i}" for i in range(1, 33)]  # BioSemi-32 ABC labels; biosemi32 template order (inferred, notes.md 5)
DROPPED = ["EXG3", "EXG4", "EXG5", "EXG6", "EXG7", "EXG8",
           "GSR1", "GSR2", "Erg1", "Erg2", "Resp", "Plet", "Temp", "Status"]
MASTOIDS = {"EXG1": "right mastoid (inferred, notes.md 5)", "EXG2": "left mastoid (inferred)"}  # kept as misc
FIXED = ["odin_1_1", "odin_1_2", "odin_1_3", "odin_1_4", "odin_4_1", "odin_4_2", "odin_4_3", "odin_4_4"]
# (subject, condition) -> segment order where it differs from FIXED (notes.md 3); missing segments are left out
ORDERS = {(2, "aided"): FIXED[:4], (2, "unaided"): ["odin_1_3", "odin_1_4", "odin_1_1", "odin_1_2"],
          (4, "unaided"): FIXED[:7], (20, "aided"): FIXED[:7], (19, "unaided"): FIXED[:6]}
EEG_ORDER = {(2, "unaided")}  # order derived from the EEG, not the fixed default
# fixed order used, but the EEG does not confirm it: file-wide, or only some slots (1-based)
AMBIGUOUS = {(4, "aided"): None, (4, "unaided"): None, (8, "aided"): None, (11, "aided"): None,
             (17, "unaided"): None, (19, "unaided"): {2, 5}}
EXTRA_PULSES = {(27, "aided")}  # 120 pulses at 1-s spacing after the audiobook: ignored (notes.md 3)
# paper Table 1 IDs from age and gender (inferred, notes.md 3); S_002, S_019, S_020 are not in the paper
PAPER_ID = {s: i + 1 for i, s in enumerate([1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 24, 27])}
PAPER_EXCLUDED = {16}  # paper subject 13, removed from the EEG analysis ("technical issue")
NOTES = ("BioSemi ActiveTwo at 2048 Hz (DC, 417 Hz hardware low-pass), decimated to 1024 Hz (anti-alias FIR); "
         "32 scalp channels plus the mastoids EXG1 (right) and EXG2 (left; sides inferred) as misc, original CMS/DRL "
         "reference (no re-referencing; the paper used the average reference), "
         "template positions. Onset = rising edge of Status bit 1 (one pulse per segment onset, no offset marker); "
         "no drift correction (not measurable); EEG checks place the pulses at the sound onset to within ~10-20 ms. "
         "Stimulus = the shipped wav (band-limited at ~4.05 kHz, the paper says 3 kHz), played by a loudspeaker at "
         "1.2 m; in the aided condition the participant's own hearing aid processed the sound (gain, compression, "
         "delay of a few ms; not shipped, not corrected).")


class Vanheusden2020Adaptor:
    """
    Vanheusden et al. 2020 (Southampton doi:10.5258/SOTON/D1140): 20 mild-to-moderately hearing-impaired listeners
    hear 8 audiobook segments (The Children of Odin, 2.4-4 min) with and without their hearing aids. One BDF per
    subject and condition ('aided'/'unaided'); segments in the fixed order odin_1_1..1_4, 4_1..4_4 (S_002: chapter 1
    only, unaided order from the EEG; S_004 unaided, S_020 aided, S_019 unaided miss the last segment(s)).
    Session = recording day (2 for S_017, S_020, S_024); trial = position in recording order over both files.
    EEG cut to the wav length. See notes.md.
    """

    def __init__(self, download_dir: str):
        pattern = re.compile(r"S_(\d{3})_(aided|unaided)_speech(-deci|_rep)\.bdf", re.IGNORECASE)
        self.files = {}
        for path in glob.glob(os.path.join(download_dir, "S_*.bdf")):
            m = pattern.fullmatch(os.path.basename(path))  # the loose S_001 "_Deci" duplicate does not match
            if m:
                self.files.setdefault(int(m.group(1)), {})[m.group(2).lower()] = path
        self.wavs = {name: os.path.join(download_dir, f"{name}.wav") for name in FIXED}
        self.n_audio = {name: _n_audio(path) for name, path in self.wavs.items()}

    def parse(self) -> Iterable[TrialRecord]:
        for sub in sorted(self.files):
            recs = sorted(self.files[sub].items(), key=lambda kv: _read(kv[1]).info["meas_date"])
            days = sorted({_read(bdf).info["meas_date"].date() for _, bdf in recs})
            trial = 0
            for rank, (cond, bdf) in enumerate(recs):
                session = days.index(_read(bdf).info["meas_date"].date()) + 1  # S_017/020/024: 2 days
                order = ORDERS.get((sub, cond), FIXED)
                onsets = _onsets(bdf)
                if (sub, cond) in EXTRA_PULSES:
                    onsets = onsets[:len(order)]
                if len(onsets) != len(order):
                    raise ValueError(f"{bdf}: {len(onsets)} onset pulses for {len(order)} segments")
                ambiguous = AMBIGUOUS.get((sub, cond), set())
                for slot, (name, onset) in enumerate(zip(order, onsets), 1):
                    trial += 1
                    extra = dict(
                        wav=name, bdf=os.path.basename(bdf), slot_in_recording=slot, onset_sample_2048=int(onset),
                        recording_rank=rank + 1, meas_date=str(_read(bdf).info["meas_date"]),
                        order_source="eeg" if (sub, cond) in EEG_ORDER else "fixed",
                        order_ambiguous=(sub, cond) in AMBIGUOUS and (ambiguous is None or slot in ambiguous),
                        missing_segments=[w for w in (FIXED[:4] if sub == 2 else FIXED) if w not in order],
                        paper_id_inferred=PAPER_ID.get(sub), excluded_in_paper=sub in PAPER_EXCLUDED,
                        reference="CMS/DRL (BioSemi, as recorded)", external_sensors=MASTOIDS, dropped=DROPPED,
                        units_as_shipped="uV", positions="template (biosemi32; A1-A32 mapping inferred)")
                    yield TrialRecord(
                        subject=sub, session=session, trial=trial, condition=cond, ns_type="eeg",
                        stimulus=StimulusRecord("audio", name, self._audio_loader(name), is_attended=True,
                                                feature_name="audio"),
                        neural_data_fn=_eeg_loader(bdf, onset, math.ceil(self.n_audio[name] * FS / AUDIO_FS), extra),
                    )

    def _audio_loader(self, name: str) -> Callable[[], dict]:
        path = self.wavs[name]

        def _loader() -> dict:
            fs, x = _read_wav(path)
            if fs != AUDIO_FS or x.dtype != np.int16 or x.ndim != 1:
                raise ValueError(f"{path}: expected 44.1 kHz mono int16")
            return {"fs": AUDIO_FS, "data": (x / 32768.0).astype(np.float32)[None, :]}
        return _loader


def _eeg_loader(bdf: str, onset: int, n_out: int, extra: dict) -> Callable[[], BaseRaw]:
    def _loader() -> BaseRaw:
        raw = crop_on_audio_clock(_read(bdf), onset, n_out, picks=SCALP + list(MASTOIDS), sfreq_out=FS)
        montage = mne.channels.make_standard_montage("biosemi32")
        raw.rename_channels(dict(zip(SCALP, montage.ch_names)))
        raw.set_channel_types(dict.fromkeys(MASTOIDS, "misc"), verbose="ERROR")
        raw.set_montage(montage)
        short = bool(raw.n_times < n_out)
        notes = NOTES + (f" The recording ends {(n_out - raw.n_times) / FS:.3f} s before the stimulus." if short
                         else "")
        raw.info["description"] = provenance(
            "onset_only", "unknown (not documented)", notes, **extra, n_samples=int(raw.n_times),
            n_samples_stimulus=n_out, eeg_shorter_than_stimulus=short)
        return raw
    return _loader


@lru_cache(maxsize=2)
def _read(bdf: str) -> BaseRaw:
    return mne.io.read_raw_bdf(bdf, preload=False, verbose="ERROR")


def _onsets(bdf: str) -> np.ndarray:
    """Samples where Status bit 1 rises (MNE scales the 24-bit BDF data to V; Status is left as integers)."""
    bit = (_read(bdf).get_data(picks=["Status"])[0].astype(np.int64) & TRIGGER_BIT) > 0
    return np.flatnonzero(~bit[:-1] & bit[1:]) + 1


def _read_wav(path: str, mmap: bool = False) -> tuple[int, np.ndarray]:
    with warnings.catch_warnings():  # odin_4_* carry a harmless chunk after the data chunk
        warnings.simplefilter("ignore", wavfile.WavFileWarning)
        return wavfile.read(path, mmap=mmap)


def _n_audio(path: str) -> int:
    return len(_read_wav(path, mmap=True)[1])


ADAPTOR = Vanheusden2020Adaptor
