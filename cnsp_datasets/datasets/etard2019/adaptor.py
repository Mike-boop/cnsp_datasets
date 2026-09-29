from __future__ import annotations

import os
import glob
from typing import Dict, Iterable, Tuple, Optional, List, Any, Callable
import numpy as np
import h5py
from scipy.io import wavfile

from mne import create_info
from mne.channels import make_standard_montage
from mne.io import RawArray, BaseRaw

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


class Etard2019Adaptor:

    # known raw condition labels in the H5 -> standardized names
    _COND_MAP = {
        "clean": "natural",
        "lb": "sin_lowSNR",
        "mb": "sin_mediumSNR",
        "hb": "sin_highSNR",
        "fM": "competing_fM",
        "fW": "competing_fF",
        "cleanDutch": "foreign_quiet",
        "lbDutch": "foreign_lowSNR",
        "mbDutch": "foreign_mediumSNR",
        "hbDutch": "foreign_highSNR",
    }

    def __init__(
        self,
        download_dir: str
    ):
        """
        Parameters
        ----------
        download_dir : str
            Root directory of the downloaded dataset.
        session : int
            Session number to put into TrialRecord (dataset has a single session; default 1).
        """
        self.download_dir = download_dir

        # Discover EEG subject files
        self._subject_files = sorted(glob.glob(os.path.join(self.download_dir, "P*.h5")))

        # Precompute MNE Info (channels, sfreq, montage)
        self._info = self._make_mne_info()

        # Discover available audio (optional; useful for validating a provided map)
        # Exclude embedded English clips inside Dutch speech (as in your original)
        all_wavs = glob.glob(os.path.join(self.download_dir, "audiobooks", "*", "*.wav"))
        self._audio_files = [p for p in all_wavs if "english" not in p.lower()]

        # Build a helper dict: condition_dir -> [wav paths]
        self._audio_by_condition: Dict[str, List[str]] = {}
        for p in self._audio_files:
            cond_dir = os.path.basename(os.path.dirname(p))
            self._audio_by_condition.setdefault(self._standardize_condition(cond_dir), []).append(p)

        # Conditions we may see in H5 files
        self._raw_conditions = set(self._COND_MAP.keys())

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Yields TrialRecord for each (subject, condition, trial).
        Stimulus list:
          - always includes an attended "story" stimulus
          - includes a "distractor" stimulus for competing-speech conditions (fM/fW)
        """
        for subj_path in self._subject_files:
            subject = self._parse_subject_id(subj_path)  # e.g., 'P03.h5' -> 3

            with h5py.File(subj_path, "r") as f:
                # Some subjects may miss Dutch conditions; only use groups present in H5
                present_conds = [c for c in f.keys() if c in self._raw_conditions]

                for raw_cond in present_conds:
                    std_cond = self._standardize_condition(raw_cond)

                    if "Dutch" in raw_cond:
                        session = 2
                    else:
                        session = 1

                    for trial in (1, 2, 3, 4):
                        # EEG lazy loader
                        neural_fn = self._make_eeg_loader(subj_path, raw_cond, trial)

                        # Stimuli list (attended always; distractor for two-speaker)
                        stimuli: List[StimulusRecord] = []

                        attended_name = f"{std_cond}_part_{trial}_story"
                        attended_fn = self._make_audio_loader(raw_cond, trial, role="story")
                        stimuli.append(
                            StimulusRecord(
                                modality="audio",
                                name=attended_name,
                                data_fn=attended_fn,
                                is_attended=True,
                                feature_name="audio",
                            )
                        )

                        if raw_cond in ("fM", "fW"):
                            distractor_name = f"{std_cond}_part_{trial}_distractor"
                            distractor_fn = self._make_audio_loader(raw_cond, trial, role="distractor")
                            stimuli.append(
                                StimulusRecord(
                                    modality="audio",
                                    name=distractor_name,
                                    data_fn=distractor_fn,
                                    is_attended=False,
                                    feature_name="audio",
                                )
                            )

                        yield TrialRecord(
                            subject=subject,
                            session=session,
                            trial=trial,
                            condition=std_cond,
                            ns_type="eeg",
                            stimulus=stimuli,
                            neural_data_fn=neural_fn,
                            structural_data_fn=None,
                            behavioural_data_fn=None,
                        )

    # ------------------------ Lazy loader makers ----------------------

    def _make_eeg_loader(self, subject_h5_path: str, raw_condition: str, trial: int) -> Callable[[], BaseRaw]:
        """
        Returns a 0-arg function that opens the H5, reads EEG, and builds mne.RawArray.
        """
        h5_path = subject_h5_path
        key = f"{raw_condition}/part_{trial}"

        def _loader() -> BaseRaw:
            with h5py.File(h5_path, "r") as f:
                if key not in f:
                    raise KeyError(f"Missing EEG dataset: '{key}' in {h5_path}")
                eeg = f[key][:]  # shape (n_channels, n_times)
            raw = RawArray(eeg, self._info, verbose="ERROR")
            return raw

        return _loader

    def _make_audio_loader(self, raw_cond: str, trial: int, role: str) -> Callable[[], Any]:
        """
        Returns a 0-arg function that loads WAV if mapping is known; otherwise raises with guidance.
        The return value is a dict: {"fs": int, "data": np.ndarray[1, T]}.
        """
        wav_path = os.path.join(self.download_dir, "audiobooks", raw_cond, f"part_{trial}_{role}.wav")

        def _loader() -> Any:
            fs, audio = wavfile.read(wav_path)
            if audio.ndim == 2:
                # ensure mono; many files are dual-mono
                if not np.array_equal(audio[:, 0], audio[:, 1]):
                    # If truly stereo, pick left channel; adjust to your needs
                    audio = audio[:, 0]
                else:
                    audio = audio[:, 0]
            waveform = np.asarray(audio)[None, :]  # shape (1, T)
            return {"fs": int(fs), "data": waveform}

        return _loader

    # --------------------------- Utilities ----------------------------

    def _parse_subject_id(self, subj_path: str) -> int:
        stem = os.path.splitext(os.path.basename(subj_path))[0]  # "P03"
        return int(stem.replace("P", ""))

    def _standardize_condition(self, raw_condition: str) -> str:
        return self._COND_MAP.get(raw_condition, raw_condition)

    def _make_mne_info(self):
        ch_names = [
            'AF3','AF4','AF7','AF8','C1','C2','C3','C4','C5','C6','CP1','CP2','CP3',
            'CP4','CP5','CP6','CPz','Cz','F1','F2','F3','F4','F5','F6','F7','F8',
            'FC1','FC2','FC3','FC4','FC5','FC6','Fp1','Fp2','FT10','FT7','FT8','FT9',
            'Fz','O1','O2','Oz','P1','P2','P3','P4','P5','P6','P7','P8','PO3','PO7',
            'PO8','POz','Pz','FCz','T7','T8','TP10','TP7','TP8','TP9','AFz'
        ]
        sfreq = 1000
        info = create_info(ch_names, sfreq, ch_types="eeg")
        info.set_montage(make_standard_montage("easycap-M1"))
        return info


ADAPTOR = Etard2019Adaptor