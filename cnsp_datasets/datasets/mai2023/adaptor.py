from __future__ import annotations

import os
import re
import glob
import mne

import numpy as np
import pandas as pd

from mne.io import read_raw_edf, BaseRaw
from mne.channels import make_standard_montage
from typing import Iterable, Optional, Callable, Any, Dict
from pathlib import Path
from scipy.io import wavfile
from scipy.signal import correlate, correlation_lags

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord

mne.set_log_level("CRITICAL")

# ------------------------------- Adaptor ------------------------------------

class Mai2023Adaptor:
    """
    Emits TrialRecord objects for the Mai2023 iEEG dataset.
    """

    def __init__(self, download_dir: str):
        self.download_dir = download_dir

        # discover EEG files
        self._eeg_files = sorted(
            glob.glob(
                os.path.join(
                    self.download_dir,
                    "sub-*",
                    "**",
                    "*_ieeg.edf",
                ),
                recursive=True,
            )
        )

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Yield TrialRecord for every EEG BDF run that has matching event metadata.
        """
        for eeg_path in self._eeg_files:
            print(eeg_path)

            sub_id = self._subject_id(eeg_path)
            session = self._session(eeg_path)

            eeg_path = Path(eeg_path)
            events_path = eeg_path.parent.parent / f"sub-SD{sub_id:03d}_ses-{session:02d}_task-PassiveListen_events.tsv"
            events = pd.read_csv(events_path, sep="\t")

            # we just want to keep the actual stimulus material (not other ambient sounds)
            events = events[~events["ex_name"].isin(["welcome", "pleasePressSpace"])]
            events = events[~events["ex_name"].str.contains("instructions", na=False)]

            # gotta split the recording into trials
            raw = read_raw_edf(eeg_path.as_posix(), preload=False, verbose="ERROR")
            eeg_sfreq = raw.info["sfreq"]
            for i, row in events.iterrows():
                trial_idx = i+1
                stimulus = row["ex_name"]

                # we need to do the crosscorr method to align the stimuli with the eeg
                if "catalan" in stimulus:
                    wav_path = os.path.join(
                        self.download_dir, "stimuli", "excerpts", "catalan_v2", f"{stimulus}_normed.wav"
                    )
                else:
                    wav_path = os.path.join(
                        self.download_dir, "stimuli", "all_stimuli", f"{stimulus}_normed.wav"
                    )
                sr, audio = wavfile.read(wav_path)
                if audio.ndim > 1:
                    audio = audio[:, 0]  # take only one channel if stereo

                stimtrack_channel = "DC1" if sub_id != 15 else "DC2"
                stimtrack_data = raw.pick(stimtrack_channel).load_data().filter(1.0, None, fir_design='firwin'.get_data())
                stimtrack_data = np.clip(stimtrack_data, np.percentile(stimtrack_data, 0.01), np.percentile(stimtrack_data, 99.99))

                audio_resampled = (audio_resampled - np.mean(audio_resampled)) / np.std(audio_resampled)
                stimtrack_data = (stimtrack_data - np.mean(stimtrack_data)) / np.std(stimtrack_data)
                corr = correlate(stimtrack_data, audio_resampled, mode='full')
                lags = correlation_lags(len(stimtrack_data), len(audio_resampled), mode='full')
                lag = lags[np.argmax(corr)]
                onset_time = lag / eeg_sfreq
                offset_time = onset_time + len(audio_resampled) / eeg_sfreq

                # Build stimuli list (single attended audio)
                stimulus = StimulusRecord(
                    modality="audio",
                    name=stimulus.replace("-", "_"),
                    data_fn=self._make_audio_loader(wav_path),
                    is_attended=True,
                    feature_name="audio",
                    )
                
                # Build anat list

                # Lazy EEG loader
                neural_fn = self._make_eeg_loader(
                    onset_time,
                    offset_time,
                    raw=raw,
                    sub_id=sub_id
                )

                if "catalan" in stimulus:
                    condition = "foreign"
                else:
                    condition = "natural"
                yield TrialRecord(
                    subject=sub_id,
                    session=session,
                    trial=trial_idx,
                    condition=condition,
                    ns_type="ieeg",
                    stimulus=[stimulus],
                    neural_data_fn=neural_fn,
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # ------------------------ Lazy loader makers ----------------------

    def _make_audio_loader(self, wav_path: str) -> Callable[[], Dict[str, Any]]:
        """
        Load an audio npz: returns {'fs': int, 'data': np.ndarray[1, T]}.
        """

        def _loader() -> Dict[str, Any]:
            fs, audio = wavfile.read(wav_path)
            if audio.ndim == 1:
                audio = audio[None, :]
            if audio.shape[0] > 1:
                audio = audio[:, 0:1]
            return {"fs": fs, "data": audio}
        return _loader

    def _make_eeg_loader(
        self,
        onset_time: float,
        offset_time: float,
        raw: BaseRaw,
        sub_id: int
    ) -> Callable[[], BaseRaw]:
        """
        """

        def _loader() -> BaseRaw:
            raw = raw.copy().crop(onset_time, offset_time)
            raw.rename_channels(lambda x: x.replace(" ", ""))
            # drop unhelpful channels
            channels_to_exclude = [
                "Pleth", "PR", "OSAT", "TRIG"
            ]

            ch_types_dict = {}

            for c in raw.ch_names:
                if c.startswith("C") and c[1:].isnumeric() and int(c[1:]) > 100:
                    channels_to_exclude.append(c)
                if c.startswith("DC") and c[2:].isnumeric():
                    channels_to_exclude.append(c) 

                if "ekg" in c.lower():
                    ch_types_dict[c] = "ecg"

                if "grid" in c.lower():
                    ch_types_dict[c] = "ecog"

                if c[0] in ["R", "L"]:
                    ch_types_dict[c] = "seeg"

            raw.set_channel_types(ch_types_dict)
            raw.drop_channels(channels_to_exclude)

            raw.rename_channels(lambda x: "T7" if x == "T3" else "T8" if x == "T4" else x)
            raw.set_montage(make_standard_montage("standard_1020"), match_case=False, on_missing="warning")

            return raw

        return _loader

    # ------------------------------ Utils -----------------------------

    def _subject_id(self, eeg_path: str) -> int:
        # .../sub-030/... -> 30
        m = re.search(r"sub-SD(\d+)", os.path.basename(eeg_path))
        return int(m.group(1)) if m else -1

    def _session(self, eeg_path: str) -> Optional[int]:
        m = re.search(r"ses-(\d+)", os.path.basename(eeg_path))
        return int(m.group(1)) if m else None


ADAPTOR = Mai2023Adaptor