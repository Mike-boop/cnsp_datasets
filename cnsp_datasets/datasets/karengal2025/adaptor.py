from __future__ import annotations

import os
import glob
import mne

import numpy as np
import pandas as pd

from scipy.io import wavfile
from mne.io import read_raw_eeglab, BaseRaw
from typing import Iterable, Dict, Tuple, Optional, Callable, Any, List

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord

mne.set_log_level("CRITICAL")
AVBOOK_DIR = "/data_nfs/gu08wuvu/datasets/varano2022/downloaded/AVbook"

# Map raw condition tokens -> standardized names
STANDARDISED_COND = {
    "AnlV__": "sin_dutch",
    "AenV__": "sin_english",
    "AenVnh": "AV_natural",
    "AnlVnh": "AV_natural_dutch",
    "AenVe2": "AV_edge_high",
    "AenVe5": "AV_edge_low",
    "A__Vnh": "V_natural",
    "A__Ve2": "V_edge_high",
    "A__Ve5": "V_edge_low",
}


class Karengal2025Adaptor:
    """

    """

    def __init__(
        self,
        download_dir: str,
    ):
        self.download_dir = download_dir
        self.session = 1

        # Discover EEG files
        self._eeg_files = sorted(
            glob.glob(
                os.path.join(
                    self.download_dir,
                    "data_ageing",
                    "split_recordings",
                    "eeg_clean_200",
                    "BP-1-80-CL50Hz-ASR-INTP-AVR-ICr",
                    "*.set",
                )
            )
        )

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Iterate all EEG FIF files, determine condition & story part,
        and yield TrialRecord with lazy EEG and stimuli loaders.
        """
        for eeg_path in self._eeg_files:
            subject_id, cond_token, cond_idx = self._parse_fname(eeg_path)
            std_cond = STANDARDISED_COND[cond_token]

            # Read per-subject condition order
            sub_df = self._get_results_df_from_subject(subject_id)
            row = sub_df[(sub_df["Condition"] == cond_token)].reset_index().loc[cond_idx]
            story_part_idx = row["Passage"]
            trial_number = story_part_idx - 2

            # Build stimuli
            stimuli: List[StimulusRecord] = []

            audio_loader = self._make_audio_loader(story_part_idx)
            stimuli = [
                StimulusRecord(
                    modality="audio",
                    name=f"M{story_part_idx:02d}",
                    data_fn=audio_loader,
                    is_attended=True,
                    feature_name="audio")
                ]

            # Lazy EEG loader (crop: remove 1.995 s at both ends)
            neural_loader = self._make_eeg_loader(eeg_path)

            yield TrialRecord(
                subject=subject_id,
                session=self.session,
                trial=trial_number,
                condition=std_cond,
                ns_type="eeg",
                stimulus=stimuli,
                neural_data_fn=neural_loader,
                structural_data_fn=None,
                behavioural_data_fn=None,
            )

    # ------------------------ Lazy loader makers ----------------------

    def _get_condition_order_df(self, subject_id: int) -> pd.DataFrame:
        """
        Load and return the condition order DataFrame for the given subject.
        """
        cond_order_csv = os.path.join(self.download_dir, "condorders", "cond_orders", f"condorder_sub{subject_id}.csv")
        if not os.path.exists(cond_order_csv):
            raise FileNotFoundError(f"Condition order CSV not found for subject {subject_id}: {cond_order_csv}")
        df = pd.read_csv(cond_order_csv, header=0, na_values=["NaN"])
        df["condCount"] = df.groupby("condition").cumcount()
        df["trial_index"] = df["trial_index"] + 1

        return df

    def _make_eeg_loader(self, fif_path: str) -> Callable[[], BaseRaw]:
        def _loader() -> BaseRaw:
            raw = read_raw_eeglab(fif_path, preload=True, verbose="ERROR")
            raw = raw.crop(tmin=1.995, tmax=raw.times[-1]-1.995) # padding was left in to allow for filter edge artifacts
            return raw
        return _loader

    def _make_audio_loader(self, story_part_a: str) -> Callable[[], Dict[str, Any]]:
        """
        Load AVbook A-stream FXX.wav and return dict {'fs': int, 'waveform': np.ndarray[1, T]}.
        """
        wav_path = os.path.join(AVBOOK_DIR, "A", f"M{story_part_a:02d}.wav")

        def _loader() -> Dict[str, Any]:
            if not os.path.exists(wav_path):
                raise FileNotFoundError(f"Audio file not found: {wav_path}")
            fs, audio = wavfile.read(wav_path)
            # ensure mono shape (1, T)
            if audio.ndim == 2:
                if audio.shape[1] == 2 and np.array_equal(audio[:, 0], audio[:, 1]):
                    audio = audio[:, 0]
                else:
                    audio = audio[:, 0]  # choose left channel by default
            waveform = np.asarray(audio)[None, :]
            return {"fs": int(fs), "waveform": waveform}

        return _loader

    # --------------------------- Utilities ----------------------------

    def _get_results_df_from_subject(self, subject_id: int) -> pd.DataFrame:
        """
        Load and return the comprehension results DataFrame for the given subject.
        These dataframes also give the mapping from cond and cond_idx to actual story chapter
        """
        results_csv = os.path.join(self.download_dir, "results", f"results_{subject_id}.csv")
        if not os.path.exists(results_csv):
            raise FileNotFoundError(f"Results CSV not found for subject {subject_id}: {results_csv}")
        if subject_id == 5:
            header_row = 8
        else:
            header_row = 3
        df = pd.read_csv(results_csv, skiprows=header_row)
        return df
    
    def _parse_fname(self, eeg_path: str) -> Tuple[int, str, int]:
        """
        Parse subject ID, condition token, and chapter number from filename.
        Returns (subject_id, cond_token, chapter_num).
        """
        # e.g., 's10_AenVe2_0.set'
        fname = os.path.splitext(os.path.basename(eeg_path))[0]
        parts = fname.split("_")

        if len(parts) < 3:
            raise ValueError(f"Unexpected filename format: {fname}")

        sub = parts[0]
        cond = "_".join(parts[1:-1])  # join everything between first and last
        cond_idx = parts[-1]

        subject_id = int(sub.replace("s", ""))
        cond_idx = int(cond_idx)

        return subject_id, cond, cond_idx

ADAPTOR = Karengal2025Adaptor