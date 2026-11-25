from __future__ import annotations

import glob
import os
from typing import Iterable

import pandas as pd

from cnsp_datasets.datasets.maddox_base.common import TUBE_DELAY, bits_to_ints, load_trial, read_recording
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import audio_loader
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

DURATION = 12.0
END_MARKER = 0.02  # S 2 is stamped 20 ms before the end (authors: time_diff / (12 - 0.02))
TYPES = ["click", "acoustic", "classical", "hiphop", "jazz", "metal", "pop",
         "chn_aud", "eng_aud", "interview", "lecture", "news", "talk"]
MUSIC = {"acoustic", "classical", "hiphop", "jazz", "metal", "pop"}


class Shan2024Adaptor(BaseAdaptor):
    """
    Shan et al. 2024 (NEMAR on004356, mirror of OpenNeuro ds004356): 22 subjects, 32 scalp channels + EP1/EP2 (FCz
    minus each earlobe, EP-PreAmp) at 10 kHz; passive listening to 12 s clips: six music genres and six types of
    speech, 40 clips each (480 trials). The 10 click trials and the undocumented 7-bit trials appended after the
    experiment are skipped (notes.md).

    The clip comes from the 10-bit trial ID after each start trigger ([type (4), clip number (6)]; matches
    events.tsv in every recording). Onset = S 1 + ER-2 tube delay (same hardware as ds005408; no artefact visible
    here to confirm it). drift_correction=True: per-recording drift from S 2 - S 1 (~25 ppm; the authors used a
    fixed 10000.25 Hz). sfreq=1000 by default (None keeps 10 kHz). Channels as recorded (types eeg). Stimuli
    `<type><NNN>` (audio, 48 kHz mono, rms 0.01), condition `music-<genre>` / `speech-<type>`.
    """

    def __init__(self, download_dir: str, sfreq: float | None = 1000, drift_correction: bool = True):
        super().__init__(download_dir)
        self.sfreq = sfreq
        self.drift_correction = drift_correction

    def parse(self) -> Iterable[TrialRecord]:
        for sub_dir in sorted(glob.glob(os.path.join(self.download_dir, "sub-*", "eeg"))):
            subject = int(os.path.basename(os.path.dirname(sub_dir))[4:])
            trial = 0
            for vhdr in sorted(glob.glob(os.path.join(sub_dir, "*_eeg.vhdr"))):
                events = pd.read_csv(vhdr.replace("_eeg.vhdr", "_events.tsv"), sep="\t")
                rec = read_recording(vhdr)
                listed = set(events["sample"])
                drift = rec.drift((DURATION - END_MARKER) * rec.sfreq) if self.drift_correction else 0.0
                for t in rec.trials:
                    trial += 1
                    if len(t.bits) != 10 or t.start not in listed:
                        continue
                    kind, number = bits_to_ints(t.bits, (4, 6))
                    if TYPES[kind] == "click" or not rec.usable(t, int(DURATION * rec.sfreq)):
                        continue
                    name = f"{TYPES[kind]}{number:03d}"
                    yield TrialRecord(
                        subject=subject, session=1, trial=trial,
                        condition=f"{'music' if TYPES[kind] in MUSIC else 'speech'}-{TYPES[kind]}", ns_type="eeg",
                        stimulus=StimulusRecord("audio", name, self._audio_loader(TYPES[kind], name),
                                                feature_name="audio"),
                        neural_data_fn=self._eeg_loader(vhdr, t.start + TUBE_DELAY * rec.sfreq, drift),
                    )

    def _audio_loader(self, kind: str, name: str):
        return audio_loader(os.path.join(self.download_dir, "stimuli", kind, f"{name}.wav"))

    def _eeg_loader(self, vhdr: str, onset: float, drift: float):
        sfreq = self.sfreq

        def _loader():
            return load_trial(vhdr, onset, DURATION, sfreq, drift)

        return _loader


ADAPTOR = Shan2024Adaptor
