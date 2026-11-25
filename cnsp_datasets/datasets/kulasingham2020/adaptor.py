from __future__ import annotations

import csv
import glob
import os
import re
from typing import Callable, Iterable

import mne

from cnsp_datasets.datasets.simon_base.common import (REFERENCE, audio_loader, check_unique_subjects, crop_meg,
                                                      find_one, read_raw, rms_bads, stim_events, subject_number,
                                                      wav_samples)
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 1000
AUDIO_FS = 44100
N_REP = 3
# Block (= wav name) -> (STI 014 onset code, i.e. the 0-based channel index of MISC 007 / 012, identical
# presacco2016 wav). Offset code 163 (MISC 004).
BLOCKS = {"Trial1": (166, "Quiet_H"), "Trial2": (171, "Quiet_L")}
OFFSET_CODE = 163
FLAT_RATIO = 20  # gradiometer rms below median / 20 (all-zero or near-flat) -> bad (notes.md section 5)
# Channels dead (all-zero) in both of presacco2016's raw quiet blocks that SNS refilled here, unlisted (notes.md
# section 5); marked bad in both blocks.
REFILLED = {"R2185": (62,), "R2079": (62,), "R2230": (62,), "R2210": (62,), "R2201": (62, 157),
            "R2254": (1, 2), "R2084": (99,)}
SUBJECTS = ("all", "unique")
TRIGGER_TYPE = "unknown (TTL lines recorded by the KIT system; whether locked to the sound is not documented)"
PREPROCESSING = "denoised by the authors: saturating channels zeroed, TSPCA (reference regression) and SNS"
NOTES = ("Continuous KIT 157-channel MEG (axial gradiometers as `mag`, 3 reference magnetometers as `ref_meg`), "
         "1000 Hz, T, as shipped: denoised by the authors (TSPCA + SNS), not raw. t = 0 is the onset-trigger edge "
         "(STI 014 code 166 / 171); 60 s per repetition. Offset trigger (code 163) comes 59,997-59,998 samples after "
         "the onset in every repetition (-37.5 ppm drift or an early end pulse; not applied). Sensor positions in "
         "KIT device coordinates, dev_head_t identity, no digitisation. MISC lines and STI 014 dropped. Bads: "
         "bad_channels.txt + flat/zero gradiometers + channels dead in presacco2016's raw recordings and refilled by "
         "SNS here. 32 of the 40 participants are presacco2016's quiet blocks (same recordings): see overlaps_with.")


class Kulasingham2020Adaptor(BaseAdaptor):
    """
    High-gamma TRF dataset of Kulasingham et al. (2020, NeuroImage; DRUM doi:10.13016/33pk-ltqh): KIT MEG of 17
    younger and 23 older normal-hearing adults listening to two 60 s audiobook segments in quiet, each repeated 3
    times (trials 1-3 = Trial1.wav, 4-6 = Trial2.wav). Subject = full R-number. 32 participants are presacco2016's
    quiet blocks (`subject_map.tsv`); `subjects="unique"` keeps only the 8 that are not. See notes.md.
    """

    def __init__(self, download_dir: str, subjects: str = "all"):
        super().__init__(download_dir)
        self.root = download_dir
        self.subjects = self.choice("subjects", subjects, SUBJECTS)

    def parse(self) -> Iterable[TrialRecord]:
        stim_dir = os.path.dirname(find_one(os.path.join(self.root, "**", "Trial1.wav")))
        listed = _listed_bads(find_one(os.path.join(self.root, "**", "bad_channels.txt")))
        overlap = _subject_map()
        paths = sorted(glob.glob(os.path.join(self.root, "**", "*_MEG", "*_R*_Trial[12]-raw.fif"), recursive=True))
        by_pid = {}
        for path in paths:
            group, pid, block = re.fullmatch(r"(Younger|Older)_(R\d+)_(Trial[12])-raw\.fif",
                                             os.path.basename(path)).groups()
            if block in by_pid.setdefault(pid, {}):
                raise ValueError(f"two files for {pid} {block}: {by_pid[pid][block][1]}, {path}")
            by_pid[pid][block] = (group, path)
        check_unique_subjects(by_pid)
        if set(by_pid) != set(overlap):
            raise ValueError(f"participants differ from subject_map.tsv: {sorted(set(by_pid) ^ set(overlap))}")
        for pid, blocks in by_pid.items():
            if {g.lower() for g, _ in blocks.values()} != {overlap[pid][1]}:
                raise ValueError(f"{pid}: age group in the file names differs from subject_map.tsv")
        for pid in sorted(by_pid, key=subject_number):
            if self.subjects == "unique" and overlap[pid][0]:
                continue
            for b, (block, (code, twin)) in enumerate(BLOCKS.items()):
                group, path = by_pid[pid][block]
                raw = read_raw(path, FS)
                onsets = (stim_events(raw, [code])[:, 0] - raw.first_samp).tolist()
                if len(onsets) != N_REP:
                    raise ValueError(f"{path}: {len(onsets)} onset triggers, expected {N_REP}")
                wav = os.path.join(stim_dir, f"{block}.wav")
                stimulus = [StimulusRecord("audio", block, audio_loader(wav, AUDIO_FS), is_attended=True)]
                extra_bads = sorted(set(listed.get((pid, block), ())) | set(REFILLED.get(pid, ())))
                for rep, onset in enumerate(onsets):
                    description = provenance(
                        "onset_only", TRIGGER_TYPE, NOTES, participant=pid, age_group=group.lower(),
                        hearing="normal", file=os.path.basename(path), block=block, repetition=rep + 1,
                        onset_trigger_code=code, offset_trigger_code=OFFSET_CODE, onset_s=onset / FS,
                        block_recorded=raw.info["meas_date"].isoformat(), stimulus_file=f"{block}.wav",
                        identical_stimulus=f"presacco2016 {twin}",
                        overlaps_with=f"presacco2016 {overlap[pid][0]}" if overlap[pid][0] else None,
                        units_as_shipped="T", reference=REFERENCE, preprocessing=PREPROCESSING)
                    yield TrialRecord(
                        subject=subject_number(pid), session=1, trial=N_REP * b + rep + 1, condition="quiet",
                        ns_type="meg", stimulus=stimulus,
                        neural_data_fn=_meg_loader(path, onset, wav_samples(wav, AUDIO_FS, FS), description,
                                                   [f"MEG {c:03d}" for c in extra_bads]))


def _listed_bads(path: str) -> dict:
    """{(participant, block): 1-based MEG numbers} from bad_channels.txt (`R2084,Trial1,111,146,`)."""
    out = {}
    with open(path) as f:
        for row in csv.reader(f):
            if row:
                out[row[0], row[1]] = tuple(int(c) for c in row[2:] if c.strip())
    return out


def _subject_map() -> dict:
    """{participant: (presacco2016 subject ('S12 Younger') or '', age group)} from subject_map.tsv next to this file."""
    with open(os.path.join(os.path.dirname(__file__), "subject_map.tsv")) as f:
        return {r["participant"]: (r["presacco2016_subject"], r["age_group"])
                for r in csv.DictReader(f, delimiter="\t")}


def _meg_loader(path: str, onset: int, n_out: int, description: str,
                extra_bads: list[str]) -> Callable[[], mne.io.BaseRaw]:
    """Trial from the onset trigger; bads = flat/zero gradiometers + `extra_bads`."""
    def _loader():
        bads = sorted(set(rms_bads(path, FS, FLAT_RATIO)) | set(extra_bads))
        return crop_meg(read_raw(path, FS), onset, n_out, description, bads)

    return _loader


ADAPTOR = Kulasingham2020Adaptor
