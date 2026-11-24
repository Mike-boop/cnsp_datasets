from __future__ import annotations

import csv
import functools
import json
import os
from collections import defaultdict
from typing import Callable, Iterable

import mne
import numpy as np
from mne.io import BaseRaw
from scipy.io import wavfile

from cnsp_datasets.datasets.broderick2019_natural.utils import multi_tier_dict_to_textgrid
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

BADS_JSON = os.path.join(os.path.dirname(__file__), "bads.json")  # "sub-XXX/<ns_type>" -> channels (notes 5)
AMP_JSON = os.path.join(os.path.dirname(__file__), "amp_steps.json")  # inter-amplifier steps (notes 6)
# paradigm -> (task in the BIDS file names, stimulus folder, stimulus name prefix, first trial number)
PARADIGMS = {"focus": ("speech~speech~focus", "synthesized_story_snippet", "synth", 1),
             "attend": ("speech~speech~attend", "real_story_snippet", "real", 21)}
START, END = 8, 9  # events.tsv trial start / end codes
POST_END_S = 1.0  # each shipped block runs 1 s past the end event (end event = attended wav end + 1 s)
SIDES = {2: "left", 3: "right"}  # attended_spk
TARGETS = {1: "human_name", 2: "animal_name", 4: "number", 5: "color", 6: "plant"}  # event_description.json
EAR = ["ELA", "ELB", "ELC", "ELE", "ELI", "ELT", "ERA", "ERB", "ERC", "ERE", "ERI", "ERT"]
# ns_type -> (channels of that amplifier in the .set, its reference channel: all zeros as shipped)
SYSTEMS = {"eeg": (slice(0, 32), "Fpz"), "ear-eeg": (EAR + ["EOG", "cRef"], "cRef")}
MASTOIDS = {"M1": "left mastoid", "M2": "right mastoid"}
VALIDATION_TIER = "low"  # notes 12 (both amplifiers)
TRIGGER = ("hardware (inferred: an audio trigger wav with pulses at speech onset and 1 s after the attended "
           "speech ends ships with every stimulus; not documented; trigger channel not shipped)")
NOTES = ("Trial = the authors' shipped block, from the trial-start event (the audio trigger at the onset of both "
         "wavs) to 1 s after the end event (the attended wav's end + 1 s; the end event is design-derived, "
         "identical in all subjects, so drift and sample losses are not estimable from it). Two TMSi Mobita "
         "amplifiers at 1 kHz, one file each: ns_type 'eeg' (32 scalp incl. M1/M2, reference Fpz) and 'ear-eeg' "
         "(12 in-ear + EOG, reference cRef); Fpz and cRef are the two halves of one combined electrode and are kept "
         "as all-zero channels (in bads). The ear amplifier is in sync with the scalp one to +-2 ms except for "
         "~10-16 ms steps in a few trials (amplifier_steps; which amplifier dropped samples is unknown; not "
         "corrected). Stimuli: both Danish TTS wavs as shipped (attended first), word timings as TextGrids.")


class Nguyen2025Adaptor:
    """
    Nguyen, Mikkelsen & Kidmose 2025 (Zenodo 8082867): two competing Danish TTS talkers (+-60 deg), simultaneous
    scalp and in-ear EEG on two TMSi Mobita amplifiers at 1 kHz, 24 participants. Yields the continuous-speech
    paradigms `focus` (trials 1-20) and `attend` (trials 21-60); each trial gives ns_type `eeg` and `ear-eeg` with
    the same stimuli. Condition `<focus|attend>-<left|right>` (attended loudspeaker). See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        with open(os.path.join(download_dir, "participants.tsv"), newline="", encoding="utf-8-sig") as f:
            self.participants = [p for p in csv.DictReader(f, delimiter="\t")
                                 if os.path.isdir(os.path.join(download_dir, p["participant_id"]))]
        with open(BADS_JSON) as f:
            self.bads = json.load(f)
        with open(AMP_JSON) as f:
            self.amp = json.load(f)

    def parse(self) -> Iterable[TrialRecord]:
        for p in self.participants:
            sub = p["participant_id"]
            electrodes = os.path.join(self.root, sub, "eeg", f"{sub}_space-CapTrak_electrodes.tsv")
            for paradigm, (task, folder, prefix, first) in PARADIGMS.items():
                base = os.path.join(self.root, sub, "eeg", f"{sub}_task-{task}")
                with open(f"{base}_events.json") as f:
                    trials = json.load(f)
                samples = defaultdict(list)
                with open(f"{base}_events.tsv", newline="") as f:
                    for e in csv.DictReader(f, delimiter="\t"):
                        samples[int(e["epoch"]), int(e["value"])].append(int(e["sample"]))
                for epoch, meta in enumerate(trials):
                    start, end = samples[epoch, START], samples[epoch, END]
                    if len(start) != 1 or len(end) != 1:
                        raise ValueError(f"{base}_events.tsv: epoch {epoch} has {len(start)} starts, {len(end)} ends")
                    att = meta["attended_stimulus"]
                    stimuli = []
                    for i in [att] + [i for i in range(len(meta["stimulies"])) if i != att]:
                        wav = os.path.join(self.root, meta["stimulies"][i])
                        if not wav.startswith(os.path.join(self.root, "stimuli", folder, "stimuli_")):
                            raise ValueError(f"{base}_events.json: unexpected stimulus {wav}")
                        stem = os.path.basename(wav)[len("stimuli_"):-len(".wav")]
                        name = f"{prefix}-{stem.replace(' ', '-').replace('_', '-')}"
                        tg = os.path.join(self.root, meta["trigger_log"][i])
                        stimuli += [StimulusRecord("audio", name, _audio_loader(wav), is_attended=i == att),
                                    StimulusRecord("audio", name, _textgrid_loader(tg), is_attended=i == att,
                                                   feature_name="textgrid")]
                    side = SIDES[meta["attended_spk"]]
                    trial = first + epoch
                    for ns_type, (chans, ref) in SYSTEMS.items():
                        scalp = ns_type == "eeg"
                        description = provenance(
                            "onset_only", TRIGGER, NOTES, validation_tier=VALIDATION_TIER, amplifier=ns_type,
                            paradigm=paradigm, source_epoch=epoch, block_start_sample=start[0],
                            attended=stimuli[0].name, ignored=stimuli[2].name, attended_side=side,
                            target_category=TARGETS.get(meta["attended_event"]),
                            amplifier_steps=self.amp["steps"].get(f"{sub}/{paradigm}/{trial}"),
                            amplifier_sync_assessable=sub not in self.amp["unassessable"],
                            sex=p["sex"], age=int(p["age"]), hand=p["hand"],
                            reference=f"{ref} (offline re-reference by the authors; kept as an all-zero channel)",
                            external_sensors=MASTOIDS if scalp else {},
                            units_as_shipped="uV (EEGLAB .set; channels.tsv says V), read into V by MNE",
                            positions="template (shipped electrodes.tsv, identical for all)" if scalp else "none",
                        )
                        yield TrialRecord(
                            subject=int(sub[4:]), session=1, trial=trial, condition=f"{paradigm}-{side}",
                            ns_type=ns_type, stimulus=stimuli,
                            neural_data_fn=_eeg_loader(f"{base}_eeg.set", start[0], end[0], chans, ref,
                                                       electrodes if scalp else None,
                                                       self.bads.get(f"{sub}/{ns_type}", []), description),
                        )


@functools.lru_cache(maxsize=1)
def _read_set(path: str) -> BaseRaw:
    """One paradigm's concatenated blocks (the .set embeds its data; < 0.6 GB), cached for its 2 x 20-40 trials."""
    return mne.io.read_raw_eeglab(path, preload=True, verbose="ERROR")  # uV -> V by MNE


def _electrodes(path: str) -> mne.channels.DigMontage:
    """Template positions from the shipped CapTrak electrodes.tsv."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        pos = {r["name"]: [float(r[k]) for k in "xyz"] for r in csv.DictReader(f, delimiter="\t") if r["x"] != "n/a"}
    return mne.channels.make_dig_montage(pos, nasion=[0, 0.095, 0], lpa=[-0.095, 0, 0], rpa=[0.095, 0, 0],
                                         coord_frame="head")


def _eeg_loader(path: str, start: int, end: int, chans: slice | list[str], ref: str, electrodes: str | None,
                bads: list[str], description: str) -> Callable[[], BaseRaw]:
    """Loader of one amplifier's channels for one block (start event to end event + 1 s)."""
    def _loader() -> BaseRaw:
        src = _read_set(path)
        sfreq = src.info["sfreq"]
        stop = end + round(POST_END_S * sfreq)
        if stop > src.n_times:
            raise ValueError(f"{path}: block {start}-{stop} past the end ({src.n_times})")
        names = src.ch_names[chans] if isinstance(chans, slice) else chans
        raw = mne.io.RawArray(src.get_data(picks=names, start=start, stop=stop), mne.create_info(
            names, sfreq, ["eog" if c == "EOG" else "misc" if c in MASTOIDS else "eeg" for c in names]),
            verbose="ERROR")
        if np.any(raw.get_data(picks=[ref])):
            raise ValueError(f"{path}: reference channel {ref} is not all zeros")
        if electrodes:
            raw.set_montage(_electrodes(electrodes), verbose="ERROR")
        raw.info["bads"] = [ref] + bads
        raw.info["description"] = description
        return raw
    return _loader


def _audio_loader(path: str) -> Callable[[], dict]:
    """Loader of one mono int16 wav as shipped (24 kHz)."""
    def _loader() -> dict:
        fs, x = wavfile.read(path)
        if x.dtype != np.int16 or x.ndim != 1:
            raise ValueError(f"{path}: expected mono int16")
        return {"fs": int(fs), "data": (x / 32768.0).astype(np.float32)[None, :]}
    return _loader


def _textgrid_loader(path: str) -> Callable[[], str]:
    """TextGrid of a stimulus' word timings (trigger_<n>.txt: code, onset ms, 0, offset ms, word; Latin-1).

    Tier `words` holds every word, tier `targets` (paradigm 3 only) the target words (codes 1-6) labelled by
    category. Rows ending before they start (two "-" rows in paradigm 4) are dropped.
    """
    def _loader() -> str:
        with open(path, encoding="latin-1") as f:
            rows = [line.rstrip("\r\n").split("\t") for line in f if line.strip()]
        words = [r for r in rows if r[2] == "0" and int(r[3]) > int(r[1])]
        tiers = {"words": words, "targets": [r for r in words if int(r[0]) in TARGETS]}
        return multi_tier_dict_to_textgrid({
            name: {"item": [TARGETS[int(r[0])] if name == "targets" else r[4] for r in tier],
                   "onset_s": [int(r[1]) / 1000 for r in tier], "offset_s": [int(r[3]) / 1000 for r in tier]}
            for name, tier in tiers.items() if tier})
    return _loader


ADAPTOR = Nguyen2025Adaptor
