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
END_MARKER = 0.02   # S 2 is stamped 20 ms before the end
STORIES = ["alice", "peterpan", "pinocchio", "timemachine", "wizardofoz"]
CONDITIONS = {"clean": "talkers1-clean", "0 dB": "talkers2-snr0dB", "-3 dB": "talkers3-snr-3dB",
              "-6 dB": "talkers5-snr-6dB"}
N_ID_BITS_FLIP = 49  # 1 stimulus + 2 SNR + 5 x 9 token bits + 1 polarity bit (sub-07 onwards)


class Polonenko2025Adaptor:
    """
    Polonenko & Maddox 2025 (OpenNeuro ds005408, "peaky_snr"): 25 subjects, 2-channel subcortical EEG (FCz minus
    left/right earlobe, 10 kHz), passive listening to 720 x 10 s trials of peaky speech from 1, 2, 3 or 5
    simultaneous male narrators (five stories, 65 dB each; clean / 0 / -3 / -6 dB), 180 trials per condition, in
    random order. Click trials (ABR only) are skipped.

    Every story playing in a trial is a separate stimulus (`<story>_NNN`, none attended). From sub-07 on, half the
    trials were played with inverted polarity (whole mixture); events.tsv does not say which, the stamped trial ID
    does (last bit 0 = inverted). Those stimuli are named `<story>_NNN_inv` and their audio is negated.

    Onset = S 1 marker + ER-2 tube delay (0.81 ms); sound-card triggers. sub-04/08/19/23 have two runs; trials are
    numbered across runs in recording order (clicks included). Trials cut by a recording pause or by the end of a
    run are skipped (sub-19 run-01: the last trial). drift_correction=True (default): per-run drift from S 2 - S 1
    (24-26 ppm). sfreq=1000 (default; None keeps 10 kHz). Features: `audio`, `pulses` (glottal pulse train) and,
    with save_anm=True, `anm` (auditory-nerve-model regressor, rows = the two polarities).
    """

    def __init__(self, download_dir: str, sfreq: float | None = 1000, drift_correction: bool = True,
                 save_anm: bool = False):
        self.download_dir = download_dir
        self.sfreq = sfreq
        self.drift_correction = drift_correction
        self.save_anm = save_anm

    def parse(self) -> Iterable[TrialRecord]:
        for sub_dir in sorted(glob.glob(os.path.join(self.download_dir, "sub-*", "eeg"))):
            subject = int(os.path.basename(os.path.dirname(sub_dir))[4:])
            trial = 0
            for vhdr in sorted(glob.glob(os.path.join(sub_dir, "*_eeg.vhdr"))):
                events = pd.read_csv(vhdr.replace("_eeg.vhdr", "_events.tsv"), sep="\t")
                rec = read_recording(vhdr)
                if len(rec.trials) != len(events) or any(
                        e - t.start != 8 for e, t in zip(events["sample"], rec.trials)):
                    raise ValueError(f"{vhdr}: events.tsv does not match the S 1 markers")
                drift = rec.drift((DURATION - END_MARKER) * FS_EEG) if self.drift_correction else 0.0
                for row, marked in zip(events.itertuples(), rec.trials):
                    trial += 1
                    if row.trial_type != "speech" or not rec.usable(marked, int(DURATION * FS_EEG)):
                        continue
                    invert = len(marked.bits) == N_ID_BITS_FLIP and marked.bits[-1] == 0
                    files = [f for f in (getattr(row, f"file_story{i + 1}") for i in range(len(STORIES)))
                             if isinstance(f, str) and f != "n/a"]
                    yield TrialRecord(
                        subject=subject,
                        session=1,
                        trial=trial,
                        condition=CONDITIONS[row.snr],
                        ns_type="eeg",
                        stimulus=[s for f in files for s in self._stimuli(f, invert)],
                        neural_data_fn=self._eeg_loader(vhdr, marked.start + TUBE_DELAY * FS_EEG, drift),
                    )

    def _stimuli(self, stim_file: str, invert: bool) -> list:
        path = os.path.join(self.download_dir, "stimuli", stim_file)
        name = "_".join(os.path.basename(stim_file).split("_")[:2]) + ("_inv" if invert else "")
        stimuli = [
            StimulusRecord(modality="audio", name=name, feature_name="audio",
                           data_fn=expyfun_loader(path, "audio", fs=FS_AUDIO, invert=invert)),
            StimulusRecord(modality="audio", name=name, feature_name="pulses",
                           data_fn=pulse_loader(path, int(DURATION * FS_AUDIO), FS_AUDIO)),
        ]
        if self.save_anm:
            stimuli.append(StimulusRecord(modality="audio", name=name, feature_name="anm",
                                          data_fn=expyfun_loader(path, "anm", fs=FS_AUDIO, invert=invert)))
        return stimuli

    def _eeg_loader(self, vhdr: str, onset: float, drift: float):
        sfreq = self.sfreq

        def _loader():
            return load_trial(vhdr, onset, DURATION, sfreq, drift)

        return _loader


ADAPTOR = Polonenko2025Adaptor
