from __future__ import annotations

import glob
import os
import re
from typing import Any, Callable, Dict, Iterable

import numpy as np
import pandas as pd
from mne.io import BaseRaw, read_raw_fif
from scipy.io import wavfile

from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

PAD_S = 1.995  # EEG kept before and after each stimulus in the split trial files

# raw condition token (file name) -> standardised name. Video: 1e envelope dot, 1m mismatched dot (1e video of
# another story part), 4v cartoon, bw edge detection, nh natural. AV conditions and A0 are speech in noise ("sin").
STANDARDISED_COND = {
    "A0": "A_sin",
    "nh_AV": "AV_natural_sin",
    "4v_AV": "AV_cartoon_sin",
    "bw_AV": "AV_edge_sin",
    "1e_AV": "AV_disk_sin",
    "1m_AV": "AV_mismatchdisk_sin",
    "nh_V0": "V0_natural",
    "4v_V0": "V0_cartoon",
    "bw_V0": "V0_edge",
    "1e_V0": "V0_disk",
    "1m_V0": "V0_disk",  # without audio a mismatched disk is a disk
}


class Varano2022Adaptor:
    """
    Adaptor for Varano et al. 2022 (AVbook audiovisual speech in noise, 1 kHz EEG, 19 subjects x 55 trials).

    Layout:
      - EEG: data_2020/split_trials/unprocessed/raw/sub<N>_<cond>_<k>.fif (<cond> '00' = A0), 1.995 s of EEG
        before and after each stimulus. <k> (0-4) counts the trials of a condition in presentation order.
      - Trial -> story part: condorders/cond_orders/condorder_sub<N>.csv (rows in presentation order; the two
        'setup' rows have no EEG). Checked: file order (meas_date, first_samp) follows trial_index, and every trial
        lasts its wav + 2 x 1.995 s (mismatched AV: the shorter of the audio and video parts).
      - Audio: AVbook/A/<part>.wav (clean speech; it was played in noise, which is not shipped); word alignments
        F/<part>.TextGrid.
    The speech starts 1.995 s into each file (as in the authors' aligned envelopes, data_2020/.../stim_dwnspl); the
    shipped files have no stimtrack, so this onset is nominal. The audio is not cut to the trial: mismatched AV
    trials end with the shorter video, so their EEG is shorter than the audio. V0 and mismatched AV trials get a 'visual' stimulus: the speech
    of the story part shown in the video (not played).
    """

    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self._eeg_files = sorted(glob.glob(os.path.join(download_dir, "data_2020", "split_trials", "unprocessed",
                                                        "raw", "sub*.fif")))

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        orders = {}
        for eeg_path in self._eeg_files:
            subject, cond, k = re.match(r"sub(\d+)_(.+)_(\d+)\.fif", os.path.basename(eeg_path)).groups()
            subject, cond = int(subject), "A0" if cond == "00" else cond
            if subject not in orders:
                orders[subject] = self._condition_order(subject)
            row = orders[subject].loc[(cond, int(k))]

            stimuli = []
            if isinstance(row.audio_story_part, str):
                part = row.audio_story_part
                stimuli += [
                    StimulusRecord(modality="audio", name=part, data_fn=self._make_audio_loader(part),
                                   is_attended=True, feature_name="audio"),
                    StimulusRecord(modality="audio", name=part, data_fn=self._make_tg_loader(part),
                                   is_attended=True, feature_name="textgrid"),
                ]
            if cond == "1m_AV" or cond.endswith("V0"):
                part = row.visual_story_part
                stimuli.append(StimulusRecord(modality="visual", name=part,
                                              data_fn=self._make_audio_loader(part),
                                              is_attended=cond.endswith("V0"), feature_name="audio"))

            yield TrialRecord(
                subject=subject,
                session=1,
                trial=int(row.trial_index) - 1,  # 1-based after the two setup trials
                condition=STANDARDISED_COND[cond],
                ns_type="eeg",
                stimulus=stimuli,
                neural_data_fn=self._make_eeg_loader(eeg_path),
                structural_data_fn=None,
                behavioural_data_fn=None,
            )

    # ------------------------ Lazy loader makers ----------------------

    def _condition_order(self, subject: int) -> pd.DataFrame:
        """condorder rows indexed by (condition, k-th trial of that condition)."""
        df = pd.read_csv(os.path.join(self.download_dir, "condorders", "cond_orders",
                                      f"condorder_sub{subject}.csv"))
        df = df[df.condition != "setup"]
        return df.set_index([df.condition, df.groupby("condition").cumcount()])

    @staticmethod
    def _make_eeg_loader(fif_path: str) -> Callable[[], BaseRaw]:
        def _loader() -> BaseRaw:
            raw = read_raw_fif(fif_path, preload=True, verbose="ERROR")
            pad = round(PAD_S * raw.info["sfreq"])
            return raw.crop(tmin=raw.times[pad], tmax=raw.times[raw.n_times - pad - 1])
        return _loader

    def _make_audio_loader(self, part: str) -> Callable[[], Dict[str, Any]]:
        """AVbook/A/<part>.wav (whole; not cut to the trial)."""
        wav_path = os.path.join(self.download_dir, "AVbook", "A", f"{part}.wav")

        def _loader() -> Dict[str, Any]:
            fs, x = wavfile.read(wav_path)
            x = x[:, 0] if x.ndim == 2 else x
            return {"fs": int(fs), "data": np.asarray(x, dtype=float)[None, :]}
        return _loader

    def _make_tg_loader(self, part: str) -> Callable[[], str]:
        tg_path = os.path.join(self.download_dir, "F", f"{part}.TextGrid")

        def _loader() -> str:
            with open(tg_path) as f:
                return f.read()
        return _loader


ADAPTOR = Varano2022Adaptor
