# nsptools/adapters/broderick2019_av.py
from __future__ import annotations

import os
import glob
from typing import Iterable, Callable, Any, Dict, Optional, Tuple, List

import numpy as np
from pymatreader import read_mat
from mne import create_info
from mne.io import RawArray, BaseRaw

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord
from cnsp_datasets.datasets.broderick2019_natural.utils import multi_tier_dict_to_textgrid


_COND_MAP = {
    "a":  "sin",         # audio-only speech in noise
    "av": "AV-sin",      # audiovisual, normal-hearing, speech in noise
    "v":  "V-natural",   # visual-only (no audio)
}


class Broderick2019AVAdapter:
    """
    Pure adapter for the Broderick 2019 AV dataset.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        self._files: List[str] = self._discover()
        self.fs_eeg = 128.0

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
                name=f"Run{run}",
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
        files = sorted(glob.glob(os.path.join(self.root, "EEG", "sub*", '*.mat')))
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

    def _make_eeg_loader(self, mat_path: str) -> Callable[[], BaseRaw]:
        def _loader() -> BaseRaw:
            m = read_mat(mat_path)
            if "EEG" not in m:
                raise KeyError(f"'EEG' not found in {mat_path}")
            eeg = np.asarray(m["EEG"], dtype=float)
            if eeg.ndim != 2:
                raise ValueError(f"EEG must be 2D in {mat_path}, got {eeg.shape}")
            
            if "mastoids" in m:
                mastoids = np.asarray(m["mastoids"], dtype=float)
                eeg = np.concatenate([eeg, mastoids], axis=1)

            # Heuristics → (n_channels, n_times)
            if eeg.shape[0] > eeg.shape[1] or (eeg.shape[0] == 128 and eeg.shape[1] != 128):
                eeg = eeg.T
            info = self._create_info(mastoids="mastoids" in m)
            return RawArray(eeg, info, verbose="ERROR")
        return _loader
    
    def _make_textgrid_loader(self, mat_path: str) -> Callable[[], str]:
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

ADAPTOR = Broderick2019AVAdapter