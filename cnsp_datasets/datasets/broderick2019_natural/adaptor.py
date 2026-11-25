from __future__ import annotations

import os
from typing import Any, Callable, Dict, Iterable

import numpy as np
from mne.io import BaseRaw
from pymatreader import read_mat

from cnsp_datasets.datasets.broderick2019_natural import cnd
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

MODES = {"natural", "reverse", "both"}


class Broderick2019NaturalAdapter(BaseAdaptor):
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
      - "natural": only natural trials (default)
      - "reverse": only reverse trials
      - "both":    iterate over both datasets
    """

    def __init__(self, download_dir: str, mode: str = "natural"):
        super().__init__(download_dir)
        self.mode = self.choice("mode", mode, MODES)
        self.trials = list(range(1, 21))

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
            mode, root, reverse_env = cfg["mode"], cfg["root"], cfg["reverse_env"]
            for sub in cfg["subjects"]:
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
                            feature_name="envelope",
                        ),
                        StimulusRecord(
                            modality="audio",
                            name=stim_name,
                            data_fn=self._make_textgrid_loader(run=trial, reverse=reverse_env),
                            is_attended=True,
                            feature_name="textgrid",
                        ),
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

    @staticmethod
    def _make_eeg_loader(mat_path: str) -> Callable[[], BaseRaw]:
        return lambda: cnd.read_eeg(mat_path, "eegData")

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
            return {"fs": 128, "data": env[None, :].astype(np.float32)}
        return _loader

    def _make_textgrid_loader(self, run: int, reverse: bool = False) -> Callable[[], str]:
        mat_path = os.path.join(self.download_dir, "Natural Speech", "Stimuli", "Text", f"Run{run}.mat")

        def _loader() -> str:
            duration = None
            if reverse:  # words of the reversed audio: mirrored about the envelope's duration
                env = self._make_env_loader(trial=run, reverse=False)()
                duration = env["data"].shape[1] / env["fs"]
            return cnd.words_textgrid(mat_path, reverse_duration=duration)
        return _loader


ADAPTOR = Broderick2019NaturalAdapter
