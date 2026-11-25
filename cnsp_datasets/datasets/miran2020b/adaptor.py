from __future__ import annotations

import glob
import os
import re
from functools import lru_cache
from typing import Callable, Iterable, Sequence

import mne
import numpy as np
from mne.io.constants import FIFF
from scipy.io import loadmat

from cnsp_datasets.datasets.simon_base.common import REFERENCE, audio_loader, find_one
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import mark_bads
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 200
AUDIO_FS = 44100
N_TIMES, N_REP = 12000, 3  # 60 s epochs, 3 repetitions per file
N_MEG = 157
SWITCH = (28.0, 30.0)      # attend the first talker until 28 s, pause cue, the other talker from 30 s (README)
# file number -> (condition, talker attended first, then)
CONDITIONS = {5: ("sp1_then_sp2", "Sp1", "Sp2"), 6: ("sp2_then_sp1", "Sp2", "Sp1")}
# Sensors missing from the 155/156-channel files (1-based), inferred (notes.md section 5): zero-filled and bad.
MISSING = {9: (56, 144)}
MISSING_DEFAULT = (56,)
SCALE = 1e-18  # nominal: the shipped scale is unknown (notes.md section 5)
TRIGGER_TYPE = "unknown (epochs cut by the authors at stimulus onset; no trigger channels shipped)"
NOTES = ("KIT 157-channel MEG as shipped by the authors: DSS-denoised (10 components projected back to the sensors, "
         "rank 10), 200 Hz (recorded at 1 kHz per the README, 2 kHz per the paper; downsampled by the authors), 60 s "
         "epochs from stimulus onset. Channel labels are not shipped: the file's 156 (S9: 155) channels are taken as "
         "MEG 001-157 in order without the sensor(s) in `missing_sensors` (inferred from nearest-neighbour "
         "correlations on the KIT-UMD-3 layout and MEG 056 being the system's dead channel), which are zero-filled "
         "and marked bad. No reference sensors, no positions. The shipped scale is unknown (values ~1e5): multiplied "
         "by a nominal 1e-18 so that amplitudes fall in the KIT fT range; treat absolute amplitudes as arbitrary. "
         "Stimuli: the two talkers as shipped (Sp1 male, Sp2 female), not the mixture; README: Sp1 + Sp2 in both "
         "conditions, paper: diotic. Attention: `attend/<talker>` annotations 0-28 s and 30-60 s and a `switch_cue` "
         "at 28-30 s (README; the pause is not in the wavs); is_attended is False for both talkers because attention "
         "switches within every trial. Presentation order unknown: trials 1-3 are file 5, 4-6 file 6.")


class Miran2020bAdaptor(BaseAdaptor):
    """
    Instructed attention switching experiment of Miran et al. (2020, PLoS Comput Biol; DRUM hdl 1903/26352; data
    of Akram et al. 2016): KIT MEG of 7 subjects (S8-S11, S14-S16) listening to a male (Sp1) and a female (Sp2)
    talker reading A Child's History of England, attending one for 0-28 s and the other for 30-60 s; 2 conditions
    (which talker first) x 3 repetitions. DSS-denoised sensor data at 200 Hz as shipped. See notes.md.
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)

    def parse(self) -> Iterable[TrialRecord]:
        speech = os.path.dirname(find_one(os.path.join(self.download_dir, "**", "Speech", "Sp1.wav")))
        stimulus = [StimulusRecord("audio", w, audio_loader(os.path.join(speech, f"{w}.wav"), AUDIO_FS),
                                   is_attended=False) for w in ("Sp1", "Sp2")]
        paths = sorted(glob.glob(os.path.join(self.download_dir, "**", "ssbj*_epochData*_DSSed.mat"), recursive=True))
        files = {}
        for path in paths:
            m = re.fullmatch(r"ssbj(\d+)_epochData(\d)_DSSed\.mat", os.path.basename(path))
            if not m:
                raise ValueError(f"unexpected file {path}")
            s, k = map(int, m.groups())
            if (s, k) in files or k not in CONDITIONS:
                raise ValueError(f"unexpected or duplicate file {path}")
            files[s, k] = path
        subjects = sorted({s for s, _ in files})
        if set(files) != {(s, k) for s in subjects for k in CONDITIONS}:
            raise ValueError(f"incomplete subjects: {sorted(files)}")
        for s in subjects:
            missing = MISSING.get(s, MISSING_DEFAULT)
            for i, (k, (cond, first, second)) in enumerate(CONDITIONS.items()):
                path = files[s, k]
                spans = [(0.0, SWITCH[0], f"attend/{first}"), (SWITCH[0], SWITCH[1] - SWITCH[0], "switch_cue"),
                         (SWITCH[1], N_TIMES / FS - SWITCH[1], f"attend/{second}")]
                for rep in range(N_REP):
                    description = provenance(
                        "onset_only", TRIGGER_TYPE, NOTES, validation_tier="low", participant=f"S{s}",
                        file=os.path.basename(path), repetition=rep + 1, attended_first=first, attended_second=second,
                        switch_cue_s=list(SWITCH), missing_sensors=[f"MEG {c:03d}" for c in missing],
                        units_as_shipped="unknown (arbitrary scale, values ~1e5); nominal x 1e-18 to T",
                        presentation_order="unknown", reference=REFERENCE,
                        preprocessing="by the authors: DSS (10 components back-projected), downsampled to 200 Hz")
                    yield TrialRecord(
                        subject=s, session=1, trial=N_REP * i + rep + 1, condition=cond, ns_type="meg",
                        stimulus=stimulus, neural_data_fn=_meg_loader(path, missing, rep, spans, description))


@lru_cache(maxsize=1)
def _read(path: str) -> np.ndarray:
    """data_DSSed as shipped, (samples, channels, repetitions), checked for length and repetitions."""
    x = loadmat(path, variable_names=["data_DSSed"])["data_DSSed"]
    if x.shape[0] != N_TIMES or x.shape[2] != N_REP:
        raise ValueError(f"{path}: unexpected shape {x.shape}")
    return x


def _info() -> mne.Info:
    """KIT-157 at 200 Hz: 157 axial gradiometers (`mag`), no reference sensors or positions."""
    info = mne.create_info([f"MEG {i:03d}" for i in range(1, N_MEG + 1)], FS, "mag")
    for ch in info["chs"]:
        ch["coil_type"] = FIFF.FIFFV_COIL_KIT_GRAD
    with info._unlock():
        info["line_freq"] = 60.0
    return info


def _meg_loader(path: str, missing: Sequence[int], rep: int, spans: Sequence[tuple[float, float, str]],
                description: str) -> Callable[[], mne.io.BaseRaw]:
    """One repetition as MEG 001-157 (`missing` 1-based sensors zero-filled and bad), nominal T, with attention
    annotations (onset, duration, description)."""
    def _loader() -> mne.io.BaseRaw:
        x = _read(path)
        missing0 = [c - 1 for c in missing]
        keep = np.setdiff1d(np.arange(N_MEG), missing0)
        if x.shape[1] != len(keep):
            raise ValueError(f"{path}: {x.shape[1]} channels, expected {len(keep)}")
        data = np.zeros((N_MEG, N_TIMES))
        data[keep] = x[:, :, rep].T * SCALE
        raw = mne.io.RawArray(data, _info(), verbose="ERROR")
        mark_bads(raw, [raw.ch_names[c] for c in missing0])
        raw.info["description"] = description
        onsets, durations, labels = zip(*spans)
        raw.set_annotations(mne.Annotations(onsets, durations, labels))
        return raw

    return _loader


ADAPTOR = Miran2020bAdaptor
