from __future__ import annotations

import glob
import json
import os
import re
from typing import Callable, Iterable

import mne
import pandas as pd
import soundfile as sf
from mne.io import BaseRaw

from cnsp_datasets.datasets.peng2026.bads import BADS_JSON
from cnsp_datasets.datasets.peng2026.onsets import eci_offset, log_arrivals, log_offset, tbeg_markers
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

SCENES = {1: "restaurant", 2: "tv", 3: "meeting"}  # BIDS run -> scene (events.tsv: Restaurant, TV, Office)
STIM_CHANNELS = ["SESS", "CELL", "TBEG", "TEND"]
TRIGGER = ("software (E-Prime 2.0 -> Net Station ECI over TCP; the TBEG event carries E-Prime's SoundOut1.OnsetTime, "
           "mapped to the amplifier clock by one NTP sync at the start of each run)")
REFERENCE = "Cz (EGI VREF, the recording reference; a zero channel in the data)"
LOG_ERROR_SD_MS = 17.6  # leave-one-subject-out run-offset error of the log reconstruction (notes 6c)
NOTES = ("Trial = one 126-s binaural scene (mixture of both talkers and background), EEG from the sound onset for "
         "the wav's duration. Onset = E-Prime SoundOut1.OnsetTime + a per-run offset (onset_source): the ECI TBEG "
         "markers (sub-09..30), or, where E-Prime sent every marker with timestamp 0 (sub-01..08), the TBEG arrival "
         "times in the Net Station log, corrected for the Mac log clock (~+65 ppm against the marker clock) and the "
         "arrival latency, both calibrated on sub-10..30 (leave-one-subject-out run-offset error SD 18 ms, max "
         "87 ms; notes.md section 6). The shipped events.tsv onsets for sub-01..09 drift by ~+65 ppm within a run "
         "(up to ~0.1 s; onset='authors' restores them). Audio output latency unknown (E-Prime OnsetTime, no "
         "stimtrack); drift between the sound card and the EEG not measurable. Separate talker streams are not in "
         "the release: cue_direction gives the attended side. Bad channels per participant (bads.json): 1-40 Hz SD "
         "> 5x or < 1/5 of the median in >= 20% of the participant's trials (periocular channels: low SD only). "
         "Positions: the MFF coordinates.xml (HydroCel GSN 128 template).")


class Peng2026Adaptor:
    """
    Peng et al. 2026 SoundBubble-EEG (Zenodo 19610628, BIDS): 30 listeners (sub-01..30), EGI HydroCel GSN 128 at
    250 Hz (Net Station MFF, raw), 25 binaural scenes of two competing Mandarin conversations (AISHELL4) plus scene
    noise: run-01 restaurant (10), run-02 TV (10), run-03 meeting (5), recorded meeting -> restaurant -> TV. The
    cue (left/right; front for the TV programme) says which conversation to attend.

    Trial = one scene, numbered in presentation order within the participant (1-25; runs by meas_date); condition
    = scene. Stimulus = the shipped binaural mixture `stimuli/<scene>/<Sxxxxx>_mix_CH0.wav` (16 kHz stereo),
    matched to the trial via the E-Prime log (`sourcedata/.../beh/*_beh.txt`: wavfile and SoundOut1.OnsetTime).
    EEG: E1-E128 + VREF (Cz, zeros), volts, native 250 Hz, original reference; the four event channels are dropped.
    onset="corrected" (default; see onsets.py) or "authors" (the shipped events.tsv onsets).
    """

    def __init__(self, download_dir: str, onset: str = "corrected"):
        if onset not in ("corrected", "authors"):
            raise ValueError(f"onset must be 'corrected' or 'authors', not {onset!r}")
        self.root, self.onset = download_dir, onset
        with open(BADS_JSON) as f:
            self.bads = json.load(f)

    def parse(self) -> Iterable[TrialRecord]:
        for sub_dir in sorted(glob.glob(os.path.join(self.root, "sub-*", ""))):
            sub = os.path.basename(sub_dir[:-1])
            runs = sorted((self._run_trials(sub, mff) for mff in glob.glob(os.path.join(sub_dir, "eeg", "*_eeg.mff"))),
                          key=lambda x: x[0])  # presentation order (meas_date)
            rows = [row for _, rows in runs for row in rows]
            for trial, row in enumerate(rows, 1):
                stim = os.path.join(self.root, "stimuli", SCENES[row["run"]], f"{row['stimulus']}.wav")
                yield TrialRecord(
                    subject=int(sub[4:]), session=1, trial=trial, condition=SCENES[row["run"]], ns_type="eeg",
                    stimulus=StimulusRecord("audio", row["stimulus"], _audio_loader(stim)),
                    neural_data_fn=self._eeg_loader(row["mff"], row["onset"], sf.info(stim).duration, self.bads[sub],
                                                    self._description(sub, row)),
                )

    def _run_trials(self, sub: str, mff: str) -> tuple:
        """(meas_date, trials) of one run; trial = stimulus, cue, E-Prime onset and the onset in the recording (s)."""
        run = int(mff.split("_run-")[1][:2])
        raw = mne.io.read_raw_egi(mff, verbose="ERROR")
        ev = pd.read_csv(mff.replace("_eeg.mff", "_events.tsv"), sep="\t")
        beh = _eprime_log(os.path.join(self.root, "sourcedata", sub, "beh",
                                       os.path.basename(mff).replace("_eeg.mff", "_beh.txt")))
        t_ep = ev["SoundOut1.OnsetTime"].to_numpy() / 1000
        if self.onset == "authors":
            onsets, source = ev["onset"].to_numpy(), "authors_events_tsv"
        else:
            c, source = eci_offset(tbeg_markers(raw), t_ep), "eci_marker"
            if c is None:
                c, source = log_offset(log_arrivals(mff), t_ep, run), "netstation_log"
            onsets = t_ep + c
        rows = [dict(mff=mff, run=run, stimulus=beh[int(r["SoundOut1.OnsetTime"])],
                     cue=r["direction_str"].split(".")[0], t_ep=t, onset=o, authors_onset=r["onset"], source=source,
                     bids_run=os.path.basename(mff)[:-len("_eeg.mff")])
                for (_, r), t, o in zip(ev.iterrows(), t_ep, onsets)]
        return raw.info["meas_date"], rows

    def _description(self, sub: str, row: dict) -> str:
        return provenance(
            "sw_trigger", TRIGGER, NOTES, validation_tier="low",
            participant=sub, bids_run=row["bids_run"], scene=SCENES[row["run"]], stimulus=row["stimulus"],
            cue_direction=row["cue"], eprime_onset_ms=round(row["t_ep"] * 1e3), onset_source=row["source"],
            onset_error_sd_ms=LOG_ERROR_SD_MS if row["source"] == "netstation_log" else None,
            onset_s=round(row["onset"], 4), authors_onset_s=row["authors_onset"],
            onset_minus_authors_ms=round((row["onset"] - row["authors_onset"]) * 1e3, 1),
            units_as_shipped="µV (MFF float32); read as V by MNE", reference=REFERENCE, external_sensors={},
        )

    def _eeg_loader(self, mff: str, onset: float, duration: float, bads: list,
                    description: str) -> Callable[[], BaseRaw]:
        def _loader() -> BaseRaw:
            raw = mne.io.read_raw_egi(mff, verbose="ERROR")
            start = int(round(onset * raw.info["sfreq"]))
            n = int(round(duration * raw.info["sfreq"]))
            raw = raw.crop(tmin=raw.times[start], tmax=raw.times[start + n - 1], include_tmax=True).load_data()
            raw.drop_channels(STIM_CHANNELS)
            raw.set_annotations(None)
            raw.set_meas_date(None)
            raw.info["bads"] = list(bads)
            raw.info["description"] = description
            return raw
        return _loader


def _eprime_log(path: str) -> dict[int, str]:
    """SoundOut1.OnsetTime (ms) -> wav stem, from an E-Prime log (one LogFrame per trial)."""
    with open(path, encoding="utf-8") as f:
        frames = f.read().split("*** LogFrame Start ***")[1:]
    out = {}
    for frame in frames:
        wav, onset = re.search(r"wavfile: (\S+)", frame), re.search(r"SoundOut1\.OnsetTime: (\d+)", frame)
        if wav and onset:
            out[int(onset.group(1))] = os.path.basename(wav.group(1).replace("\\", "/"))[:-4]
    return out


def _audio_loader(path: str) -> Callable[[], dict]:
    def _loader() -> dict:
        x, fs = sf.read(path, dtype="float32")
        return {"fs": fs, "data": x.T}  # (2, n): left, right ear
    return _loader


ADAPTOR = Peng2026Adaptor
