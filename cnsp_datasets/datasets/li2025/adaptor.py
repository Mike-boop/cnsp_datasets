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
NOTES = ("Raw OPM-MEG as shipped (Quanmag, 64 radial magnetometers, 1000 Hz, no HFC/SSS or other processing). The "
         "authors cut each recording at the video's start trigger (STI1 code 6 on the first sample; sub-49 code 1, "
         "sub-40 none) and to 1519.001 s, so the trial is the whole file: onset = its first sample, as shipped. "
         "Trigger type and audio-video latency after the trigger are undocumented; no end trigger, so drift is "
         "not measured or corrected. The audio (2 channels, 44.1 kHz) is decoded from the shipped video and runs "
         "0.23 s past the recording. Audiovisual stimulus: the participants also watched the video (not stored). "
         "Sensor positions from the helmet geometry; dev_head_t identity, fiducials are placeholders.")

VALIDATION_NOTE = ("low tier (0.5-8 Hz, HFC in the validation only); the envelope TRF peaks ~0.9 s (sub-31..47) or "
                   "~0.65 s (sub-48..60) after the onset: the sound starts ~0.80 / ~0.55 s after it (brain-based, "
                   "not corrected, notes.md section 7). High-frequency tiers not credible.")


class Li2025Adaptor:
    """
    BABA (Li et al. 2025, OpenNeuro ds005346): 30 participants (sub-31..60) watched a 25 min excerpt of the Chinese
    reality show "Where Are We Going, Dad?" in an OPM-MEG (Quanmag, 64 magnetometers, 1000 Hz). One trial per
    participant (task-baba); the quiz and the eyes-closed replay runs have no auditory stimulus and are not used.
    sub-54's upload is truncated after 698 s (both baba and replay).

    Neural data: the shipped baba file (the authors' crop from the video trigger), magnetometers only, bads per
    participant. Stimuli: the video's audio track (ffmpeg decode, both channels), and the shipped word annotation
    (Whisper + manual review; speaker, timing, linguistic features) and transcript as CSV text. See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir

    def parse(self) -> Iterable[TrialRecord]:
        video = os.path.join(self.root, VIDEO)
        stimuli = [StimulusRecord("audio", NAME, _audio_loader(video), True, "audio")]
        stimuli += [StimulusRecord("audio", NAME, _text_loader(os.path.join(self.root, "sourcedata", "annotation", f)),
                                   True, feature) for feature, f in ANNOTATIONS.items()]
        for fif in sorted(glob.glob(os.path.join(self.root, "sub-*", "meg", "sub-*_task-baba_meg.fif"))):
            sub = os.path.basename(fif).split("_")[0]
            subject = int(sub[4:])
            bads = (PAPER_BADS if 32 <= subject <= 47 else []) + EXTRA_BADS.get(sub, [])
            yield TrialRecord(subject=subject, session=1, trial=1, condition="audiovisual", ns_type="meg",
                              stimulus=stimuli, neural_data_fn=_meg_loader(fif, bads))


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


def _meg_loader(fif: str, bads: list[str]) -> Callable[[], mne.io.BaseRaw]:
    def _loader():
        raw = readable(fif)
        trigger = raw.get_data(picks="STI1", stop=1)[0, 0]
        raw.pick("mag").load_data(verbose="ERROR")
        raw.info["bads"] = bads
        raw.info["description"] = provenance(
            "onset_only", "unknown (not documented; STI1 code on the first sample of the authors' crop)", NOTES,
            first_sample_trigger=int(trigger), crop_first_samp=int(raw.first_samp),
            truncated_upload=bool(raw.n_times < N_TIMES), bads=bads, reference="not applicable (MEG)",
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
