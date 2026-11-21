"""
Cut a trial out of a continuous recording on the audio clock, keeping the recording's channel info (MEG sensors).

drift: the neural clock counts (1 + drift) samples per audio-clock sample (drift > 0: neural clock fast), as in
bentum2023/drift.py and maddox_base. Output sample k is read at onset + k * step * (1 + drift) (neural samples,
step = sfreq / sfreq_out) with one quintic-spline interpolation, after an anti-alias low-pass when decimating
(as maddox_base.common.load_trial); integer positions are copied without interpolation.
"""
from __future__ import annotations

import mne
import numpy as np
from scipy.interpolate import make_interp_spline
from scipy.signal import firwin, oaconvolve

SPLINE_ORDER = 5


def antialias(sfreq: float, sfreq_out: float) -> np.ndarray:
    """Low-pass FIR (Kaiser, as scipy.signal.resample_poly) for decimating sfreq -> sfreq_out."""
    factor = sfreq / sfreq_out
    half = int(np.ceil(10 * factor))
    return firwin(2 * half + 1, 1 / factor, window=("kaiser", 5.0))


def crop_on_audio_clock(raw: mne.io.BaseRaw, onset: float, n_out: int, drift: float = 0.0, picks=None,
                        sfreq_out: float | None = None) -> mne.io.RawArray:
    """
    n_out samples (at sfreq_out; default and maximum: the recording's rate) starting at `onset` (neural samples
    from the first sample of `raw`, may be fractional), on the audio clock. Stops early at the end of the recording.
    """
    sfreq = raw.info["sfreq"]
    sfreq_out = sfreq if sfreq_out is None else min(sfreq_out, sfreq)
    positions = onset + np.arange(n_out) * (sfreq / sfreq_out) * (1 + drift)
    positions = positions[positions <= raw.n_times - 1]
    if positions.size == 0 or positions[0] < 0:
        raise ValueError(f"trial at sample {onset} lies outside the recording ({raw.n_times} samples)")
    raw = raw.copy().pick(picks) if picks is not None else raw
    fir = antialias(sfreq, sfreq_out) if sfreq_out < sfreq else None
    pad = (len(fir) // 2 if fir is not None else 0) + SPLINE_ORDER + 1
    if fir is None and np.all(np.abs(positions - np.round(positions)) < 1e-6):
        idx = np.round(positions).astype(int)
        data = raw.get_data(start=idx[0], stop=idx[-1] + 1)
    else:
        first = max(int(np.floor(positions[0])) - pad, 0)
        last = min(int(np.ceil(positions[-1])) + pad + 1, raw.n_times)
        data = raw.get_data(start=first, stop=last)
        if fir is not None:
            data = oaconvolve(data, fir[None, :], mode="same", axes=1)
        data = make_interp_spline(np.arange(first, last), data, k=SPLINE_ORDER, axis=1)(positions)
    info = raw.info.copy()
    if sfreq_out != sfreq:
        with info._unlock():
            info["sfreq"] = sfreq_out
            info["lowpass"] = min(info["lowpass"], sfreq_out / 2)
    return mne.io.RawArray(data, info, verbose="ERROR")
