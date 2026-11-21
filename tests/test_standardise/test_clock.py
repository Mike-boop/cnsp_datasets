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
