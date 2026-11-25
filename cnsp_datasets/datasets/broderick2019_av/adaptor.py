from __future__ import annotations

import os
from typing import Callable, Iterable, List, Tuple

from mne.io import BaseRaw

from cnsp_datasets.datasets.broderick2019_natural import cnd
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord


_COND_MAP = {
    "a":  "sin",         # audio-only speech in noise
    "av": "AV-sin",      # audiovisual, normal-hearing, speech in noise
    "v":  "V-natural",   # visual-only (no audio)
}


class Broderick2019AVAdapter(BaseAdaptor):
    """
    Broderick 2019 audiovisual speech-in-noise data (the Dryad package's "Speech in Noise" folder): audio-only (a),
    audiovisual (av) and visual-only (v) conditions, 15 runs each. The package provides word timings only (no audio
    or envelopes). EEG is converted from microvolts to volts; the mat files' fs field reads 512, but the data are
    128 Hz (7680 samples per 60 s run, as the Readme states).
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self.root = os.path.join(download_dir, "Speech in Noise")
        self._files: List[str] = self._discover()

    def parse(self) -> Iterable[TrialRecord]:
        for path in self._files:
            sub, cond_code, run = self._parse_name(path)
            condition = _COND_MAP[cond_code]
            neural_fn = self._make_eeg_loader(path)

            stim_run = run%15
            if stim_run == 0:
                stim_run = 15  # participants were stimulated with 15 trials each of a, v, av. So repeat stimuli 1-15 for these three conditions.
            stim_path = os.path.join(self.root, "Stimuli", f"Run{stim_run}.mat")
            stim = StimulusRecord(
                modality="audio" if cond_code in ("a", "av") else "visual",
                name=f"Run{stim_run}",  # runs are numbered per condition (a 1-15, v 16-30, av 31-45)
                data_fn=self._make_textgrid_loader(stim_path),
                is_attended=True,
                feature_name="textgrid"
            )

            yield TrialRecord(
                subject=sub,
                session=1,
                trial=run,
                condition=condition,
                ns_type="eeg",
                stimulus=[stim],
                neural_data_fn=neural_fn,
                structural_data_fn=None,
                behavioural_data_fn=None,
            )

    # ------------------------- discovery & parsing -------------------------

    def _discover(self) -> List[str]:
        files = self.sorted_glob(self.root, "EEG/sub*/*.mat")
        if not files:
            raise FileNotFoundError(f"No .mat files found under {os.path.join(self.root, 'EEG', 'sub*')}")
        return files

    def _parse_name(self, path: str) -> Tuple[int, str, int]:
        """
        Extract (subject, cond_code, run) from path like:
          .../EEG/sub7/sub7_<cond>_3.mat  -> (7, 'av', 3)
        """
        subdir = os.path.basename(os.path.dirname(path))   # 'sub7'
        subject = int(subdir.replace("sub", ""))

        stem = os.path.splitext(os.path.basename(path))[0] # 'sub7_<cond>_3.mat'
        parts = stem.split("_")
        if len(parts) != 3:
            raise ValueError(f"Cannot parse condition/run from filename: {stem}")
        
        subject = int(parts[0].replace("sub", ""))
        cond_code = parts[1]  # 'a', 'av', or 'v'
        run = int(parts[2])   # e.g. '3'
        return subject, cond_code, run

    # ------------------------------ loaders -------------------------------

    @staticmethod
    def _make_eeg_loader(mat_path: str) -> Callable[[], BaseRaw]:
        return lambda: cnd.read_eeg(mat_path, "EEG")

    @staticmethod
    def _make_textgrid_loader(mat_path: str) -> Callable[[], str]:
        return lambda: cnd.words_textgrid(mat_path)


ADAPTOR = Broderick2019AVAdapter
