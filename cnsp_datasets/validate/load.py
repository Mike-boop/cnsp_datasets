"""Load TrialRecords into band-passed neural and stimulus arrays for validation."""
import random
from collections import defaultdict

import numpy as np
from scipy.signal import butter, sosfiltfilt

from cnsp_datasets.preprocess.base import get_stim_array
from cnsp_datasets.preprocess.stimulus import HalfWaveRectify, HilbertEnvelope, ResampleStimulus

STIM_FEATURES = ("audio", "envelope")


def group_by_subject(records, n_subjects=None, seed=0):
    """Group records by subject; keep a random subset of n_subjects (all if None)."""
    subjects = defaultdict(list)
    for record in records:
        subjects[record.subject].append(record)
    keys = sorted(subjects)
    if n_subjects is not None and n_subjects < len(keys):
        keys = sorted(random.Random(seed).sample(keys, n_subjects))
    return {k: sorted(subjects[k], key=lambda r: (r.session, r.trial)) for k in keys}


def pick_stimulus(record):
    """The attended speech stimulus if one is marked, else the first; audio preferred over envelope."""
    stims = [s for s in record.stimulus if s.modality == "audio" and s.feature_name in STIM_FEATURES]
    if not stims:
        return None
    stims.sort(key=lambda s: (not s.is_attended, STIM_FEATURES.index(s.feature_name)))
    return stims[0]


def bandpass(x, band, fs, order=4):
    """Zero-phase Butterworth band-pass along the last axis."""
    sos = butter(order, [band[0], min(band[1], 0.45 * fs)], btype="bandpass", fs=fs, output="sos")
    return sosfiltfilt(sos, x, axis=-1)


def load_neural(record, picks, reference=None):
    """
    Raw at its native rate, picked and (for EEG) re-referenced; reference is 'average', channel names or None.
    Channels in info['bads'] are left out of the picks and the average reference when picking by type (MNE keeps
    them unless told); explicitly named channels are kept.
    """
    raw = record.neural_data_fn()
    raw.load_data(verbose="ERROR")
    ref = None
    if reference == "average":
        ref = raw.copy().pick(picks, exclude="bads").get_data().mean(0)
    elif reference:
        ref = raw.get_data(picks=list(reference)).mean(0)
    raw.pick(picks, exclude="bads")
    if ref is not None:
        raw._data -= ref
    return raw


def stimulus_feature(stim, tier, fs, cache):
    """
    Envelope ('low') or high-rate feature ('hf') at fs, cached across subjects. For 'hf': the half-wave-rectified
    waveform from audio, or a shipped envelope sampled at fs or above (None below: no content in the hf bands).
    """
    key = (stim.modality, stim.name, stim.feature_name, tier, fs)
    if key not in cache:
        data = stim.data_fn()
        if tier == "hf" and stim.feature_name != "audio" and data["fs"] < fs:
            cache[key] = None
            return None
        steps = [ResampleStimulus(fs)]
        if stim.feature_name == "audio":
            steps.insert(0, HilbertEnvelope() if tier == "low" else HalfWaveRectify())
        for step in steps:
            data = step.run(data)
        cache[key] = np.atleast_2d(get_stim_array(data)).astype(float).mean(0)
    return cache[key]


def resampled(raw, fs):
    """Data of raw resampled to fs (or to the integer part of the native rate if that is lower), and the rate."""
    fs = min(fs, int(raw.info["sfreq"]))
    if fs == raw.info["sfreq"]:
        return raw.get_data(), fs
    return raw.copy().resample(fs, verbose="ERROR").get_data(), fs
