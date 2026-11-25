from __future__ import annotations

import os
import re
from typing import Iterable

import numpy as np
import pandas as pd
from mne.channels import make_standard_montage
from mne.io import BaseRaw, read_raw_brainvision

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import read_wav
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord


class Etard2019Adaptor(BaseAdaptor):
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
    Stimulus names are `<condition>_part_<run>_<role>`, plus `_at<offset>ms` (each stream's offset from the trial
    start, joined by '+') when a stream does not start at the trial start: the padding is part of the content, and
    one name must always mean one content (notes.md).
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

    def parse(self) -> Iterable[TrialRecord]:
        for events_path in self.sorted_glob(self.download_dir, "sub-*/ses-*/eeg/*_events.tsv"):
            m = re.search(r"sub-(\d+)_ses-(\w+)_task-(\w+)_run-(\d+)_events", os.path.basename(events_path))
            subject, ses, task, run = int(m.group(1)), m.group(2), m.group(3), int(m.group(4))
            condition = self._COND_MAP[(ses, task)]
            ev = pd.read_csv(events_path, sep="\t")
            streams = ev[ev.stim_file.notna()].set_index("trial_type")
            start = int(streams["sample"].min())
            stop = int((streams["sample"] + (streams.duration * 1000).round()).max()) + 1
            prefix = f"{condition}_part_{run}"
            kinds = ["speech", "english_track"]
            stimuli = [StimulusRecord(modality="audio", name=_name(f"{prefix}_story", streams, kinds, start),
                                      is_attended=True, feature_name="audio",
                                      data_fn=self._audio_loader(streams, kinds, start))]
            for kind, role in (("babble", "babble"), ("competing", "distractor")):
                if kind in streams.index:
                    name = _name(f"{prefix}_{role}", streams, [kind], start)
                    stimuli.append(StimulusRecord(modality="audio", name=name, is_attended=False, feature_name="audio",
                                                  data_fn=self._audio_loader(streams, [kind], start)))
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
        parts = [(os.path.join(self.download_dir, "stimuli", streams.loc[k, "stim_file"]), offset_ms)
                 for k, offset_ms in _offsets(streams, kinds, start)]

        def _loader() -> dict:
            out, fs = np.zeros(0), None
            for path, offset_ms in parts:
                x, rate = read_wav(path)  # float32 as written by make_bids (44.1 kHz mono)
                if x.shape[0] != 1 or fs not in (None, rate):
                    raise ValueError(f"{path}: expected mono at {fs or rate} Hz")
                fs, x = rate, x[0]
                pad = int(round(offset_ms * fs / 1000))
                n = pad + len(x)
                if len(out) < n:
                    out = np.concatenate([out, np.zeros(n - len(out))])
                out[pad:n] += x
            return {"fs": int(fs), "data": out[None, :].astype(np.float32)}

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


def _offsets(streams: pd.DataFrame, kinds: list[str], start: int) -> list[tuple[str, int]]:
    """(kind, onset in ms (1 kHz samples) relative to the trial start) of the given streams present in the run."""
    return [(k, int(streams.loc[k, "sample"]) - start) for k in kinds if k in streams.index]


def _name(base: str, streams: pd.DataFrame, kinds: list[str], start: int) -> str:
    """Stimulus name: `base`, plus `_at<ms>[+<ms>]` when a stream is padded (the padding is part of the content)."""
    offsets = [off for _, off in _offsets(streams, kinds, start)]
    return base if not any(offsets) else f"{base}_at{'+'.join(map(str, offsets))}ms"


ADAPTOR = Etard2019Adaptor
