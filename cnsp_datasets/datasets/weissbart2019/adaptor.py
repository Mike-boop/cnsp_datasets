from __future__ import annotations

import os
import glob
import h5py

import numpy as np
import pandas as pd

from scipy.io import wavfile
from typing import Dict, Iterable, List

from mne import create_info
from mne.channels import make_standard_montage
from mne.io import RawArray, BaseRaw

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


class Weissbart2019Adaptor:
    """
    Emits TrialRecord objects for the Weissbart 2019 dataset.

    Neutral fields used:
      - subject (int), session (int), trial (int), condition (str), ns_type (str)
      - stimulus: List[StimulusRecord] with modality="audio", name=<story>
      - neural_data_fn: lazy loader returning an mne.BaseRaw
    """

    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self.session = 1

        # Discover files
        self._stim_order = pd.read_csv(
            os.path.join(self.download_dir, "stimulus_order.csv"), index_col=0
        )
        self._audiobooks = sorted(
            glob.glob(os.path.join(self.download_dir, "audiobooks", "*.wav"))
        )
        self._subject_files = sorted(
            glob.glob(os.path.join(self.download_dir, "P*.h5"))
        )

        # Map story_name -> wav path, e.g., "Alice" -> ".../audiobooks/Alice.wav"
        self._story_to_wav: Dict[str, str] = {
            os.path.splitext(os.path.basename(p))[0]: p for p in self._audiobooks
        }

        # channel names and sample rate as stored in the HDF5 files (identical for all participants)
        self._info = self._make_mne_info(self._subject_files[0])


    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Yield TrialRecord for each (subject, story) pair.
        """
        for subj_path in self._subject_files:
            subject_id = self._parse_subject_id(subj_path)  # e.g., P03 -> 3

            # stimulus_order.csv holds np.argsort(onsets) under story-name headers: row k lists the index of the
            # story presented k-th, so a story's (1-based) trial number is its position in that row
            presented = list(self._stim_order.loc[f"P{subject_id:02d}"].to_numpy())
            for i, story in enumerate(self._stim_order.columns):
                trial_idx = presented.index(i) + 1

                # Build StimulusRecord (lazy read of WAV)
                stim = StimulusRecord(
                    modality="audio",
                    name=story,
                    data_fn=self._make_audio_loader(story),
                    is_attended=False,  # toggle if you have that info
                )

                # Build TrialRecord with lazy EEG loader
                yield TrialRecord(
                    subject=subject_id,
                    session=self.session,
                    trial=trial_idx,
                    condition="natural",
                    ns_type="eeg",
                    stimulus=[stim],
                    neural_data_fn=self._make_eeg_loader(subj_path, story),
                    structural_data_fn=None,
                    behavioural_data_fn=None,  # plug in if you have events table
                )

    # ------------------------ Lazy loader makers ----------------------

    def _make_audio_loader(self, story_name: str):
        """
        Returns a zero-arg function that reads the WAV on demand.
        Suggested return: dict with fs + mono waveform (1 x T).
        """
        wav_path = self._story_to_wav[story_name]

        def _loader() -> dict:
            fs, audio = wavfile.read(wav_path)
            # Ensure mono: dataset claims identical stereo; verify & pick one channel
            if audio.ndim == 2:
                if not np.array_equal(audio[:, 0], audio[:, 1]):
                    raise ValueError(f"Stereo channels differ in {wav_path}")
                audio = audio[:, 0]
            return {"fs": int(fs), "data": (audio / 32768.0).astype(np.float32)[None, :]}  # int16 -> [-1, 1)

        return _loader

    def _make_eeg_loader(self, subject_h5_path: str, story_name: str):
        """
        Returns a zero-arg function that opens the HDF5, extracts EEG for this story,
        and builds an mne.RawArray with the prebuilt Info (no lingering open file handle).
        """
        h5_path = subject_h5_path
        h5_key = f"data/{story_name}"

        def _loader() -> BaseRaw:
            with h5py.File(h5_path, "r") as f:
                if h5_key not in f:
                    raise KeyError(f"Missing EEG dataset: {h5_key} in {h5_path}")
                eeg = f[h5_key][:]  # expected shape (n_channels, n_times)
            raw = RawArray(eeg, self._info, verbose="ERROR")
            return raw

        return _loader

    # --------------------------- Utilities ----------------------------

    def _parse_subject_id(self, subj_path: str) -> int:
        # e.g., ".../P03.h5" -> 3
        stem = os.path.splitext(os.path.basename(subj_path))[0]
        return int(stem.replace("P", ""))

    def _make_mne_info(self, h5_path: str):
        # EEG in volts, recorded with a BrainVision system; layout easycap-M1
        with h5py.File(h5_path, "r") as f:
            ch_names = [c.decode() for c in f["ch_names"][:]]
            sfreq = float(f["srate"][0])
        info = create_info(ch_names, sfreq, ch_types="eeg")
        info.set_montage(make_standard_montage("easycap-M1"))
        return info


ADAPTOR = Weissbart2019Adaptor