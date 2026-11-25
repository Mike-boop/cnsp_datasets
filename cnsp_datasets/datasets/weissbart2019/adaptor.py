from __future__ import annotations

import os
from typing import Iterable

import pandas as pd
from mne.channels import make_standard_montage
from mne.io import BaseRaw, read_raw_brainvision

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import audio_loader, mark_bads
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord


class Weissbart2019Adaptor(BaseAdaptor):
    """
    Weissbart et al. 2019 in its BIDS version (built by make_bids.py from the original record, Zenodo 7086168): one
    continuous BrainVision recording per participant (63 EEG channels + the `Sound` stimtrack, 1 kHz), 15 English
    audiobook chapters, onsets in `*_events.tsv` measured from the stimtrack.

    One trial per story: the EEG from the onset sample for the story's duration + 1 sample (as the HDF5 release cut
    it), EEG channels only (volts), bad channels from `*_channels.tsv` in info["bads"]. Subjects are numbered as in the
    HDF5 release (sub-00 = P00). Stimuli: the story audio (first channel, float32) and its word/phone TextGrid as
    shipped. Drift (~1.2 ppm, listed per story) is not corrected. Original participant P04 (sub-03) did not hear
    BROP01; its events leave it out (194 trials).
    """

    TASK = "audiobook"

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self._participants = pd.read_csv(os.path.join(download_dir, "participants.tsv"), sep="\t")

    def parse(self) -> Iterable[TrialRecord]:
        for label in self._participants.participant_id:
            stem = os.path.join(self.download_dir, label, "eeg", f"{label}_task-{self.TASK}")
            events = pd.read_csv(f"{stem}_events.tsv", sep="\t")
            channels = pd.read_csv(f"{stem}_channels.tsv", sep="\t")
            bads = channels.name[channels.status == "bad"].tolist()
            for _, ev in events[events.trial_type == "story"].iterrows():
                story = os.path.dirname(ev.stim_file)
                yield TrialRecord(
                    subject=int(label.split("-")[1]),
                    session=1,
                    trial=int(ev.trial),
                    condition="natural",
                    ns_type="eeg",
                    stimulus=[StimulusRecord(modality="audio", name=story, is_attended=True,
                                             data_fn=audio_loader(os.path.join(self.download_dir, "stimuli",
                                                                               ev.stim_file), channel=0)),
                              StimulusRecord(modality="audio", name=story, is_attended=True, feature_name="textgrid",
                                             data_fn=self._text_loader(f"{story}/{story}.TextGrid"))],
                    neural_data_fn=self._eeg_loader(f"{stem}_eeg.vhdr", int(ev["sample"]), float(ev.duration), bads),
                )

    def _text_loader(self, rel: str):
        path = os.path.join(self.download_dir, "stimuli", rel)

        def _loader() -> str:
            with open(path, encoding="utf-8") as f:
                return f.read()

        return _loader

    @staticmethod
    def _eeg_loader(vhdr: str, sample: int, duration: float, bads: list[str]):
        def _loader() -> BaseRaw:
            raw = read_raw_brainvision(vhdr, preload=False, verbose="ERROR")
            sfreq = raw.info["sfreq"]
            stop = sample + int(round(duration * sfreq)) + 1
            raw = raw.crop(tmin=raw.times[sample], tmax=raw.times[min(stop, raw.n_times) - 1]).load_data()
            raw.pick([c for c in raw.ch_names if c != "Sound"])
            raw.set_montage(make_standard_montage("easycap-M1"), on_missing="warn")
            mark_bads(raw, [b for b in bads if b != "Sound"])  # channels.tsv's own list: strict
            raw.set_meas_date(None)
            return raw

        return _loader


ADAPTOR = Weissbart2019Adaptor
