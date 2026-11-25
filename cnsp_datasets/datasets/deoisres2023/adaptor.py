from __future__ import annotations

import math
import os
import re
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
from mne.io import BaseRaw
from openpyxl import load_workbook
from scipy.io import wavfile

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.iohelpers import mark_bads, read_wav, status_edges
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 1024  # recorded at 2048 Hz, decimated by 2
AUDIO_FS = 44100
SEGMENT_S = 120.0  # SNR-block segment length; pulse pairs this far apart (+-TOL_S) open and close a segment
TOL_S = 0.05
SCALP = [f"A{i}" for i in range(1, 33)]  # biosemi32 template order (authors drop A7/A24 as T7/T8, notes.md 5)
KIND_TARGET = {"speech": "speech", "noise": "modnoise"}  # quiet file kind -> target
WAV_STEM = {"speech": "speech", "modnoise": "mod_amp"}
BLOCK_WAV = "odin_01_{}_full_65dB_2minsx4_trig.wav"  # speech and mod_amp share the trigger track (notes.md 2)
SKIP = {(11, "MixedSpeechNoise")}  # 116.05-s segments: stimulus version not shipped (notes.md 3)
# segment index 1..40 (order sheet) -> (target, SNR); 4 consecutive indices = 2-min chunks 1..4 (authors' code)
GROUPS = [("speech", "quiet"), ("modnoise", "0dB"), ("speech", "-5dB"), ("modnoise", "-10dB"),
          ("speech", "-15dB"), ("modnoise", "quiet"), ("speech", "0dB"), ("modnoise", "-5dB"),
          ("speech", "-10dB"), ("modnoise", "-15dB")]
BADS: dict[int, list[str]] = {}  # per subject, template names; none found in the pilot (notes.md 9)
NOTES = ("BioSemi ActiveTwo 32 ch at 2048 Hz (417 Hz hardware bandwidth), decimated to 1024 Hz; original CMS/DRL "
         "reference (the thesis re-referenced to T7/T8), template positions, no EOG/mastoids recorded. Onsets from "
         "Status bit 0: a TTL made from the trigger track (channel 2) of each stimulus wav, played by the same RME "
         "Fireface UC that drove the ER-2A insert earphones (hardware, sound-card locked; trigger-box and tube "
         "latency not corrected). Drift from the pulse train (EEG clock vs sound card). Stimulus = wav channel 1 "
         "(the trigger track is not stored). In the SNR blocks the target was fixed at 65 dBA and a stationary "
         "speech-shaped noise (not shipped) set the SNR: the stored stimulus is the target only.")


class Deoisres2023Adaptor(BaseAdaptor):
    """
    Deoisres (2023) Southampton thesis dataset (doi:10.5258/SOTON/D2578): 22 normal-hearing adults ignore a story
    (The Children of Odin) while watching a muted documentary. Per subject three BDFs: ~15 min speech and ~15 min
    speech-envelope-modulated noise in quiet (S03/S04: ~26 min, chapters 4+5), then 40 x 2-min segments (speech or
    modulated noise, 4 chunks each, in quiet and at 0/-5/-10/-15 dB SNR in speech-shaped noise) in the
    pre-assigned order of Subject_SNRpresent_order_speech_and_noise.xlsx. Expects the extracted RARs under
    download_dir (bsdtar -xf <rar>). /da/ recordings are not used. See notes.md.
    """

    def __init__(self, download_dir: str, drift_correction: bool = True):
        super().__init__(download_dir)
        self.drift_correction = self.choice("drift_correction", drift_correction, (True, False))
        self.files = {}
        for path in self.sorted_glob(download_dir, "**/SIN_S*_*.bdf"):
            m = re.fullmatch(r"SIN_S(\d\d)_(speech|noise|MixedSpeechNoise)\.bdf", os.path.basename(path))
            if m:
                files = self.files.setdefault(int(m.group(1)), {})
                if m.group(2) in files:
                    raise ValueError(f"two {os.path.basename(path)} under {download_dir}: {files[m.group(2)]}, {path}")
                files[m.group(2)] = path
        self.stim_dir = _find_dir(download_dir, "SIN_Stimuli")
        wb = load_workbook(os.path.join(_find_dir(download_dir, "SIN_Stimuli_Order"),
                                        "Subject_SNRpresent_order_speech_and_noise.xlsx"), read_only=True)
        self.order = [[int(i) for i in col] for col in zip(*wb.active.iter_rows(values_only=True))]  # subject - 1
        wb.close()

    def parse(self) -> Iterable[TrialRecord]:
        for sub in sorted(self.files):
            dates = {kind: _meas_date(bdf) for kind, bdf in self.files[sub].items()}
            trial = 0
            for kind in sorted(dates, key=dates.get):
                if (sub, kind) in SKIP:
                    continue
                bdf = self.files[sub][kind]
                trials = self._quiet(kind, bdf) if kind in KIND_TARGET else self._blocks(sub, bdf)
                for cond, stim, n_audio, onset, drift, extra in trials:
                    trial += 1
                    extra.update(bdf=os.path.basename(bdf), meas_date=str(dates[kind]),
                                 drift_corrected=self.drift_correction, onset_sample_2048=float(onset),
                                 reference="CMS/DRL (BioSemi, as recorded)",
                                 units_as_shipped="uV (BDF), read into V", positions="template (biosemi32)")
                    yield TrialRecord(
                        subject=sub, session=1, trial=trial, condition=cond, ns_type="eeg", stimulus=stim,
                        neural_data_fn=_eeg_loader(bdf, onset, math.ceil(n_audio * FS / AUDIO_FS), drift,
                                                   self.drift_correction, BADS.get(sub, []), extra))

    def _quiet(self, kind: str, bdf: str):
        """One trial per file: the wav (and pulse offset) whose trigger-track intervals match the EEG pulses."""
        rise, fs = _status_rises(bdf), _read(bdf).info["sfreq"]
        target = KIND_TARGET[kind]
        hits = []
        for w in self.sorted_glob(self.stim_dir, f"odin_04*_{WAV_STEM[target]}_full_65dB_trig.wav"):
            ws = _wav_rises(w) / AUDIO_FS
            for k in range(len(ws) - len(rise) + 1):  # S11 noise misses the first pulse
                if np.abs(np.diff(rise) / fs - np.diff(ws[k:k + len(rise)])).max() < 0.01:
                    hits.append((len(ws) - len(rise), w, k, ws[k:k + len(rise)]))
        hits.sort(key=lambda h: h[0])  # odin_04_and_05 starts like odin_04: take the wav with fewest unmatched
        if not hits or (len(hits) > 1 and hits[1][0] == hits[0][0]):
            raise ValueError(f"{bdf}: {len(rise)} pulses match {len(hits)} wav positions")
        unmatched, wav, first, wav_s = hits[0]
        slope, intercept = np.polyfit(wav_s, rise, 1)  # EEG sample = slope * audio time + intercept
        resid = (rise - (slope * wav_s + intercept)) / fs * 1e3
        extra = dict(wav=os.path.basename(wav), n_pulses=len(rise), missing_pulses_at_start=first,
                     unmatched_wav_pulses=unmatched, pulse_resid_ms_max=float(abs(resid).max()), target=target,
                     snr="quiet")
        stim = StimulusRecord("audio", os.path.basename(wav)[:-len("_trig.wav")], _audio_loader(wav),
                              is_attended=False, feature_name="audio")
        yield f"{target}_story", stim, _n_frames(wav), intercept, slope / fs - 1, extra

    def _blocks(self, sub: int, bdf: str):
        """Segments opened and closed by pulses SEGMENT_S apart; lone pulses (S01: an aborted segment) skipped."""
        rise, fs = _status_rises(bdf), _read(bdf).info["sfreq"]
        pairs, stray, i = [], [], 0
        while i < len(rise):
            if i + 1 < len(rise) and abs((rise[i + 1] - rise[i]) / fs - SEGMENT_S) < TOL_S:
                pairs.append((rise[i], rise[i + 1]))
                i += 2
            else:
                stray.append(int(rise[i]))
                i += 1
        order = np.array(self.order[sub - 1])
        if len(pairs) != len(order):
            raise ValueError(f"{bdf}: {len(pairs)} segments for {len(order)} order entries")
        edges = _wav_rises(os.path.join(self.stim_dir, BLOCK_WAV.format("speech")))
        chunks = (order - 1) % 4  # 0-based chunk per position
        durations = np.diff(np.array(pairs), axis=1)[:, 0] / fs
        drift = float(np.mean(durations / (np.diff(edges)[chunks] / AUDIO_FS))) - 1
        for pos, ((start, _), index, chunk) in enumerate(zip(pairs, order, chunks), 1):
            target, snr = GROUPS[(index - 1) // 4]
            wav = os.path.join(self.stim_dir, BLOCK_WAV.format(WAV_STEM[target]))
            name = f"{os.path.basename(wav)[:-len('_trig.wav')]}_chunk{chunk + 1}"
            stim = StimulusRecord("audio", name, _audio_loader(wav, edges[chunk], edges[chunk + 1]),
                                  is_attended=False, feature_name="audio")
            extra = dict(wav=os.path.basename(wav), chunk=int(chunk + 1), segment_index=int(index),
                         position_in_block=pos, target=target, snr=snr,
                         masker=None if snr == "quiet" else "speech-shaped noise (not shipped)",
                         stray_pulses_2048=stray, segment_duration_s_eeg=float(durations[pos - 1]))
            yield f"{target}_{snr}", stim, int(edges[chunk + 1] - edges[chunk]), float(start), drift, extra


def _eeg_loader(bdf: str, onset: float, n_out: int, drift: float, correct: bool, bads: list[str],
                extra: dict) -> Callable[[], BaseRaw]:
    def _loader() -> BaseRaw:
        raw = crop_on_audio_clock(_read(bdf), onset, n_out, drift=drift if correct else 0.0, picks=SCALP,
                                  sfreq_out=FS)
        montage = mne.channels.make_standard_montage("biosemi32")
        raw.rename_channels(dict(zip(SCALP, montage.ch_names)))
        raw.set_montage(montage)
        mark_bads(raw, bads)
        short = bool(raw.n_times < n_out)
        raw.info["description"] = provenance(
            "hw_trigger", "hardware (inferred: TTL from the wav trigger track, notes.md 6)", NOTES,
            drift_ppm=drift * 1e6, jitter_ms=0.5, **extra, n_samples=int(raw.n_times), n_samples_stimulus=n_out,
            eeg_shorter_than_stimulus=short)
        return raw
    return _loader


def _audio_loader(path: str, start: int = 0, stop: int | None = None) -> Callable[[], dict]:
    def _loader() -> dict:
        x, _ = read_wav(path, channel=0, expect_fs=AUDIO_FS)  # channel 1 is the trigger track
        return {"fs": AUDIO_FS, "data": np.ascontiguousarray(x[:, start:stop])}
    return _loader


def _find_dir(root: str, name: str) -> str:
    hits = BaseAdaptor.sorted_glob(root, f"**/{name}")
    if len(hits) != 1:
        raise FileNotFoundError(f"{name} under {root}: {hits}")
    return hits[0]


@lru_cache(maxsize=3)
def _read(bdf: str) -> BaseRaw:
    return mne.io.read_raw_bdf(bdf, preload=False, verbose="ERROR")


def _meas_date(bdf: str):
    """The BDF's start time (orders a subject's recordings); ValueError if the header has none."""
    date = _read(bdf).info["meas_date"]
    if date is None:
        raise ValueError(f"{bdf}: no meas_date in the header, so the recording order is unknown")
    return date


@lru_cache(maxsize=None)
def _status_rises(bdf: str) -> np.ndarray:
    """Samples where Status bit 0 rises (MNE leaves Status as integers)."""
    return status_edges(_read(bdf).get_data(picks=["Status"])[0], mask=1, kind="rise", idle=0)


@lru_cache(maxsize=None)
def _wav_rises(path: str) -> np.ndarray:
    """Rising edges of the trigger track (channel 2; 500-ms pulses at full scale)."""
    x = np.abs(wavfile.read(path, mmap=True)[1][:, 1].astype(np.float32))
    on = x > 0.5 * x.max()
    return np.flatnonzero(~on[:-1] & on[1:]) + 1


def _n_frames(path: str) -> int:
    return len(wavfile.read(path, mmap=True)[1])


ADAPTOR = Deoisres2023Adaptor
