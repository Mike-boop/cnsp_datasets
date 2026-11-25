from __future__ import annotations

import csv
import os
import re
from typing import Callable, Iterable

import mne
import numpy as np
import scipy.io as sio
from mne.channels import make_standard_montage

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.iohelpers import audio_loader, mark_bads
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 1024  # BioSemi rate, kept
WAV_FS = 44100
GAP = 200  # samples of silence that separate two pulse bursts (bursts last ~0.5 s, one per second)
LEAD = 20  # samples: a burst opens with ~60 high samples; shorter blips are not bursts (sub-16 trial 8)
GLITCH = 1  # samples: a longer deviation of a burst interval from 1 s is a playback stall (quantisation <= 1)
VALIDATION_TIER = "mlr"  # validation.json: low and mlr pass, brainstem fails (notes.md 9)
# (subject, session) -> channels with 40-200 Hz RMS > 5x the session median (median over trials; notes.md 5)
BADS = {(2, 1): ["P2", "PO4"], (6, 1): ["P2"], (11, 1): ["P2"], (12, 1): ["P2"], (13, 1): ["POz"]}
SUFFIX = "_10min_trimmedSilencesTo0.20s.wav"  # common to all wavs; dropped from the stimulus names
SIDES = {"left": "L", "right": "R"}
NAME = re.compile(r"sub-(\d+)_ses-(\d+)_trial(\d+)_task-(.+)_eeg")
TRIGGER_TYPE = ("hardware (a pulse burst at the start of every 1-s audio buffer, played on the stimulus sound card "
                "(Behringer UMC1820) with the speech and recorded in BioSemi Status bit 0; paper 2.4)")
NOTES = ("Trial = one BDF (one presentation). Audio-clock timeline from the Status-bit-0 pulse bursts: burst k marks "
         "audio second k; one least-squares fit per trial (common sound-card/EEG clock drift, one onset per run of "
         "bursts) and one spline resample at 1024 Hz per run; an interval off by more than 1 sample (playback stall, "
         "~2 or ~12.5 ms) starts a new run (BAD/EDGE boundary annotation at the join), so the EEG during a stall is "
         "dropped and the stimulus stays continuous. Stimuli: the left and right loudspeaker wavs as shipped (44.1 "
         "kHz, longer than the trial; cut at the point of use). Attention: `attend/left` / `attend/right` annotations "
         "from the authors' params_randomization (initial ear, switch times); is_attended is set only in trials "
         "without a switch (OL-CAL). In CLA and psCLA the two talkers' gains changed every second (complementary, "
         "-6..+6 dB, from the online/offline HMM); the gain trajectories are not shipped, so the stored wavs are the "
         "unscaled sources, not the sound heard. Loudspeakers at 1.4 m (about 4 ms acoustic delay, not corrected). "
         "Reference: BioSemi CMS/DRL, not re-referenced.")


class Rotaru2026Adaptor(BaseAdaptor):
    """
    Rotaru et al. 2026 KUL-AAD-NFB (Zenodo 20442638): closed-loop auditory attention decoding with neurofeedback.
    11 shared participants (sub-09 in two sessions), BioSemi 64-channel EEG at 1024 Hz, two Flemish podcasts from
    loudspeakers at +-14 deg. Conditions OL, CLV, CLA, psCLA (8-min trials with 1 or 3 cued switches) and OL-CAL
    (5-min calibration, no switch; sub-11..19). Trials without the authors' .mat (no stimulus names) are skipped.
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self.eeg_dir = os.path.join(download_dir, "eeg")
        self.wav_dir = os.path.join(download_dir, "stimuli")
        self.ratings = _ratings(os.path.join(download_dir, "KUL-AAD-NFB_behavioral_results.csv"))

    def parse(self) -> Iterable[TrialRecord]:
        for bdf in self.sorted_glob(self.eeg_dir, "sub-*/*_eeg.bdf"):
            mat = bdf[:-4] + "_preprocessed.mat"
            if not os.path.exists(mat):
                continue  # no stimulus names or attention schedule (notes.md 3)
            name = os.path.basename(bdf)
            sub, ses, trial, task = NAME.match(name).groups()
            sub, ses, trial = int(sub), int(ses), int(trial)
            p = sio.loadmat(mat, squeeze_me=True, struct_as_record=False,
                            variable_names=["params_randomization"])["params_randomization"]
            mapping = p.stim_mapping if hasattr(p, "stim_mapping") else p.stimuli_to_chans_mapping  # sub-03
            if {"CLAsham": "psCLA"}.get(p.id_condition, p.id_condition) != task or list(mapping) != ["L", "R"]:
                raise ValueError(f"{mat}: condition {p.id_condition} / mapping {mapping} not as expected")
            duration = int(p.duration)
            switches = np.atleast_1d(p.switch_times).astype(float)
            spans = _attention_spans(SIDES[p.init_attended_ear], switches, duration)
            fixed = spans[0][2] if len(spans) == 1 else None
            wavs = [w.strip() for w in p.speakers]  # sub-03 names are space-padded
            stems = [w.removesuffix(SUFFIX) for w in wavs]
            stimuli = [StimulusRecord("audio", stem, audio_loader(os.path.join(self.wav_dir, wav), expect_fs=WAV_FS),
                                      is_attended=side == fixed, feature_name="audio")
                       for stem, wav, side in zip(stems, wavs, "LR")]
            bads = BADS.get((sub, ses), [])
            extra = dict(participant=f"sub-{sub:02d}", session_label=f"ses-{ses:02d}", file=name,
                         left_stimulus=stems[0], right_stimulus=stems[1], initial_attended_ear=p.init_attended_ear,
                         switch_times_s=switches.tolist(), visual_feedback=int(p.visual_feedback),
                         audio_feedback=int(p.audio_feedback), audio_feedback_sham=int(p.audio_feedback_sham),
                         level_dba=np.atleast_1d(p.calibr_target_dbA_per_ch).tolist(), bad_channels=bads,
                         reference="BioSemi CMS/DRL (reference-free recording, not re-referenced)",
                         units_as_shipped="BDF, read into V", montage="biosemi64 template (no digitisation)",
                         ratings=self.ratings.get((sub, ses, trial)))
            yield TrialRecord(subject=sub, session=ses, trial=trial, condition=task, ns_type="eeg",
                              stimulus=stimuli, neural_data_fn=_eeg_loader(bdf, duration, spans, bads, extra))


def _ratings(path: str) -> dict:
    """(subject, session, trial) -> the participant's ratings after the trial (behavioral_results.csv)."""
    keys = ("SpeechIntell", "ListEffort", "DegreeDistraction", "SwitchEffort", "AgencyScore", "ScorePrediction")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {(int(r["SubjectID"][4:]), int(r["SessionID"][4:]), int(r["TrialID"])):
            {k: float(r[k]) if r[k] else None for k in keys} for r in rows}


def _attention_spans(first: str, switches: np.ndarray, duration: int) -> list:
    """(onset, end, side) of the cued attention spans: `first` until the first switch, then alternating."""
    edges = [0.0, *sorted(switches), float(duration)]
    sides = [first if i % 2 == 0 else ("R" if first == "L" else "L") for i in range(len(edges) - 1)]
    return [(a, b, s) for a, b, s in zip(edges[:-1], edges[1:], sides)]


def _bursts(raw: mne.io.BaseRaw) -> np.ndarray:
    """
    EEG sample of the first rising edge of each pulse burst in Status bit 0: a rise more than GAP samples after the
    previous fall (or with no fall before it), followed by LEAD high samples.
    """
    bit = raw.get_data(picks=["Status"])[0].astype(np.int64) & 1
    rises = np.flatnonzero(np.diff(bit) == 1) + 1
    falls = np.flatnonzero(np.diff(bit) == -1) + 1
    prev = np.searchsorted(falls, rises) - 1  # index of the last fall before each rise
    gap = np.where(prev >= 0, rises - falls[np.maximum(prev, 0)], GAP + 1)
    return np.array([i for i in rises[gap > GAP] if bit[i:i + LEAD].all()], dtype=int)


def _runs(starts: np.ndarray, duration: int) -> tuple[list, float, float]:
    """
    Runs of bursts (burst k = audio second k), split where an interval between consecutive bursts is more than
    GLITCH samples off k * FS (playback stall). One least-squares fit for the whole trial: a common slope (the
    sound-card/EEG drift; same clocks throughout) and one intercept per run. Returns [(first audio second, EEG
    onset)] per run, the drift and the residual SD (ms).
    """
    k = np.round((starts - starts[0]) / FS).astype(int)
    if k[-1] < duration - 1 or len(np.unique(k)) != len(k):
        raise ValueError(f"bursts cover {k[-1] + 1} s of a {duration}-s trial or repeat a second")
    run = np.cumsum(np.r_[0, np.abs(np.diff(starts) - FS * np.diff(k)) > GLITCH])
    design = np.c_[k, run[:, None] == np.arange(run[-1] + 1)]
    coef, *_ = np.linalg.lstsq(design.astype(float), starts.astype(float), rcond=None)
    slope, icpt = coef[0], coef[1:]
    jitter = float(np.std(starts - design @ coef)) / FS * 1e3
    first = [int(k[run == r][0]) for r in range(run[-1] + 1)]
    for r in range(1, len(first)):
        if icpt[r] < icpt[r - 1]:  # an early burst would make run r - 1 read into run r's EEG
            raise ValueError(f"run at audio s {first[r]} starts before the previous run's grid")
    runs = [(k0, icpt[r] + slope * k0) for r, k0 in enumerate(first) if k0 < duration]  # bursts go on after the trial
    return runs, slope / FS - 1, jitter


def _eeg_loader(bdf: str, duration: int, spans: list, bads: list, extra: dict) -> Callable[[], mne.io.BaseRaw]:
    """Loader of one trial on the audio clock (drift-corrected per playback run), with attention annotations."""
    def _loader() -> mne.io.BaseRaw:
        raw = mne.io.read_raw_bdf(bdf, preload=False, verbose="ERROR")
        try:
            runs, drift, jitter = _runs(_bursts(raw), duration)
        except ValueError as e:
            raise ValueError(f"{bdf}: {e}") from None
        raw.drop_channels(["Status"])
        n_total = duration * FS
        ends = [k0 * FS for k0, _ in runs[1:]] + [n_total]
        parts = [crop_on_audio_clock(raw, onset, end - k0 * FS, drift) for (k0, onset), end in zip(runs, ends)]
        if sum(p.n_times for p in parts) != n_total:
            raise ValueError(f"{bdf}: trial runs past the end of the recording")
        out = mne.concatenate_raws(parts, verbose="ERROR")  # keeps BAD/EDGE boundary annotations at stalls
        out.set_annotations(out.annotations + mne.Annotations(
            [a for a, _, _ in spans], [b - a for a, b, _ in spans],
            [f"attend/{'left' if s == 'L' else 'right'}" for _, _, s in spans], orig_time=out.annotations.orig_time))
        out.set_montage(make_standard_montage("biosemi64"), verbose="ERROR")
        mark_bads(out, bads)
        out.info["description"] = provenance(
            "hw_trigger", TRIGGER_TYPE, NOTES, drift_ppm=round(drift * 1e6, 2), jitter_ms=round(jitter, 3),
            validation_tier=VALIDATION_TIER, onset_sample=round(runs[0][1]), n_playback_runs=len(runs),
            run_start_s=[k0 for k0, _ in runs], **extra)
        return out

    return _loader


ADAPTOR = Rotaru2026Adaptor
