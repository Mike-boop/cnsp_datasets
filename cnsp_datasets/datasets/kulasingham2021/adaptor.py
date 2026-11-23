from __future__ import annotations

import csv
import glob
import io
import itertools
import os
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np

from cnsp_datasets.datasets.simon_base.common import (REFERENCE, audio_loader, check_unique_subjects, epoch_raw,
                                                      find_one, read_epochs, read_wav, subject_number)
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 200             # shipped epochs: TSPCA, SNS, FIR band-pass, ICA, decimated to 200 Hz by the authors
N_TIMES = 4000       # 0 .. 19.995 s: the 18 s stimulus and 2 s after it
AUDIO_FS = 22050
STIM_END = 18.0      # s; end-of-stimulus pulse on END_LINE (notes.md section 6)
END_LINE, NO_LINE, YES_LINE = "MISC 014", "MISC 024", "MISC 025"
NO_END_PULSE = {("R2570", "cocktail_party", 35)}  # (subject, file, 0-based epoch) without an end pulse
FILES = {"single_speaker": 10, "cocktail_party": 6}  # trials per block
BLOCKS = {"single_speaker": ["01jamesMATH", "02jamesLANG", "03kateMATH", "04kateLANG"],
          "cocktail_party": ["05kateLANG", "06kateMATH", "07jamesLANG", "08jamesMATH",
                             "09kateLANG", "10kateMATH", "11jamesLANG", "12jamesMATH"]}
FEMALE_FIRST_ORDER = {"single_speaker": [2, 3, 0, 1], "cocktail_party": [2, 3, 0, 1, 6, 7, 4, 5]}
# readme: female first (R2567 is listed but not shipped); R2522 is male first in the readme, female first by its
# button presses and the MEG (notes.md section 3)
FEMALE_FIRST = {"R2522", "R2569", "R2570", "R2573", "R2575", "R2578", "R2581", "R2583", "R2586", "R2587", "R2589"}
ORDER_FROM_DATA = {"R2522"}
OTHER_VOICE = {"james": "kate", "kate": "james"}
OTHER_TASK = {"equations": "sentences", "sentences": "equations"}
TRIGGER_TYPE = "unknown (paper silent; TTL lines recorded by the KIT system)"
NOTES = ("Authors' preprocessed KIT 157-channel MEG epochs (DRUM): TSPCA, SNS, FIR band-pass (0.3-40 Hz; 0.3-30 Hz "
         "in most single-speaker files, see `preprocessing`), ICA, decimated to "
         "200 Hz; axial gradiometers as `mag`, 3 reference magnetometers as `ref_meg`, T. Raw data were not "
         "released. t = 0 is the authors' epoch start = stimulus onset (evoked onset response at 75-120 ms); the "
         "end-of-stimulus pulse (MISC 014) is at 18.00 s. No drift correction (not measurable). MISC and STI "
         "dropped. Cocktail trials: attended stream (fg, is_attended), the played mixture and the ignored stream "
         "(bg); fg/bg are unscaled, the mixture = mix_gain x (fg + bg).")


class Kulasingham2021Adaptor:
    """
    Kulasingham, Joshi, Rezaeizadeh & Simon 2021 (DRUM 10.13016/xd2i-vyke): 22 listeners, KIT MEG, synthesised
    isochronous 4-word sentences and 5-symbol equations (voices "james" and "kate"), 18 s trials. Per subject 40
    single-speaker trials, then 48 two-talker trials (attend sentences or equations), in presentation order.
    Subject = R-number mod 1000 (R2522 -> 522). Shipped neural data are the authors' preprocessed 200 Hz epochs.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir

    def parse(self) -> Iterable[TrialRecord]:
        stim_dir = os.path.dirname(find_one(os.path.join(self.root, "**", "stimuli", "single_speaker_stimuli")))
        sdirs = sorted(glob.glob(os.path.join(self.root, "**", "R[0-9][0-9][0-9][0-9]"), recursive=True))
        check_unique_subjects(os.path.basename(d) for d in sdirs)
        for sdir in sdirs:
            pid = os.path.basename(sdir)
            female_first = pid in FEMALE_FIRST
            trial = 0
            for kind, n in FILES.items():
                fname = os.path.join(sdir, f"{pid}_{kind}_meg-epo.fif")
                order = FEMALE_FIRST_ORDER[kind] if female_first else range(len(BLOCKS[kind]))
                single = kind == "single_speaker"
                for idx, (b, k) in enumerate(itertools.product(order, range(n))):
                    trial += 1
                    block = BLOCKS[kind][b]
                    voice, task = block[2:-4], "equations" if block.endswith("MATH") else "sentences"
                    items, deviant = _items(stim_dir, kind, block, k)
                    meta = dict(
                        participant=pid, block_order="female_first" if female_first else "male_first",
                        block_order_source=("button presses and MEG decoding (readme: male_first)"
                                            if pid in ORDER_FROM_DATA else "readme"),
                        block=block, block_trial=k, epoch_file=os.path.basename(fname), epoch_index=idx,
                        attended_voice=voice, attended_task=task,
                        ignored_voice=None if single else OTHER_VOICE[voice],
                        ignored_task=None if single else OTHER_TASK[task],
                        attended_items=items, deviant_items=deviant, deviant_trial=any(deviant),
                        mix_gain=None if single else _mix_gain(stim_dir, block, k),
                        stimulus_end_s=STIM_END, units_as_shipped="T", reference=REFERENCE)
                    yield TrialRecord(
                        subject=subject_number(pid), session=1, trial=trial,
                        condition=f"single_{task}" if single else f"cocktail_attend_{task}", ns_type="meg",
                        stimulus=_stimuli(stim_dir, kind, block, k),
                        neural_data_fn=_meg_loader(fname, idx, (pid, kind, idx) in NO_END_PULSE, meta))


@lru_cache(maxsize=None)
def _wav(stim_dir: str, kind: str, block: str, k: int, stream: str = "") -> str:
    """Path of a trial wav; block 10kateMATH names its files `<stream>_block0_trial<k>.wav`."""
    prefix = f"{stream}_" if stream else ""
    return find_one(os.path.join(stim_dir, f"{kind}_stimuli", block, f"{prefix}*trial{k:02d}.wav"))


@lru_cache(maxsize=None)
def _block_items(stim_dir: str, kind: str, block: str) -> list[dict]:
    """Rows of a block's trials.csv (old-Mac CR line endings)."""
    with open(os.path.join(stim_dir, f"{kind}_stimuli", block, "trials.csv"), newline="") as f:
        text = f.read().replace("\r\n", "\n").replace("\r", "\n")
    return list(csv.DictReader(io.StringIO(text)))


def _items(stim_dir: str, kind: str, block: str, k: int) -> tuple[list[str], list[bool]]:
    """Attended sentences/equations of trial k in order (e.g. "4=3+1", "frogs croak all night") and deviant flags."""
    rows = [r for r in _block_items(stim_dir, kind, block) if int(r["trial"]) == k]
    names = [r["sent"].removesuffix(".wav").split("_", 1)[-1] for r in rows]
    if block.endswith("LANG"):
        names = [n.replace("-", " ") for n in names]
    return names, [r["deviant"] == "1" for r in rows]


@lru_cache(maxsize=None)
def _mix_gain(stim_dir: str, block: str, k: int) -> float:
    """Least-squares g in mix = g (fg + bg) (notes.md section 3)."""
    mix, fg, bg = (read_wav(_wav(stim_dir, "cocktail_party", block, k, s), AUDIO_FS) for s in ("mix", "fg", "bg"))
    both = fg + bg
    return round(float(both @ mix / (both @ both)), 5)


def _stimuli(stim_dir: str, kind: str, block: str, k: int) -> list[StimulusRecord]:
    """Single talker; or attended stream, played mixture, ignored stream (in that order)."""
    def audio(stream: str = "") -> Callable[[], dict]:
        return audio_loader(_wav(stim_dir, kind, block, k, stream), AUDIO_FS)

    if kind == "single_speaker":
        return [StimulusRecord("audio", f"{block}_trial{k:02d}", audio(), is_attended=True)]
    return [StimulusRecord("audio", f"{block}_{s}_trial{k:02d}", audio(s), is_attended=att)
            for s, att in (("fg", True), ("mix", False), ("bg", False))]


def _read(fname: str) -> mne.Epochs:
    """Shipped epochs, checked for 200 Hz, 4000 samples from t = 0, all epochs in recording order."""
    epochs = read_epochs(fname, FS, N_TIMES)
    kind = "single_speaker" if "single_speaker" in os.path.basename(fname) else "cocktail_party"
    if len(epochs) != FILES[kind] * len(BLOCKS[kind]) or not np.all(np.diff(epochs.events[:, 0]) > 0):
        raise ValueError(f"{fname}: unexpected number or order of epochs")
    return epochs


def _pulses(line: np.ndarray) -> np.ndarray:
    """Times (s) at which an active-low TTL line (5 V idle) goes below 2.5 V."""
    low = (line < 2.5).astype(int)
    return (np.flatnonzero(np.diff(low) == 1) + 1) / FS


def _meg_loader(fname: str, idx: int, no_end: bool, meta: dict) -> Callable[[], mne.io.BaseRaw]:
    """One epoch as Raw (MEG + ref_meg, de-duplicated bads), end pulse checked, button presses in the sidecar."""
    def _loader() -> mne.io.BaseRaw:
        epochs = _read(fname)
        end, no, yes = epochs.get_data(picks=[END_LINE, NO_LINE, YES_LINE], item=idx)[0]
        end_t = _pulses(end)
        if no_end != (len(end_t) == 0) or not np.all(np.abs(end_t - STIM_END) < 0.01):
            raise ValueError(f"{fname}[{idx}]: end pulse at {end_t}, expected {STIM_END} s")
        presses = sorted([(round(t, 3), "no") for t in _pulses(no)] + [(round(t, 3), "yes") for t in _pulses(yes)])
        after = [p for p in presses if p[0] > STIM_END - 0.01]
        raw = epoch_raw(epochs, idx)
        raw.info["description"] = provenance(
            "onset_only", TRIGGER_TYPE, NOTES, validation_tier="low", **meta,
            preprocessing=(f"TSPCA, SNS, FIR {raw.info['highpass']:.1f}-{raw.info['lowpass']:.0f} Hz, ICA, "
                           "decimated to 200 Hz (authors)"),
            end_pulse_first_low_sample_s=float(end_t[0]) if len(end_t) else None,
            button_presses_s=presses, response=after[0][1] if after else None,
            response_time_after_end_s=round(after[0][0] - STIM_END, 3) if after else None)
        return raw

    return _loader


ADAPTOR = Kulasingham2021Adaptor
