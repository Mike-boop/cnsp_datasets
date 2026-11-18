import mne
import numpy as np
from scipy.signal import resample_poly

from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord
from cnsp_datasets.validate import group_by_subject, validate
from cnsp_datasets.validate.checks import LOW

FS_AUDIO, FS, DUR = 8000, 1000, 40


def _records(offset=0.0, n_subjects=3, n_trials=4, seed=0):
    """Synthetic EEG with an envelope response at 100 ms and a rectified-waveform response at 7 ms."""
    rng = np.random.default_rng(seed)
    stories = []
    for _ in range(n_trials):
        env = np.repeat(rng.random(DUR * 4) ** 2, FS_AUDIO // 4)
        stories.append(env * rng.standard_normal(DUR * FS_AUDIO))
    info = mne.create_info([f"E{i}" for i in range(8)], FS, "eeg")
    records = []
    for sub in range(n_subjects):
        for trial, audio in enumerate(stories):
            hwr = resample_poly(np.maximum(audio, 0), 1, FS_AUDIO // FS)
            env = resample_poly(np.abs(audio), 1, FS_AUDIO // FS)
            sig = 2 * np.roll(env - env.mean(), 100) / env.std() + 0.5 * np.roll(hwr - hwr.mean(), 7) / hwr.std()
            sig = np.roll(sig, int(offset * FS))
            eeg = 1e-6 * (sig + 3 * rng.standard_normal((8, len(sig))))
            stim = StimulusRecord("audio", f"story{trial}", lambda a=audio: {"fs": FS_AUDIO, "data": a[None]})
            records.append(TrialRecord(sub, 1, trial, "c", "eeg", stim,
                                       lambda d=eeg: mne.io.RawArray(d, info, verbose="ERROR")))
    return records


def test_aligned_passes_all_tiers():
    result = validate(group_by_subject(_records()), picks="eeg", n_jobs=3)
    s = result["summary"]
    assert s["low"]["pass"] and s["mlr"]["pass"] and s["brainstem"]["pass"], s
    assert abs(s["low"]["sweep_peak_s"]) <= LOW["sweep_tol"]
    assert not any(t["flags"] for sub in result["subjects"] for t in sub["trials"])


def test_offset_is_detected():
    result = validate(group_by_subject(_records(offset=0.3)), picks="eeg", n_jobs=3)
    s = result["summary"]
    # the sweep only localises an offset to within the decoder window (0-250 ms), so test detection
    assert not s["low"]["pass"]
    assert s["low"]["sweep_peak_s"] > LOW["sweep_tol"], s["low"]["sweep_peak_s"]


def test_ridge_pcg_matches_direct_solve():
    from cnsp_datasets.validate.models import lagged_stats, ridge_pcg
    rng = np.random.default_rng(1)
    x = np.cumsum(rng.standard_normal((6, 3000)), 1)
    x -= x.mean(1, keepdims=True)
    Y = rng.standard_normal((3000, 3))
    A, B = lagged_stats(x, Y, 9)
    C, L = 6, 9
    T = np.zeros((C, L, C, L))
    for j in range(L):
        for k in range(L):
            T[:, j, :, k] = A[k - j] if k >= j else A[j - k].T
    T = T.reshape(C * L, C * L)
    lam = np.trace(A[0]) / C
    W = np.linalg.solve(T + lam * np.eye(C * L), B.reshape(C * L, -1)).reshape(C, L, -1)
    assert np.allclose(ridge_pcg(A, B, alpha=1.0, tol=1e-10), W, rtol=1e-6, atol=1e-8 * np.abs(W).max())
