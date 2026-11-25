from __future__ import annotations

import glob
import os
import re
from typing import Iterable

import h5py
import numpy as np
import pandas as pd

from cnsp_datasets.datasets.maddox_base.common import (TUBE_DELAY, bits_to_ints, load_trial, read_expyfun,
                                                       read_recording)
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS_AUDIO = 48000
FS_EEG = 10000
DURATION = 10.0
END_MARKER = 0.02
EP_PREAMP_GAIN = 100  # not in the BrainVision headers; the authors divide by it ("account for gain")
RMS = 0.01            # exp2/exp3 scaled each trial to this std when playing it

# per task: ID bit widths; stimulus index -> (stimulus folder, file stem prefix, audio key); played file number
TASKS = {
    "phases": dict(bits=(1, 10, 10), folder="exp1_phases",
                   stimuli={0: ("wizardofoz", "wizardofoz_original", "x_play_band_zero", "zero"),
                            1: ("wizardofoz", "wizardofoz_original", "x_play_band_chirp", "chirp")},
                   number=lambda f: f[2] + 1, events_offset=0, scale=False,
                   pulses=("pulse_inds", "fake_pulse_inds")),
    "f0s": dict(bits=(2, 10, 10), folder="exp2_f0s",
                stimuli={0: ("toto_shifted", "toto_shifted", "x_play_band_chirp_CE", "toto-shifted"),
                         1: ("toto_original", "toto_original", "x_play_band_chirp_CE", "toto-original"),
                         2: ("wizardofoz_shifted", "wizardofoz_shifted", "x_play_band_chirp_CE", "wizardofoz-shifted"),
                         3: ("wizardofoz_original", "wizardofoz_original", "x_play_band_chirp_CE",
                             "wizardofoz-original")},
                number=lambda f: f[2] + 1, events_offset=1, scale=True,
                pulses=("pulse_inds", "fake_pulse_inds")),
    "f0s2": dict(bits=(2, 10, 10), folder="exp3_f0s2",
                 stimuli={0: ("wizard", "wizard_shifted", "x_play_band_chirp_CE", "wizard"),
                          1: ("wonderland", "wonderland_shifted", "x_play_band_chirp_CE", "wonderland"),
                          2: ("drdolittle", "drdolittle_shifted", "x_play_band_chirp_CE", "drdolittle")},
                 number=lambda f: f[1] + 1, events_offset=1, scale=True,
                 pulses=("pulseinds_true", "pulseinds_fake")),
}


class Polonenko2026Adaptor(BaseAdaptor):
    """
    Polonenko & Eisenreich 2026 (OpenNeuro ds008065): multiband peaky speech (dichotic, 5 audiological bands per
    ear), passive listening, 10 s trials, 3-channel subcortical EEG at 10 kHz. Three experiments (participants
    differ): phases (exp1, sub-exp1NN, 17: zero- vs chirp-phase, 720 trials), f0s (exp2, sub-exp2NN, 30: two
    narrators at natural f0 or shifted to 100 Hz, 840 trials), f0s2 (exp3, sub-exp3NN, 15: three narrators shifted
    to 90 Hz, 630 trials). Subjects are numbered by their label (101..117, 201..230, 301..315).

    The played file comes from the ID bits stamped after each start trigger (verified against events.tsv). In exp2
    and exp3, events.tsv names the file before the played one (the BIDS script drops the experiment's `+ 1`;
    confirmed by the ABR to each candidate file's pulse train). Trials whose ID bits are garbled (24, mostly a
    trigger burst in sub-exp225) or that cross a recording pause or the end are skipped.

    EEG: channels FCzA1 (FCz minus left earlobe), FCz and A2 as recorded (the authors use FCzA1 and FCz - A2),
    divided by the EP-PreAmp gain of 100 that the headers omit. Onset = S 1 + ER-2 tube delay; drift_correction
    per run (S 2 - S 1, ~10 ppm); sfreq=1000 by default (None keeps 10 kHz).
    Stimuli per file (`<stem>_NNNN`, exp1 `..._zero` / `..._chirp`): `audio` (2 x 48 kHz, left/right ear, as
    played: exp2/exp3 scaled to std 0.01 like the experiment), `pulses` (10 trains, row 2 * band + ear) and
    `pulses_fake` (5 trains for the common component), 48 kHz.
    """

    def __init__(self, download_dir: str, sfreq: float | None = 1000, drift_correction: bool = True):
        super().__init__(download_dir)
        self.sfreq = sfreq
        self.drift_correction = drift_correction

    def parse(self) -> Iterable[TrialRecord]:
        for sub_dir in sorted(glob.glob(os.path.join(self.download_dir, "sub-exp*", "eeg"))):
            subject = int(os.path.basename(os.path.dirname(sub_dir))[7:])
            trial = 0
            for vhdr in sorted(glob.glob(os.path.join(sub_dir, "*_eeg.vhdr"))):
                task = re.search(r"task-([^_]+)", vhdr).group(1)
                spec = TASKS[task]
                events = pd.read_csv(vhdr.replace("_eeg.vhdr", "_events.tsv"), sep="\t")
                events = events[events.trial_type == "stimulus_start"]
                rec = read_recording(vhdr)
                if len(rec.trials) != len(events):
                    raise ValueError(f"{vhdr}: {len(rec.trials)} start markers, {len(events)} events")
                drift = rec.drift((DURATION - END_MARKER) * FS_EEG) if self.drift_correction else 0.0
                for marked, row in zip(rec.trials, events.itertuples()):
                    trial += 1
                    if len(marked.bits) != sum(spec["bits"]) or not rec.usable(marked, int(DURATION * FS_EEG)):
                        continue
                    fields = bits_to_ints(marked.bits, spec["bits"])
                    folder, stem, key, label = spec["stimuli"][fields[0]]
                    number = spec["number"](fields)
                    if int(re.search(r"_(\d+)\.hdf5", row.audio).group(1)) + spec["events_offset"] != number:
                        raise ValueError(f"{vhdr} trial {trial}: ID bits and events.tsv disagree")
                    path = os.path.join(self.download_dir, "stimuli", spec["folder"], folder,
                                        f"{stem}_{number:04d}.hdf5")
                    yield TrialRecord(
                        subject=subject,
                        session=1,
                        trial=trial,
                        condition=f"{task}-{label}",
                        ns_type="eeg",
                        stimulus=self._stimuli(path, key, task, label),
                        neural_data_fn=self._eeg_loader(vhdr, marked.start + TUBE_DELAY * FS_EEG, drift),
                    )

    def _stimuli(self, path: str, key: str, task: str, label: str) -> list:
        spec = TASKS[task]
        name = os.path.basename(path)[:-5] + (f"_{label}" if task == "phases" else "")
        true_key, fake_key = spec["pulses"]
        return [
            StimulusRecord(modality="audio", name=name, feature_name="audio",
                           data_fn=_audio_loader(path, key, spec["scale"])),
            StimulusRecord(modality="audio", name=name, feature_name="pulses", data_fn=_pulse_loader(path, true_key)),
            StimulusRecord(modality="audio", name=name, feature_name="pulses_fake",
                           data_fn=_pulse_loader(path, fake_key)),
        ]

    def _eeg_loader(self, vhdr: str, onset: float, drift: float):
        sfreq = self.sfreq

        def _loader():
            raw = load_trial(vhdr, onset, DURATION, sfreq, drift)
            raw._data /= EP_PREAMP_GAIN
            return raw

        return _loader


def _audio_loader(path: str, key: str, scale: bool):
    def _loader() -> dict:
        data = read_expyfun(path, key).astype(np.float32)
        if scale:
            data *= RMS / data.std()
        return {"fs": FS_AUDIO, "data": data}

    return _loader


def _pulse_loader(path: str, key: str):
    def _loader() -> dict:
        with h5py.File(path, "r") as f:
            group = f[f"expyfun/key_{key}"]
            indices = [group[f"idx_{i}"][()] for i in range(len(group))]
        train = np.zeros((len(indices), int(DURATION * FS_AUDIO)), np.uint8)  # 0/1: 4x smaller than float32
        for row, idx in enumerate(indices):
            train[row, idx.astype(int)] = 1
        return {"fs": FS_AUDIO, "data": train}

    return _loader


ADAPTOR = Polonenko2026Adaptor
