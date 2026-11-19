from __future__ import annotations

import os
import glob
from typing import Any, Callable, Iterable, List
import numpy as np
import h5py
from scipy.io import wavfile

from mne import create_info
from mne.channels import make_standard_montage
from mne.io import RawArray, BaseRaw

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


class Etard2019Adaptor:
    """
    Etard et al. 2019 (Reichenbach lab): 63-channel EEG at 1 kHz, English audiobooks in quiet, in babble noise at
    three SNRs and with a competing speaker, and Dutch (foreign) audiobooks in quiet and in babble; 4 parts each.

    The authors cut the EEG per part (`align_data.py`) at the onset found by cross-correlating the Sound stimtrack
    with the attended stream (sample-accurate; drift not corrected), and wrote the streams as played next to it:
    `audiobooks/<cond>/part_<n>_story.wav` (attended) and `part_<n>_distractor.wav` (babble noise or the competing
    speaker), both starting at the EEG's first sample. English babble conditions: noise 1 s before and after the
    story (the story wav is zero-padded). Dutch babble conditions: noise starts 1 s after the story.

    Dutch parts contain short English sentences (participants detected them) in silent gaps of the Dutch stream.
    For cleanDutch they are added to the attended stream (`part_<n>_english.wav`, same length). For lb/mb/hbDutch
    the shipped English wavs and onsets are copies of the cleanDutch ones (align_data.py reads them from cleanDutch
    for all four conditions) and do not fit those stories, so the English is missing there (2.5-4 s gaps).
    """

    # known raw condition labels in the H5 -> standardized names
    _COND_MAP = {
        "clean": "natural",
        "lb": "sin_lowSNR",
        "mb": "sin_mediumSNR",
        "hb": "sin_highSNR",
        "fM": "competing_fM",
        "fW": "competing_fF",
        "cleanDutch": "foreign_quiet",
        "lbDutch": "foreign_lowSNR",
        "mbDutch": "foreign_mediumSNR",
        "hbDutch": "foreign_highSNR",
    }

    def __init__(
        self,
        download_dir: str
    ):
        """English conditions are session 1, Dutch session 2 (P11 and P12 took part in the Dutch session only)."""
        self.download_dir = download_dir
        self._subject_files = sorted(glob.glob(os.path.join(self.download_dir, "P*.h5")))
        self._info = self._make_mne_info(self._subject_files[0])
        self._raw_conditions = set(self._COND_MAP.keys())

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Yields TrialRecord for each (subject, condition, trial).
        Stimulus list:
          - always includes an attended "story" stimulus
          - includes a "distractor" stimulus for competing-speech conditions (fM/fW)
        """
        for subj_path in self._subject_files:
            subject = self._parse_subject_id(subj_path)  # e.g., 'P03.h5' -> 3

            with h5py.File(subj_path, "r") as f:
                # Some subjects may miss Dutch conditions; only use groups present in H5
                present_conds = [c for c in f.keys() if c in self._raw_conditions]

                for raw_cond in present_conds:
                    std_cond = self._standardize_condition(raw_cond)

                    if "Dutch" in raw_cond:
                        session = 2
                    else:
                        session = 1

                    for trial in (1, 2, 3, 4):
                        # EEG lazy loader
                        neural_fn = self._make_eeg_loader(subj_path, raw_cond, trial)

                        # Stimuli list (attended always; distractor for two-speaker)
                        stimuli: List[StimulusRecord] = []

                        attended_name = f"{std_cond}_part_{trial}_story"
                        attended_fn = self._make_audio_loader(raw_cond, trial, role="story")
                        stimuli.append(
                            StimulusRecord(
                                modality="audio",
                                name=attended_name,
                                data_fn=attended_fn,
                                is_attended=True,
                                feature_name="audio",
                            )
                        )

                        if not raw_cond.startswith("clean"):
                            role = "distractor" if raw_cond in ("fM", "fW") else "babble"
                            distractor_name = f"{std_cond}_part_{trial}_{role}"
                            distractor_fn = self._make_audio_loader(raw_cond, trial, role="distractor")
                            stimuli.append(
                                StimulusRecord(
                                    modality="audio",
                                    name=distractor_name,
                                    data_fn=distractor_fn,
                                    is_attended=False,
                                    feature_name="audio",
                                )
                            )

                        yield TrialRecord(
                            subject=subject,
                            session=session,
                            trial=trial,
                            condition=std_cond,
                            ns_type="eeg",
                            stimulus=stimuli,
                            neural_data_fn=neural_fn,
                            structural_data_fn=None,
                            behavioural_data_fn=None,
                        )

    # ------------------------ Lazy loader makers ----------------------

    def _make_eeg_loader(self, subject_h5_path: str, raw_condition: str, trial: int) -> Callable[[], BaseRaw]:
        """
        Returns a 0-arg function that opens the H5, reads EEG, and builds mne.RawArray.
        """
        h5_path = subject_h5_path
        key = f"{raw_condition}/part_{trial}"

        def _loader() -> BaseRaw:
            with h5py.File(h5_path, "r") as f:
                if key not in f:
                    raise KeyError(f"Missing EEG dataset: '{key}' in {h5_path}")
                eeg = f[key][:]  # shape (n_channels, n_times)
            raw = RawArray(eeg, self._info, verbose="ERROR")
            return raw

        return _loader

    def _make_audio_loader(self, raw_cond: str, trial: int, role: str) -> Callable[[], Any]:
        """
        Returns a 0-arg function that loads WAV if mapping is known; otherwise raises with guidance.
        The return value is a dict: {"fs": int, "data": np.ndarray[1, T]}.
        """
        wav_path = os.path.join(self.download_dir, "audiobooks", raw_cond, f"part_{trial}_{role}.wav")

        english_path = os.path.join(self.download_dir, "audiobooks", raw_cond, f"part_{trial}_english.wav")

        def _loader() -> Any:
            fs, audio = wavfile.read(wav_path)
            if raw_cond == "cleanDutch" and role == "story":  # the English sentences fill gaps in the Dutch stream
                audio = audio + wavfile.read(english_path)[1]
            return {"fs": int(fs), "data": np.asarray(audio, dtype=float)[None, :]}

        return _loader

    # --------------------------- Utilities ----------------------------

    def _parse_subject_id(self, subj_path: str) -> int:
        stem = os.path.splitext(os.path.basename(subj_path))[0]  # "P03"
        return int(stem.replace("P", ""))

    def _standardize_condition(self, raw_condition: str) -> str:
        return self._COND_MAP.get(raw_condition, raw_condition)

    @staticmethod
    def _make_mne_info(h5_path: str):
        with h5py.File(h5_path, "r") as f:
            ch_names = [c.decode() for c in f["ch_names"][:]]
            sfreq = float(f["srate"][0])
        info = create_info(ch_names, sfreq, ch_types="eeg")
        info.set_montage(make_standard_montage("easycap-M1"))
        return info


ADAPTOR = Etard2019Adaptor