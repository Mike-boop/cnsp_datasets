"""
Clock drift between the EEG amplifier and the stimulus audio in bentum2023.

Only two timing fields per block are measured EEG markers: st_sample (audio onset) and
et_sample (audio offset). fid_st / fid_et are nominal: each file's audio duration rounded to
whole ms, with gaps of exactly 0 or 900 ms (fid_st[0] == st_sample). Rounding errors add up over
a block's files (up to about 2 ms in a 14-file news block, the same for every subject hearing it),
so the block duration is taken from the wav files when they are available:

    duration = sum of the files' exact durations + nominal gaps     (what the adaptor plays back)
    inacc = et_sample - st_sample - duration = c + drift_rec * duration

where c is a constant end-marker offset (about -1 sample) and drift_rec is the recording's
clock drift (about 30-35 ppm, varying by about 6 ppm between recordings but stable within one).
c cannot be separated from drift within a recording (its blocks all last about the same),
but across recordings block durations range from about 250 s to 900 s, so c is the slope of
per-recording raw drift against 1 / duration.

See drift_analysis.ipynb for the full analysis.
"""
from __future__ import annotations

import glob
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Sequence

import numpy as np
from scipy import stats
from scipy.io import wavfile

from cnsp_datasets.standardise.clock import to_audio_clock  # noqa: F401 (re-exported)

# blocks with larger discrepancies have marker problems, not drift
MAX_INACC_SAMPLES = 1000

# quintic spline: amplitude error ~0.04% at 200 Hz and ~1% at 300 Hz for 1 kHz data
# (linear interpolation loses ~14% at 200 Hz)


@dataclass(frozen=True)
class BlockTiming:
    recording: str   # vhdr_fn: one BrainVision recording is one run of the EEG clock
    duration: float  # block duration (EEG samples = ms): exact if the audio is available, else nominal
    inacc: float     # et_sample - st_sample - duration (EEG samples)


@dataclass(frozen=True)
class DriftEstimate:
    marker_offset: float                # c, in EEG samples
    by_recording: Dict[str, float]      # vhdr_fn -> drift as a fraction (35e-6 = 35 ppm)
    global_drift: float                 # median of by_recording

    def drift(self, recording: str, mode: str = "recording") -> float:
        """Drift for a recording; mode 'recording' falls back to the global value if unknown."""
        if mode == "global":
            return self.global_drift
        if mode == "recording":
            return self.by_recording.get(recording, self.global_drift)
        raise ValueError(f"Unknown drift mode {mode!r} (expected 'recording' or 'global')")


@lru_cache(maxsize=8)
def wav_index(directory: str) -> Dict[str, str]:
    """{wav stem: path} for every .wav under directory (recursive); a stem found twice raises."""
    index: Dict[str, str] = {}
    for p in sorted(glob.glob(os.path.join(glob.escape(directory), "**", "*.wav"), recursive=True)):
        stem = os.path.splitext(os.path.basename(p))[0]
        if stem in index:
            raise ValueError(f"{stem}.wav is in {directory} twice: {index[stem]}, {p}")
        index[stem] = p
    return index


@lru_cache(maxsize=None)
def wav_duration_ms(path: str) -> float:
    """Exact duration of a wav file in ms (header only: the data are memory-mapped, not read)."""
    fs, x = wavfile.read(path, mmap=True)
    return 1000 * x.shape[0] / fs


def file_starts_ms(durations_ms: Sequence[float], fid_st: Sequence[int], fid_et: Sequence[int]) -> np.ndarray:
    """
    Onset of each concatenated file relative to the block onset (ms), plus the block end as the last entry:
    the files' exact durations with the nominal gaps between them (fid_st[i + 1] - fid_et[i], 0 or 900 ms).
    """
    gaps = np.diff(np.c_[fid_et[:-1], fid_st[1:]], axis=1).ravel() if len(fid_st) > 1 else np.zeros(0)
    return np.r_[0.0, np.cumsum(np.asarray(durations_ms, float) + np.r_[gaps, 0.0])]


def read_block_timings(xml_root: str, corpus_dirs: tuple = ()) -> List[BlockTiming]:
    """
    Timing of every block in XML_INFO/PP*/blocks.xml, regardless of usability.

    corpus_dirs: ((corpus, wav directory), ...), e.g. (("CGN", sdc_dir), ("IFADV", ifadv_dir)). Blocks whose wav
    files are all found get their exact duration; the others fall back to the nominal fid_et[-1] - fid_st[0].
    """
    indexes = {corpus: wav_index(d) for corpus, d in corpus_dirs if d}
    timings = []
    for path in sorted(glob.glob(os.path.join(xml_root, "PP*", "blocks.xml"))):
        for el in ET.parse(path).getroot():
            block = {c.tag: (c.text or "").strip() for c in el}
            fid_st = [int(v) for v in block["fid_st"].split(",") if v and v != "NA"]
            fid_et = [int(v) for v in block["fid_et"].split(",") if v and v != "NA"]
            if not fid_st or not fid_et or not block["et_sample"]:
                continue
            index = indexes.get(block.get("corpus"), {})
            fids = [v for v in block.get("fids", "").split(",") if v and v != "NA"]
            if fids and len(fids) == len(fid_st) and all(f in index for f in fids):
                duration = file_starts_ms([wav_duration_ms(index[f]) for f in fids], fid_st, fid_et)[-1]
            else:
                duration = float(fid_et[-1] - fid_st[0])
            inacc = int(block["et_sample"]) - int(block["st_sample"]) - duration
            if abs(inacc) > MAX_INACC_SAMPLES:
                continue
            timings.append(BlockTiming(block["vhdr_fn"], duration, inacc))
    return timings


def estimate_marker_offset(timings: List[BlockTiming]) -> float:
    """
    Constant end-marker offset c (EEG samples), shared by all recordings.

    Per recording, median(inacc) / median(duration) = drift_rec + c / duration, so regressing
    that ratio on 1 / duration across recordings gives c as the slope (Theil-Sen, robust to
    the between-recording spread in drift).
    """
    per_rec = _group(timings)
    inacc = np.array([np.median([t.inacc for t in ts]) for ts in per_rec.values()], dtype=float)
    dur = np.array([np.median([t.duration for t in ts]) for ts in per_rec.values()], dtype=float)
    # scipy's theilslopes sorts its inputs in place, which is harmless here only because
    # these arrays are fresh; keep it that way
    slope, _, _, _ = stats.theilslopes(inacc / dur, 1.0 / dur)
    return float(slope)


def estimate_drift(timings: List[BlockTiming], marker_offset: float | None = None) -> DriftEstimate:
    """
    Per-recording drift: the median over a recording's blocks of (inacc - c) / duration.

    marker_offset fixes c; if None, it is estimated from the timings (estimate_marker_offset).
    """
    if not timings:
        raise ValueError("No block timings to estimate drift from")
    c = estimate_marker_offset(timings) if marker_offset is None else float(marker_offset)
    by_recording = {
        rec: float(np.median([(t.inacc - c) / t.duration for t in ts]))
        for rec, ts in _group(timings).items()
    }
    return DriftEstimate(c, by_recording, float(np.median(list(by_recording.values()))))


@lru_cache(maxsize=4)
def estimate_drift_from_xml(xml_root: str, marker_offset: float | None = None, corpus_dirs: tuple = ()) -> DriftEstimate:
    """estimate_drift over every block in the dataset's XML_INFO directory (cached); see read_block_timings."""
    return estimate_drift(read_block_timings(xml_root, corpus_dirs), marker_offset)


def _group(timings: List[BlockTiming]) -> Dict[str, List[BlockTiming]]:
    groups: Dict[str, List[BlockTiming]] = defaultdict(list)
    for t in timings:
        groups[t.recording].append(t)
    return groups
