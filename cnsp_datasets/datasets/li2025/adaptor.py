from __future__ import annotations

import glob
import os
import subprocess
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

NAME = "baba"
VIDEO = os.path.join("sourcedata", "stimuli", "baba_video.mp4")
ANNOTATIONS = {"words_csv": "word_information.csv", "transcript": "transcripts.csv"}  # CSV text, as shipped
N_TIMES = 1519001  # every baba file (the authors' fixed-length crop), except the truncated sub-54
# paper: channels 19 and 48 bad in 16 participants (equipment); MEG019 is flat or ~3000x noisy in exactly sub-32..47.
# Others: 1-40 Hz amplitude spectrum > 10x the subject's channel median (notes.md section 5).
PAPER_BADS = ["MEG019", "MEG048"]
EXTRA_BADS = {"sub-34": ["MEG023", "MEG040"], "sub-42": ["MEG005"], "sub-47": ["MEG005"], "sub-48": ["MEG040"]}
# Sound onset after the first sample of the shipped file, per recording group (brain-based, notes.md section 7;
# applied by default, user decision 2026-11-23). Whole samples at 1000 Hz, so the correction is a crop.
ONSET_DELAY_S = {"A": 0.80, "B": 0.42}
GROUP_LABEL = {"A": "sub-31..47", "B": "sub-48..60"}  # recording periods (spectra and sound delay differ)
ONSET_METHOD = {
    "A": "brain-based: peak of the population 0.5-8 Hz envelope TRF (+0.92 s) minus ~0.1 s (corrected peaks at "
         "+94/+250 ms); +-~50 ms (alignment/poptrf.py)",
    "B": "brain-based: group B's multichannel TRF matched to group A's corrected TRF (best 0.44 s, bootstrap 95% CI "
         "0.41-0.80 s, skewed; user's reading 0.41 s) -> 0.42 s; a component at ~-40 ms remains unexplained "
         "(alignment/match_groups.py)"}
NOTES = ("Raw OPM-MEG as shipped (Quanmag, 64 radial magnetometers, 1000 Hz, no HFC/SSS or other processing). The "
         "authors cut each recording at the video's start trigger (STI1 code 6 on the first sample; sub-49 code 1, "
         "sub-40 none) and to 1519.001 s. The sound starts later than that trigger (software trigger before "
         "playback, inferred): with onset_correction (default) the trial starts 0.80 s (sub-31..47) or 0.42 s "
         "(sub-48..60) into the file, delays estimated from the MEG itself (circular; onset_correction_method). "
         "No end trigger or audio copy: drift not corrected. The audio (2 channels, 44.1 kHz) is decoded from the "
         "shipped video and runs past the recording (cut at the point of use). Audiovisual stimulus: the "
         "participants also watched the video (not stored). Sensor positions from the helmet geometry; dev_head_t "
         "identity, fiducials are placeholders.")
VALIDATION_NOTE = ("low tier (0.5-8 Hz, HFC in the validation only, onset-corrected data); high-frequency tiers not "
                   "credible (lag-0 analysis artefact also present at a wrong offset).")


class Li2025Adaptor:
    """
    BABA (Li et al. 2025, OpenNeuro ds005346): 30 participants (sub-31..60) watched a 25 min excerpt of the Chinese
    reality show "Where Are We Going, Dad?" in an OPM-MEG (Quanmag, 64 magnetometers, 1000 Hz). One trial per
    participant (task-baba); the quiz and the eyes-closed replay runs have no auditory stimulus and are not used.
    sub-54's upload is truncated after 698 s (both baba and replay).

    Neural data: the shipped baba file (the authors' crop from the video trigger), from the brain-based sound onset
    (onset_correction=True, default: 0.80 s in for sub-31..47, 0.42 s for sub-48..60; False: from the first sample),
    magnetometers only, bads per participant. Stimuli: the video's audio track (ffmpeg decode, both channels), and
    the shipped word annotation (Whisper + manual review; speaker, timing, linguistic features) and transcript as CSV
    text. See notes.md.
    """

    def __init__(self, download_dir: str, onset_correction: bool = True):
        self.root = download_dir
        self.onset_correction = onset_correction

    def parse(self) -> Iterable[TrialRecord]:
        video = os.path.join(self.root, VIDEO)
        stimuli = [StimulusRecord("audio", NAME, _audio_loader(video), True, "audio")]
        stimuli += [StimulusRecord("audio", NAME, _text_loader(os.path.join(self.root, "sourcedata", "annotation", f)),
                                   True, feature) for feature, f in ANNOTATIONS.items()]
        for fif in sorted(glob.glob(os.path.join(self.root, "sub-*", "meg", "sub-*_task-baba_meg.fif"))):
            sub = os.path.basename(fif).split("_")[0]
            subject = int(sub[4:])
            bads = (PAPER_BADS if 32 <= subject <= 47 else []) + EXTRA_BADS.get(sub, [])
            delay = ONSET_DELAY_S[group(subject)] if self.onset_correction else 0.0
            yield TrialRecord(subject=subject, session=1, trial=1, condition="audiovisual", ns_type="meg",
                              stimulus=stimuli, neural_data_fn=_meg_loader(fif, bads, group(subject), delay))


def group(subject: int) -> str:
    """Recording group: A = sub-31..47, B = sub-48..60."""
    return "A" if subject <= 47 else "B"


def readable(fif: str) -> mne.io.BaseRaw:
    """
    The fif without its last data buffer if that is truncated (sub-54: the upload stops mid-buffer). Uses MNE's
    private `_raw_extras[0]["bounds"]` (absolute buffer starts; checked with MNE 1.9).
    """
    raw = mne.io.read_raw_fif(fif, preload=False, verbose="ERROR")
    try:
        raw.get_data(start=raw.n_times - 1)
    except ValueError:
        start = raw._raw_extras[0]["bounds"][-2] - raw.first_samp  # start of the truncated buffer
        raw.crop(tmax=(start - 1) / raw.info["sfreq"])
        raw.get_data(start=raw.n_times - 1)  # any other read error still raises
    return raw


def _meg_loader(fif: str, bads: list[str], group: str, delay: float) -> Callable[[], mne.io.BaseRaw]:
    def _loader():
        raw = readable(fif)
        trigger = raw.get_data(picks="STI1", stop=1)[0, 0]
        truncated, first = raw.n_times < N_TIMES, raw.first_samp
        raw.pick("mag").crop(tmin=delay).load_data(verbose="ERROR")
        raw.info["bads"] = bads
        raw.info["description"] = provenance(
            "onset_only", "unknown (not documented; inferred software: the sound starts after it). Onset = the STI1 "
            "code on the first sample of the authors' crop + onset_correction_s", NOTES,
            first_sample_trigger=int(trigger), crop_first_samp=int(first),
            recording_group=group, onset_correction_s=delay,
            onset_correction_method=ONSET_METHOD[group] if delay else "none (first sample of the shipped file)",
            truncated_upload=bool(truncated), bads=bads, reference="not applicable (MEG)",
            sss="none (raw as shipped)", drift_corrected_ppm=0.0, validation_tier="low",
            validation_note=VALIDATION_NOTE)
        return raw

    return _loader


@lru_cache(maxsize=1)
def _decode(video: str) -> np.ndarray:
    """Audio track as float32 (2, n) at its 44.1 kHz; ffmpeg honours the mp4 edit list (AAC priming removed)."""
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", video, "-map", "0:a:0", "-f", "f32le",
                          "-c:a", "pcm_f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype="<f4").reshape(-1, 2).T.copy()


def _audio_loader(video: str) -> Callable[[], dict]:
    def _loader() -> dict:
        return {"fs": 44100, "data": _decode(video)}

    return _loader


def _text_loader(path: str) -> Callable[[], str]:
    def _loader() -> str:
        with open(path, encoding="utf-8-sig") as f:
            return f.read()

    return _loader


ADAPTOR = Li2025Adaptor
