"""
Cut a trial out of a continuous recording on the audio clock: the one resampler of the package.

drift: the neural clock counts (1 + drift) samples per audio-clock sample (drift > 0: neural clock fast), as in
bentum2023/drift.py and maddox_base. Output sample k is read at onset + k * step * (1 + drift) (neural samples,
step = sfreq / sfreq_out) with one quintic-spline interpolation, after an anti-alias low-pass when decimating;
integer positions (no drift, integer onset, no decimation) are copied without interpolation.

If the recording ends before the trial does, the output is shorter and a warning is logged (it ends up in the
standardisation log, cnsp_datasets.log); `strict=True` raises instead.
"""
from __future__ import annotations

import logging
from typing import Callable

import mne
import numpy as np
from scipy.interpolate import make_interp_spline
from scipy.signal import firwin, oaconvolve

log = logging.getLogger(__name__)

SPLINE_ORDER = 5
INTEGER_TOL = 1e-6  # positions closer than this to an integer (in samples) are copied, not interpolated


def antialias(sfreq: float, sfreq_out: float) -> np.ndarray:
    """Low-pass FIR (Kaiser, as scipy.signal.resample_poly) for decimating sfreq -> sfreq_out."""
    factor = sfreq / sfreq_out
    half = int(np.ceil(10 * factor))
    return firwin(2 * half + 1, 1 / factor, window=("kaiser", 5.0))


def positions_on_audio_clock(onset: float, n_out: int, sfreq: float, sfreq_out: float, drift: float = 0.0):
    """Neural-sample positions of the n_out output samples."""
    return onset + np.arange(n_out) * (sfreq / sfreq_out) * (1 + drift)


def resample_on_audio_clock(read: Callable[[int, int], np.ndarray], n_times: int, sfreq: float, onset: float,
                            n_out: int, drift: float = 0.0, sfreq_out: float | None = None, strict: bool = False,
                            label: str = "recording") -> np.ndarray:
    """
    Core of the module on arrays. read(start, stop) returns samples [start, stop) of the recording,
    shape (n_channels, stop - start); n_times: its length. Returns (n_channels, n) with n = n_out unless the
    recording ends first (then fewer, with a warning; strict: ValueError). sfreq_out: output rate (default and
    maximum: sfreq; never upsampled). Raises if the trial starts before the recording.
    """
    sfreq_out = sfreq if sfreq_out is None else min(sfreq_out, sfreq)
    positions = positions_on_audio_clock(onset, n_out, sfreq, sfreq_out, drift)
    if positions[0] < 0:
        raise ValueError(f"{label}: trial starts at sample {onset}, before the recording")
    inside = positions <= n_times - 1
    if not inside.all():
        msg = (f"{label}: the recording ({n_times} samples) ends {np.sum(~inside)} of {n_out} output samples "
               f"before the trial does (onset {onset:.3f})")
        if strict:
            raise ValueError(msg)
        log.warning(msg)
        positions = positions[inside]
    if positions.size == 0:
        raise ValueError(f"{label}: trial at sample {onset} lies outside the recording ({n_times} samples)")
    fir = antialias(sfreq, sfreq_out) if sfreq_out < sfreq else None
    if fir is None and np.all(np.abs(positions - np.round(positions)) < INTEGER_TOL):
        idx = np.round(positions).astype(int)
        return read(idx[0], idx[-1] + 1)[:, idx - idx[0]]
    pad = (len(fir) // 2 if fir is not None else 0) + SPLINE_ORDER + 1
    first = max(int(np.floor(positions[0])) - pad, 0)
    last = min(int(np.ceil(positions[-1])) + pad + 1, n_times)
    data = read(first, last)
    if fir is not None:
        data = oaconvolve(data, fir[None, :], mode="same", axes=1)
    return make_interp_spline(np.arange(first, last), data, k=SPLINE_ORDER, axis=1)(positions)


def crop_on_audio_clock(raw: mne.io.BaseRaw, onset: float, n_out: int, drift: float = 0.0, picks=None,
                        sfreq_out: float | None = None, strict: bool = False) -> mne.io.RawArray:
    """
    n_out samples (at sfreq_out; default and maximum: the recording's rate) starting at `onset` (neural samples
    from the first sample of `raw`, may be fractional), on the audio clock, keeping the recording's channel info.
    If the recording ends first the result is shorter and a warning is logged (strict: ValueError).
    """
    raw = raw.copy().pick(picks) if picks is not None else raw
    sfreq = raw.info["sfreq"]
    sfreq_out = sfreq if sfreq_out is None else min(sfreq_out, sfreq)
    label = str(raw.filenames[0]) if getattr(raw, "filenames", None) and raw.filenames[0] else "recording"
    data = resample_on_audio_clock(lambda a, b: raw.get_data(start=a, stop=b), raw.n_times, sfreq, onset, n_out,
                                   drift, sfreq_out, strict, label)
    info = raw.info.copy()
    if sfreq_out != sfreq:
        with info._unlock():
            info["sfreq"] = sfreq_out
            info["lowpass"] = min(info["lowpass"], sfreq_out / 2)
    return mne.io.RawArray(data, info, verbose="ERROR")


def to_audio_clock(data: np.ndarray, drift: float) -> np.ndarray:
    """
    A whole array (n_channels, n_times) from the neural clock onto the audio clock, anchored at sample 0: output
    sample k is read at k * (1 + drift). With drift > 0 the output is shorter; nothing is extrapolated.
    """
    n = data.shape[1]
    if drift == 0 or n < SPLINE_ORDER + 1:
        return data
    n_out = int(np.floor((n - 1) / (1 + drift))) + 1
    out = resample_on_audio_clock(lambda a, b: data[:, a:b], n, 1.0, 0.0, n_out, drift)
    return out.astype(data.dtype, copy=False)
