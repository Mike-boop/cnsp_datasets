'''
Note: adapted from the original code by Bollens and Accou.
'''
from __future__ import annotations

import os
import re
import glob
import mne

import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET
import scipy.interpolate

from mne import create_info
from mne.io import read_raw_bdf, RawArray, BaseRaw
from mne.channels import make_standard_montage
from typing import Iterable, Optional, Callable, Any, Dict, List

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord

mne.set_log_level("CRITICAL")


# -------------------------- Trigger helpers (pure) --------------------------

def get_trigger_indices(trigger_array: np.ndarray) -> np.ndarray:
    """Indices of onsets in a ~binary trigger signal."""
    indices = np.where(trigger_array > 0.5)[0]
    return indices[np.insert(np.diff(indices) > 1, 0, True)]

def biosemi_trigger_processing_fn(trigger: np.ndarray) -> np.ndarray:
    """
    Convert BioSemi 'Status' channel to a 0/1 trigger vector by:
    - masking to 16 bits
    - finding the most common (idle) value
    - returning 1 where value != idle
    """
    triggers = trigger.flatten().astype(np.int32) & (2**16 - 1)
    values, counts = np.unique(triggers, return_counts=True)
    valid_mask = (0 < values) & (values < 256)
    val_indices = np.argsort(counts[valid_mask])
    most_common = values[valid_mask][val_indices[-1]]
    if triggers[0] != most_common:
        print("First value of the EEG triggers is on, shouldn't be the case")
    return np.int32(triggers != most_common)

def default_drift_correction(
    brain_data: np.ndarray,
    brain_trigger_indices: np.ndarray,
    brain_fs: int,
    stimulus_trigger_indices: np.ndarray,
    stimulus_fs: int,
) -> np.ndarray:
    """
    Correct clock drift between EEG and stimulus by resampling the EEG segment
    between the first and last trigger to match stimulus duration.
    """
    # allow mismatch of one trigger -> try to repair
    if len(brain_trigger_indices) + 1 < len(stimulus_trigger_indices):
        raise ValueError(
            f"Too many missing EEG triggers: EEG {len(brain_trigger_indices)} vs Stim {len(stimulus_trigger_indices)}"
        )
    elif len(brain_trigger_indices) < len(stimulus_trigger_indices):
        eeg_last = (brain_trigger_indices[-1] - brain_trigger_indices[-2]) / brain_fs
        stim_last = (stimulus_trigger_indices[-1] - stimulus_trigger_indices[-2]) / stimulus_fs
        if abs(eeg_last - stim_last) / max(stim_last, 1e-9) < 0.01:
            estimated_end = brain_trigger_indices[-1] + round(stim_last * brain_fs)
            brain_trigger_indices = np.append(brain_trigger_indices, estimated_end)
        else:
            estimated_start = brain_trigger_indices[0] - round(stim_last * brain_fs)
            brain_trigger_indices = np.insert(brain_trigger_indices, 0, estimated_start)
    elif len(brain_trigger_indices) == len(stimulus_trigger_indices) + 1:
        if brain_trigger_indices[0] == 0:
            brain_trigger_indices = brain_trigger_indices[1:]
    if len(brain_trigger_indices) != len(stimulus_trigger_indices):
        raise ValueError(
            f"Trigger correction failed: EEG {len(brain_trigger_indices)} vs Stim {len(stimulus_trigger_indices)}"
        )

    stim_duration = (stimulus_trigger_indices[-1] - stimulus_trigger_indices[0]) / stimulus_fs
    brain_start, brain_end = brain_trigger_indices[0], brain_trigger_indices[-1]
    eeg_segment = brain_data[:, brain_start:brain_end]

    original_times = np.linspace(0, 1, eeg_segment.shape[1])
    target_length = int(round(stim_duration * brain_fs))
    target_times = np.linspace(0, 1, target_length)

    interpolator = scipy.interpolate.interp1d(
        original_times, eeg_segment, kind="linear", axis=1, fill_value="extrapolate"
    )
    return interpolator(target_times)


# ------------------------------- Adapter ------------------------------------

class Accou2023Adaptor:
    """
    Emits TrialRecord objects for the Bollens2023 EEG dataset.

    - EEG: <download_dir>/sub-*/**/*task-listeningActive*_eeg.bdf
    - Events TSV next to EEG: *_events.tsv (with 'stim_file' and 'trigger_file')
    - Stimulus triggers: <download_dir>/stimuli/<trigger_file> (.npz with 'audio' and 'fs')
    - Audiobooks: <download_dir>/stimuli/eeg/*.npz (audio npz with 'audio' and 'fs')

    Notes:
      * Infers condition (natural/sin/av) using .apr XML for SNR when needed.
      * Subjects 52, 61, 64 treated as 'no mastoids' (64 channels); others 66 including A1/A2.
      * All heavy I/O is lazy: data are loaded when their callables are invoked.
      * TODO: repeatedly loading the same EEG file for each trial is inefficient. We could do some caching here.
    """

    def __init__(self, download_dir: str, session: int = 1):
        self.download_dir = download_dir
        self.session = session

        # discover EEG files
        self._eeg_files = sorted(
            glob.glob(
                os.path.join(
                    self.download_dir,
                    "sub-*",
                    "**",
                    "*task-listeningActive*_eeg.bdf",
                ),
                recursive=True,
            )
        )

        # prebuild Info with mastoids
        self._info_with_mastoids = self._create_mne_info(mastoids=True)
        self._info_no_mastoids = self._create_mne_info(mastoids=False)

    # --------------------------- Public API ---------------------------

    def parse(self) -> Iterable[TrialRecord]:
        """
        Yield TrialRecord for every EEG BDF run that has matching event metadata.
        """
        for eeg_path in self._eeg_files:
            print(eeg_path)
            sub_id = self._subject_id(eeg_path)
            run_number = self._run_number(eeg_path)
            events_path = eeg_path.replace("_eeg.bdf", "_events.tsv")
            if not os.path.exists(events_path):
                # no events file → cannot map to stimulus
                continue

            events = pd.read_csv(events_path, sep="\t")
            stim_file = events["stim_file"].item()
            trigger_file = events["trigger_file"].item().replace(".gz", "")
            trig_path = os.path.join(self.download_dir, "stimuli", trigger_file)

            audio_name = (
                os.path.basename(stim_file)
                .replace(".npz", "")
                .replace(".gz", "")
                .replace("_video", "")
            )

            condition = self._infer_condition(sub_id, eeg_path, audio_name)

            # Build stimuli list (single attended audio)
            stimuli: List[StimulusRecord] = [
                StimulusRecord(
                    modality="audio",
                    name=audio_name,
                    data_fn=self._make_audio_loader(audio_name),
                    is_attended=True,
                    feature_name="audio",
                )
            ]

            # Lazy EEG loader (drift-correct to stimulus using triggers)
            try:
                neural_fn = self._make_eeg_loader(
                    eeg_path=eeg_path,
                    trig_npz_path=trig_path,
                    use_mastoids=(sub_id not in {52, 61, 64}),
                )
            except Exception as e:
                print("Runtime Error: ", e)

            yield TrialRecord(
                subject=sub_id,
                session=self.session,
                trial=run_number,
                condition=condition,
                ns_type="eeg",
                stimulus=stimuli,
                neural_data_fn=neural_fn,
                structural_data_fn=None,
                behavioural_data_fn=None,
            )

    # ------------------------ Lazy loader makers ----------------------

    def _make_audio_loader(self, audio_name: str) -> Callable[[], Dict[str, Any]]:
        """
        Load an audio npz: returns {'fs': int, 'waveform': np.ndarray[1, T]}.
        Files live under <download_dir>/stimuli/eeg/<audio_name>.npz
        """
        npz_path = os.path.join(self.download_dir, "stimuli", "eeg", f"{audio_name}.npz")

        def _loader() -> Dict[str, Any]:
            if not os.path.exists(npz_path):
                raise FileNotFoundError(f"Audio npz not found: {npz_path}")
            data = np.load(npz_path)
            audio = data["audio"]
            fs = int(data["fs"])
            if audio.ndim == 1:
                audio = audio[None, :]
            return {"fs": fs, "waveform": audio}
        return _loader

    def _make_eeg_loader(
        self,
        eeg_path: str,
        trig_npz_path: str,
        use_mastoids: bool,
    ) -> Callable[[], BaseRaw]:
        """
        Returns a loader that:
          - reads BDF
          - extracts & binarizes BioSemi Status (EEG triggers)
          - loads stimulus triggers from npz
          - drift-corrects EEG to stimulus trigger train
          - creates RawArray with appropriate montage (64 or 66 channels)
        """
        info = self._info_with_mastoids if use_mastoids else self._info_no_mastoids

        def _loader() -> BaseRaw:
            raw = read_raw_bdf(eeg_path, preload=True, verbose="ERROR")

            eeg_trigger = raw.copy().pick("Status").get_data().squeeze()
            eeg_trigger = biosemi_trigger_processing_fn(eeg_trigger)

            if not os.path.exists(trig_npz_path):
                raise FileNotFoundError(f"Stimulus trigger file not found: {trig_npz_path}")
            ref = np.load(trig_npz_path)
            stim_trigger = ref["audio"]
            stim_fs = int(ref["fs"])

            eeg_idx = get_trigger_indices(eeg_trigger)
            stim_idx = get_trigger_indices(stim_trigger)

            corrected = default_drift_correction(
                brain_data=raw.get_data(),
                brain_trigger_indices=eeg_idx,
                brain_fs=int(round(raw.info["sfreq"])),
                stimulus_trigger_indices=stim_idx,
                stimulus_fs=stim_fs,
            )

            # 64 EEG channels first; if mastoids present, add them
            if info["nchan"] == 64:
                data = corrected[:64]
            else:
                data = corrected[:66]

            raw_corrected = RawArray(data, info, verbose="ERROR")
            return raw_corrected

        return _loader

    # ------------------------------ Utils -----------------------------

    def _subject_id(self, eeg_path: str) -> int:
        # .../sub-030/... -> 30
        m = re.search(r"sub-(\d+)", eeg_path)
        return int(m.group(1)) if m else -1

    def _run_number(self, eeg_path: str) -> Optional[int]:
        m = re.search(r"run-(\d+)", os.path.basename(eeg_path))
        return int(m.group(1)) if m else None

    def _infer_condition(self, sub_id: int, eeg_file: str, audio_name: str) -> str:
        """
        Legacy logic:
          - subjects 1..26: if .apr SNR == '5' -> 'sin'
          - subjects 27..36: if audio == 'podcast_10' -> 'av'
          - special-case sub 30 'av' remarks -> downgrade to 'natural'
          - else 'natural'
        """
        if 1 <= sub_id <= 26:
            apr_path = eeg_file.replace(".bdf", ".apr")
            snr = self._parse_snr_from_apr_file(apr_path)
            if snr == "5":
                return "sin"

        if 27 <= sub_id <= 36 and audio_name == "podcast_10":
            return "av"

        if sub_id == 30 and audio_name == "podcast_10":
            return "natural"
        
        if audio_name == "audiobook_1_artefact":
            return "control"

        return "natural"

    def _parse_snr_from_apr_file(self, path: str) -> Optional[str]:
        """
        Extract SNR from a .apr XML (same approach as legacy).
        """
        if not os.path.exists(path):
            return None
        tree = ET.parse(path)
        root = tree.getroot()
        # 'general' is not namespaced
        general = root.find("general")
        if general is None:
            return None
        interactive = general.find("interactive")
        if interactive is None:
            return None

        for entry in interactive.findall("entry"):
            description = entry.find("description")
            if description is not None and (description.text or "").strip().lower() == "snr":
                new_value = entry.find("new_value")
                return (new_value.text or "").strip() if new_value is not None else None
        return None

    def _create_mne_info(self, mastoids: bool) -> mne.Info:
        """
        Build Info with BioSemi 64 channels; optionally add A1/A2 mastoids with approximate positions.
        """
        ch_names = [
            "Fp1","AF7","AF3","F1","F3","F5","F7","FT7","FC5","FC3","FC1","C1","C3","C5","T7",
            "TP7","CP5","CP3","CP1","P1","P3","P5","P7","P9","PO7","PO3","O1","Iz","Oz","POz",
            "Pz","CPz","Fpz","Fp2","AF8","AF4","AFz","Fz","F2","F4","F6","F8","FT8","FC6","FC4",
            "FC2","FCz","Cz","C2","C4","C6","T8","TP8","CP6","CP4","CP2","P2","P4","P6","P8","P10",
            "PO8","PO4","O2"
        ]

        if not mastoids:
            info = create_info(ch_names=ch_names, sfreq=1024, ch_types=["eeg"] * len(ch_names))
        else:
            ch_names_with = ch_names + ["A1", "A2"]
            info = create_info(ch_names=ch_names_with, sfreq=1024, ch_types=["eeg"] * len(ch_names) + ["misc"] * 2)

        info.set_montage(make_standard_montage("biosemi64"))
        return info

ADAPTOR = Accou2023Adaptor