from __future__ import annotations

import glob
import os
from typing import Callable, Iterable

import mne
import numpy as np

from cnsp_datasets.datasets.simon_base.common import (REFERENCE, audio_loader, check_unique_subjects, epoch_raw,
                                                      find_one, read_epochs, subject_number)
from cnsp_datasets.standardise.adaptor import BaseAdaptor
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


class Brodbeck2018Adaptor(BaseAdaptor):
    """
    Brodbeck, Hong & Simon 2018 (DRUM 10.13016/M2ZC7RZ0F): 26 listeners, KIT MEG, Dickens audiobook (LibriVox),
    one male and one female talker. Per subject 24 one-minute trials in presentation order: 4 two-talker mixtures
    x 4 repetitions (`two_speakers`, attend one talker, counterbalanced) and the 8 single talkers once
    (`single_speaker`). Subject = full R-number (R2262 -> 2262). Shipped neural data are the authors'
    preprocessed 100 Hz epochs. Stimuli: 22.05 kHz wavs as shipped (see notes.md).
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self.root = download_dir

    def parse(self) -> Iterable[TrialRecord]:
        stim_dir = os.path.dirname(find_one(os.path.join(self.root, "**", "stimuli", "male_1.wav")))
        sdirs = sorted(glob.glob(os.path.join(self.root, "**", "R[0-9][0-9][0-9][0-9]"), recursive=True))
        check_unique_subjects(os.path.basename(d) for d in sdirs)
        for sdir in sdirs:
            pid = os.path.basename(sdir)
            for trial, (sample, cond, fname, idx, code) in enumerate(_trial_order(sdir, pid), 1):
                fg, bg = CODES[code]
                description = provenance(
                    "sw_trigger", TRIGGER_TYPE, NOTES, participant=pid, trigger_code=code,
                    onset_sample_raw_1khz=sample, epoch_file=os.path.basename(fname), epoch_index=idx,
                    attended=fg, ignored=bg, attended_talker=fg.split("_")[0], units_as_shipped="T",
                    reference=REFERENCE, preprocessing="tSSS, FIR 1-40 Hz, decimated to 100 Hz (authors)")
                yield TrialRecord(
                    subject=subject_number(pid), session=1, trial=trial, condition=cond, ns_type="meg",
                    stimulus=_stimuli(stim_dir, fg, bg), neural_data_fn=_meg_loader(fname, idx, code, description))


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
    def audio(name: str, mute: int = 0) -> Callable[[], dict]:
        return audio_loader(os.path.join(stim_dir, f"{name}.wav"), AUDIO_FS, mute)

    attended = StimulusRecord("audio", fg, audio(fg), is_attended=True)
    if bg is None:
        return [attended]
    return [attended, StimulusRecord("audio", f"{fg}_mix", audio(f"{fg}_mix")),
            StimulusRecord("audio", f"{bg}_from1s", audio(bg, mute=BG_START), is_attended=False)]


def _meg_loader(fname: str, idx: int, code: int, description: str) -> Callable[[], mne.io.BaseRaw]:
    """One epoch as Raw: gradiometers and reference magnetometers, shipped bads plus any zero-variance channel."""
    def _loader() -> mne.io.BaseRaw:
        epochs = read_epochs(fname, FS, N_TIMES)
        if epochs.events[idx, 2] != code:
            raise ValueError(f"{fname}[{idx}]: code {epochs.events[idx, 2]}, expected {code}")
        lines = epochs.get_data(picks=[f"MISC {code - 159:03d}", OFFSET_LINE], item=idx)[0]
        active = np.abs(lines - np.median(lines, axis=1, keepdims=True)) > 2.5  # half the 5 V TTL swing
        expected = np.zeros_like(active)
        expected[0, 0] = expected[1, -1] = True
        if not (active == expected).all():  # onset line only at t = 0, offset line only at 60.00 s
            raise ValueError(f"{fname}[{idx}]: onset/offset trigger lines not at the epoch edges")
        raw = epoch_raw(epochs, idx)
        raw.info["description"] = description
        return raw

    return _loader


ADAPTOR = Brodbeck2018Adaptor
