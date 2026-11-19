from __future__ import annotations

import glob
import os
import re
from typing import Iterable

import numpy as np
import pandas as pd
from mne.channels import make_standard_montage
from mne.io import BaseRaw, read_raw_brainvision
from scipy.io import wavfile

from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord


class Etard2019Adaptor:
    """
    Etard et al. 2019 (Reichenbach lab) in its BIDS version (built by make_bids.py from the original record, Zenodo
    7086209): 63-channel EEG at 1 kHz plus the `Sound` stimtrack, one BrainVision recording per run; English
    audiobooks in quiet, in babble noise at three levels and with a competing speaker (ses-english), and Dutch
    audiobooks with embedded English sentences in quiet and in babble (ses-dutch); 4 runs per condition.

    Stream onsets in `*_events.tsv` are measured from the stimtrack (sub-ms; drift ~1 ppm, not corrected). One trial
    per run: the EEG from the earliest stream onset (the babble in English noise runs, 1 s before the speech; the
    speech otherwise) to the end of the last stream + 1 sample, EEG channels only (volts). Every stimulus is padded
    with zeros to start at the trial start:
      - attended: the speech; in Dutch runs with the run's own English sentences added (both normalised to the same
        RMS by the authors and summed when played);
      - unattended (noise runs): the babble (`*_babble`) or the competing speaker (`*_distractor`).
    lb/mb/hb = low/medium/high babble level, i.e. high/medium/low SNR (measured per run, `snr_db`).
    """

    _COND_MAP = {  # (session, task) -> standardised condition
        ("english", "clean"): "natural",
        ("english", "lb"): "sin_highSNR",
        ("english", "mb"): "sin_mediumSNR",
        ("english", "hb"): "sin_lowSNR",
        ("english", "fM"): "competing_fM",
        ("english", "fW"): "competing_fF",
        ("dutch", "clean"): "foreign_quiet",
        ("dutch", "lb"): "foreign_highSNR",
        ("dutch", "mb"): "foreign_mediumSNR",
        ("dutch", "hb"): "foreign_lowSNR",
    }
    _SESSION = {"english": 1, "dutch": 2}

    def __init__(self, download_dir: str):
        self.download_dir = download_dir

    def parse(self) -> Iterable[TrialRecord]:
        pattern = os.path.join(self.download_dir, "sub-*", "ses-*", "eeg", "*_events.tsv")
        for events_path in sorted(glob.glob(pattern)):
            m = re.search(r"sub-(\d+)_ses-(\w+)_task-(\w+)_run-(\d+)_events", os.path.basename(events_path))
            subject, ses, task, run = int(m.group(1)), m.group(2), m.group(3), int(m.group(4))
            condition = self._COND_MAP[(ses, task)]
            ev = pd.read_csv(events_path, sep="\t")
            streams = ev[ev.stim_file.notna()].set_index("trial_type")
            start = int(streams["sample"].min())
            stop = int((streams["sample"] + (streams.duration * 1000).round()).max()) + 1
            prefix = f"{condition}_part_{run}"
            stimuli = [StimulusRecord(modality="audio", name=f"{prefix}_story", is_attended=True, feature_name="audio",
                                      data_fn=self._audio_loader(streams, ["speech", "english_track"], start))]
            for kind, role in (("babble", "babble"), ("competing", "distractor")):
                if kind in streams.index:
                    stimuli.append(StimulusRecord(modality="audio", name=f"{prefix}_{role}", is_attended=False,
                                                  feature_name="audio", data_fn=self._audio_loader(streams, [kind], start)))
            yield TrialRecord(
                subject=subject,
                session=self._SESSION[ses],
                trial=run,
                condition=condition,
                ns_type="eeg",
                stimulus=stimuli,
                neural_data_fn=self._eeg_loader(events_path.replace("_events.tsv", "_eeg.vhdr"), start, stop),
            )

    def _audio_loader(self, streams: pd.DataFrame, kinds: list[str], start: int):
        """Sum of the given streams, each placed at its onset relative to the trial start (sample at 1 kHz)."""
        parts = [(os.path.join(self.download_dir, "stimuli", streams.loc[k, "stim_file"]),
                  int(streams.loc[k, "sample"]) - start) for k in kinds if k in streams.index]

        def _loader() -> dict:
            out, fs = np.zeros(0), None
            for path, offset_ms in parts:
                fs, x = wavfile.read(path)
                pad = int(round(offset_ms * fs / 1000))
                n = pad + len(x)
                if len(out) < n:
                    out = np.concatenate([out, np.zeros(n - len(out))])
                out[pad:n] += x
            return {"fs": int(fs), "data": out[None, :]}

        return _loader

    @staticmethod
    def _eeg_loader(vhdr: str, start: int, stop: int):
        def _loader() -> BaseRaw:
            raw = read_raw_brainvision(vhdr, preload=False, verbose="ERROR")
            raw = raw.crop(tmin=raw.times[start], tmax=raw.times[min(stop, raw.n_times) - 1]).load_data()
            raw.pick([c for c in raw.ch_names if c != "Sound"])
            raw.set_montage(make_standard_montage("easycap-M1"), on_missing="warn")
            raw.set_meas_date(None)
            return raw

        return _loader


ADAPTOR = Etard2019Adaptor
