from __future__ import annotations

import glob
import os
import re
from functools import lru_cache
from typing import Callable, Iterable

import h5py
import mne
import numpy as np
from mne.io.constants import FIFF
from scipy.io import wavfile

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 1000
AUDIO_FS = 44100
N_EPOCH = 60000      # samples per shipped epoch (60 s)
ONSET = 1            # onset-trigger edge: epoch index 1 (notes.md section 6)
N_MEG, N_REF = 157, 3
UNIT = 1e-15         # shipped values are fT (notes.md section 5)
GROUPS = {"Younger": ("younger", "normal", 0), "Older_Normal_Hearing": ("older", "normal", 0),
          "Older_Hearing_Impaired": ("older", "impaired", 100)}  # subject number offset: S01..S17 exist twice
# file tag: (condition, foreground wav, background wav or None, SNR dB, onset trigger line); notes.md sections 3, 6
CONDITIONS = {
    "Q_H": ("quiet", "Quiet_H", None, None, 167), "Q_L": ("quiet", "Quiet_L", None, None, 172),
    "P3_H": ("english_snr+3dB", "Plus_3_H", "English_F", 3, 168),
    "Zero_H": ("english_snr0dB", "Zero_H", "English_F", 0, 169),
    "M3_H": ("english_snr-3dB", "Minus_3_H", "English_F", -3, 170),
    "M6_H": ("english_snr-6dB", "Minus_6_H", "English_F", -6, 171),
    "P3_L": ("dutch_snr+3dB", "Plus_3_L", "Dutch_F", 3, 173),
    "Zero_L": ("dutch_snr0dB", "Zero_L", "Dutch_F", 0, 174),
    "M3_L": ("dutch_snr-3dB", "Minus_3_L", "Dutch_F", -3, 175),
    "M6_L": ("dutch_snr-6dB", "Minus_6_L", "Dutch_F", -6, 176),
}
OFFSET_LINE = 164
IDENTICAL = {"Minus_6_H": "Quiet_H", "Minus_6_L": "Quiet_L"}  # byte-identical wavs (notes.md section 3)
TRIGGER_TYPE = "unknown (TTL lines recorded by the KIT system; whether locked to the sound is not documented)"
NOTES = ("Raw KIT 157-channel MEG (axial gradiometers as `mag`, 3 reference magnetometers as `ref_meg`), 1000 Hz "
         "as recorded, no denoising; shipped as 60 s epochs cut by the authors at the onset trigger. t = 0 is the "
         "onset-trigger edge (epoch sample 1); the epoch's sample 0 is dropped, so trials are 59.999 s long. "
         "Shipped values are fT, converted to T. No sensor positions are shipped (positions are zero). MISC "
         "trigger and idle lines dropped. No drift correction. The mixture was not shipped: stimuli are the "
         "attended male foreground and the unattended female background, which starts with the foreground "
         "(lag 0, from the MEG) at the trial's SNR (background level relative to the foreground, not applied). "
         "Presentation order unknown: trial numbers follow condition order, 3 repetitions each.")


class Presacco2016Adaptor:
    """
    Presacco et al. 2016 (DRUM 10.13016/M2599Z52H), MEG part only: 17 younger and 15 older normal-hearing listeners
    plus 14 older hearing-impaired listeners, KIT 157-channel MEG at 1000 Hz. A male talker (Sleepy Hollow,
    attended) in quiet or with a female English or Dutch competing talker at +3, 0, -3, -6 dB SNR; 10 conditions x
    3 repetitions of the same 60 s mixture. Subjects: younger 1-17, older normal-hearing 21-35, older
    hearing-impaired 101-117 (S01_HL = 101). Stimuli (44.1 kHz wavs as shipped): foreground (attended) and, in
    noise, the background talker. See notes.md.
    """

    def __init__(self, download_dir: str):
        self.download_dir = download_dir

    def parse(self) -> Iterable[TrialRecord]:
        stim_dir = _one(os.path.join(self.download_dir, "**", "High Context"))
        stim_dir = os.path.dirname(stim_dir)
        for sdir in sorted(glob.glob(os.path.join(self.download_dir, "**", "S[0-9][0-9]_*_MEG"), recursive=True)):
            name = os.path.basename(sdir)
            m = re.fullmatch(r"S(\d\d)_(.+)_MEG", name)
            age, hearing, offset = GROUPS[m.group(2)]
            subject = int(m.group(1)) + offset
            for i, (tag, (cond, fg, bg, snr, line)) in enumerate(CONDITIONS.items()):
                mat = _find_mat(sdir, tag)
                for rep in range(3):
                    description = provenance(
                        "onset_only", TRIGGER_TYPE, NOTES, participant=name,
                        age_group=age, hearing=hearing, file=os.path.basename(mat), repetition=rep + 1,
                        foreground=fg, background=bg, snr_db=snr, onset_trigger_line=line,
                        offset_trigger_line=OFFSET_LINE, onset_sample_in_epoch=ONSET, presentation_order="unknown",
                        identical_stimulus=IDENTICAL.get(fg), units_as_shipped="fT (MEG and reference sensors)",
                        reference="not applicable (MEG)",
                        preprocessing="none (raw; online filters of the KIT system only)")
                    yield TrialRecord(
                        subject=subject, session=1, trial=3 * i + rep + 1, condition=cond, ns_type="meg",
                        stimulus=self._stimuli(stim_dir, fg, bg),
                        neural_data_fn=_meg_loader(mat, rep, line, description))

    def _stimuli(self, stim_dir: str, fg: str, bg: str | None) -> list[StimulusRecord]:
        """Foreground (attended), then the background talker (unattended) in noise."""
        out = [StimulusRecord("audio", fg, _audio(_wav(stim_dir, fg)), is_attended=True)]
        if bg:
            out.append(StimulusRecord("audio", bg, _audio(_wav(stim_dir, bg)), is_attended=False))
        return out


def _find_mat(sdir: str, tag: str) -> str:
    """The file of one condition. Names vary in the hearing-impaired group (S01HL_M3H, S01HL_M3_H, S01_HL_M3H,
    S04HL_M6L_II; notes.md section 2): match the tag without underscores, allowing an `II` suffix."""
    want = tag.replace("_", "")
    hits = [p for p in glob.glob(os.path.join(sdir, "*.mat"))
            if re.sub(r"^S\d\d_?(HL)?_", "", os.path.basename(p)[:-4]).replace("_", "") in (want, want + "II")]
    if len(hits) != 1:
        raise FileNotFoundError(f"{sdir}: expected one file for {tag}, found {hits}")
    return hits[0]


def _one(pattern: str) -> str:
    hits = glob.glob(pattern, recursive=True)
    if len(hits) != 1:
        raise FileNotFoundError(f"expected one match for {pattern}, found {hits}")
    return hits[0]


def _wav(stim_dir: str, name: str) -> str:
    folder = "High Context" if name.endswith("_H") or name == "English_F" else "Low Context"
    return os.path.join(stim_dir, folder, f"{name}.wav")


def _audio(path: str) -> Callable[[], dict]:
    def _load() -> dict:
        fs, x = wavfile.read(path)
        if fs != AUDIO_FS or x.dtype != np.int16 or x.ndim != 1:
            raise ValueError(f"{path}: expected {AUDIO_FS} Hz mono int16")
        return {"fs": AUDIO_FS, "data": (x / 32768.0).astype(np.float32)[None, :]}

    return _load


@lru_cache(maxsize=1)
def _read(mat: str) -> tuple[np.ndarray, list[int]]:
    """(3 repetitions, 192 channels, 60000 samples) as shipped and the authors' bad channels (0-based indices,
    notes.md section 5); checks layout and labels."""
    with h5py.File(mat, "r") as f:
        d = f["data_exported"]
        labels = ["".join(map(chr, f[r][()].ravel())) for r in d["labels"][0]]
        if d["sampling_frequency"][()].item() != FS or labels != [str(i) for i in range(1, 193)]:
            raise ValueError(f"{mat}: unexpected rate or channel labels")
        b = d["bad_channels"]
        bads = [] if b.attrs.get("MATLAB_empty", 0) else [int(i) for i in b[()].ravel()]
        x = d["eeg_data_aligned"][()]
    if x.shape != (3, 192, N_EPOCH):
        raise ValueError(f"{mat}: unexpected shape {x.shape}")
    return x, bads


def _info() -> mne.Info:
    names = [f"MEG {i:03d}" for i in range(1, N_MEG + N_REF + 1)]
    info = mne.create_info(names, FS, ["mag"] * N_MEG + ["ref_meg"] * N_REF)
    for i, ch in enumerate(info["chs"]):
        ch["coil_type"] = FIFF.FIFFV_COIL_KIT_GRAD if i < N_MEG else FIFF.FIFFV_COIL_KIT_REF_MAG
        ch["unit"] = FIFF.FIFF_UNIT_T
    with info._unlock():
        info["line_freq"] = 60.0
    return info


def _meg_loader(mat: str, rep: int, line: int, description: str) -> Callable[[], mne.io.BaseRaw]:
    def _loader() -> mne.io.BaseRaw:
        x, listed = _read(mat)
        x = x[rep]
        trig = x[line - 1, :10]
        if not (trig[ONSET] < 0.5 * trig[0] and trig[ONSET - 1] > 0.5 * trig[0]):  # active-low edge at ONSET
            raise ValueError(f"{mat} rep {rep + 1}: onset trigger edge not at sample {ONSET}")
        data = x[: N_MEG + N_REF, ONSET:] * UNIT
        raw = mne.io.RawArray(np.ascontiguousarray(data), _info(), verbose="ERROR")
        bads = set(listed) | set(np.flatnonzero(data[:N_MEG].std(1) == 0).tolist())  # authors' list + zeroed/dead
        raw.info["bads"] = [raw.ch_names[i] for i in sorted(bads)]
        raw.info["description"] = description
        return raw

    return _loader


ADAPTOR = Presacco2016Adaptor
