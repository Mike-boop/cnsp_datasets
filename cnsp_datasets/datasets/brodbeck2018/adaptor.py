from __future__ import annotations

import glob
import os
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
from scipy.io import wavfile

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 100             # shipped epochs: tSSS, 1-40 Hz FIR, decimated to 100 Hz by the authors
N_TIMES = 6001       # 0 .. 60.00 s inclusive
AUDIO_FS = 22050
BG_START = AUDIO_FS  # the background talker is muted for the first 1.000 s of every mixture (notes.md sections 3, 9)
FILES = {"two_speakers": (16, 4), "single_speaker": (8, 8)}  # epochs, distinct codes per file
# trigger code: (foreground = attended, background = ignored or None); conditions.txt, verified in notes.md
CODES = {163: ("male_1", "female_1"), 164: ("female_2", "male_2"), 169: ("female_1", "male_1"),
         170: ("male_2", "female_2"), 178: ("male_3", "female_3"), 179: ("female_4", "male_4"),
         184: ("female_3", "male_3"), 185: ("male_4", "female_4"),
         165: ("male_1", None), 166: ("female_1", None), 167: ("male_2", None), 168: ("female_2", None),
         183: ("male_4", None), 186: ("female_3", None), 187: ("male_3", None), 188: ("female_4", None)}
OFFSET_LINE = "MISC 003"  # common end-of-stimulus TTL line (code 162)
TRIGGER_TYPE = ("software (inferred: Presentation, Neurobehavioral Systems, is listed in the paper's key resources; "
                "TTL lines recorded by the KIT system; latency to the sound not documented)")
NOTES = ("Authors' preprocessed KIT 157-channel MEG epochs (DRUM): tSSS (mne-python 0.14, 10 s buffer, "
         "correlation 0.9), zero-phase FIR 1-40 Hz, decimated to 100 Hz; axial gradiometers as `mag`, 3 reference "
         "magnetometers as `ref_meg`, T. Raw continuous data were not released. t = 0 is the onset trigger (the "
         "authors' epoch start); the common offset line is high at 60.00 s in every epoch (trigger interval "
         "59.995-60.000 s at 100 Hz). No drift correction (not measurable). MISC and STI channels dropped. Two-talker "
         "stimuli: attended talker (is_attended), the mixture as played and the ignored talker as played (muted "
         "for its first 1.000 s, `<name>_from1s`).")


class Brodbeck2018Adaptor:
    """
    Brodbeck, Hong & Simon 2018 (DRUM 10.13016/M2ZC7RZ0F): 26 listeners, KIT MEG, Dickens audiobook (LibriVox),
    one male and one female talker. Per subject 24 one-minute trials in presentation order: 4 two-talker mixtures
    x 4 repetitions (`two_speakers`, attend one talker, counterbalanced) and the 8 single talkers once
    (`single_speaker`). Subject = R-number mod 1000 (R2262 -> 262). Shipped neural data are the authors'
    preprocessed 100 Hz epochs. Stimuli: 22.05 kHz wavs as shipped (see notes.md).
    """

    def __init__(self, download_dir: str):
        self.root = download_dir

    def parse(self) -> Iterable[TrialRecord]:
        stim_dir = os.path.dirname(_one(os.path.join(self.root, "**", "stimuli", "male_1.wav")))
        sdirs = sorted(glob.glob(os.path.join(self.root, "**", "R[0-9][0-9][0-9][0-9]"), recursive=True))
        if len({int(os.path.basename(d)[1:]) % 1000 for d in sdirs}) != len(sdirs):
            raise ValueError("subject numbers (R-number mod 1000) are not unique")
        for sdir in sdirs:
            pid = os.path.basename(sdir)
            for trial, (sample, cond, fname, idx, code) in enumerate(_trial_order(sdir, pid), 1):
                fg, bg = CODES[code]
                description = provenance(
                    "sw_trigger", TRIGGER_TYPE, NOTES, participant=pid, trigger_code=code,
                    onset_sample_raw_1khz=sample, epoch_file=os.path.basename(fname), epoch_index=idx,
                    attended=fg, ignored=bg, attended_talker=fg.split("_")[0], units_as_shipped="T", reference="not applicable (MEG)",
                    preprocessing="tSSS, FIR 1-40 Hz, decimated to 100 Hz (authors)")
                yield TrialRecord(
                    subject=int(pid[1:]) % 1000, session=1, trial=trial, condition=cond, ns_type="meg",
                    stimulus=_stimuli(stim_dir, fg, bg), neural_data_fn=_meg_loader(fname, idx, code, description))


def _one(pattern: str) -> str:
    """The single match of a recursive glob."""
    hits = glob.glob(pattern, recursive=True)
    if len(hits) != 1:
        raise FileNotFoundError(f"expected one match for {pattern}, found {hits}")
    return hits[0]


def _trial_order(sdir: str, pid: str) -> list[tuple[int, str, str, int, int]]:
    """(raw onset sample, condition, epoch file, index in file, code) of all 24 epochs, sorted by onset sample
    (presentation order; both files come from one recording, notes.md section 3)."""
    out = []
    for cond, (n_epochs, n_codes) in FILES.items():
        fname = os.path.join(sdir, f"{pid}-{cond}-epo.fif")
        events = mne.read_epochs(fname, preload=False, verbose="ERROR").events
        codes = events[:, 2].tolist()
        if (len(codes) != n_epochs or len(set(codes)) != n_codes
                or any((CODES[c][1] is not None) != (cond == "two_speakers") for c in codes)):
            raise ValueError(f"{fname}: unexpected events {codes}")
        out += [(int(s), cond, fname, i, int(c)) for i, (s, _, c) in enumerate(events)]
    return sorted(out, key=lambda t: t[0])


def _stimuli(stim_dir: str, fg: str, bg: str | None) -> list[StimulusRecord]:
    """Single talker; or attended talker, played mixture, ignored talker as played (in that order)."""
    attended = StimulusRecord("audio", fg, _audio(stim_dir, fg), is_attended=True)
    if bg is None:
        return [attended]
    return [attended, StimulusRecord("audio", f"{fg}_mix", _audio(stim_dir, f"{fg}_mix")),
            StimulusRecord("audio", f"{bg}_from1s", _audio(stim_dir, bg, mute=BG_START), is_attended=False)]


def _audio(stim_dir: str, name: str, mute: int = 0) -> Callable[[], dict]:
    """Loader of a 22.05 kHz int16 wav as float32 in [-1, 1), samples before `mute` set to 0."""
    def _load() -> dict:
        fs, x = wavfile.read(os.path.join(stim_dir, f"{name}.wav"))
        if fs != AUDIO_FS or x.dtype != np.int16 or x.ndim != 1:
            raise ValueError(f"{name}.wav: expected {AUDIO_FS} Hz mono int16")
        x = (x / 32768.0).astype(np.float32)
        x[:mute] = 0
        return {"fs": AUDIO_FS, "data": x[None, :]}

    return _load


@lru_cache(maxsize=2)
def _read(fname: str) -> mne.Epochs:
    """Shipped epochs, checked for 100 Hz, 6001 samples from t = 0."""
    epochs = mne.read_epochs(fname, preload=True, verbose="ERROR")
    if epochs.info["sfreq"] != FS or len(epochs.times) != N_TIMES or epochs.tmin != 0:
        raise ValueError(f"{fname}: unexpected rate or epoch length")
    return epochs


def _meg_loader(fname: str, idx: int, code: int, description: str) -> Callable[[], mne.io.BaseRaw]:
    """One epoch as Raw: gradiometers and reference magnetometers, shipped bads plus any zero-variance channel."""
    def _loader() -> mne.io.BaseRaw:
        epochs = _read(fname)
        if epochs.events[idx, 2] != code:
            raise ValueError(f"{fname}[{idx}]: code {epochs.events[idx, 2]}, expected {code}")
        lines = epochs.get_data(picks=[f"MISC {code - 159:03d}", OFFSET_LINE], item=idx)[0]
        active = np.abs(lines - np.median(lines, axis=1, keepdims=True)) > 2.5  # half the 5 V TTL swing
        expected = np.zeros_like(active)
        expected[0, 0] = expected[1, -1] = True
        if not (active == expected).all():  # onset line only at t = 0, offset line only at 60.00 s
            raise ValueError(f"{fname}[{idx}]: onset/offset trigger lines not at the epoch edges")
        picks = mne.pick_types(epochs.info, meg=True, ref_meg=True, exclude=[])
        info = mne.pick_info(epochs.info, picks)
        data = epochs.get_data(picks=picks, item=idx)[0]
        raw = mne.io.RawArray(data, info, verbose="ERROR")
        flat = [raw.ch_names[i] for i in np.flatnonzero(data.std(axis=1) == 0)]
        raw.info["bads"] = sorted(set(info["bads"]) | set(flat))
        raw.info["description"] = description
        return raw

    return _loader


ADAPTOR = Brodbeck2018Adaptor
