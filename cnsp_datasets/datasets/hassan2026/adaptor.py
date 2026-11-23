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
NOTES = ("Onset = align.anchor_unix (earliest audio playback-start timestamp) - eeg.first_sample_unix (LSL), "
         "software timestamps on one host clock (paper II-D); all six loudspeaker streams share this onset: the "
         "per-device playback timestamps (0/+80/+160 ms) are not applied, because the scene microphone shows "
         "devices 1 and 2 sounding together (notes.md section 6). EEG clock vs host clock ~+9 ppm, not corrected "
         "(0.27 ms per 30 s trial). Values as shipped (volts); original amplifier reference (CPz, inferred).")


class Hassan2026Adaptor:
    """
    Hassan 2026 MAESTRO (Hugging Face aspire-osu/maestro-eeg-dataset): 16 listeners (S01-S16), 5 training + 100
    evaluation trials of 30 s, 4 LibriSpeech talkers (speakers 1-4, attendable) + 2 CHiME-Home noise sources
    (speakers 5-6) on 6 loudspeakers; 32-ch ANT eego at 500 Hz, shipped per trial (parquet) with unix timestamps.

    Trial = presentation position (1-105); condition = the authors' kind (`training`, `main`). The EEG is cropped
    at the stimulus onset (notes.md section 6) and runs to the end of the shipped trial (~30.3 s). Stimuli: the six
    16 kHz FLACs as played, named `<trial_id>_speaker<k>`, the attended talker flagged. M1/M2 are `misc`. Gaze, IMU
    and video are not included.
    """

    def __init__(self, download_dir: str):
        self.root = os.path.join(download_dir, "maestro-eeg-dataset")
        meta = os.path.join(self.root, "metadata")
        self.trials = pd.read_csv(os.path.join(meta, "trials.csv")).set_index("trial_id")
        scores = pd.read_csv(os.path.join(meta, "trials_per_subject.csv"))
        self.correct = scores.set_index(["subject_id", "trial_id"])["comprehension_correct"]
        with open(os.path.join(meta, "audio_manifest.json")) as f:
            self.manifest = json.load(f)
        with open(os.path.join(meta, "audio_layout.json")) as f:
            self.azimuth = {s["speaker"]: s["azimuth_deg"] for s in json.load(f)["speakers"]}
        with open(os.path.join(meta, "eeg_channels.json")) as f:
            self.channels = json.load(f)["channels"]
        with open(BADS_JSON) as f:
            self.bads = json.load(f)

    def parse(self) -> Iterable[TrialRecord]:
        for subject in sorted(self.bads):
            timings = [self._timing(subject, t) for t in self.trials.index]
            timings.sort(key=lambda j: j["eeg"]["first_sample_unix"])
            block = 1
            for pos, j in enumerate(timings, 1):
                tid = j["trial_id"]
                if tid == "eval_050":
                    block = 2  # 10-min break before the second evaluation session (paper II-B)
                onset = round((j["align"]["anchor_unix"] - j["eeg"]["first_sample_unix"]) * EEG_FS)
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
        anchor = j["align"]["anchor_unix"]
        correct = self.correct.get((subject, tid))
        return provenance(
            "sw_trigger", "software (paper: LSL first-sample and playback-start unix timestamps, one host clock)",
            NOTES, drift_ppm=None, jitter_ms=None,
            participant=subject, trial_id=tid, block=block, attended_speaker=int(row["attended_speaker"]),
            hemisphere_attended=row["hemisphere_attended"], inout_attended=row["inout_attended"],
            azimuth_attended_deg=self.azimuth[int(row["attended_speaker"])], snr_db=float(row["snr_db"]),
            comprehension_correct=None if pd.isna(correct) else bool(correct), onset_sample=onset,
            playback_offsets_ms={str(d["device_id_raw"]): round(1e3 * (d["playback_start_unix"] - anchor), 1)
                                 for d in j["audio"]["devices"]},
            reference="amplifier reference (CPz, inferred; not shipped)",
            external_sensors={"M1": "left mastoid", "M2": "right mastoid"},
        )

    def _stimuli(self, trial_id: str) -> List[StimulusRecord]:
        attended = int(self.trials.loc[trial_id, "attended_speaker"])
        return [StimulusRecord("audio", f"{trial_id}_speaker{k}",
                               _audio_loader(os.path.join(self.root, "media", "audio", trial_id, fname)),
                               is_attended=int(k) == attended, feature_name="audio")
                for k, fname in sorted(self.manifest[trial_id].items())]

    def _eeg_loader(self, subject: str, trial_id: str, onset: int, description: str) -> Callable[[], BaseRaw]:
        path = os.path.join(self.root, "data", "eeg", f"subject={subject}", f"trial={trial_id}.parquet")

        def _loader() -> BaseRaw:
            df = pd.read_parquet(path)
            x = df[[f"ch_{c}" for c in self.channels]].to_numpy(np.float64).T[:, onset:]  # volts as shipped
            types = ["misc" if c in MASTOIDS else "eeg" for c in self.channels]
            info = create_info(self.channels, EEG_FS, types)
            raw = RawArray(x, info, verbose="ERROR")
            raw.set_montage(make_standard_montage("standard_1020"), on_missing="ignore", verbose="ERROR")
            raw.info["bads"] = list(self.bads[subject])
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
