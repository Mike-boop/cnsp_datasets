# nsptools/adapters/das2019.py
from __future__ import annotations

import os
import glob
from functools import lru_cache
from typing import Iterable, Callable, Any, Dict

import numpy as np
from pymatreader import read_mat
from scipy.io import wavfile
from mne import create_info
from mne.io import RawArray, BaseRaw
from mne.channels import make_standard_montage

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


class Das2019Adapter:
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

    Notes:
      - Trial indices are kept 0-based (to match your original filenames). Switch to 1-based
        by changing `trial=j` → `trial=j+1`.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        self._mat_files = sorted(glob.glob(os.path.join(download_dir, "S*.mat")))
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
                    trial=j,                 # change to j+1 if you prefer 1-based trials
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

            eeg = np.asarray(tr["RawData"]["EegData"], dtype=float).T  # shape (n_ch, n_time)
            if eeg.ndim != 2:
                raise ValueError(f"Unexpected EEG shape for trial {trial_index}: {eeg.shape}")

            # If labels count mismatches, fall back to generic names
            if len(ch_names) != eeg.shape[0]:
                ch_names = [f"EEG{i+1:02d}" for i in range(eeg.shape[0])]

            info = create_info(ch_names=ch_names, sfreq=Fs, ch_types="eeg")
            info.set_montage(make_standard_montage("biosemi64"))
            raw = RawArray(eeg, info, verbose="ERROR")
            return raw
        return _loader

    def _make_audio_loader(self, story_name_no_ext: str) -> Callable[[], Dict[str, Any]]:
        """
        Returns a loader that finds '<story>.wav' (dry) under stimuli/ and returns
        {'fs': int, 'waveform': (1, T)}.
        """
        wav_basename = f"{story_name_no_ext}.wav"
        wav_path = self._audio_index.get(wav_basename)
        if wav_path is None:
            # try a best-effort search each call if not in index
            cand = glob.glob(os.path.join(self.root, "stimuli", "**", wav_basename), recursive=True)
            if cand:
                wav_path = cand[0]
                self._audio_index[wav_basename] = wav_path

        def _loader() -> Dict[str, Any]:
            if wav_path is None or not os.path.exists(wav_path):
                raise FileNotFoundError(f"Audio file not found for story '{story_name_no_ext}': expected '{wav_basename}'")
            fs, x = wavfile.read(wav_path)
            if x.ndim == 2:
                x = x[:, 0]  # mono
            return {"fs": int(fs), "waveform": np.asarray(x, dtype=float)[None, :]}
        return _loader

    # ----------------------------- Helpers -----------------------------

    @lru_cache(maxsize=None)
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
        """
        Index all dry WAVs under stimuli/ for quick lookup.
        """
        index: Dict[str, str] = {}
        for p in glob.glob(os.path.join(self.root, "stimuli", "**", "*dry.wav"), recursive=True):
            index[os.path.basename(p)] = p
        # also index any plain .wav (in case you already have cleaned names without 'dry')
        for p in glob.glob(os.path.join(self.root, "stimuli", "**", "*.wav"), recursive=True):
            index.setdefault(os.path.basename(p), p)
        return index

ADAPTOR = Das2019Adapter