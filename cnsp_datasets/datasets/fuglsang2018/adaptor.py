from __future__ import annotations

import os
import glob
from typing import Iterable, Callable, Any, Dict, List
from functools import lru_cache

import numpy as np
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import RawArray, BaseRaw
from scipy.io import wavfile
from pymatreader import read_mat

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


REVERB_MAP = {1: "noRev", 2: "lowRev", 3: "highRev"}

# BioSemi EXG channels: EOG pairs as used in the authors' preproc_data.m; the others are undocumented
# (EXG1/EXG2 are probably the mastoids), so they are kept as misc
EOG = ("EXG3", "EXG4", "EXG5", "EXG7")
MISC = ("EXG1", "EXG2", "EXG6", "EXG8")


class Fuglsang2018Adapter:
    """
    Adapter for the Fuglsang 2018 dataset (EEG + two-talker audio with reverb).

    Expected layout:
      <root>/
        ├─ S*.mat     (per-subject EEG + events, BioSemi 512 Hz, microvolts)
        └─ *.wav      (stimuli; also accepted under AUDIO/)
      expinfo_S<sub>.mat (per-subject experiment info) ship with this adaptor (expinfos/).

    Behaviour:
      - Trials start at their onset trigger (code == expinfo.trigger) and last exactly as long as the stimulus
        (all 50 s), so missing or stray end triggers do not matter. Onsets are matched to expinfo by code, in order.
      - The end triggers (code 191) arrive 3-4 samples (5.9-7.8 ms) before the stimulus duration. Since every trial
        is 50 s, a constant end-trigger latency and -120 ppm clock drift cannot be told apart; no correction.
      - EEG in volts: 64 scalp channels, EOG (EXG3/4/5/7) as 'eog', EXG1/2/6/8 as 'misc'; Status is dropped.
      - Condition: competing-f{L|R}-{noRev|lowRev|highRev}; single-talker DSS trials (male wav == 'dss.wav'):
        natural-{L|R}, single attended stimulus ('dss').
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        self._eeg_files = sorted(glob.glob(os.path.join(download_dir, "S*.mat")))
        self._eeg_files = [f for f in self._eeg_files if "_data_preproc" not in f]
        if not self._eeg_files:
            raise FileNotFoundError(f"No EEG files found under {download_dir}")
        self._audio_index: Dict[str, str] = self._build_audio_index()

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        for subj_mat in self._eeg_files:
            sub_id = self._subject_id(subj_mat)
            exp = read_mat(os.path.join(os.path.dirname(__file__), "expinfos", f"expinfo_S{sub_id}.mat"))["data"]
            onsets = self._onsets(subj_mat, np.asarray(exp["trigger"], dtype=int))

            for i, onset in enumerate(onsets):
                if onset is None:
                    continue
                attended_sex = "M" if int(exp["attend_mf"][i]) == 1 else "F"
                attended_ear = "L" if int(exp["attend_lr"][i]) == 1 else "R"
                male_wav, female_wav = str(exp["wavfile_male"][i]), str(exp["wavfile_female"][i])
                is_dss = male_wav == "dss.wav"
                att_file, un_file = (male_wav, female_wav) if attended_sex == "M" else (female_wav, male_wav)

                if is_dss:
                    condition = f"natural-{attended_ear}"
                else:
                    rev_code = int(exp["acoustic_condition"][i])
                    condition = f"competing-f{attended_ear}-{REVERB_MAP.get(rev_code, str(rev_code))}"

                stimuli: List[StimulusRecord] = [StimulusRecord(
                    modality="audio", name=os.path.splitext(att_file)[0], data_fn=self._make_audio_loader(att_file),
                    is_attended=True, feature_name="audio",
                )]
                if not is_dss:
                    stimuli.append(StimulusRecord(
                        modality="audio", name=os.path.splitext(un_file)[0], data_fn=self._make_audio_loader(un_file),
                        is_attended=False, feature_name="audio",
                    ))

                yield TrialRecord(
                    subject=sub_id,
                    session=1,
                    trial=i + 1,
                    condition=condition,
                    ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=self._make_eeg_loader(subj_mat, onset, self._audio_duration(att_file)),
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # ------------------------ Lazy loaders ------------------------

    def _make_eeg_loader(self, subj_mat: str, onset: int, duration_s: float) -> Callable[[], BaseRaw]:
        """EEG from the onset sample for the stimulus duration, in volts, with EOG/misc channel types."""
        def _loader() -> BaseRaw:
            d = self._read_subject(subj_mat)["data"]
            fs = float(d["fsample"]["eeg"])
            ch_names = [str(c) for c in d["dim"]["chan"]["eeg"]]
            keep = [i for i, c in enumerate(ch_names) if c != "Status"]
            stop = onset + int(round(duration_s * fs))
            eeg = 1e-6 * np.asarray(d["eeg"][onset:stop, keep], dtype=float).T  # microvolts -> volts
            names = [ch_names[i] for i in keep]
            types = ["eog" if c in EOG else "misc" if c in MISC else "eeg" for c in names]
            info = create_info(ch_names=names, sfreq=fs, ch_types=types)
            info.set_montage(make_standard_montage("biosemi64"), on_missing="ignore")
            return RawArray(eeg, info, verbose="ERROR")
        return _loader

    def _make_audio_loader(self, wav_filename: str) -> Callable[[], Dict[str, Any]]:
        wav_path = self._wav_path(wav_filename)

        def _loader() -> Dict[str, Any]:
            fs, x = wavfile.read(wav_path)
            if x.ndim == 2:
                x = x[:, 0]
            return {"fs": int(fs), "data": np.asarray(x, dtype=float)[None, :]}
        return _loader

    # ------------------------ Helpers ------------------------

    def _onsets(self, subj_mat: str, triggers: np.ndarray) -> List[int | None]:
        """
        Onset sample of each expinfo trial, matching trigger codes in order (None if a trial's onset is missing).

        Matching in order skips stray events: in S8, trial 46's end trigger is missing and an event coded 192
        arrives 19.6 s after its onset, which broke the former alternating onset/offset pairing.
        """
        ev = self._read_subject(subj_mat)["data"]["event"]["eeg"]
        codes = [int(v) for v in ev["value"]]
        samples = np.asarray(ev["sample"], dtype=int)
        onsets, k = [], 0
        for code in triggers:
            while k < len(codes) and codes[k] != code:
                k += 1
            onsets.append(int(samples[k]) if k < len(codes) else None)
            k += 1
        if None in onsets:
            raise ValueError(f"{subj_mat}: could not match onset codes {codes} to expinfo {triggers.tolist()}")
        return onsets

    def _wav_path(self, wav_filename: str) -> str | None:
        return self._audio_index.get(wav_filename)

    def _audio_duration(self, wav_filename: str) -> float:
        fs, x = wavfile.read(self._wav_path(wav_filename), mmap=True)
        return len(x) / fs

    def _subject_id(self, subj_mat: str) -> int:
        return int(os.path.splitext(os.path.basename(subj_mat))[0].replace("S", ""))

    def _build_audio_index(self) -> Dict[str, str]:
        paths = glob.glob(os.path.join(self.root, "*.wav")) + glob.glob(os.path.join(self.root, "AUDIO", "*.wav"))
        return {os.path.basename(p): p for p in paths}

    @lru_cache(maxsize=2)  # each subject file is ~1 GB; trials are read subject by subject
    def _read_subject(self, mat_path: str):
        return read_mat(mat_path)


ADAPTOR = Fuglsang2018Adapter
