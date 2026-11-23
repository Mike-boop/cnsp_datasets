import numpy as np
import pytest

from cnsp_datasets.align.scan import correct_drift, joint_fit, peak_offset, pooled_drift

FS, SEG = 256, 5 * 256


def _ridge_scores(centre_ms, ppm, lags, starts, noise, rng):
    """Per-window scores with a smooth ridge along the true lag line, plus lag-correlated noise."""
    t = (starts + SEG / 2) / FS
    true = centre_ms * FS / 1000 + ppm * 1e-6 * (t - t.mean()) * FS
    scores = np.exp(-((lags[:, None] - true[None, :]) / (0.03 * FS)) ** 2)
    smooth = np.exp(-(np.arange(-15, 16) / 5.0) ** 2)
    n = np.apply_along_axis(lambda c: np.convolve(c, smooth / smooth.sum() * 3, "same"), 0,
                            rng.normal(size=scores.shape))
    return scores + noise * n


def test_peak_offset():
    assert peak_offset(-(np.arange(10) - 4.3) ** 2) == pytest.approx(4.3)
    assert peak_offset(np.arange(5.0)) == 4


def test_joint_fit_recovers_drift_and_onset():
    rng = np.random.default_rng(0)
    lags = np.arange(-90, 91)
    starts = np.arange(90, 90 + 800 * FS, FS)
    scores = _ridge_scores(-50, -40, lags, starts, 0.5, rng)
    fit = joint_fit(scores, starts, lags, FS, SEG, drift_grid_ppm=np.arange(-100, 100.5, 0.5))
    assert abs(fit["drift_ppm"] + 40) < 3 * fit["drift_se"] + 1
    assert 1000 * fit["centre_lag"] / FS == pytest.approx(-50, abs=1)
    t_centre = fit["t_centre"]
    assert fit["onset"] == pytest.approx(fit["centre_lag"] + 40e-6 * t_centre * FS, abs=0.5)
    assert fit["drift_se"] < 10


def test_pooled_drift_shares_drift_but_not_onsets():
    rng = np.random.default_rng(1)
    lags = np.arange(-90, 91)
    starts = np.arange(90, 90 + 600 * FS, FS)
    grid = np.arange(-100, 100.5, 0.5)
    centres = [-60, -45, -52, -55, -48, -58]
    fits = [joint_fit(_ridge_scores(c, -30, lags, starts, 0.8, rng), starts, lags, FS, SEG, drift_grid_ppm=grid)
            for c in centres]
    pooled = pooled_drift(fits, FS)
    assert abs(pooled["drift_ppm"] + 30) < 3 * pooled["drift_se"] + 2
    assert pooled["drift_se"] < np.mean([f["drift_se"] for f in fits])   # pooling is more precise than one block
    np.testing.assert_allclose(1000 * pooled["centre_lags"] / FS, centres, atol=2)


def test_correct_drift_makes_lag_constant():
    fs = 1024
    f = lambda t: np.sin(2 * np.pi * 3.1 * t) + 0.5 * np.sin(2 * np.pi * 17.3 * t + 1)
    t = np.arange(120 * fs) / fs
    onset, ppm = 0.057, -40.0
    eeg = f(t + onset + ppm * 1e-6 * t)[None]
    corrected = correct_drift(eeg, ppm)[0]
    u = np.arange(len(corrected)) / fs
    assert np.abs(corrected - f(u + onset))[fs:-fs].max() < 1e-3
