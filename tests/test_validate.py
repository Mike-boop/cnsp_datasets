import mne
import numpy as np
from scipy.signal import resample_poly

from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord
from cnsp_datasets.validate import group_by_subject, validate

FS_AUDIO, FS, DUR = 8000, 1000, 40


def _records(offset=0.0, jitter=0.0, drift_ppm=0.0, gain=1.0, dc=0.0, silence=0.0, n_subjects=3, n_trials=4,
             seed=0):
    """
    Synthetic EEG with an envelope response at 100 ms and a rectified-waveform response at 7 ms.

    offset: constant delay (s); jitter: SD of an extra per-trial delay (s); drift_ppm: EEG clock running fast;
    gain: response amplitude; dc: per-channel DC offset (V); silence: silent lead-in and tail of the audio (s).
    """
    rng = np.random.default_rng(seed)
    stories = []
    for _ in range(n_trials):
        env = np.repeat(rng.random(DUR * 4) ** 2, FS_AUDIO // 4)
        audio = env * rng.standard_normal(DUR * FS_AUDIO)
        quiet = int(silence * FS_AUDIO)
        if quiet:
            audio[:quiet] = audio[-quiet:] = 0
        stories.append(audio)
    info = mne.create_info([f"E{i}" for i in range(8)], FS, "eeg")
    records = []
    for sub in range(n_subjects):
        for trial, audio in enumerate(stories):
            hwr = resample_poly(np.maximum(audio, 0), 1, FS_AUDIO // FS)
            env = resample_poly(np.abs(audio), 1, FS_AUDIO // FS)
            sig = 2 * np.roll(env - env.mean(), 100) / env.std() + 0.5 * np.roll(hwr - hwr.mean(), 7) / hwr.std()
            sig *= gain
            sig = np.roll(sig, int((offset + jitter * rng.standard_normal()) * FS))
            t = np.arange(len(sig))
            sig = np.interp(t / (1 + drift_ppm * 1e-6), t, sig)  # sample k of the EEG is stimulus time k / (1 + d)
            eeg = 1e-6 * (sig + 3 * rng.standard_normal((8, len(sig)))) + dc * rng.standard_normal((8, 1))
            stim = StimulusRecord("audio", f"story{trial}", lambda a=audio: {"fs": FS_AUDIO, "data": a[None]})
            records.append(TrialRecord(sub, 1, trial, "c", "eeg", stim,
                                       lambda d=eeg: mne.io.RawArray(d, info, verbose="ERROR")))
    return records


def test_aligned_passes_all_tiers():
    result = validate(group_by_subject(_records()), picks="eeg", n_jobs=3)
    s = result["summary"]
    assert s["low"]["pass"] and s["mlr"]["pass"] and s["brainstem"]["pass"], s
    assert abs(s["low"]["trf_peak_s"] - 0.1) < 0.03, s["low"]["trf_peak_s"]
    assert s["low"]["jitter_sd_ms"] < 10, s["low"]["jitter_sd_ms"]
    assert not any(t["flags"] for sub in result["subjects"] for t in sub["trials"])


def test_constant_offset_shifts_trf_peak():
    s = validate(group_by_subject(_records(offset=0.3)), picks="eeg", n_jobs=3, tiers=["low"])["summary"]
    assert abs(s["low"]["trf_peak_s"] - 0.4) < 0.03, s["low"]["trf_peak_s"]


def test_low_tier_at_native_rate_below_64_hz():
    """EEG kept at 50 Hz (not upsampled to 64): lags in seconds still match the 50 Hz samples."""
    records = _records(offset=0.2, n_subjects=2)
    for r in records:
        r.neural_data_fn = lambda f=r.neural_data_fn: f().resample(50, verbose="ERROR")
    s = validate(group_by_subject(records), picks="eeg", n_jobs=2, tiers=["low"])["summary"]
    assert abs(s["low"]["trf_peak_s"] - 0.3) < 0.03, s["low"]["trf_peak_s"]


def test_jitter_and_drift_are_estimated():
    s = validate(group_by_subject(_records(jitter=0.04, n_trials=8)), picks="eeg", n_jobs=3, tiers=["low"])["summary"]
    assert 25 < s["low"]["jitter_sd_ms"] < 60, s["low"]["jitter_sd_ms"]
    s = validate(group_by_subject(_records(drift_ppm=2000)), picks="eeg", n_jobs=3, tiers=["low"])["summary"]
    assert abs(s["low"]["drift_ppm_median"] - 2000) < 500, s["low"]["drift_ppm_median"]


def test_no_response_does_not_pass():
    """Null calibration: offsets that ring when filtered, silent stimulus edges, and no response at all."""
    records = _records(gain=0.0, dc=1e-3, silence=2.0, n_subjects=4)
    s = validate(group_by_subject(records), picks="eeg", n_jobs=4)["summary"]
    assert s["validation_tier"] == "none", s
