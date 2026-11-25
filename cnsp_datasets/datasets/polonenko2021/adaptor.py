from __future__ import annotations

import glob
import os
import re
from typing import Dict, Iterable, List, Tuple

import h5py
import numpy as np

from cnsp_datasets.datasets.maddox_base.common import Recording, bits_to_ints, load_trial, read_recording
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS_AUDIO = 44100
DURATION = 64.0
N_ID_BITS = 7       # trial number 0-119
N_BANDS = {"Exp1": 4, "Exp2": 4, "Exp3": 10}   # Exp3: 5 bands x 2 ears, row 2 * band + ear
N_FAKE = 6          # common-component pulse trains after the band trains
EXPERIMENTS = {"Exp1": "Exp1_Peaky-vs-Unaltered_Speech_Dataset", "Exp2": "Exp2_Peaky_Speech_Narrators_Dataset",
               "Exp3": "Exp3_Peaky_Speech_Audiological_Dataset"}
AUDIO_KEY = {"unaltered": "x", "broadband": "x_play_single", "multiband": "x_play_band"}


def trial_stimulus(exp: str, trial: int) -> Tuple[str, str, int]:
    """(narrator, speech type, chapter file number) of a trial number (0-119), as in the authors' analysis code."""
    if exp == "Exp1":
        return "Male", ("unaltered", "broadband", "multiband")[trial % 3], trial
    if exp == "Exp2":
        return ("Male", "Female")[trial % 4 // 2], ("broadband", "multiband")[trial % 2], 2 * (trial // 4) + trial % 2
    return ("Male", "Female")[trial % 2], "multiband", trial // 2


def start_drift(rec: Recording) -> float | None:
    """
    Drift from back-to-back trials (no end markers): mean start-to-start interval / 64 s - 1 over consecutive
    pairs 64 s (+-0.1%) apart with no pause between; None if there are none.
    """
    nominal = DURATION * rec.sfreq
    starts = [t.start for t in rec.trials if len(t.bits) == N_ID_BITS]
    diffs = [b - a for a, b in zip(starts[:-1], starts[1:])
             if abs(b - a - nominal) < 1e-3 * nominal and not any(a < x <= b for x in rec.boundaries)]
    return float(np.mean(diffs) / nominal - 1) if diffs else None


class Polonenko2021Adaptor(BaseAdaptor):
    """
    Polonenko & Maddox 2021 (eLife, Dryad doi:10.5061/dryad.12jm63xwd): 64 s peaky-speech trials, 2-channel
    subcortical EEG (A1, A2: earlobes referenced to FCz, 10 kHz), three experiments with different participants:
    Exp1 (22): unaltered / broadband / multiband peaky speech, male narrator, interleaved, 40 each;
    Exp2 (11): male / female narrator x broadband / multiband, 30 each; Exp3 (11): dichotic multiband (5 bands
    per ear), male / female, 60 each. The pilot (dynamic f0 shifts) is left out: its male stimuli are not on Dryad.

    Trial n (7-bit ID after each S 1) -> stimulus file as in the authors' code (`trial_stimulus`); events.tsv agrees
    except for its `file` column in Exp2 run-2 files. Repeated trials after a restart: the later complete copy is
    kept; trials cut by a pause or the end of a recording are skipped. Onset = S 1 (the README says the markers
    already include the ER-2 tube delay; see notes). drift_correction=True: per recording from the start-to-start
    intervals (no end markers). sfreq=1000 by default (None keeps 10 kHz).
    Subjects 100 * experiment + label. Stimulus `<exp>_<narrator><NNN>_<type>`: `audio` (44.1 kHz as played; Exp3
    stereo), `pulses` (glottal pulse trains: 1 for unaltered/broadband, one per band for multiband) and, for
    multiband, `pulses_fake` (6 common-component trains), uint8.
    """

    def __init__(self, download_dir: str, sfreq: float | None = 1000, drift_correction: bool = True):
        super().__init__(download_dir)
        self.sfreq = sfreq
        self.drift_correction = drift_correction

    def parse(self) -> Iterable[TrialRecord]:
        files = self._stimulus_files()
        for exp, folder in EXPERIMENTS.items():
            for sub_dir in sorted(glob.glob(os.path.join(self.download_dir, folder, "sub-*"))):
                label = int(os.path.basename(sub_dir)[4:])
                for trial, (vhdr, onset, drift) in sorted(self._subject_trials(sub_dir).items()):
                    narrator, kind, chapter = trial_stimulus(exp, trial)
                    yield TrialRecord(
                        subject=100 * int(exp[3]) + label,
                        session=1,
                        trial=trial + 1,
                        condition=(f"{exp.lower()}-{kind}" if exp == "Exp1"
                                   else f"{exp.lower()}-{narrator.lower()}-{kind}"),
                        ns_type="eeg",
                        stimulus=self._stimuli(exp, files[exp, narrator, chapter], narrator, kind, chapter),
                        neural_data_fn=self._eeg_loader(vhdr, onset, drift),
                    )

    def _subject_trials(self, sub_dir: str) -> Dict[int, Tuple[str, float, float]]:
        """Trial number -> (vhdr, onset sample, drift); a later complete copy replaces an earlier one."""
        recordings = [(vhdr, read_recording(vhdr))
                      for vhdr in sorted(glob.glob(os.path.join(sub_dir, "eeg", "*_eeg.vhdr")))]
        drifts = [start_drift(rec) for _, rec in recordings]
        known = [d for d in drifts if d is not None]
        trials = {}
        for (vhdr, rec), drift in zip(recordings, drifts):
            drift = (drift if drift is not None else float(np.mean(known))) if self.drift_correction else 0.0
            for t in rec.trials:
                if len(t.bits) == N_ID_BITS and rec.usable(t, int(np.ceil(DURATION * rec.sfreq * (1 + drift)))):
                    trials[bits_to_ints(t.bits, (N_ID_BITS,))[0]] = (vhdr, float(t.start), drift)
        return trials

    def _stimulus_files(self) -> Dict[Tuple[str, str, int], str]:
        files = {}
        for path in self.sorted_glob(self.download_dir, "Exp*_Stimuli_*_Narrator_*/*Narrator*.hdf5"):
            m = re.match(r"(Male|Female)Narrator(\d{3})_bands", os.path.basename(path))
            if not m:
                raise ValueError(f"unexpected stimulus file {path}")
            key = os.path.basename(os.path.dirname(path))[:4], m.group(1), int(m.group(2))
            if key in files:
                raise ValueError(f"two stimulus files for {key}: {files[key]}, {path}")
            files[key] = path
        return files

    def _stimuli(self, exp: str, path: str, narrator: str, kind: str, chapter: int) -> List[StimulusRecord]:
        name = f"{exp.lower()}_{narrator.lower()}{chapter:03d}_{kind}"
        n_bands = N_BANDS[exp] if kind == "multiband" else 1
        stimuli = [
            StimulusRecord(modality="audio", name=name, is_attended=True, feature_name="audio",
                           data_fn=_audio_loader(path, AUDIO_KEY[kind])),
            StimulusRecord(modality="audio", name=name, is_attended=True, feature_name="pulses",
                           data_fn=_pulse_loader(path, range(n_bands))),
        ]
        if kind == "multiband":
            stimuli.append(StimulusRecord(modality="audio", name=name, is_attended=True, feature_name="pulses_fake",
                                          data_fn=_pulse_loader(path, range(n_bands, n_bands + N_FAKE))))
        return stimuli

    def _eeg_loader(self, vhdr: str, onset: float, drift: float):
        sfreq = self.sfreq

        def _loader():
            return load_trial(vhdr, onset, DURATION, sfreq, drift)

        return _loader


def _audio_loader(path: str, key: str):
    def _loader() -> dict:
        with h5py.File(path, "r") as f:
            data = np.atleast_2d(f[f"expyfun/key_{key}"][()]).astype(np.float32)
            fs = int(np.ravel(f["expyfun/key_fs"][()])[0])
        return {"fs": fs, "data": data}

    return _loader


def _pulse_loader(path: str, rows: range):
    def _loader() -> dict:
        with h5py.File(path, "r") as f:
            indices = [f[f"expyfun/key_pulse_inds/idx_{i}"][()] for i in rows]
        train = np.zeros((len(indices), int(DURATION * FS_AUDIO)), np.uint8)  # 0/1: 4x smaller than float32
        for row, idx in enumerate(indices):
            train[row, idx.astype(int)] = 1
        return {"fs": FS_AUDIO, "data": train}

    return _loader


ADAPTOR = Polonenko2021Adaptor
