'''
Note: trigger handling and drift correction adapted from the original code by Bollens and Accou
(https://github.com/exporl/auditory-eeg-dataset).
'''
from __future__ import annotations

import glob
import gzip
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from typing import Iterable

import mne
import numpy as np
import pandas as pd
import scipy.interpolate
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray, read_raw_bdf

from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

mne.set_log_level("CRITICAL")

# The release README: too few triggers to align these runs with the stimulus.
UNALIGNABLE = {
    "sub-006_ses-shortstories01_task-listeningActive_run-06",
    "sub-017_ses-shortstories01_task-listeningActive_run-03",
    "sub-048_ses-varyingStories05_task-listeningActive_run-04",
}
# podcast_10 was shown with video of the speaker to these subjects (paper, figure 4); sub-030 heard it without.
AV_SUBJECTS = set(range(27, 37)) - {30}
CH_NAMES = [
    "Fp1", "AF7", "AF3", "F1", "F3", "F5", "F7", "FT7", "FC5", "FC3", "FC1", "C1", "C3", "C5", "T7",
    "TP7", "CP5", "CP3", "CP1", "P1", "P3", "P5", "P7", "P9", "PO7", "PO3", "O1", "Iz", "Oz", "POz",
    "Pz", "CPz", "Fpz", "Fp2", "AF8", "AF4", "AFz", "Fz", "F2", "F4", "F6", "F8", "FT8", "FC6", "FC4",
    "FC2", "FCz", "Cz", "C2", "C4", "C6", "T8", "TP8", "CP6", "CP4", "CP2", "P2", "P4", "P6", "P8", "P10",
    "PO8", "PO4", "O2",
]


# -------------------------- Trigger helpers (pure) --------------------------

def get_trigger_indices(trigger_array: np.ndarray) -> np.ndarray:
    """Indices of onsets in a ~binary trigger signal."""
    indices = np.where(trigger_array > 0.5)[0]
    return indices[np.insert(np.diff(indices) > 1, 0, True)]


def biosemi_trigger_processing_fn(trigger: np.ndarray) -> np.ndarray:
    """BioSemi 'Status' -> 0/1: 1 where the lower 16 bits differ from their most common (idle) value."""
    triggers = trigger.flatten().astype(np.int32) & (2**16 - 1)
    values, counts = np.unique(triggers, return_counts=True)
    valid_mask = (0 < values) & (values < 256)
    most_common = values[valid_mask][np.argmax(counts[valid_mask])]
    return np.int32(triggers != most_common)


def default_drift_correction(brain_data: np.ndarray, brain_trigger_indices: np.ndarray, brain_fs: int,
                             stimulus_trigger_indices: np.ndarray, stimulus_fs: int) -> np.ndarray:
    """
    Linearly resample the EEG between its first and last trigger to the stimulus' first-to-last trigger duration
    (the stimulus triggers start on its first sample). One missing EEG
    trigger is repaired as in the authors' code.
    """
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
    eeg_segment = brain_data[:, brain_trigger_indices[0]:brain_trigger_indices[-1]]
    target_times = np.linspace(0, 1, int(round(stim_duration * brain_fs)))
    interpolator = scipy.interpolate.interp1d(np.linspace(0, 1, eeg_segment.shape[1]), eeg_segment, kind="linear",
                                              axis=1, fill_value="extrapolate")
    return interpolator(target_times)


def apr_snr(apr_path: str) -> float | None:
    """SNR (dB) the experimenter set in an APEX results file, None if the file or entry is missing."""
    if not os.path.exists(apr_path):
        return None
    for entry in ET.parse(apr_path).getroot().findall("general/interactive/entry"):
        if (entry.findtext("description") or "").strip().lower() == "snr":
            return float(entry.findtext("new_value"))
    return None


# ------------------------------- Adaptor ------------------------------------

class Accou2023Adaptor:
    """
    SparrKULee (Accou et al. 2024, KU Leuven RDR doi:10.48804/K3VSND): 64-channel BioSemi EEG at 1024 Hz, 85
    participants (sub-019..022 and sub-026 are restricted), one session each, one BIDS run per stimulus.

    - EEG: sub-*/ses-*/eeg/*task-listeningActive*_eeg.bdf (or .bdf.gz), channels named by position (some files
      spell PO7/PO3 as P07/P03). EXG1/EXG2 are the mastoids (A1/A2, misc); flat (unconnected) ones go into bads.
      Runs without EEG in the release (7) and the three runs the README calls unalignable are skipped.
    - Alignment: the stimulus' trigger track (stimuli/eeg/t_<stim>.npz, a pulse every second from the first sample,
      mostly also on the last) was recorded in the BioSemi Status channel; the EEG between the first and last
      trigger is linearly resampled to the stimulus' first-to-last trigger duration (drift correction, as in the
      authors' code).
    - Conditions: 'sin' with the SNR (e.g. 'sin5dB'): SNR from the run's .apr file (the experimenter's setting; the
      paper: 2 of 10 shortstories01 trials at 5 dB) and else from events.tsv (which says 100 for the 5 dB runs);
      'av' podcast_10 with video (AV_SUBJECTS); 'control' audiobook_1_artefact (played without insert phones in
      the ears); 'pitchshifted' audiobook_1_*_shifted; else 'natural'.
      The -4 / 2.5 dB runs (audiobook_7_5 / 7_6, sub-027..031) take their SNR from events.tsv and the .apx noisegain.
    - Stimuli: the speech only. APEX played the noise as a loop starting at a random point (dataloop, randomjump),
      so the shipped noise files do not give the noise waveform as played. The stimulus trigger tracks of
      audiobook_6_1, audiobook_6_2 and audiobook_1_artefact end 0.3-0.6 s before the audio, so their EEG does too.
      The trigger track is the one events.tsv names: audiobook_2_2's experiment (.xml) played t_audiobook_2_1 with
      it (both after 1 s of silence, so the onset holds), so those trials have 29 s of EEG after the speech.
    """

    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self._events = sorted(glob.glob(os.path.join(download_dir, "sub-*", "ses-*", "eeg",
                                                     "*task-listeningActive*_events.tsv")))

    def parse(self) -> Iterable[TrialRecord]:
        for events_path in self._events:
            stem = events_path[: -len("_events.tsv")]
            bdf = next((p for p in (f"{stem}_eeg.bdf", f"{stem}_eeg.bdf.gz") if os.path.exists(p)), None)
            if bdf is None or os.path.basename(stem) in UNALIGNABLE:
                continue
            ev = pd.read_csv(events_path, sep="\t").iloc[0]
            sub = int(re.search(r"sub-(\d+)", stem).group(1))
            speech = _stem(ev.stim_file)
            snr = apr_snr(f"{stem}_eeg.apr")
            snr = float(ev.snr) if snr is None else snr
            condition = self._condition(sub, speech, snr)

            stimuli = [StimulusRecord(modality="audio", name=speech, is_attended=True,
                                      data_fn=self._audio_loader(speech))]
            yield TrialRecord(
                subject=sub,
                session=1,
                trial=int(re.search(r"run-(\d+)", stem).group(1)),
                condition=condition,
                ns_type="eeg",
                stimulus=stimuli,
                neural_data_fn=self._eeg_loader(bdf, self._stim_path(_stem(ev.trigger_file))),
            )

    @staticmethod
    def _condition(sub: int, speech: str, snr: float) -> str:
        if speech.endswith("artefact"):
            return "control"
        if speech.endswith("shifted"):
            return "pitchshifted"
        if snr < 100:
            return f"sin{snr:g}dB"
        if speech == "podcast_10" and sub in AV_SUBJECTS:
            return "av"
        return "natural"

    def _stim_path(self, name: str) -> str:
        path = os.path.join(self.download_dir, "stimuli", "eeg", f"{name}.npz")
        return path if os.path.exists(path) else path + ".gz"

    def _audio_loader(self, name: str):
        path = self._stim_path(name)

        def _loader() -> dict:
            data = _load_npz(path)
            return {"fs": int(data["fs"]), "data": data["audio"].astype(np.float32).reshape(1, -1)}

        return _loader

    @staticmethod
    def _eeg_loader(bdf: str, trig_path: str):
        def _loader() -> BaseRaw:
            with _plain_file(bdf) as path:
                raw = read_raw_bdf(path, preload=True, verbose="ERROR")
            ref = _load_npz(trig_path)
            corrected = default_drift_correction(
                brain_data=raw.get_data(),
                brain_trigger_indices=get_trigger_indices(
                    biosemi_trigger_processing_fn(raw.get_data(picks="Status")[0])),
                brain_fs=int(round(raw.info["sfreq"])),
                stimulus_trigger_indices=get_trigger_indices(ref["audio"].ravel()),
                stimulus_fs=int(ref["fs"]),
            )
            mastoids = [raw.ch_names.index(c) for c in ("EXG1", "EXG2") if c in raw.ch_names]
            names = CH_NAMES + ["A1", "A2"][: len(mastoids)]
            info = create_info(names, raw.info["sfreq"], ["eeg"] * 64 + ["misc"] * len(mastoids))
            out = RawArray(corrected[list(range(64)) + mastoids], info, verbose="ERROR")
            out.set_montage(make_standard_montage("biosemi64"), on_missing="ignore")
            out.info["bads"] = [n for n, i in zip(["A1", "A2"], mastoids) if np.std(np.diff(corrected[i])) < 1e-6]
            return out

        return _loader


def _stem(bids_path: str) -> str:
    """'eeg/audiobook_1.npz.gz' -> 'audiobook_1'."""
    return os.path.basename(bids_path).replace(".gz", "")[: -len(".npz")]


def _load_npz(path: str) -> dict:
    if path.endswith(".gz"):
        with gzip.open(path) as f:
            return dict(np.load(f))
    return dict(np.load(path))


class _plain_file:
    """Context manager: the path itself, or a temporary decompressed copy of a .gz file."""

    def __init__(self, path: str):
        self.path, self._tmp = path, None

    def __enter__(self) -> str:
        if not self.path.endswith(".gz"):
            return self.path
        self._tmp = tempfile.NamedTemporaryFile(suffix=".bdf", delete=False)
        with gzip.open(self.path) as src:
            shutil.copyfileobj(src, self._tmp)
        self._tmp.close()
        return self._tmp.name

    def __exit__(self, *exc):
        if self._tmp is not None:
            os.unlink(self._tmp.name)


ADAPTOR = Accou2023Adaptor
