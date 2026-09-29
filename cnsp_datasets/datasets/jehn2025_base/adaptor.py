from __future__ import annotations

import os
import h5py
import numpy as np

from mne import create_info
from mne.io import RawArray, read_info, BaseRaw

from typing import Iterable, Callable, Any, Dict, List, Optional, Tuple
from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


class Jehn2025Adaptor:
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
      - Participants started by focussing on the loudspeaker to their right (thus trial index parity defines attended direction; used below)
    """

    SESSION = 1
    FS_EEG = 1000
    FS_ENV = 1000
    FS_AUDIO = 48000
    INFO_FIF_PATH = os.path.join(os.path.dirname(__file__), "info_1000.fif")


    def __init__(
        self,
        download_dir: str,
        h5_fname: str
    ):
        self.download_dir = download_dir

        self.h5_path = os.path.join(download_dir, h5_fname)
        if not os.path.exists(self.h5_path):
            raise FileNotFoundError(f"HDF5 archive not found: {self.h5_path}")

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
                attended_direction = "fL" if (trial % 2 == 0) else "fR"
                condition_full = f"{condition}_{attended_direction}_{group}"

                # Build stimuli list:
                #  - attended audio
                #  - if competing: also distractor audio
                stimuli: List[StimulusRecord] = []

                att_name = f"{att_story}_{part}_target"
                stimuli.append(
                    StimulusRecord(
                        modality="audio",
                        name=att_name,
                        data_fn=self._make_audio_loader(stim_code, role="attended", feature="audio"),
                        is_attended=True,
                        feature_name="audio",
                    )
                )

                if condition == "competing":
                    dis_name = f"{ign_story}_{part}_distractor"
                    stimuli.append(
                        StimulusRecord(
                            modality="audio",
                            name=dis_name,
                            data_fn=self._make_audio_loader(stim_code, role="distractor", feature="audio"),
                            is_attended=False,
                            feature_name="audio",
                        )
                    )

                # Lazy EEG loader (per-trial dataset), mark CI missing channels as bad
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
        Loads EEG [31 x T] for a given subject code and trial, sets `info.bads` for CI.
        """
        def _loader() -> BaseRaw:
            with h5py.File(self.h5_path, "r") as f:
                node = f[f"eeg/{sub_code}/{trial}"]
                data = np.array(node[:31], dtype=float)  # ensure shape (31, T)
                # Copy base Info so we can mutate 'bads' per subject
                info = self._base_info.copy()

                if group == "ci":
                    taken_key = f"eeg/{sub_code}/taken_out_indices"
                    if taken_key in f:
                        missing = np.array(f[taken_key][:], dtype=int).tolist()
                        info["bads"] = [info["ch_names"][i] for i in missing]
                raw = RawArray(data, info, verbose="ERROR")
                raw.pick(picks="eeg", exclude="bads")  # drop missing channels so they don’t mess up processing later
                return raw
        return _loader

    def _make_audio_loader(self, stim_code: str, role: str, feature: str) -> Callable[[], Dict[str, Any]]:
        """
        role: 'attended' | 'distractor'
        feature: 'audio' (wav) | 'env' (envelope)
        Returns dict {"fs": <float>, "data": np.ndarray[1, T]}.
        """
        assert role in ("attended", "distractor")
        assert feature in ("audio", "env")
        ds_key = f"stimulus_files/{stim_code}/{role}_{'wav' if feature=='audio' else 'env'}"

        fs = self.FS_AUDIO if feature == "audio" else self.FS_ENV

        def _loader() -> Dict[str, Any]:
            with h5py.File(self.h5_path, "r") as f:
                if ds_key not in f:
                    raise KeyError(f"Missing stimulus dataset: '{ds_key}'")
                x = f[ds_key][:]
            x = np.asarray(x)
            if x.ndim == 1:
                x = x[None, :]
            return {"fs": fs, "data": x}
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
        g = int(code[0])
        group = "ci" if g == 1 else ("hi" if g == 2 else "nh")
        participant = int(code[1:])
        return group, participant

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
            node = f[key]
            stim = node.attrs.get("stimulus", None)
            if stim is None:
                return None
            # ensure str
            if isinstance(stim, (bytes, np.bytes_)):
                stim = stim.decode("utf-8")
            else:
                stim = str(stim)
            return stim

    def _make_info(self, info_fif_path: Optional[str] = os.path.join(os.path.dirname(__file__), "info_125.fif")) -> Dict:
        """
        Create a 31-channel EEG Info. If an info.fif is provided and readable,
        we use its channel names + montage, but force `sfreq` to `fs_eeg`.
        Otherwise fall back to a standard montage with generic names.
        """
        info = read_info(info_fif_path)
        ch_names = info["ch_names"][:31]
        new_info = create_info(ch_names=ch_names, sfreq=self.FS_EEG, ch_types="eeg")
        new_info.set_montage(info.get_montage())
        return new_info