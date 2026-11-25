from __future__ import annotations

import glob
import math
import os
from typing import Iterable

import mne
import numpy as np
import pandas as pd
import soundfile
from mne.channels import make_dig_montage
from mne.io import BaseRaw, read_raw_curry

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import to_audio_clock
from cnsp_datasets.standardise.iohelpers import audio_loader
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

# Recording P -> (left-ear track, right-ear track), from the Zenodo record's table as corrected on 2026-08-11.
# The letter in P is the attended side.
EARS = {
    "1L": ("part1_track2_dry", "part1_track1_dry"),
    "1R": ("part1_track2_dry", "part1_track1_dry"),
    "2L": ("part2_track1_dry", "part2_track2_dry"),
    "2R": ("part2_track1_dry", "part2_track2_dry"),
}
NON_EEG = ["XtraL", "XtraR", "Trigger"]


class Narayanan2021Adaptor(BaseAdaptor):
    """
    Narayanan et al. 2021 (Zenodo 4518754): 255-channel EEG (SynAmps RT, 1 kHz, Curry .dat/.dap/.rs3/.ceo), 30
    subjects, auditory attention to one of two Dutch stories (HRTF-filtered to left/right; the dry wavs are shipped).
    Four ~6.5-min recordings per subject, S<n>/S<n>_AAD_<P>, P = story part (1, 2) + attended side (L, R).

    One trial per recording, numbered in recording order (meas_date). The `Trigger` channel pulses once per second
    while the story plays (390 pulses for part 1, 392 for part 2); the EEG is cut from the first pulse of that 1-s
    train for the duration of the wav (ceil(wav samples * 1000 / 44100) EEG samples; the pulses stop 5.00 / 4.33 s
    before the story ends). Whether the first pulse coincides with the sound onset is not documented (no stimtrack).
    drift_correction=True (default): the pulse period is -10 ppm against the EEG clock (S24-S29: -16.8 ppm); each
    trial is resampled onto the pulse clock (period fitted per recording, onset as the anchor), assuming the pulses
    follow the audio clock. XtraL/XtraR (no audio on them) and Trigger
    are dropped. Channel positions from the authors' misc/eeg255ch_locs.csv (spherical, BESA convention); recording
    labels FP/AFP/PPO8h are renamed to the csv's Fp/AFp/PPO8.
    """

    def __init__(self, download_dir: str, drift_correction: bool = True):
        super().__init__(download_dir)
        self.drift_correction = drift_correction
        self._montage = _montage(self.path("misc", "eeg255ch_locs.csv"))

    def parse(self) -> Iterable[TrialRecord]:
        subjects = sorted(glob.glob(os.path.join(self.download_dir, "S*", "")), key=lambda p: int(p.split("S")[-1][:-1]))
        for sub_dir in subjects:
            dats = sorted(glob.glob(os.path.join(sub_dir, "*.dat")))
            order = sorted(dats, key=lambda f: read_raw_curry(f, preload=False, verbose="ERROR").info["meas_date"])
            for trial, dat in enumerate(order, start=1):
                base = os.path.basename(dat)[:-4]
                p = base.split("_")[-1]
                side = p[1]
                attended = EARS[p][0 if side == "L" else 1]
                ignored = EARS[p][1 if side == "L" else 0]
                yield TrialRecord(
                    subject=int(base.split("_")[0][1:]),
                    session=1,
                    trial=trial,
                    condition=f"competing-f{side}-hrtf",
                    ns_type="eeg",
                    stimulus=[StimulusRecord(modality="audio", name=attended, is_attended=True,
                                             data_fn=audio_loader(self._wav_path(attended), channel=0)),
                              StimulusRecord(modality="audio", name=ignored, is_attended=False,
                                             data_fn=audio_loader(self._wav_path(ignored), channel=0))],
                    neural_data_fn=self._eeg_loader(dat, soundfile.info(self._wav_path(attended))),
                )

    def _wav_path(self, stem: str) -> str:
        return os.path.join(self.download_dir, "stimuli", f"{stem}.wav")

    def _eeg_loader(self, dat: str, wav: soundfile._SoundFileInfo):
        montage, correct = self._montage, self.drift_correction

        def _loader() -> BaseRaw:
            raw = read_raw_curry(dat, preload=False, verbose="ERROR")
            sfreq = raw.info["sfreq"]
            trig = raw.get_data(picks=["Trigger"])[0]
            onset = train_onset(trig, sfreq)
            n = math.ceil(wav.frames * sfreq / wav.samplerate)  # the wav's span (was one sample more)
            margin = int(sfreq) if correct else 0  # resampling onto a faster clock needs a few more EEG samples
            stop = min(onset + n + margin, raw.n_times)
            raw = raw.crop(tmin=raw.times[onset], tmax=raw.times[stop - 1]).load_data()
            raw.drop_channels(NON_EEG)
            if correct:
                data = to_audio_clock(raw.get_data(), pulse_drift(trig, sfreq))[:, :n]
                raw = mne.io.RawArray(data, raw.info, verbose="ERROR")
            raw.set_annotations(None)
            raw.rename_channels(lambda c: "PPO8" if c == "PPO8h" else c.replace("FP", "Fp"))
            raw.set_montage(montage)
            raw.set_meas_date(None)
            return raw

        return _loader


def _pulse_train(trig: np.ndarray, sfreq: float):
    """Rising edges of Trigger, which are followed by a 1-s spacing, and the index of the first such edge."""
    pulses = np.flatnonzero(np.diff(trig) > 0) + 1
    regular = np.abs(np.diff(pulses) - sfreq) <= 2
    if not regular.any():
        raise ValueError(f"no 1-s pulse train on the Trigger channel ({len(pulses)} pulses)")
    return pulses, regular, int(np.argmax(regular))


def train_onset(trig: np.ndarray, sfreq: float) -> int:
    """Sample of the first pulse followed by a 1-s spacing (S8_AAD_1R has a stray pulse 16 s before the train)."""
    pulses, _, start = _pulse_train(trig, sfreq)
    return int(pulses[start])


def pulse_drift(trig: np.ndarray, sfreq: float) -> float:
    """Relative drift of the 1-s pulse train against the EEG clock: fitted period / sfreq - 1."""
    pulses, regular, start = _pulse_train(trig, sfreq)
    gaps = np.flatnonzero(~regular[start:])
    train = pulses[start: start + (gaps[0] + 1 if gaps.size else len(pulses))]
    return float(np.polyfit(np.arange(len(train)), train, 1)[0] / sfreq - 1)


def _montage(csv: str) -> mne.channels.DigMontage:
    """Montage from the authors' spherical coordinates (theta signed by hemisphere, phi azimuth; degrees)."""
    locs = pd.read_csv(csv)
    locs = locs[~locs["Channel Name"].isin(NON_EEG)]

    def xyz(theta, phi, r=0.095):
        theta, phi = np.deg2rad(theta), np.deg2rad(phi)
        return r * np.array([np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)])

    return make_dig_montage(ch_pos={n: xyz(t, p) for n, t, p in zip(locs["Channel Name"], locs.Theta, locs.Phi)},
                            nasion=xyz(115, 90), lpa=xyz(-115, 0), rpa=xyz(115, 0), coord_frame="head")


ADAPTOR = Narayanan2021Adaptor
