"""narayanan2021 pulse-train onset and drift (synthetic Trigger channel)."""
import numpy as np
import pytest

from cnsp_datasets.datasets.narayanan2021.adaptor import pulse_drift, train_onset


def _trigger(starts, n=600_000):
    trig = np.zeros(n)
    for s in starts:
        trig[s:s + 34] = 1
    return trig


def test_stray_pulse_skipped():
    period = 1000 * (1 - 10e-6)
    train = np.round(50_000 + np.arange(390) * period).astype(int)
    trig = _trigger([33_000, *train])  # stray pulse 17 s before the train
    assert train_onset(trig, 1000.0) == train[0]
    assert abs(pulse_drift(trig, 1000.0) + 10e-6) < 1e-6


def test_no_train_raises():
    with pytest.raises(ValueError, match="no 1-s pulse train"):
        train_onset(_trigger([1000, 5000, 9000]), 1000.0)
    with pytest.raises(ValueError, match="no 1-s pulse train"):
        pulse_drift(_trigger([]), 1000.0)


@pytest.mark.parametrize("correct", [False, True])
@pytest.mark.parametrize("frames, n", [(44_100 * 5, 5000), (44_100 * 5 + 1, 5001)])
def test_trial_length(tmp_path, monkeypatch, correct, frames, n):
    """The EEG trial spans ceil(wav samples * fs_eeg / fs_wav) samples (was one more), starting at the train."""
    import mne
    import soundfile

    from cnsp_datasets.datasets.narayanan2021 import adaptor as mod

    wav = tmp_path / "a.wav"
    soundfile.write(wav, np.zeros(frames), 44_100, subtype="PCM_16")
    onset = 2000
    trig = _trigger(onset + np.arange(12) * 1000, n=12_000)
    eeg = np.arange(12_000, dtype=float)
    info = mne.create_info(["Fz", "XtraL", "XtraR", "Trigger"], 1000.0, ["eeg", "misc", "misc", "stim"])
    monkeypatch.setattr(mod, "read_raw_curry",
                        lambda *a, **k: mne.io.RawArray(np.vstack([eeg, eeg, eeg, trig]), info, verbose="ERROR"))
    adaptor = mod.Narayanan2021Adaptor.__new__(mod.Narayanan2021Adaptor)
    adaptor.drift_correction, adaptor._montage = correct, None
    raw = adaptor._eeg_loader("x.dat", soundfile.info(wav))()
    assert raw.ch_names == ["Fz"] and raw.n_times == n and raw.get_data()[0, 0] == onset
