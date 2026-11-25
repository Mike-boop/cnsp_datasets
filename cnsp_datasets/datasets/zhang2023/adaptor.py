from __future__ import annotations

import collections
import functools
import os
from typing import Callable, Iterable

import h5py
import mne
import numpy as np
from mne.io import BaseRaw

from cnsp_datasets.datasets.zhang2023.alignment.splices import (FS_AUDIO, FS_EEG, SIDES, mat_files, read_csv,
                                                                read_wav, realigned, source_audio, trial_lengths)
from cnsp_datasets.datasets.zhang2023.expinfo import channel_names, read_expinfo
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

PAIRS = ("all", "confident")
UNCLEANED = {("S06", t) for t in range(1, 11)}  # full 115 s, never artefact-cleaned (SD 25-72 uV; notes 3)
TRIGGER = "unknown (Emotiv EPOC Flex; the authors' trial epoching is not documented, probably software markers)"
NOTES = ("Authors' preprocessed EEG (EEGLAB: 1-32 Hz, 128 Hz, ICA, interpolated channels, artefact segments cut "
         "out of the EEG and both wavs together; splice_pieces lists the contiguous pieces). Streams l/r = the "
         "table's l_audio/r_audio, not sides. The shipped timing shows no envelope tracking in 17/21 subjects; "
         "DNN offsets of ~1-3 s per presentation pair were found where estimable (notes 6b).")


class Zhang2023Adaptor(BaseAdaptor):
    """
    Zhang, Yuan & Lu (Zenodo 7253438; ICASSP 2023) NJU auditory attention detection: two Mandarin news talkers over
    a loudspeaker array, attend one (static azimuths, or moving in trials 25-32 of S01-S15); 21 participants x
    28-32 trials of 10-110 s; Emotiv EPOC Flex 32 channels, authors' preprocessed EEG at 128 Hz.

    pairs="all" (default): every shipped trial as shipped (spliced EEG, shipped timing, shipped per-trial wavs).
    This timing fails validation in 17 of 21 subjects.
    pairs="confident": only the 16 presentation pairs (32 trials) with a confident DNN offset (precomputed:
    alignment/pair_offsets.csv), each stimulus rebuilt from its unspliced source at the trial's splice map + the
    pair's offset (alignment/splices.py); grade poor (brain-based). See notes.md 6b and README.md.
    """

    def __init__(self, download_dir: str, pairs: str = "all"):
        super().__init__(download_dir)
        self.root = download_dir
        self.pairs = self.choice("pairs", pairs, PAIRS)
        self.pieces = collections.defaultdict(list)
        for p in read_csv("pieces.csv"):
            self.pieces[(p["subject"], p["trial"])].append(p)
        self.offsets = {}
        if pairs == "confident":
            rows = read_csv("pair_offsets.csv", text=("subject", "lag_s", "z", "p", "lag_a_s", "lag_b_s", "confident"))
            for r in (r for r in rows if r["confident"] == "True"):
                pair = f"{r['trial_a']}+{r['trial_b']}"
                self.offsets.update({(r["subject"], t): (r["lag_samples"], pair) for t in (r["trial_a"], r["trial_b"])})

    def parse(self) -> Iterable[TrialRecord]:
        for path in mat_files(self.root):
            subject = os.path.basename(path)[:-4]
            with h5py.File(path, "r") as f:
                info, ch_names, lengths = read_expinfo(f), channel_names(f), trial_lengths(f)
            for t, n in enumerate(lengths, 1):
                if not n or (self.pairs == "confident" and (subject, t) not in self.offsets):
                    continue
                yield self._record(path, subject, t, n, info, ch_names)

    def _record(self, path, subject, t, n, info, ch_names) -> TrialRecord:
        azimuth = info["azimuth"][t - 1]
        moving = len(azimuth) > 2
        attended = "l" if info["attended_lr"][t - 1] == "left" else "r"
        files = {side: info[col][t - 1].removesuffix(".wav") for side, (_, col) in SIDES.items()}
        pieces = self.pieces[(subject, t)]
        lag, pair = self.offsets.get((subject, t), (None, None))
        stimuli = []
        for side, name in files.items():
            stim = f"{subject}_t{t:02d}_{side}_{name}"
            if lag is None:
                loader = _wav_loader(path, t, side)
            else:
                stim += "_dnn"
                loader = _realigned_loader(self.root, name, pieces, n, lag)
            stimuli.append(StimulusRecord("audio", stim, loader, is_attended=side == attended, feature_name="audio"))
        mapped = sum(p["n"] for p in pieces) / n
        description = provenance(
            "onset_only" if lag is None else "dnn", TRIGGER, NOTES, validation_tier=None,
            subject_name=subject, protocol="A" if int(subject[1:]) <= 15 else "B",
            l_audio=files["l"], r_audio=files["r"], attended_stream=attended,
            azimuth_deg=azimuth if moving else {"l": azimuth[0], "r": azimuth[1]},
            azimuth_note="5-point trajectory as shipped (meaning not documented)" if moving else "per stream",
            uncleaned=(subject, t) in UNCLEANED,
            splice_pieces=[[p["eeg_start"], p["n"], p["source_start"]] for p in pieces],
            splice_pieces_note="[EEG sample start, samples, 115 s source position] at 128 Hz; only where both "
                               "streams' rebuilds agree",
            mapped_fraction=round(mapped, 4),
            dnn_offset_samples=lag, dnn_offset_s=None if lag is None else lag / FS_EEG, dnn_pair=pair,
            dnn_note=None if lag is None else "stimulus = source audio at the mapped position + offset (negative: "
                                              "EEG later than the shipped pairing); unmapped samples are zeros",
            units_as_shipped="uV (float32), read into V",
            reference="Emotiv CMS/DRL (positions not documented), as shipped",
            positions="template (standard_1020)",
        )
        condition = f"attend-{attended}-{'moving' if moving else 'static'}"
        return TrialRecord(subject=int(subject[1:]), session=1, trial=t, condition=condition, ns_type="eeg",
                           stimulus=stimuli,
                           neural_data_fn=_eeg_loader(path, t, ch_names, description))


@functools.lru_cache(maxsize=1)
def _cover() -> list[dict]:
    return read_csv("source_cover.csv")


@functools.lru_cache(maxsize=8)
def _source(root: str, name: str) -> np.ndarray:
    return source_audio(root, name, _cover())


def _wav_loader(path: str, trial: int, side: str) -> Callable[[], dict]:
    """Loader of the shipped per-trial wav (16 kHz, float64 -> float32)."""
    def _loader() -> dict:
        with h5py.File(path, "r") as f:
            return {"fs": FS_AUDIO, "data": read_wav(f, trial - 1, side).astype(np.float32)[None]}
    return _loader


def _realigned_loader(root: str, name: str, pieces: list[dict], n_eeg: int, lag: int) -> Callable[[], dict]:
    """Loader of a trial stimulus rebuilt from the source at the splice map + lag (EEG samples)."""
    def _loader() -> dict:
        return {"fs": FS_AUDIO, "data": realigned(_source(root, name), pieces, n_eeg, lag)[None]}
    return _loader


def _eeg_loader(path: str, trial: int, ch_names: list[str], description: str) -> Callable[[], BaseRaw]:
    """Loader of the shipped trial EEG (uV -> V) at 128 Hz with template 10-20 positions."""
    def _loader() -> BaseRaw:
        with h5py.File(path, "r") as f:
            x = np.asarray(f[f["data/eeg"][trial - 1, 0]], dtype=float) * 1e-6  # uV -> V, (channels, time)
        raw = mne.io.RawArray(x, mne.create_info(ch_names, float(FS_EEG), "eeg"), verbose="ERROR")
        raw.set_montage("standard_1020", verbose="ERROR")
        raw.info["description"] = description
        return raw
    return _loader


ADAPTOR = Zhang2023Adaptor
