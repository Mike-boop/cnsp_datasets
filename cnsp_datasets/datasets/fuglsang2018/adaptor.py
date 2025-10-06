from __future__ import annotations

import os
import glob
from typing import Iterable, Callable, Any, Dict, List
from functools import lru_cache

import numpy as np
from mne import create_info
from mne.io import RawArray, BaseRaw
from scipy.io import wavfile
from pymatreader import read_mat

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


REVERB_MAP = {1: "noRev", 2: "lowRev", 3: "highRev"}


class Fuglsang2018Adapter:
    """
    Adapter for the Fuglsang 2018 dataset (EEG + two-talker audio with reverb).

    Expected layout (as in your script):
      <root>/
        ├─ EEG/S*.mat                         (per-subject EEG + events)
        ├─ AUDIO/*.wav                        (stimuli wavs)
        └─ info/expinfo_S<sub>.mat            (per-subject experiment info)

    Behavior:
      - EEG fs assumed 512 Hz.
      - Use event/eeg/sample alternating (onset, offset, onset, offset, ...) to cut trials.
      - Extend each trial by +5 s after offset.
      - Keep only first 64 EEG channels (drop EOG/Status).
      - Determine attended sex (M/F) and ear (L/R), select attended/unattended wavs.
      - Condition:
            competing-f{L|R}-{noRev|lowRev|highRev}
        DSS control (male wav == 'dss.wav'):
            natural-{L|R}, single attended stimulus ('dss')
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        self._eeg_files = sorted(glob.glob(os.path.join(download_dir, "S*.mat")))
        self._eeg_files = [f for f in self._eeg_files if not "_data_preproc" in f]
        if not self._eeg_files:
            raise FileNotFoundError(f"No EEG files found under {os.path.join(download_dir, 'EEG')}")

        # Index AUDIO wavs for quick lookup
        self._audio_index: Dict[str, str] = self._build_audio_index()

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        for subj_mat in self._eeg_files:
            sub_id = self._subject_id(subj_mat)
            expinfo_path = os.path.join(os.path.dirname(__file__), "expinfos", f"expinfo_S{sub_id}.mat")
            exp = read_mat(expinfo_path)  # contains keys like attend_mf, attend_lr, wavfile_male/female, acoustic_condition

            dm = self._read_subject(subj_mat)
            data = dm["data"]

            # EEG is time x channels; keep first 64 (drop EOG/status)
            # We'll slice per trial lazily.
            # Events: alternating onset/offset sample indices
            onsets = np.asarray(data["event"]["eeg"]["sample"][::2], dtype=int)
            offsets = np.asarray(data["event"]["eeg"]["sample"][1::2], dtype=int)

            fs = 512
            tail = 5 * fs  # +5s tail

            n_trials = min(len(onsets), len(offsets))

            for i in range(n_trials):
                # who is attended this trial?
                attended_sex = "M" if int(exp["data"]["attend_mf"][i]) == 1 else "F"
                attended_ear = "L" if int(exp["data"]["attend_lr"][i]) == 1 else "R"

                # file names from expinfo
                male_wav = str(exp["data"]["wavfile_male"][i])
                female_wav = str(exp["data"]["wavfile_female"][i])

                # DSS control?
                is_dss = (male_wav == "dss.wav")

                if attended_sex == "M":
                    att_file = male_wav
                    un_file  = female_wav
                else:
                    att_file = female_wav
                    un_file  = male_wav

                # condition label
                if is_dss:
                    condition = f"natural-{attended_ear}"
                else:
                    rev_code = int(exp["data"]["acoustic_condition"][i])
                    reverb = REVERB_MAP.get(rev_code, str(rev_code))
                    condition = f"competing-f{attended_ear}-{reverb}"

                # Stimulus names (strip .wav)
                att_name = os.path.splitext(att_file)[0]
                stimuli: List[StimulusRecord] = [
                    StimulusRecord(
                        modality="audio",
                        name=att_name,
                        data_fn=self._make_audio_loader(att_file),
                        is_attended=True,
                        feature_name="audio",
                    )
                ]
                if not is_dss:
                    un_name = os.path.splitext(un_file)[0]
                    stimuli.append(
                        StimulusRecord(
                            modality="audio",
                            name=un_name,
                            data_fn=self._make_audio_loader(un_file),
                            is_attended=False,
                            feature_name="audio",
                        )
                    )

                # lazy EEG loader for this trial
                t0 = int(onsets[i])
                t1 = int(offsets[i]) + tail
                neural_fn = self._make_eeg_loader(subj_mat, t0, t1, fs)

                yield TrialRecord(
                    subject=sub_id,
                    session=1,
                    trial=i,  # keep 0-based to mirror your original; change to i+1 if preferred
                    condition=condition,
                    ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=neural_fn,
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # ------------------------ Lazy loaders ------------------------

    def _make_eeg_loader(self, subj_mat: str, s0: int, s1: int, fs: int) -> Callable[[], BaseRaw]:
        """
        Load this subject's EEG mat, slice [s0:s1] (time x ch), keep first 64 ch,
        transpose to (ch, time), return RawArray with channel names if available.
        """
        def _loader() -> BaseRaw:
            dm = self._read_subject(subj_mat)
            d = dm["data"]

            # time x ch, keep 64 EEG channels
            full = np.asarray(d["eeg"], dtype=float)  # (T, C)
            eeg = full[s0 : min(s1, full.shape[0]), :64]  # (T_slice, 64)

            # channel names (first 64); fallback to generic if mismatch
            ch = d["dim"]["chan"]["eeg"]
            ch_names = [str(x) for x in (list(ch) if isinstance(ch, (list, tuple, np.ndarray)) else [ch])]
            if len(ch_names) < 64:
                ch_names = [f"EEG{i+1:02d}" for i in range(64)]
            else:
                ch_names = ch_names[:64]

            info = create_info(ch_names=ch_names, sfreq=float(fs), ch_types="eeg")
            raw = RawArray(eeg.T, info, verbose="ERROR")  # transpose to (ch, time)
            return raw
        return _loader

    def _make_audio_loader(self, wav_filename: str) -> Callable[[], Dict[str, Any]]:
        """
        Return loader for AUDIO/<wav_filename>.
        """
        wav_path = self._audio_index.get(wav_filename)
        if wav_path is None:
            # try direct path under AUDIO in case index missed it
            candidate = os.path.join(self.root, wav_filename)
            if os.path.exists(candidate):
                wav_path = candidate
                self._audio_index[wav_filename] = candidate

        def _loader() -> Dict[str, Any]:
            if wav_path is None or not os.path.exists(wav_path):
                raise FileNotFoundError(f"Audio not found: {wav_filename}")
            fs, x = wavfile.read(wav_path)
            if x.ndim == 2:
                x = x[:, 0]
            return {"fs": int(fs), "waveform": np.asarray(x, dtype=float)[None, :]}
        return _loader

    # ------------------------ Helpers ------------------------

    def _subject_id(self, subj_mat: str) -> int:
        base = os.path.splitext(os.path.basename(subj_mat))[0]  # 'S12'
        return int(base.replace("S", ""))

    def _build_audio_index(self) -> Dict[str, str]:
        index: Dict[str, str] = {}
        for p in glob.glob(os.path.join(self.root, "AUDIO", "*.wav")):
            index[os.path.basename(p)] = p
        return index
    
    @lru_cache(maxsize=None)
    def _read_subject(self, mat_path: str):
        return read_mat(mat_path)

ADAPTOR = Fuglsang2018Adapter