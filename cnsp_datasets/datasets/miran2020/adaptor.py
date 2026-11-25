from __future__ import annotations

import os
from functools import lru_cache
from typing import Callable, Iterable

import h5py
import mne
import numpy as np
from mne.io.constants import FIFF

from cnsp_datasets.datasets.simon_base.common import REFERENCE, audio_loader, find_one, subject_number
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.iohelpers import mark_bads
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

PARTICIPANT = "R2082"
FS_IN, FS = 2000, 1000
AUDIO_FS = 22050
N_EPOCH, N_REP, N_CH = 180000, 3, 192  # 90 s epochs at 2 kHz, repetitions, channels (+ 32 MISC after MEG and ref)
N_MEG, N_REF = 157, 3
N_OUT = 90000                          # 90 s at 1 kHz from the trigger edge
ONSET, ONSET_LINE = 1, 171             # active-low onset pulse on channel 171 (MISC 011) from epoch index 1
UNIT = 1e-15                           # shipped values are fT (notes.md section 5)
MALE = "Seg_V_885_5_Sec_filt.wav_Short_Norm"
FEMALE = "Seg_IV_Female_Sleepy_1413.2_Sec_filt.wav_Short_Norm"
TRIGGER_TYPE = "unknown (TTL line recorded by the KIT system; whether locked to the sound is not documented)"
NOTES = ("Raw KIT 157-channel MEG (axial gradiometers as `mag`, 3 reference magnetometers as `ref_meg`), recorded at "
         "2 kHz, shipped as three 90 s epochs cut by the authors at the onset trigger; resampled to 1 kHz (anti-alias "
         "FIR + one spline resample). t = 0 is the onset-trigger edge (epoch sample 1). Shipped values are fT, "
         "converted to T. No sensor positions shipped. MISC lines dropped. No drift correction. Stimuli: the male and "
         "female talkers (The Legend of Sleepy Hollow) as shipped, not the mixture (diotic, paper). Attention "
         "switched at will (1-3 times per trial, button presses); the switch times are not shipped, so only a "
         "zero-length `attend_start/<male>` annotation at t = 0 (instructed start) marks attention and is_attended is "
         "False for both talkers.")


class Miran2020Adaptor(BaseAdaptor):
    """
    At-will attention switching experiment of Miran et al. (2020, PLoS Comput Biol; DRUM hdl 1903/26351; from
    Presacco et al. 2019, EMBC): KIT MEG of one subject (R2082), 3 trials of the same 90 s mixture of a male and a
    female talker, starting on the male talker and switching at will. Raw sensor data, 1 kHz. See notes.md.
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)

    def parse(self) -> Iterable[TrialRecord]:
        mat = find_one(os.path.join(self.download_dir, "**", f"{PARTICIPANT}_Cocktail_*.mat"))
        wavs = {w: find_one(os.path.join(self.download_dir, "**", f"{w}.wav")) for w in (MALE, FEMALE)}
        stimulus = [StimulusRecord("audio", w, audio_loader(p, AUDIO_FS), is_attended=False) for w, p in wavs.items()]
        for rep in range(N_REP):
            description = provenance(
                "onset_only", TRIGGER_TYPE, NOTES, validation_tier="mlr", participant=PARTICIPANT,
                file=os.path.basename(mat), repetition=rep + 1, onset_trigger_line=ONSET_LINE,
                onset_sample_in_epoch=ONSET, attended_first=MALE,
                switch_times="not shipped (button presses; paper Fig 6 shows trials 1-2)",
                units_as_shipped="fT (MEG and reference sensors)", reference=REFERENCE,
                preprocessing="none (raw; online filters of the KIT system only)")
            yield TrialRecord(subject=subject_number(PARTICIPANT), session=1, trial=rep + 1,
                              condition="at_will_switching", ns_type="meg", stimulus=stimulus,
                              neural_data_fn=_meg_loader(mat, rep, description))


@lru_cache(maxsize=1)
def _read(mat: str) -> tuple[np.ndarray, list[int]]:
    """(3 repetitions, 192 channels, 180000 samples) as shipped and the authors' bad channels (0-based indices,
    notes.md section 5); checks layout and labels (as presacco2016)."""
    with h5py.File(mat, "r") as f:
        d = f["data_exported"]
        labels = ["".join(map(chr, f[r][()].ravel())) for r in d["labels"][0]]
        if d["sampling_frequency"][()].item() != FS_IN or labels != [str(i) for i in range(1, N_CH + 1)]:
            raise ValueError(f"{mat}: unexpected rate or channel labels")
        b = d["bad_channels"]
        bads = [] if b.attrs.get("MATLAB_empty", 0) else [int(i) for i in b[()].ravel()]
        x = d["eeg_data_aligned"][()]
    if x.shape != (N_REP, N_CH, N_EPOCH) or any(i >= N_MEG for i in bads):
        raise ValueError(f"{mat}: unexpected shape {x.shape} or bad channels {bads}")
    return x, bads


def _info() -> mne.Info:
    """KIT-157 at 2 kHz: 157 axial gradiometers (`mag`) and 3 reference magnetometers, no positions."""
    names = [f"MEG {i:03d}" for i in range(1, N_MEG + N_REF + 1)]
    info = mne.create_info(names, FS_IN, ["mag"] * N_MEG + ["ref_meg"] * N_REF)
    for i, ch in enumerate(info["chs"]):
        ch["coil_type"] = FIFF.FIFFV_COIL_KIT_GRAD if i < N_MEG else FIFF.FIFFV_COIL_KIT_REF_MAG
    with info._unlock():
        info["line_freq"] = 60.0
    return info


def _meg_loader(mat: str, rep: int, description: str) -> Callable[[], mne.io.BaseRaw]:
    """One repetition from the onset-trigger edge, in T, at 1 kHz, with bads and the attention annotation."""
    def _loader() -> mne.io.BaseRaw:
        x, listed = _read(mat)
        x = x[rep]
        hi, lo = x[ONSET_LINE - 1, ONSET - 1:ONSET + 1]
        if not (hi > 0 and lo < 0.5 * hi):  # active-low edge at ONSET
            raise ValueError(f"{mat} rep {rep + 1}: onset trigger edge not at sample {ONSET}")
        raw = mne.io.RawArray(x[:N_MEG + N_REF] * UNIT, _info(), verbose="ERROR")
        out = crop_on_audio_clock(raw, ONSET, N_OUT, sfreq_out=FS)
        flat = np.flatnonzero(x[:N_MEG].std(axis=1) == 0).tolist()
        mark_bads(out, [out.ch_names[i] for i in sorted(set(listed) | set(flat))])
        out.info["description"] = description
        out.set_annotations(mne.Annotations([0.0], [0.0], [f"attend_start/{MALE}"]))
        return out

    return _loader


ADAPTOR = Miran2020Adaptor
