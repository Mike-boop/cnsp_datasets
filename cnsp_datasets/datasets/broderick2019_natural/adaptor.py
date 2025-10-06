from __future__ import annotations

import os
from typing import Iterable, Callable, Dict, Any
import numpy as np
from pymatreader import read_mat
from mne import create_info
from mne.io import RawArray, BaseRaw

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord
from cnsp_datasets.datasets.utils import multi_tier_dict_to_textgrid

class Broderick2019NaturalAdapter:
    """
    Unified adapter for Broderick 2019 Natural Speech and Reverse variants.

    Layout:
      <root>/
        ├─ Natural Speech/
        │    ├─ EEG/Subject{sub}/Subject{sub}_Run{trial}.mat   (key 'eegData')
        │    └─ Stimuli/Envelopes/audio{trial}_128Hz.mat       (key 'env', fs=128)
        └─ Natural Speech - Reverse/
             ├─ EEG/Subject{sub}/Subject{sub}_Run{trial}.mat   (key 'eegData')
             └─ Stimuli/Envelopes/audio{trial}_128Hz.mat       (key 'env', fs=128)

    mode:
      - "natural": only natural trials
      - "reverse": only reverse trials
      - "both":    iterate over both datasets (default)
    """

    def __init__(
        self,
        download_dir: str,
        mode: str = "natural",
    ):
        assert mode in {"natural", "reverse", "both"}, "mode must be 'natural', 'reverse', or 'both'"
        self.download_dir = download_dir
        self.mode = mode
        self.trials = list(range(1, 21))
        self.fs_eeg = 128

        # small per-mode configuration used by parse()
        self._modes_cfg = []
        if mode in {"natural", "both"}:
            self._modes_cfg.append({
                "mode": "natural",
                "root": os.path.join(download_dir, "Natural Speech"),
                "subjects": list(range(1, 20)),  # 1..19
                "reverse_env": False,
            })
        if mode in {"reverse", "both"}:
            self._modes_cfg.append({
                "mode": "reverse",
                "root": os.path.join(download_dir, "Natural Speech - Reverse"),
                "subjects": list(range(1, 10)),  # 1..9
                "reverse_env": True,
            })

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        for cfg in self._modes_cfg:
            mode = cfg["mode"]
            root = cfg["root"]
            subjects = cfg["subjects"]
            reverse_env = cfg["reverse_env"]

            for sub in subjects:
                for trial in self.trials:
                    eeg_path = os.path.join(root, "EEG", f"Subject{sub}", f"Subject{sub}_Run{trial}.mat")
                    if not os.path.exists(eeg_path):
                        continue

                    stim_base = f"nat-audio-{trial:02d}"
                    stim_name = f"{stim_base}-rev" if mode == "reverse" else stim_base

                    stimuli = [
                        StimulusRecord(
                            modality="audio",
                            name=stim_name,
                            data_fn=self._make_env_loader(trial=trial, reverse=reverse_env),
                            is_attended=True,
                            feature_name="env",
                        ),
                       StimulusRecord(
                            modality="audio",
                            name=stim_name,
                            data_fn=self._make_textgrid_loader(run=trial, reverse=reverse_env),
                            is_attended=True,
                            feature_name="textgrid",
                        )
                    ]

                    yield TrialRecord(
                        subject=int(sub),
                        session=1,
                        trial=int(trial),
                        condition=mode,     # "natural" or "reverse"
                        ns_type="eeg",
                        stimulus=stimuli,
                        neural_data_fn=self._make_eeg_loader(eeg_path),
                        structural_data_fn=None,
                        behavioural_data_fn=None,
                    )

    # ------------------------ Lazy loaders ------------------------

    def _make_eeg_loader(self, mat_path: str) -> Callable[[], BaseRaw]:
        def _loader() -> BaseRaw:
            m = read_mat(mat_path)
            if "eegData" not in m:
                raise KeyError(f"'eegData' not found in {mat_path}")
            eeg = np.asarray(m["eegData"], dtype=float)
            if eeg.ndim != 2:
                raise ValueError(f"eegData must be 2D in {mat_path}, got {eeg.shape}")
            
            if "mastoids" in m:
                mastoids = np.asarray(m["mastoids"], dtype=float)
                eeg = np.concatenate([eeg, mastoids], axis=1)

            # Heuristics → (n_channels, n_times)
            if eeg.shape[0] > eeg.shape[1] or (eeg.shape[0] == 128 and eeg.shape[1] != 128):
                eeg = eeg.T
            info = self._create_info(mastoids="mastoids" in m)
            return RawArray(eeg, info, verbose="ERROR")
        return _loader

    def _make_env_loader(self, trial: int, reverse: bool) -> Callable[[], Dict[str, Any]]:
        env_path = os.path.join(self.download_dir, "Natural Speech", "Stimuli", "Envelopes", f"audio{trial}_128Hz.mat")

        def _loader() -> Dict[str, Any]:
            if not os.path.exists(env_path):
                raise FileNotFoundError(f"Envelope not found: {env_path}")
            mat = read_mat(env_path)
            if "env" not in mat:
                raise KeyError(f"'env' not found in {env_path}")
            env = np.asarray(mat["env"], dtype=float).squeeze()
            if reverse:
                env = env[::-1]
            return {"fs": 128, "waveform": env[None, :].astype(np.float32)}
        return _loader
    
    def _make_textgrid_loader(self, run: str, reverse=False) -> Callable[[], str]:

        mat_path = os.path.join(self.download_dir, "Natural Speech", "Stimuli", "Text", f"Run{run}.mat")
        
        def _loader() -> str:

            m = read_mat(mat_path)
            
            words = m["wordVec"]
            words = [w.lower() for w in words]  # list of str

            onsets = m["onset_time"].flatten()  # np.ndarray of float
            offsets = m["offset_time"].flatten()  # np.ndarray of float

            if reverse:
                env_dict = self._make_env_loader(trial=int(run), reverse=reverse)()
                env = env_dict["waveform"].squeeze()
                env_duration = len(env) / env_dict["fs"]
                data = {
                    "words": {
                        "item": words[::-1],
                        "onset_s": env_duration - offsets[::-1],
                        "offset_s": env_duration - onsets[::-1],
                    }
                }

            else:
                data = {
                    "words": {
                        "item": words,
                        "onset_s": onsets,
                        "offset_s": offsets,
                    }
                }
        
            return multi_tier_dict_to_textgrid(data)
        return _loader

    # ------------------------ Utilities ------------------------

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


ADAPTOR = Broderick2019NaturalAdapter