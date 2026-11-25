import mne
import numpy as np
import pytest

from cnsp_datasets.standardise.clock import crop_on_audio_clock


@pytest.mark.parametrize("drift", [0.0, 8e-6, -46e-6])
def test_crop_on_audio_clock_applies_small_drift(drift):
    """Output sample k must be the recording at onset + k (1 + drift), also for drifts of a few ppm."""
    t = np.arange(200_000) / 1000
    raw = mne.io.RawArray(np.sin(2 * np.pi * 3 * t)[None, :], mne.create_info(1, 1000.0, "mag"), verbose="ERROR")
    y = crop_on_audio_clock(raw, 6, 190_000, drift).get_data()[0]
    k = np.arange(190_000)
    assert len(y) == 190_000
    assert np.abs(y - np.sin(2 * np.pi * 3 * (6 + k * (1 + drift)) / 1000)).max() < 1e-9


def test_crop_on_audio_clock_decimates():
    raw = mne.io.RawArray(np.random.default_rng(0).standard_normal((2, 12_000)), mne.create_info(2, 1200.0, "mag"),
                          verbose="ERROR")
    out = crop_on_audio_clock(raw, 100.5, 5000, 5.7e-6, sfreq_out=1000)
    assert out.info["sfreq"] == 1000 and out.n_times == 5000


def test_truncated_trial_is_logged_or_raises(caplog):
    raw = mne.io.RawArray(np.zeros((1, 1000)), mne.create_info(1, 1000.0, "eeg"), verbose="ERROR")
    with caplog.at_level("WARNING", logger="cnsp_datasets"):
        out = crop_on_audio_clock(raw, 900, 200)
    assert out.n_times == 100 and "ends 100 of 200" in caplog.text
    with pytest.raises(ValueError, match="ends 100 of 200"):
        crop_on_audio_clock(raw, 900, 200, strict=True)


def test_large_positions_are_interpolated_not_snapped():
    """maddox_base used np.allclose, which rounded fractional positions near 1e6 to the nearest sample."""
    from cnsp_datasets.standardise.clock import resample_on_audio_clock
    n = 1_200_000
    x = np.sin(2 * np.pi * 0.37 * np.arange(n) / 1000)[None, :]
    onset = 1_000_000.3
    y = resample_on_audio_clock(lambda a, b: x[:, a:b], n, 1000.0, onset, 1000)[0]
    expected = np.sin(2 * np.pi * 0.37 * (onset + np.arange(1000)) / 1000)
    assert np.abs(y - expected).max() < 1e-9


def test_to_audio_clock_matches_positions():
    from cnsp_datasets.standardise.clock import to_audio_clock
    x = np.sin(2 * np.pi * 2 * np.arange(10_000) / 1000)[None, :]
    drift = 50e-6
    y = to_audio_clock(x, drift)[0]
    k = np.arange(len(y))
    assert np.abs(y - np.sin(2 * np.pi * 2 * k * (1 + drift) / 1000)).max() < 1e-9
