from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable

import numpy as np
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray
from pymatreader import read_mat

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import read_wav
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord


class Das2019Adapter(BaseAdaptor):
    """
    Adapter for the Das (2019) EEG dataset.

    Expected layout:
      <root>/
        ├─ S*.mat                          (per-subject MATLAB files; contain 'trials')
        └─ stimuli/*dry.wav                (audio files; 'hrtf' → 'dry' in names)

    For each subject Sxx and each trial:
      - Build condition "competing-f{L|R}-{stimulation_mode}[-rep]".
      - Determine attended/unattended stories from 'attended_ear' + 'stimuli' fields.
      - Emit two stimuli (attended/unattended) with feature_name='audio'.
      - Provide a lazy EEG loader that returns an mne.RawArray using header Fs & ch labels.
      - Audio: the first channel of the wav, float32 in [-1, 1).

    Notes:
      - Trials are 1-based, in recorded order (TrialID).
      - The EEG and the stimuli are aligned at onset; the EEG ends before the longer story, so the audio should be
        truncated to the EEG length (README). Repetition trials use the full part (rep_*.wav equals its first 125 s).
      - The dry (unfiltered) audio is provided for both 'dry' and 'HRTF' trials, as in the authors' analyses.
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self.root = download_dir
        self._mat_files = self.sorted_glob(download_dir, "S*.mat")
        if not self._mat_files:
            raise FileNotFoundError(f"No subject .mat files found under {download_dir!r}")

        # cache: (wav_basename) -> full path
        self._audio_index: Dict[str, str] = self._build_audio_index()

    # ----------------------------- Public API -----------------------------

    def parse(self) -> Iterable[TrialRecord]:
        for mat_path in self._mat_files:
            subj_num = self._subject_number(mat_path)
            data = self._read_subject(mat_path) 
            trials = data["trials"]  # list of dict-like

            for j, tr in enumerate(trials):
                attended_ear: str = tr["attended_ear"]  # 'L' or 'R'
                stim_L, stim_R = tr["stimuli"]          # strings
                stim_mode: str = tr["condition"]        # e.g., 'hrtf' variant etc.

                # choose attended/unattended story names
                att_story = stim_R if attended_ear == "R" else stim_L
                unatt_story = stim_L if attended_ear == "R" else stim_R

                # condition string
                cond = f"competing_f{attended_ear}_{stim_mode}"
                if "rep" in att_story:
                    cond += "_rep"

                # normalise story names to match available audio files
                att_name = self._normalise_story_name(att_story)      # no 'rep_', 'hrtf'→'dry', no '.wav'
                un_name = self._normalise_story_name(unatt_story)


                # Build stimuli (audio only; add envelopes later in canonicalizer if desired)
                stimuli = [
                    StimulusRecord(
                        modality="audio",
                        name=att_name,
                        data_fn=self._make_audio_loader(att_name),
                        is_attended=True,
                        feature_name="audio",
                    ),
                    StimulusRecord(
                        modality="audio",
                        name=un_name,
                        data_fn=self._make_audio_loader(un_name),
                        is_attended=False,
                        feature_name="audio",
                    ),
                ]

                # Lazy EEG loader for this trial
                neural_fn = self._make_eeg_loader(mat_path, trial_index=j)

                yield TrialRecord(
                    subject=subj_num,
                    session=1,
                    trial=j + 1,
                    condition=cond,
                    ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=neural_fn,
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # ----------------------------- Lazy loaders -----------------------------

    def _make_eeg_loader(self, mat_path: str, trial_index: int) -> Callable[[], BaseRaw]:
        """
        Returns a loader that opens the .mat, pulls trial EEG, and constructs RawArray
        using header-derived sampling rate and channel labels.
        """
        def _loader() -> BaseRaw:
            data = self._read_subject(mat_path) # cached, no disk hit
            tr = data["trials"][trial_index]

            Fs = float(tr["FileHeader"]["SampleRate"])
            # channel labels (ensure list[str] length matches eeg rows)
            ch_labels = tr["FileHeader"]["Channels"]["Label"]
            if isinstance(ch_labels, (np.ndarray, tuple, list)):
                ch_names = [str(x) for x in list(ch_labels)]
            else:
                ch_names = [str(ch_labels)]

            # shipped in microvolts, 0.5 Hz high-passed and downsampled to 128 Hz by the authors
            eeg = 1e-6 * np.asarray(tr["RawData"]["EegData"], dtype=float).T  # (n_ch, n_time), volts
            if eeg.ndim != 2:
                raise ValueError(f"Unexpected EEG shape for trial {trial_index}: {eeg.shape}")

            if len(ch_names) != eeg.shape[0]:
                raise ValueError(f"{mat_path} trial {trial_index}: {len(ch_names)} channel labels for "
                                 f"{eeg.shape[0]} channels")

            info = create_info(ch_names=ch_names, sfreq=Fs, ch_types="eeg")
            info.set_montage(make_standard_montage("biosemi64"))
            raw = RawArray(eeg, info, verbose="ERROR")
            return raw
        return _loader

    def _make_audio_loader(self, story_name_no_ext: str) -> Callable[[], Dict[str, Any]]:
        """
        Returns a loader that finds '<story>.wav' (dry) under stimuli/ and returns
        {'fs': int, 'data': float32 (1, T)} (first channel).
        """
        wav_basename = f"{story_name_no_ext}.wav"
        wav_path = self._audio_index.get(wav_basename)  # the index holds every wav under stimuli/

        def _loader() -> Dict[str, Any]:
            if wav_path is None or not os.path.exists(wav_path):
                raise FileNotFoundError(f"Audio not found for story '{story_name_no_ext}': expected '{wav_basename}'")
            data, fs = read_wav(wav_path, channel=0)
            return {"fs": fs, "data": data}
        return _loader

    # ----------------------------- Helpers -----------------------------

    @lru_cache(maxsize=2)  # each subject file is ~0.3 GB; trials are read subject by subject
    def _read_subject(self, mat_path: str):
        return read_mat(mat_path)

    def _subject_number(self, mat_path: str) -> int:
        # 'S12.mat' -> 12, 'S003.mat' -> 3
        base = os.path.splitext(os.path.basename(mat_path))[0]
        return int(base.replace("S", ""))

    def _normalise_story_name(self, name: str) -> str:
        # match your legacy cleaning: drop 'rep_', replace 'hrtf' with 'dry', drop extension
        clean = name.replace("rep_", "").replace("hrtf", "dry").replace(".wav", "")
        return clean.replace("-", "_")

    def _build_audio_index(self) -> Dict[str, str]:
        """Basename -> path of every wav under stimuli/ (any depth); a basename found twice raises."""
        index: Dict[str, str] = {}
        for p in self.sorted_glob(os.path.join(self.root, "stimuli"), "**/*.wav"):
            name = os.path.basename(p)
            if name in index:
                raise ValueError(f"two stimulus files named {name}: {index[name]} and {p}")
            index[name] = p
        return index


ADAPTOR = Das2019Adapter
