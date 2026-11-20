from __future__ import annotations

import glob
import os
from typing import Iterable

import numpy as np
import pandas as pd

from cnsp_datasets.datasets.maddox_base.common import (TUBE_DELAY, expyfun_loader, load_trial, pulse_loader,
                                                       read_recording)
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS_AUDIO = 48000
FS_EEG = 10000
DURATION = 10.0     # every speech file is 480000 samples
END_MARKER = 0.02   # S 2 is stamped 20 ms before the end (authors' dur_stamp = 9.98)


class Polonenko2024Adaptor:
    """
    Polonenko & Maddox 2024 (OpenNeuro ds005340, "peaky_pitchshift"): 15 subjects, 2-channel subcortical EEG
    (FCz minus left/right earlobe, 10 kHz), 720 x 10 s peaky-speech trials per subject: male/female narrator at
    three f0s (low/mid/high = 123/150/183 Hz), 120 each. Click trials (ABR only) are skipped.

    Onset = S 1 marker + ER-2 tube delay (0.81 ms); sound-card triggers, so no jitter. Trials are numbered by their
    row in events.tsv (recording order, clicks included), whose mapping matches the bit-stamped trial IDs.
    drift_correction=True (default): per-subject drift from S 2 - S 1 (25 ppm in every subject), applied in the
    same interpolation as the resample. sfreq=1000 (default; None keeps 10 kHz).
    Stimuli per file `<narrator>_<f0>_NNN`: `audio` (48 kHz, as played, diotic), `pulses` (glottal pulse train
    from `pinds`, 48 kHz) and, with save_anm=True, `anm` (the authors' auditory-nerve-model regressor, two
    polarities, already shifted by 1 ms in their pipeline).
    """

    def __init__(self, download_dir: str, sfreq: float | None = 1000, drift_correction: bool = True,
                 save_anm: bool = False):
        self.download_dir = download_dir
        self.sfreq = sfreq
        self.drift_correction = drift_correction
        self.save_anm = save_anm

    def parse(self) -> Iterable[TrialRecord]:
        for vhdr in sorted(glob.glob(os.path.join(self.download_dir, "sub-*", "eeg", "*_eeg.vhdr"))):
            events = pd.read_csv(vhdr.replace("_eeg.vhdr", "_events.tsv"), sep="\t")
            rec = read_recording(vhdr)
            starts = np.array([t.start for t in rec.trials])
            if len(starts) != len(events) or not np.all(events["sample"].values - starts == 8):
                raise ValueError(f"{vhdr}: events.tsv does not match the S 1 markers")
            drift = rec.drift((DURATION - END_MARKER) * FS_EEG) if self.drift_correction else 0.0
            subject = int(os.path.basename(vhdr).split("_")[0][4:])
            for row, start in zip(events.itertuples(), starts):
                if row.trial_type.startswith("clicks"):
                    continue
                yield TrialRecord(
                    subject=subject,
                    session=1,
                    trial=row.Index + 1,
                    condition=row.trial_type.replace("_", "-f0"),
                    ns_type="eeg",
                    stimulus=self._stimuli(row.stim_file),
                    neural_data_fn=self._eeg_loader(vhdr, start + TUBE_DELAY * FS_EEG, drift),
                )

    def _stimuli(self, stim_file: str) -> list:
        path = os.path.join(self.download_dir, "stimuli", stim_file)
        name = os.path.basename(stim_file).replace("_regress.hdf5", "")
        stimuli = [
            StimulusRecord(modality="audio", name=name, is_attended=True, feature_name="audio",
                           data_fn=expyfun_loader(path, "x")),
            StimulusRecord(modality="audio", name=name, is_attended=True, feature_name="pulses",
                           data_fn=pulse_loader(path, int(DURATION * FS_AUDIO), FS_AUDIO)),
        ]
        if self.save_anm:
            stimuli.append(StimulusRecord(modality="audio", name=name, is_attended=True, feature_name="anm",
                                          data_fn=expyfun_loader(path, "anm")))
        return stimuli

    def _eeg_loader(self, vhdr: str, onset: float, drift: float):
        sfreq = self.sfreq

        def _loader():
            return load_trial(vhdr, onset, DURATION, sfreq, drift)

        return _loader


ADAPTOR = Polonenko2024Adaptor
