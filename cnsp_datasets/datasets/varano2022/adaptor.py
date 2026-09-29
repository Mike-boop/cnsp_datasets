from __future__ import annotations

import os
import glob
import mne

import numpy as np
import pandas as pd

from scipy.io import wavfile
from mne.io import read_raw_fif, BaseRaw
from typing import Iterable, Dict, Tuple, Optional, Callable, Any, List

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord

mne.set_log_level("CRITICAL")


# Map raw condition tokens -> standardized names
STANDARDISED_COND = {
    "00": "sin",
    "nh_AV": "AV_natural_sin",
    "4v_AV": "AV_edge_sin",
    "bw_AV": "AV_cartoon_sin",
    "1e_AV": "AV_disk_sin",
    "1m_AV": "AV_mismatchdisk_sin",
    "nh_V0": "V0_natural",
    "4v_V0": "V0_edge",
    "bw_V0": "V0_cartoon",
    "1e_V0": "V0_disk",
    "1m_V0": "V0_disk",  # not a typo
}


class Varano2022Adaptor:
    """
    Adapter for the Varano AV dataset, generating TrialRecord objects.

    Expected layout (as in your legacy code):
      - EEG FIF files:
          <download_dir>/data_2020/split_trials/unprocessed/raw//*.fif
      - Audio (A stream):
          <download_dir>/AVbook/A/FXX.wav
      - Per-subject condition order CSVs:
          <download_dir>/condorders/cond_orders/condorder_subN.csv

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
                    "data_2020",
                    "split_trials",
                    "unprocessed",
                    "raw",
                    "*.fif",
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
            subject_id = self._subject_from_fname(eeg_path)  # int
            cond_token, chapter_num = self._condition_and_chapter(eeg_path)
            std_cond = STANDARDISED_COND.get(cond_token, cond_token)

            # Read per-subject condition order
            try:
                cond_order_df = self._get_condition_order_df(subject_id)
            except FileNotFoundError as e:
                continue

            # Locate the row for this file’s condition/chapter -> story_part_idx
            if cond_token == "00": cond_token = "A0" # different symbol in the csv!!
            trial_row = cond_order_df[(cond_order_df["condition"] == cond_token) & (cond_order_df["condCount"] == chapter_num)]
            if trial_row.empty:
                continue

            story_part_idx: int = trial_row["trial_index"].item()

            # Trial number
            trial_number = story_part_idx - 2

            # Build stimuli
            stimuli: List[StimulusRecord] = []

            # Attended AUDIO A-stream: AVbook/A/FXX.wav
            if "V0" not in cond_token:
                story_part_a = trial_row["audio_story_part"].item()
                audio_name = story_part_a

                audio_loader = self._make_audio_loader(story_part_a)
                stimuli.append(
                    StimulusRecord(
                        modality="audio",
                        name=audio_name,
                        data_fn=audio_loader,
                        is_attended=True,
                        feature_name="audio",
                    )
                )

                tg_loader = self._make_tg_loader(story_part_a)
                stimuli.append(
                    StimulusRecord(
                        modality="audio",
                        name=audio_name,
                        data_fn=tg_loader,
                        is_attended=True,
                        feature_name="textgrid",
                    )
                )



            # Special cases with mismatched A/V pairing: add a second "visual" stimulus name
            if cond_token == "1m_AV" or "V0" in cond_token:
                story_part_v = trial_row["visual_story_part"].item()
                visual_name = story_part_v
                visual_loader = self._make_audio_loader(story_part_v)
                stimuli.append(
                    StimulusRecord(
                        modality="visual",
                        name=visual_name,
                        data_fn=visual_loader,
                        is_attended=(cond_token == "1m_V0"),  # V0-only may be attended visually
                        feature_name="audio",
                    )
                )

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
            raw = read_raw_fif(fif_path, preload=True, verbose="ERROR")
            # crop: 1.995 s from both ends
            sf = raw.info["sfreq"]
            raw.crop(1.995, raw.n_times / sf - 1.995)
            return raw
        return _loader

    def _make_audio_loader(self, story_part_a: str) -> Callable[[], Dict[str, Any]]:
        """
        Load AVbook A-stream FXX.wav and return dict {'fs': int, 'data': np.ndarray[1, T]}.
        """
        wav_path = os.path.join(self.download_dir, "AVbook", "A", f"{story_part_a}.wav")

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
            return {"fs": int(fs), "data": waveform}

        return _loader
    
    def _make_tg_loader(self, story_part_a: str) -> Callable[[], str]:
        tg_path = os.path.join(self.download_dir, "F", f"{story_part_a}.TextGrid")

        def _loader() -> str:
            with open(tg_path, "r") as f:
                text = f.read()
            return text
        return _loader

    # --------------------------- Utilities ----------------------------

    def _subject_from_fname(self, eeg_path: str) -> int:
        # e.g., 'sub012_nh_AV_3_raw.fif' or 'sub012_3_raw.fif'
        stem = os.path.splitext(os.path.basename(eeg_path))[0]
        first = stem.split("_")[0]
        return int(first.replace("sub", ""))

    def _condition_and_chapter(self, eeg_path: str) -> Tuple[str, int]:
        """
        Parse condition token and chapter number from filename.
        Matches your legacy logic:
          - if 3 tokens -> '00' (sin), else '_'.join(tokens[1:3])
          - chapter number = last token (int)
        """
        stem = os.path.splitext(os.path.basename(eeg_path))[0]
        parts = stem.split("_")
        if len(parts) == 3:
            cond = "00"
        else:
            cond = "_".join(parts[1:3])
        chapter = int(parts[-1])
        return cond, chapter

    def _mismatched_visual_part(self, subject_id: int, story_part_a: str) -> Optional[str]:
        """
        For 1m_* cases, find the paired V part from the CSV if available.
        """
        csv_path = os.path.join(self.info_dir, f"mismatched_stimuli_pairs-sub{subject_id}.csv")
        if not os.path.exists(csv_path):
            return None
        df = pd.read_csv(csv_path)
        row = df.loc[df["A"] == story_part_a]
        if row.empty:
            return None
        return row["V"].item()


ADAPTOR = Varano2022Adaptor