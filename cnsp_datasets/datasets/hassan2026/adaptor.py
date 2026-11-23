from __future__ import annotations

import json
import os
from typing import Callable, Iterable, List

import numpy as np
import pandas as pd
import soundfile as sf
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray

from cnsp_datasets.datasets.hassan2026.bads import BADS_JSON
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

EEG_FS, AUDIO_FS = 500.0, 16000
MASTOIDS = ("M1", "M2")
DRIFT_PPM = 9.0  # amplifier vs host clock, median of 16 subjects (notes 6a); not corrected
# The sound reaches the EEG 0.718 s after the earliest playback timestamp (brain-based, notes.md section 6e; applied
# by default, rule in CLAUDE.md): pooled accou2023 DNN offset -718 ms (negative = EEG late; 95% CI -719..-717, 16
# subjects, 1,600 trials), the same for trials attended on device 1 and 2; per-subject values -703..-723 ms, not
# reliably different, so one constant.
ONSET_CORRECTION_S = 0.718
BLOCK2_START = "eval_050"  # first trial after the longest break in 12 of 16 subjects (notes 3)
UNITS = ("raw ADC per the card; values are volts (+-2^23 x 1e-8 clip, 1-40 Hz RMS 5-19 uV, alpha peak; notes 5), "
         "kept unscaled")
NOTES = ("Onset = align.anchor_unix (earliest audio playback-start timestamp) - eeg.first_sample_unix (LSL) + "
         "onset_correction_s (see onset_correction_method; the sound reaches the EEG ~0.72 s after the playback "
         "timestamp, notes.md section 6e); software timestamps on one host clock (paper II-D). With the correction, "
         "the last ~0.4 s of each stimulus has no EEG. All six loudspeaker streams share the onset: the "
         "per-device playback timestamps (0/+80/+160 ms) are not applied, because the scene microphone and the EEG "
         "show devices 1 and 2 sounding together (notes.md section 6). EEG clock vs host clock ~+9 ppm, not "
         "corrected (0.27 ms per 30 s trial). Original amplifier reference (CPz, inferred).")
DNN_METHOD = ("brain-based, constant: accou2023 match-mismatch DNN offset of the attended talker, pooled over 16 "
              "subjects (notes.md section 6e; circular: estimated from this EEG); may include ~15 ms of "
              "speech-in-noise response latency")
COMPREHENSION_NOTE = "comprehension_correct is False for all 1,600 evaluation trials as shipped (upstream issue)"


class Hassan2026Adaptor:
    """
    Hassan 2026 MAESTRO (Hugging Face aspire-osu/maestro-eeg-dataset): 16 listeners (S01-S16), 5 training + 100
    evaluation trials of 30 s, 4 LibriSpeech talkers (speakers 1-4, attendable) + 2 CHiME-Home noise sources
    (speakers 5-6) on 6 loudspeakers; 32-ch ANT eego at 500 Hz, shipped per trial (parquet) with unix timestamps.

    Trial = presentation position (1-105, the same order for all subjects); condition = the authors' kind
    (`training`, `main`). The EEG is cropped at the stimulus onset and runs to the end of the shipped trial: onset
    = earliest playback timestamp + ONSET_CORRECTION_S (onset="dnn", default; ~29.6 s of EEG) or the timestamp
    alone (onset="none", ~30.3 s); notes.md section 6. Stimuli: the six 16 kHz FLACs, named
    `<trial_id>_speaker<k>`, the attended talker flagged. M1/M2 are `misc`. Gaze, IMU and video are not included.
    """

    def __init__(self, download_dir: str, onset: str = "dnn"):
        if onset not in ("dnn", "none"):
            raise ValueError(f"onset must be 'dnn' or 'none', not {onset!r}")
        self.method = "dnn" if onset == "dnn" else "sw_trigger"
        self.onset = (dict(onset_correction_s=ONSET_CORRECTION_S, onset_correction_method=DNN_METHOD) if onset == "dnn"
                      else dict(onset_correction_s=0.0, onset_correction_method="none (earliest playback timestamp)"))
        self.root = os.path.join(download_dir, "maestro-eeg-dataset")
        meta = os.path.join(self.root, "metadata")
        self.subjects = pd.read_csv(os.path.join(meta, "subjects.csv"))["subject_id"].tolist()
        self.trials = pd.read_csv(os.path.join(meta, "trials.csv")).set_index("trial_id")
        scores = pd.read_csv(os.path.join(meta, "trials_per_subject.csv"))
        self.correct = scores.set_index(["subject_id", "trial_id"])["comprehension_correct"]
        with open(os.path.join(meta, "audio_manifest.json")) as f:
            self.manifest = json.load(f)
        with open(os.path.join(meta, "audio_layout.json")) as f:
            self.azimuth = {s["speaker"]: s["azimuth_deg"] for s in json.load(f)["speakers"]}
        with open(os.path.join(meta, "eeg_channels.json")) as f:
            self.channels = json.load(f)["channels"]
        self.types = ["misc" if c in MASTOIDS else "eeg" for c in self.channels]
        with open(BADS_JSON) as f:
            self.bads = json.load(f)

    def parse(self) -> Iterable[TrialRecord]:
        for subject in self.subjects:
            # presentation order = order of the EEG first-sample timestamps
            timings = sorted((self._timing(subject, t) for t in self.trials.index),
                             key=lambda j: j["eeg"]["first_sample_unix"])
            block = 1
            for pos, j in enumerate(timings, 1):
                tid = j["trial_id"]
                if tid == BLOCK2_START:
                    block = 2  # paper: two sessions; longest break before eval_050 in 12 of 16 subjects (notes 3)
                lead = j["align"]["anchor_unix"] - j["eeg"]["first_sample_unix"]
                onset = round((lead + self.onset["onset_correction_s"]) * EEG_FS)
                yield TrialRecord(
                    subject=int(subject[1:]), session=1, trial=pos, condition=j["kind"], ns_type="eeg",
                    stimulus=self._stimuli(tid),
                    neural_data_fn=self._eeg_loader(subject, tid, onset, self._description(subject, j, onset, block)),
                )

    def _timing(self, subject: str, trial_id: str) -> dict:
        path = os.path.join(self.root, "media", "timing", f"subject={subject}", f"trial={trial_id}.json")
        with open(path) as f:
            return json.load(f)

    def _description(self, subject: str, j: dict, onset: int, block: int) -> str:
        tid, row = j["trial_id"], self.trials.loc[j["trial_id"]]
        att, anchor = int(row["attended_speaker"]), j["align"]["anchor_unix"]
        correct = self.correct.get((subject, tid))
        # keyed by device_id_raw: its mapping to devices 1-3 of the FLAC names is not documented (notes 6a)
        offsets = {str(d["device_id_raw"]): round(1e3 * (d["playback_start_unix"] - anchor), 1)
                   for d in j["audio"]["devices"]}
        return provenance(
            self.method,
            "software (paper: LSL first-sample and playback-start unix timestamps, one host clock)",
            f"{NOTES} {COMPREHENSION_NOTE}.", drift_ppm=DRIFT_PPM, validation_tier="low",
            participant=subject, trial_id=tid, block=block, attended_speaker=att,
            hemisphere_attended=row["hemisphere_attended"], inout_attended=row["inout_attended"],
            azimuth_attended_deg=self.azimuth[att], snr_db=float(row["snr_db"]),
            comprehension_correct=None if pd.isna(correct) else bool(correct), onset_sample=onset,
            playback_offsets_ms_by_raw_device=offsets, **self.onset,
            units_as_shipped=UNITS, reference="amplifier reference (CPz, inferred; not shipped)",
            external_sensors={"M1": "left mastoid", "M2": "right mastoid"},
        )

    def _stimuli(self, trial_id: str) -> List[StimulusRecord]:
        attended = int(self.trials.loc[trial_id, "attended_speaker"])
        return [StimulusRecord("audio", f"{trial_id}_speaker{k}",
                               _audio_loader(os.path.join(self.root, "media", "audio", trial_id, fname)),
                               is_attended=int(k) == attended)
                for k, fname in sorted(self.manifest[trial_id].items())]

    def _eeg_loader(self, subject: str, trial_id: str, onset: int, description: str) -> Callable[[], BaseRaw]:
        path = os.path.join(self.root, "data", "eeg", f"subject={subject}", f"trial={trial_id}.parquet")

        def _loader() -> BaseRaw:
            df = pd.read_parquet(path)
            x = df[[f"ch_{c}" for c in self.channels]].to_numpy(np.float64).T[:, onset:]  # volts as shipped
            raw = RawArray(x, create_info(self.channels, EEG_FS, self.types), verbose="ERROR")
            raw.set_montage(make_standard_montage("standard_1020"), verbose="ERROR")
            raw.info["bads"] = list(self.bads.get(subject, []))
            raw.info["description"] = description
            return raw
        return _loader


def _audio_loader(path: str) -> Callable[[], dict]:
    def _loader() -> dict:
        x, fs = sf.read(path, dtype="float32")
        if fs != AUDIO_FS or x.ndim != 1:
            raise ValueError(f"{path}: expected 16 kHz mono")
        return {"fs": AUDIO_FS, "data": x[None, :]}
    return _loader


ADAPTOR = Hassan2026Adaptor
