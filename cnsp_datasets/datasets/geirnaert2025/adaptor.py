from __future__ import annotations

import csv
import os
from typing import Callable, Iterable

import mne
from mne.io import BaseRaw

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import mark_bads, read_wav
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

TASK = "selectiveAttention"
PRELISTEN_S = 5.0  # the wavs start with the 5 s prelisten; the EEG epoch starts at the trigger after it (notes 3)
# ns_type -> (channels of that amplifier in the .set, montage, external sensors)
SYSTEMS = {"eeg": (slice(0, 32), "standard_1020", ["M1", "M2"]), "ear-eeg": (slice(32, 64), None, ["Fp1-cr"])}
MISC = ("M1", "M2", "Fp1-cr")  # mastoids; shared frontal electrode of the ear amplifier (Fp2 for sub-04)
# per subject and amplifier (notes 5): flat (1-40 Hz SD < 0.5 uV), railing (> 1 mV) or > 10x its group's median SD
# after a median re-reference, in any trial (union over trials)
BADS = {
    ("sub-01", "eeg"): ["Fz"], ("sub-04", "eeg"): ["M2", "F8"], ("sub-07", "eeg"): ["M2"],
    ("sub-01", "ear-eeg"): ["ELC", "cEL2", "cEL3", "ERC", "ERT", "cER2"],
    ("sub-02", "ear-eeg"): ["ELB", "ELE", "ERA", "ERC", "ERE"], ("sub-04", "ear-eeg"): ["cER8"],
    ("sub-06", "ear-eeg"): ["ELC", "ERE"], ("sub-07", "ear-eeg"): ["ELB", "cEL1", "cEL2", "ERB", "cER2", "cER8"],
    ("sub-08", "ear-eeg"): ["ELC", "ELE", "cEL4"], ("sub-09", "ear-eeg"): ["cER4"], ("sub-11", "ear-eeg"): ["ELB"],
    ("sub-12", "ear-eeg"): ["ERA", "ERB", "ERC"], ("sub-14", "ear-eeg"): ["ELE", "ERE"],
    ("sub-15", "ear-eeg"): ["ELC", "ERC"],
}
SATURATED = {("sub-05", "ear-eeg", 5), ("sub-05", "ear-eeg", 6)}  # all 32 channels railing (SD ~3.6 V): all bad
# steps in the scalp-vs-ear amplifier lag from the shared frontal electrode (notes 6); which amplifier lost samples
# is unknown; not corrected
AMP_STEPS = {
    ("sub-04", 2): "-15 ms at ~95 s, again at ~485 s", ("sub-07", 1): "-16 ms at ~385 s",
    ("sub-07", 4): "+13 ms at ~275 s", ("sub-07", 6): "-15 ms at ~125-195 s",
    ("sub-12", 5): "possibly +7.5 ms at ~325 s",
}
AMP_UNASSESSABLE = {("sub-02", t) for t in (4, 5, 6)} | {("sub-09", t) for t in range(1, 7)} | {
    ("sub-12", t) for t in (1, 2, 3, 4, 6)}
NOTES = ("Trial = the authors' 600 s epoch, cut at the 2-bit audio trigger that the stimulus PC played 5 s into each "
         "605 s wav pair (paper: separate audio trigger channel); the trigger channel is not shipped, so onsets "
         "cannot be re-measured and drift is not estimable (fixed-length epochs). Stimulus = the shipped wav from "
         "5.000 s on (the prelisten is not in the EEG). Two TMSi Mobita amplifiers, one file each: ns_type 'eeg' "
         "(scalp + EOG) and 'ear-eeg' (in-ear + around-ear + the shared frontal electrode Fp1-cr). Each amplifier "
         "has its own common reference; shared ground CPz; the ear amplifier lags the scalp one by 0-2 ms (+2 ppm), "
         "with ~15 ms steps in a few trials (amplifier_steps). Bads per subject (notes 5).")


class Geirnaert2025Adaptor(BaseAdaptor):
    """
    Geirnaert, Kappel & Kidmose 2025 (Zenodo 16536441, Ear-SAAD): attend one of two Danish talkers (+-60 deg,
    HRTF), 15 subjects x 6 trials of 10 min, video of the attended talker in half the trials. Simultaneous scalp
    EEG (27 + M1/M2 + 3 EOG) and ear-EEG (12 in-ear, 19 around-ear, shared Fp1), two TMSi Mobita amplifiers, 1 kHz.

    Each trial gives two records with the same stimuli: ns_type `eeg` (scalp amplifier) and `ear-eeg` (ear
    amplifier). Stimuli `Speaker<k>Part<p>` (attended = Part1) as shipped (48 kHz stereo, L = R before HRTF) from
    5 s on. Condition `attend-<left|right>-<video|novideo>`. See notes.md.
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self.root = os.path.join(download_dir, "bids_dataset")
        with open(os.path.join(self.root, "participants.tsv"), newline="") as f:
            self.participants = list(csv.DictReader(f, delimiter="\t"))

    def parse(self) -> Iterable[TrialRecord]:
        for p in self.participants:
            sub = p["participant_id"]
            base = os.path.join(self.root, sub, "ses-01", "eeg", f"{sub}_ses-01_task-{TASK}")
            with open(f"{base}_events.tsv", newline="") as f:
                events = list(csv.DictReader(f, delimiter="\t"))
            for trial, ev in enumerate(events, 1):
                left, right = (s.removesuffix(".wav") for s in ev["stim_file"].split(";"))
                side = ev["attended_ear"]
                attended = left if side == "left" else right
                if ev["trial_type"] != f"trial{trial}" or not attended.startswith(ev["attended_speaker"]):
                    raise ValueError(f"{base}_events.tsv: unexpected row {ev}")
                video, onset = ev["video_condition"] == "yes", float(ev["onset"])
                stimuli = [StimulusRecord("audio", name, _audio_loader(self.root, name), is_attended=name == attended,
                                          feature_name="audio") for name in (left, right)]
                for ns_type, (chans, montage, external) in SYSTEMS.items():
                    saturated = (sub, ns_type, trial) in SATURATED
                    description = provenance(
                        "onset_only", "hardware (paper: audio trigger from a separate sound-card channel; trigger "
                        "channel not shipped)", NOTES, validation_tier=None, amplifier=ns_type,
                        epoch_onset_s=onset, stimulus_start_in_wav_s=PRELISTEN_S,
                        left=left, right=right, attended_side=side, video=video,
                        sex=p["sex"], age=int(p["age"]),
                        reference="amplifier common reference (TMSi Mobita; not a recorded channel)",
                        shared_electrode="Fp2" if sub == "sub-04" else "Fp1", amplifier_saturated=saturated,
                        amplifier_steps=AMP_STEPS.get((sub, trial)),
                        amplifier_sync_assessable=(sub, trial) not in AMP_UNASSESSABLE,
                        external_sensors=external, units_as_shipped="uV (EEGLAB .set), read into V",
                        positions="template (standard_1020)" if montage else "none",
                    )
                    yield TrialRecord(
                        subject=int(sub[4:]), session=1, trial=trial,
                        condition=f"attend-{side}-{'video' if video else 'novideo'}",
                        ns_type=ns_type, stimulus=stimuli,
                        neural_data_fn=_eeg_loader(f"{base}_eeg.set", onset, float(ev["duration"]), chans,
                                                   montage, None if saturated else BADS.get((sub, ns_type), []),
                                                   description),
                    )


def _audio_loader(root: str, name: str) -> Callable[[], dict]:
    """Loader of one stereo wav from the end of the 5 s prelisten on (float32 in [-1, 1))."""
    path = os.path.join(root, "stimuli", f"{name}.wav")

    def _loader() -> dict:
        x, fs = read_wav(path)
        if x.shape[0] != 2:
            raise ValueError(f"{path}: expected stereo, got {x.shape[0]} channels")
        return {"fs": fs, "data": x[:, round(PRELISTEN_S * fs):].copy()}
    return _loader


def _eeg_loader(path: str, onset: float, duration: float, chans: slice, montage: str | None,
                bads: list[str] | None, description: str) -> Callable[[], BaseRaw]:
    """Loader of one amplifier's channels for one trial; bads None = all channels bad."""
    def _loader() -> BaseRaw:
        raw = mne.io.read_raw_eeglab(path, preload=False, verbose="ERROR")  # uV -> V by MNE
        sfreq = raw.info["sfreq"]
        i0, n = round(onset * sfreq), round(duration * sfreq)
        raw.crop(i0 / sfreq, (i0 + n) / sfreq, include_tmax=False)
        raw.pick(raw.ch_names[chans]).load_data(verbose="ERROR")
        raw.set_annotations(None)
        raw.set_channel_types({c: "misc" for c in MISC if c in raw.ch_names}
                              | {c: "eog" for c in raw.ch_names if c.startswith("EOG")}, on_unit_change="ignore")
        raw.set_montage(montage, on_missing="ignore")  # the .set has no positions (all NaN)
        mark_bads(raw, raw.ch_names if bads is None else bads)
        raw.info["description"] = description
        return raw
    return _loader


ADAPTOR = Geirnaert2025Adaptor
