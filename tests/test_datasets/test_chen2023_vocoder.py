import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt

from cnsp_datasets.datasets.chen2023.vocoder import greenwood_bands, vocode


def test_greenwood_edges():
    edges = greenwood_bands(3)
    assert np.allclose(edges[[0, -1]], [200, 7000])
    assert np.all(np.diff(edges) > 0)


def test_vocode_deterministic_rms_and_envelope():
    fs = 16000
    t = np.arange(4 * fs) / fs
    rng = np.random.default_rng(1)
    x = rng.standard_normal(t.size) * (1 + np.sin(2 * np.pi * 3 * t))  # 3 Hz modulated noise
    y = vocode(x, fs, 4, seed=7)
    assert np.array_equal(y, vocode(x, fs, 4, seed=7))
    band = butter(3, [200, 7000], "bandpass", fs=fs, output="sos")
    assert np.isclose(y.std(), sosfiltfilt(band, x).std(), rtol=1e-6)
    lp = butter(3, 8, "low", fs=fs, output="sos")
    env_x, env_y = (sosfiltfilt(lp, np.abs(hilbert(v))) for v in (x, y))
    assert np.corrcoef(env_x, env_y)[0, 1] > 0.9
