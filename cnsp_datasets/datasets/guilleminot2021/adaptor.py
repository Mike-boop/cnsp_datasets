from __future__ import annotations

import os
from fractions import Fraction
from typing import Iterable, Dict, Callable, Any

import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.signal import resample_poly

from mne.io import read_raw_brainvision, BaseRaw

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord
from cnsp_datasets.datasets.guilleminot2021.timing import BUFFER_FS, OUT as TIMING_CSV, PAD_S, tactile_buffer


EEG_FNAME_DICT = {
    "al": {
        "1": "al.vhdr",
        "1_2": None,
        "2": "al_2.vhdr",
        "2_2": None
    },
    "yr": {
        "1": "yr.vhdr",
        "1_2": "yr2.vhdr",
        "2": "yr_2.vhdr",
        "2_2": None
    },
    "alio": {
        "1": "alio_1.vhdr",
        "1_2": None,
        "2": "alio_2.vhdr",
        "2_2": None
    },
    "chap": {
        "1": "chap_1.vhdr",
        "1_2": None,
        "2": "chap_2.vhdr",
        "2_2": None
    },
    "sep": {
        "1": "sep_1.vhdr",
        "1_2": None,
        "2": "sep_2.vhdr",
        "2_2": None
    },
    "phil": {
        "1": "phil_1.vhdr",
        "1_2": None,
        "2": "phil_2.vhdr",
        "2_2": None
    },
    "lad": {
        "1": "lad_1.vhdr",
        "1_2": "lad_1_1.vhdr",
        "2": "lad_2.vhdr",
        "2_2": None
    },
    "calco": {
        "1": "calco_1.vhdr",
        "1_2": None,
        "2": "calco_2.vhdr",
        "2_2": None
    },
    "hudi": {
        "1": "hudi_1.vhdr",
        "1_2": None,
        "2": "hudi_2.vhdr",
        "2_2": None
    },
    "nima": {
        "1": "nima.vhdr",
        "1_2": None,
        "2": "nima_2.vhdr",
        "2_2": None
    },
    "ogre": {
        "1": "ogre_1.vhdr",
        "1_2": None,
        "2": "ogre_2.vhdr",
        "2_2": None
    },
    "raqu": {
        "1": "raqu.vhdr",
        "1_2": None,
        "2": "raqu_2.vhdr",
        "2_2": None
    },
    "nikf": {
        "1": "nikf.vhdr",
        "1_2": None,
        "2": "nikf_2.vhdr",
        "2_2": None
    },
    "zartan": {
        "1": "zartan_1.vhdr",
        "1_2": None,
        "2": "zartan_2.vhdr",
        "2_2": None
    },
    "naga": {
        "1": "naga_1.vhdr",
        "1_2": None,
        "2": "naga_2.vhdr",
        "2_2": None
    },
    "miya": {
        "1": "miya_1.vhdr",
        "1_2": None,
        "2": "miya_2.vhdr",
        "2_2": None
    },
    "elios": {
        "1": "elios_1.vhdr",
        "1_2": "elios_1_2.vhdr",
        "2": "elios_2.vhdr",
        "2_2": None
    },
    "olio": {
        "1": "olio_1.vhdr",
        "1_2": None,
        "2": "olio_2.vhdr",
        "2_2": None
    }
}

PARTICIPANTS = [
    'al', 'yr', 'alio', 'chap', 'sep',
    'phil', 'lad', 'calco', 'hudi', 'nima',
    'ogre', 'raqu', 'nikf', 'zartan', 'naga',
    'miya', 'elios', 'olio'
]
SESSIONS = [1, 2]


# stable int id per participant (TrialRecord.subject requires int)
_SUB_INDEX = {p: i + 1 for i, p in enumerate(PARTICIPANTS)}


class Guilleminot2021Adaptor:
    """
    Adaptor for the Guilleminot 2021 audio-tactile speech-in-noise dataset (1 kHz EEG).

    Folder layout expected:
      <root>/
        ├─ Stimuli/Odin_<File>.wav, .TextGrid, _audio.npy, _phone_.npy
        └─ <participant>/<participant>_EEG_<session>/
             ├─ *.vhdr (no standardised naming scheme, see EEG_FNAME_DICT)
             └─ <participant>_EEG_<session>.csv  (columns: File, Type, Delay, Correlated)

    Timing (see timing.py, which writes trial_timing.csv from the EEG 'Sound' channel):
      - Each trial plays a 39062.5 Hz buffer: 1 s silence, the story part (Odin_<File>.wav), 1 s silence. The buffer
        starts 1-3 ms after the R3 marker; trial_timing.csv gives each trial's measured buffer onset (and drops the
        few trials without a usable marker, cut by a recording pause or running past its end), and the EEG is cropped from buffer onset + 1 s for the
        duration of the wav. Condition 'T' (tactile only) has no speech; its EEG is cropped the same way.
      - Tactile stimulus: Odin_<File>_phone_.npy (the vibrotactile signal, ~100 Hz carrier), started `Delay` ms
        after the speech (negative: tactile first). Mismatched trials (Correlated = 0) used the same buffer
        circularly shifted by a quarter of its length. It is resampled to the wav's rate and cut to the trial.
    Conditions: 'A', 'T', 'AT_<Delay>' ('-' -> 'm'), 'AT_mismatched'. Subject IDs are 1-based in PARTICIPANTS order.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        self.timing = pd.read_csv(TIMING_CSV)

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        usable = self.timing[self.timing.method.isin(["stimtrack", "marker"]) & self.timing.issue.isna()]
        for p in PARTICIPANTS:
            for ses in SESSIONS:
                eeg_dir = os.path.join(self.root, p, f"{p}_EEG_{ses}")
                csv_path = os.path.join(eeg_dir, f"{p}_EEG_{ses}.csv")
                if not os.path.exists(csv_path):
                    continue
                info_df = pd.read_csv(csv_path)
                timing = usable[(usable.participant == p) & (usable.session == ses)].set_index("row")
                for trial_idx in info_df.index:
                    if trial_idx not in timing.index:
                        continue
                    t = timing.loc[trial_idx]
                    file_token = str(info_df.loc[trial_idx, "File"])
                    stim_type = str(info_df.loc[trial_idx, "Type"])
                    delay = int(info_df.loc[trial_idx, "Delay"])
                    correlated = bool(info_df.loc[trial_idx, "Correlated"])
                    wav_path = os.path.join(self.root, "Stimuli", f"Odin_{file_token}.wav")

                    if stim_type == "audio":
                        condition = "A"
                    elif stim_type == "tactile":
                        condition = "T"
                    elif correlated:
                        condition = f"AT_{str(delay).replace('-', 'm')}"
                    else:
                        condition = "AT_mismatched"

                    stimuli = []
                    if "audio" in stim_type:
                        name = f"Odin_{file_token}"
                        stimuli += [
                            StimulusRecord(modality="audio", name=name, data_fn=self._make_audio_loader(wav_path),
                                           is_attended=True, feature_name="audio"),
                            StimulusRecord(modality="audio", name=name,
                                           data_fn=self._make_tg_loader(wav_path.replace(".wav", ".TextGrid")),
                                           is_attended=True, feature_name="textgrid"),
                        ]
                    if stim_type in ("audio-tactile", "tactile"):
                        suffix = f"delay_{str(delay).replace('-', 'm')}" if correlated else "rolled_quarter"
                        stimuli.append(StimulusRecord(
                            modality="tactile", name=f"Odin_{file_token}_{suffix}",
                            data_fn=self._make_tactile_loader(file_token, wav_path, delay, correlated),
                            is_attended=True, feature_name="audio"))

                    yield TrialRecord(
                        subject=_SUB_INDEX[p],
                        session=ses,
                        trial=int(trial_idx),
                        condition=condition,
                        ns_type="eeg",
                        stimulus=stimuli,
                        neural_data_fn=self._make_eeg_loader(os.path.join(eeg_dir, t.recording), wav_path,
                                                             float(t.buffer_onset_s) + PAD_S),
                        structural_data_fn=None,
                        behavioural_data_fn=None,
                    )

    # ------------------------ Lazy loaders ------------------------

    @staticmethod
    def _make_audio_loader(wav_path: str) -> Callable[[], Dict[str, Any]]:
        def _loader() -> Dict[str, Any]:
            fs, x = wavfile.read(wav_path)
            if x.ndim == 2:
                x = x[:, 0]
            return {"fs": int(fs), "data": np.asarray(x, dtype=float)[None, :]}
        return _loader

    def _make_tactile_loader(self, file_token: str, wav_path: str, delay_ms: int,
                             correlated: bool) -> Callable[[], Dict[str, Any]]:
        """The vibrotactile signal as played, on the wav's time axis and sample rate (t = 0 at speech onset)."""
        stimuli_dir = os.path.join(self.root, "Stimuli")

        def _loader() -> Dict[str, Any]:
            fs, x = wavfile.read(wav_path, mmap=True)
            n = x.shape[0]
            buf = tactile_buffer(stimuli_dir, file_token, correlated)
            ratio = Fraction(int(fs) * 2, int(BUFFER_FS * 2))           # e.g. 44100 / 39062.5 = 3528 / 3125
            buf = resample_poly(buf, ratio.numerator, ratio.denominator)
            # speech onset is PAD_S into its buffer; the tactile buffer starts delay_ms later (mismatched: 0)
            start = int(round((PAD_S - (delay_ms if correlated else 0) / 1000) * fs))
            out = np.zeros(n)
            seg = buf[max(start, 0):max(start, 0) + n - max(-start, 0)]
            out[max(-start, 0):max(-start, 0) + len(seg)] = seg
            return {"fs": int(fs), "data": out[None, :]}
        return _loader

    @staticmethod
    def _make_tg_loader(tg_path: str) -> Callable[[], str]:
        def _loader() -> str:
            with open(tg_path, "r") as f:
                return f.read()
        return _loader

    @staticmethod
    def _make_eeg_loader(vhdr_path: str, wav_path: str, onset_s: float) -> Callable[[], BaseRaw]:
        """Crop the recording to [speech onset, + wav duration]."""
        def _loader() -> BaseRaw:
            fs, x = wavfile.read(wav_path, mmap=True)
            raw = read_raw_brainvision(vhdr_path, preload=False, verbose="ERROR")
            tmax = onset_s + x.shape[0] / fs
            if tmax > raw.times[-1]:
                raise ValueError(f"{vhdr_path}: trial ends at {tmax:.1f} s, after the recording ({raw.times[-1]:.1f} s)")
            return raw.crop(tmin=onset_s, tmax=tmax)
        return _loader


ADAPTOR = Guilleminot2021Adaptor
