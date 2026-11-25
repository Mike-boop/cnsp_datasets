from __future__ import annotations

import os
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import h5py
import numpy as np
import pandas as pd
from mne import create_info
from mne.io import BaseRaw, RawArray, read_info

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import to_audio_clock
from cnsp_datasets.standardise.iohelpers import mark_bads, to_float32
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

DRIFT_CSV = os.path.join(os.path.dirname(__file__), "alignment", "drift.csv")  # from alignment/drift.py
MIN_WINDOWS = 10  # trials with fewer valid xcorr windows are left out of the subject median
GROUPS = {"1": "ci", "2": "hi", "3": "nh"}  # first digit of the subject code


def subject_drift(table: str = DRIFT_CSV) -> dict[str, float]:
    """Median drift (as a fraction, not ppm) per subject code over trials with enough valid windows."""
    d = pd.read_csv(table, dtype={"subject": str})
    d = d[d.n_windows >= MIN_WINDOWS]
    return (d.groupby("subject").drift_ppm.median() * 1e-6).to_dict()


class Jehn2025Adaptor(BaseAdaptor):
    """
    Adaptor for the Jehn 2025 datasets that yields TrialRecord objects.

    Raw archive layout (single HDF5 file):
      - /eeg/<sub_code>/<trial>      : float array (at least 31 EEG channels x time)
      - /eeg/<sub_code>/taken_out_indices (optional for CI subjects): int[]
      - /stimulus_files/<stim_code>/attended_wav : 1D audio
      - /stimulus_files/<stim_code>/attended_env : 1D envelope
      - /stimulus_files/<stim_code>/distractor_wav (if competing)
      - /stimulus_files/<stim_code>/distractor_env (if competing)

    Codes:
      - sub_code: e.g. "1XX" = CI, "2XX" = HI, "3XX" = NH (X are digits corresponding to participant number)
      - stim_code: 3 chars:
          [0]: '1'->natural, '2'->competing
          [1]: '1'->attended=elbenwald (ignored=polarnacht), '2'->attended=polarnacht (ignored=elbenwald)
          [2]: story part '1'..'9' with '0' meaning '10'

    Notes:
      - Participants started by focussing on the loudspeaker to their right, so odd trials are attended on the right
        and even trials on the left, except for SWAPPED_SIDES (odd trials on the left). Checked with the two aux
        channels (rows 32-33: left and right loudspeaker recordings): every other subject follows the parity rule;
        for ci 121 and nh 308 both streams appear on one aux channel, so their side is unverified.
      - Onsets: the aux channels match the shipped stimuli to ~2 ms at trial start (the offset depends on the
        stimulus file). The EEG is not drift-corrected: the aux channels drift by ~26.7 ppm (~18 ppm for ci 118-122
        and hi 201) relative to the stimuli. The aux channels of ci 127 do not contain the stimulus.
      - CI channels removed at the magnet position (`taken_out_indices`) are kept and listed in info["bads"].

    Class attributes parametrise the archive (jehn2024 subclasses this adaptor with its own).
    """

    SWAPPED_SIDES = {"103", "305", "306"}
    NAME_SUFFIX = {"attended": "_target", "distractor": "_distractor"}

    SESSION = 1
    FS_EEG = 1000
    FS_ENV = 1000
    FS_AUDIO = 48000
    INFO_FIF_PATH = os.path.join(os.path.dirname(__file__), "info_1000.fif")

    def __init__(
        self,
        download_dir: str,
        h5_fname: str,
        drift_correction: Optional[str] = None,
    ):
        """drift_correction: None or "subject" (resample each trial onto the stimulus clock with the subject's median
        drift from alignment/drift.csv; the trial onset is the anchor)."""
        super().__init__(download_dir)
        self.choice("drift_correction", drift_correction, (None, "subject"))
        self._drift = subject_drift() if drift_correction else {}

        self.h5_path = self.path(h5_fname)

        # Discover codes once
        self._stim_codes, self._sub_codes = self._get_codes(self.h5_path)

        # Prepare a base Info (31 EEG channels) from a provided info.fif
        self._base_info = self._make_info(self.INFO_FIF_PATH)

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Yield one TrialRecord per (subject code, trial 1..20).
        """
        for sub_code in self._sub_codes:
            group, subj_idx = self._parse_sub_code(sub_code)

            for trial in range(1, 21):
                stim_code = self._read_stim_code(sub_code, trial)
                if stim_code is None:
                    # no such trial in file; skip
                    continue
                condition, att_story, ign_story, part = self._parse_stim_code(stim_code)

                # trial parity defines attended direction
                odd_side, even_side = ("fL", "fR") if sub_code in self.SWAPPED_SIDES else ("fR", "fL")
                attended_direction = odd_side if trial % 2 else even_side
                condition_full = f"{condition}_{attended_direction}_{group}"

                # Build stimuli list:
                #  - attended audio
                #  - if competing: also distractor audio
                stimuli: List[StimulusRecord] = [
                    StimulusRecord(
                        modality="audio",
                        name=f"{att_story}_{part}{self.NAME_SUFFIX['attended']}",
                        data_fn=self._make_audio_loader(stim_code, role="attended", feature="audio"),
                        is_attended=True,
                        feature_name="audio",
                    )
                ]

                if condition == "competing":
                    stimuli.append(
                        StimulusRecord(
                            modality="audio",
                            name=f"{ign_story}_{part}{self.NAME_SUFFIX['distractor']}",
                            data_fn=self._make_audio_loader(stim_code, role="distractor", feature="audio"),
                            is_attended=False,
                            feature_name="audio",
                        )
                    )

                # Lazy EEG loader (per-trial dataset), CI missing channels marked bad
                neural_fn = self._make_eeg_loader(sub_code=sub_code, trial=trial, group=group)

                yield TrialRecord(
                    subject=subj_idx,
                    session=self.SESSION,
                    trial=trial,
                    condition=condition_full,
                    ns_type="eeg",
                    stimulus=stimuli,
                    neural_data_fn=neural_fn,
                    structural_data_fn=None,
                    behavioural_data_fn=None,
                )

    # ------------------------- Lazy loaders ---------------------------

    def _make_eeg_loader(self, sub_code: str, trial: int, group: str) -> Callable[[], BaseRaw]:
        """
        Loads EEG [31 x T] for a given subject code and trial; CI channels taken out are kept and marked bad.
        """
        def _loader() -> BaseRaw:
            with h5py.File(self.h5_path, "r") as f:
                node = f[f"eeg/{sub_code}/{trial}"]
                data = to_audio_clock(np.array(node[:31], dtype=float), self._drift.get(sub_code, 0.0))
                raw = RawArray(data, self._base_info.copy(), verbose="ERROR")
                taken_key = f"eeg/{sub_code}/taken_out_indices"
                if group == "ci" and taken_key in f:
                    missing = np.array(f[taken_key][:], dtype=int).tolist()
                    mark_bads(raw, [raw.ch_names[i] for i in missing])
                return raw
        return _loader

    def _make_audio_loader(self, stim_code: str, role: str, feature: str) -> Callable[[], Dict[str, Any]]:
        """
        role: 'attended' | 'distractor'
        feature: 'audio' (wav) | 'env' (envelope)
        Returns dict {"fs": <int>, "data": float32 np.ndarray[1, T]} (integer samples scaled to [-1, 1)).
        """
        self.choice("role", role, ("attended", "distractor"))
        self.choice("feature", feature, ("audio", "env"))
        ds_key = f"stimulus_files/{stim_code}/{role}_{'wav' if feature == 'audio' else 'env'}"

        fs = self.FS_AUDIO if feature == "audio" else self.FS_ENV

        def _loader() -> Dict[str, Any]:
            with h5py.File(self.h5_path, "r") as f:
                if ds_key not in f:
                    raise KeyError(f"Missing stimulus dataset: '{ds_key}'")
                x = f[ds_key][:]
            return {"fs": fs, "data": np.atleast_2d(to_float32(x))}
        return _loader

    # ---------------------------- Helpers -----------------------------

    def _get_codes(self, h5_path: str) -> Tuple[List[str], List[str]]:
        with h5py.File(h5_path, "r") as f:
            stim_codes = list(f["stimulus_files"].keys())
            sub_codes = list(f["eeg"].keys())
        return stim_codes, sub_codes

    def _parse_sub_code(self, code: str) -> Tuple[str, int]:
        """
        Returns (group, participant_number) where group in {'ci','hi','nh'}.
        """
        if code[:1] not in GROUPS:
            raise ValueError(f"subject code {code!r}: first digit not in {sorted(GROUPS)} (ci/hi/nh)")
        return GROUPS[code[0]], int(code[1:])

    def _parse_stim_code(self, stim_code: str) -> Tuple[str, str, str, int]:
        """
        Map 'stim_code' -> (condition, attended_story, ignored_story, story_part)
        """
        cond = "natural" if stim_code[0] == "1" else "competing"
        if stim_code[1] == "1":
            att, ign = "elbenwald", "polarnacht"
        else:
            att, ign = "polarnacht", "elbenwald"
        part = int(stim_code[2])
        if part == 0:
            part = 10
        return cond, att, ign, part

    def _read_stim_code(self, sub_code: str, trial: int) -> Optional[str]:
        """
        Read the 'stimulus' attribute for a given trial; returns None if missing.
        """
        with h5py.File(self.h5_path, "r") as f:
            key = f"eeg/{sub_code}/{trial}"
            if key not in f:
                return None
            stim = f[key].attrs.get("stimulus", None)
            if stim is None:
                return None
            # ensure str
            if isinstance(stim, (bytes, np.bytes_)):
                return stim.decode("utf-8")
            return str(stim)

    def _make_info(self, info_fif_path: str):
        """
        A 31-channel EEG Info with the channel names and montage of `info_fif_path`, at FS_EEG.
        """
        info = read_info(info_fif_path, verbose="ERROR")
        new_info = create_info(ch_names=info["ch_names"][:31], sfreq=self.FS_EEG, ch_types="eeg")
        new_info.set_montage(info.get_montage())
        return new_info
