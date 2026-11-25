from __future__ import annotations

import os
from typing import Any, Callable, Dict, Iterable

import numpy as np
from mne.io import BaseRaw
from pymatreader import read_mat

from cnsp_datasets.datasets.broderick2019_natural import cnd
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord


# Attended story per subject, from the dataset's "Cocktail_Party_Read_Me_-_Correction.rtf". The EEG Readme's rule
# (subjects 1-17 attended 20000, 18-33 Journey) is wrong for 16 of 33 subjects.
ATTENDED_20000 = {3, 6, 7, 8, 9, 10, 13, 15, 17, 18, 19, 21, 24, 25, 27, 31, 32}
ATTENDED_JOURNEY = {1, 2, 4, 5, 11, 12, 14, 16, 20, 22, 23, 26, 28, 29, 30, 33}


class Broderick2019CocktailAdapter(BaseAdaptor):
    """
    Broderick 2019 'Cocktail Party' adapter with BioSemi-128 channel map. Mastoids, where the file has them, are
    M1/M2 typed 'misc' (no re-referencing here). EEG is converted from microvolts to volts.
    Twenty Thousand Leagues (20000) played in the left ear, Journey in the right; attended story per subject
    from the dataset's correction note (ATTENDED_20000 / ATTENDED_JOURNEY).
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self.root = os.path.join(download_dir, "Cocktail Party")
        self.subjects = list(range(1, 34))
        self.trials = list(range(1, 21))

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        for sub in self.subjects:
            attends_20000 = sub in ATTENDED_20000
            condition = "competing-fL" if attends_20000 else "competing-fR"
            for trial in self.trials:
                eeg_path = os.path.join(
                    self.root, "EEG", f"Subject{sub}", f"Subject{sub}_Run{trial}.mat"
                )
                if not os.path.exists(eeg_path):
                    continue  # silently skip missing runs

                # attended/unattended by subject rule
                journey_name = f"Journey_{trial}"
                twenty_name  = f"20000_{trial}"
                if attends_20000:
                    att_name, un_name = twenty_name, journey_name
                else:
                    att_name, un_name = journey_name, twenty_name

                stimuli = [
                    StimulusRecord(
                        modality="audio",
                        name=att_name,
                        data_fn=self._make_env_loader(att_name),
                        is_attended=True,
                        feature_name="envelope",
                    ),
                    StimulusRecord(
                        modality="audio",
                        name=att_name,
                        data_fn=self._make_textgrid_loader(att_name),
                        is_attended=True,
                        feature_name="textgrid",
                    ),
                    StimulusRecord(
                        modality="audio",
                        name=un_name,
                        data_fn=self._make_env_loader(un_name),
                        is_attended=False,
                        feature_name="envelope",
                    ),
                    StimulusRecord(
                        modality="audio",
                        name=un_name,
                        data_fn=self._make_textgrid_loader(un_name),
                        is_attended=False,
                        feature_name="textgrid",
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

    @staticmethod
    def _make_eeg_loader(mat_path: str) -> Callable[[], BaseRaw]:
        """128 EEG channels + M1/M2 (misc) in V; no re-referencing."""
        return lambda: cnd.read_eeg(mat_path, "eegData")

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
        return lambda: cnd.words_textgrid(mat_path)


ADAPTOR = Broderick2019CocktailAdapter
