# nsptools/adapters/broderick2019_cocktail.py
from __future__ import annotations

import os
from typing import Iterable, Callable, Any, Dict, Optional, List

import numpy as np
from pymatreader import read_mat
from mne import create_info
from mne.io import RawArray, BaseRaw

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord
from cnsp_datasets.datasets.broderick2019_natural.utils import multi_tier_dict_to_textgrid


class Broderick2019CocktailAdapter:
    """
    Broderick 2019 'Cocktail Party' adapter with BioSemi-128 channel map.
    If 130 channels are present, last two are treated as mastoids (M1/M2) and
    are typed as 'misc' (no re-referencing here).
    """

    def __init__(self, download_dir: str):
        self.root = os.path.join(download_dir, "Cocktail Party")
        self.subjects = list(range(1, 34))
        self.trials = list(range(1, 21))
        self.fs_eeg = 128.0

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        for sub in self.subjects:
            condition = "competing-fL" if sub < 18 else "competing-fR"
            for trial in self.trials:
                eeg_path = os.path.join(
                    self.root, "EEG", f"Subject{sub}", f"Subject{sub}_Run{trial}.mat"
                )
                print(eeg_path)
                if not os.path.exists(eeg_path):
                    continue  # silently skip missing runs

                # attended/unattended by subject rule
                journey_name = f"Journey_{trial}"
                twenty_name  = f"20000_{trial}"
                if sub < 18:
                    att_name, un_name = twenty_name, journey_name
                else:
                    att_name, un_name = journey_name, twenty_name

                stimuli = [
                    StimulusRecord(
                        modality="audio",
                        name=att_name,
                        data_fn=self._make_env_loader(att_name),
                        is_attended=True,
                        feature_name="env",
                    ),
                    StimulusRecord(
                    modality="audio",
                    name=att_name,
                    data_fn=self._make_textgrid_loader(att_name),
                    is_attended=True,
                    feature_name="textgrid"
                    ),
                    StimulusRecord(
                        modality="audio",
                        name=un_name,
                        data_fn=self._make_env_loader(un_name),
                        is_attended=False,
                        feature_name="env",
                    ),
                    StimulusRecord(
                    modality="audio",
                    name=un_name,
                    data_fn=self._make_textgrid_loader(un_name),
                    is_attended=False,
                    feature_name="textgrid"
                    ),
                ]

                yield TrialRecord(
                    subject=int(sub),
                    session=1,
                    trial=int(trial),
                    condition=condition,
                    ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=self._make_eeg_loader(eeg_path),
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # ------------------------ Lazy loaders ------------------------

    def _make_eeg_loader(self, mat_path: str) -> Callable[[], BaseRaw]:
        """
        Load 'eegData'; if 130 channels, last two are mastoids (M1/M2) marked as 'misc'.
        No re-referencing is performed here.
        """
        def _loader() -> BaseRaw:
            m = read_mat(mat_path)
            if "eegData" not in m:
                raise KeyError(f"'eegData' not found in {mat_path}")
            eeg = np.asarray(m["eegData"], dtype=float)
            if eeg.ndim != 2:
                raise ValueError(f"eegData in {mat_path} must be 2D, got {eeg.shape}")

            # Heuristics → (n_channels, n_times)
            if eeg.shape[0] == 128 and eeg.shape[1] != 128:
                eeg = eeg.T
            if eeg.shape[0] > eeg.shape[1]:
                eeg = eeg.T

            if "mastoids" in m:
                mastoids = np.asarray(m["mastoids"], dtype=float)
                if mastoids.shape[0] != 2:
                    mastoids = mastoids.T
                eeg = np.concatenate([eeg, mastoids], axis=0)

            info = self._create_info(mastoids=(eeg.shape[0] == 130))

            return RawArray(eeg, info, verbose="ERROR")
        return _loader

    def _make_env_loader(self, story_name: str) -> Callable[[], Dict[str, Any]]:
        """
        Load Hilbert envelope for 'Journey_X' or '20000_X' (key 'envelope').
        Returns {'fs': 128, 'data': (1, T)}.
        """
        if story_name.startswith("Journey_"):
            folder = "Journey"
        elif story_name.startswith("20000_"):
            folder = "20000"
        else:
            raise ValueError(f"Unexpected story name: {story_name}")

        env_path = os.path.join(
            self.root, "Stimuli", "Envelopes", folder, f"{story_name}_env.mat"
        )

        def _loader() -> Dict[str, Any]:
            if not os.path.exists(env_path):
                raise FileNotFoundError(f"Envelope not found: {env_path}")
            
            mat = read_mat(env_path)
            env = mat["envelope"]
            env = np.asarray(env, dtype=float)

            if env.ndim == 2:
                env = np.squeeze(env)
            return {"fs": 128, "data": env[None, :].astype(np.float32)}
        return _loader
    
    def _make_textgrid_loader(self, audio_name: str) -> Callable[[], str]:

        story, run = audio_name.split("_")
        mat_path = os.path.join(self.root, "Stimuli", "Text", story, f"Run{run}.mat")

        def _loader() -> str:

            m = read_mat(mat_path)
            
            words = m["wordVec"]
            words = [w.lower() for w in words]  # list of str

            onsets = m["onset_time"].flatten()  # np.ndarray of float
            offsets = m["offset_time"].flatten()  # np.ndarray of float

            data = {
                "words": {
                    "item": words,
                    "onset_s": onsets,
                    "offset_s": offsets,
                }
            }
            return multi_tier_dict_to_textgrid(data)
        return _loader
    
    def _create_info(self, mastoids):
        ch_names = ["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12",
                    "A13","A14","A15","A16","A17","A18","A19","A20","A21","A22","A23","A24",
                    "A25","A26","A27","A28","A29","A30","A31","A32","B1","B2","B3","B4","B5",
                    "B6","B7","B8","B9","B10","B11","B12","B13","B14","B15","B16","B17","B18",
                    "B19","B20","B21","B22","B23","B24","B25","B26","B27","B28","B29","B30",
                    "B31","B32","C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12",
                    "C13","C14","C15","C16","C17","C18","C19","C20","C21","C22","C23","C24",
                    "C25","C26","C27","C28","C29","C30","C31","C32","D1","D2","D3","D4","D5",
                    "D6","D7","D8","D9","D10","D11","D12","D13","D14","D15","D16","D17","D18",
                    "D19","D20","D21","D22","D23","D24","D25","D26","D27","D28","D29","D30","D31","D32"]
        
        if mastoids:
            ch_names += ["M1", "M2"]  # mastoids
        info = create_info(ch_names=ch_names, sfreq=self.fs_eeg, ch_types=["eeg"]*128 + ["misc"]*2 if mastoids else "eeg")
        info.set_montage("biosemi128")
        return info

ADAPTOR = Broderick2019CocktailAdapter