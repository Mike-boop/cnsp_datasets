"""
Clock drift between the EEG amplifier and the stimulus audio in bentum2023.

Only two timing fields per block are measured EEG markers: st_sample (audio onset) and
et_sample (audio offset). fid_st / fid_et are nominal, computed from the audio durations
on the stimulus clock. Their end discrepancy follows

    inacc = et_sample - fid_et[-1] = c + drift_rec * duration

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
from typing import Dict, List

import numpy as np
from scipy import stats
from scipy.interpolate import make_interp_spline

# blocks with larger discrepancies have marker problems, not drift
MAX_INACC_SAMPLES = 1000

# quintic spline: amplitude error ~0.04% at 200 Hz and ~1% at 300 Hz for 1 kHz data
# (linear interpolation loses ~14% at 200 Hz)
SPLINE_ORDER = 5


@dataclass(frozen=True)
class BlockTiming:
    recording: str   # vhdr_fn: one BrainVision recording is one run of the EEG clock
    duration: int    # nominal block duration, fid_et[-1] - fid_st[0] (EEG samples)
    inacc: int       # et_sample - fid_et[-1] (EEG samples)


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


def read_block_timings(xml_root: str) -> List[BlockTiming]:
    """Timing of every block in XML_INFO/PP*/blocks.xml, regardless of usability."""
    timings = []
    for path in sorted(glob.glob(os.path.join(xml_root, "PP*", "blocks.xml"))):
        for el in ET.parse(path).getroot():
            block = {c.tag: (c.text or "").strip() for c in el}
            fid_st = [int(v) for v in block["fid_st"].split(",") if v and v != "NA"]
            fid_et = [int(v) for v in block["fid_et"].split(",") if v and v != "NA"]
            if not fid_st or not fid_et or not block["et_sample"]:
                continue
            inacc = int(block["et_sample"]) - fid_et[-1]
            if abs(inacc) > MAX_INACC_SAMPLES:
                continue
            timings.append(BlockTiming(block["vhdr_fn"], fid_et[-1] - fid_st[0], inacc))
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
def estimate_drift_from_xml(xml_root: str, marker_offset: float | None = None) -> DriftEstimate:
    """estimate_drift over every block in the dataset's XML_INFO directory (cached)."""
    return estimate_drift(read_block_timings(xml_root), marker_offset)


def to_audio_clock(data: np.ndarray, drift: float) -> np.ndarray:
    """
    Resample EEG (n_channels, n_times) from the EEG clock onto the audio clock.

    The EEG clock counts (1 + drift) samples per audio sample, so output sample k is taken
    at EEG position k * (1 + drift) by spline interpolation. Sample 0 is unchanged (the
    block onset marker is the anchor). With drift > 0 the output is slightly shorter than
    the input; the last output sample stays within the input, so nothing is extrapolated.
    """
    n = data.shape[1]
    if drift == 0 or n < SPLINE_ORDER + 1:
        return data
    n_out = int(np.floor((n - 1) / (1 + drift))) + 1
    positions = np.arange(n_out) * (1 + drift)
    spline = make_interp_spline(np.arange(n), data, k=SPLINE_ORDER, axis=1)
    return spline(positions).astype(data.dtype, copy=False)


def _group(timings: List[BlockTiming]) -> Dict[str, List[BlockTiming]]:
    groups: Dict[str, List[BlockTiming]] = defaultdict(list)
    for t in timings:
        groups[t.recording].append(t)
    return groups
