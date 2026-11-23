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


def _white_noise_scores(rng, dur_s, onset_s, ppm, snr, lags):
    """Gaussian ridge (sigma 60 ms) along lag(t) = onset + ppm t, plus noise white along lags and windows (DNN scores
    of 5-s windows at 1-s hop are jagged sample-to-sample along lags; chen2026)."""
    fs, hop = 128, 128
    starts = np.arange(-lags.min(), round(dur_s * fs) - lags.max() - 5 * fs, hop)
    t = (starts + 5 * fs / 2) / fs
    d = lags[:, None] - (onset_s + ppm * 1e-6 * t)[None, :] * fs
    return snr * np.exp(-d ** 2 / (2 * 7.7 ** 2)) + rng.standard_normal(d.shape), starts


def test_upsample_lags_keeps_samples_and_noise_variance():
    from cnsp_datasets.align.scan import upsample_lags
    x = np.random.default_rng(0).standard_normal((121, 2000))
    fine = upsample_lags(x, 8)
    assert fine.shape == (961, 2000)
    np.testing.assert_allclose(fine[::8], x, atol=1e-10)
    variance = [fine[80 + p:-80:8].var() for p in range(8)]   # linear interpolation: 0.5 half-way
    np.testing.assert_allclose(variance, 1, atol=0.03)


def test_joint_fit_noise_has_no_pull_to_zero_drift():
    """On pure noise the drift argmax lands anywhere; linear lag interpolation put it at exactly 0 in half the cases."""
    rng = np.random.default_rng(0)
    lags, grid = np.arange(-80, 41), np.arange(-100, 101.0)
    drifts = [joint_fit(*_white_noise_scores(rng, 300, -0.3, 0, 0, lags), lags, 128, 640,
                        drift_grid_ppm=grid)["drift_ppm"] for _ in range(16)]
    assert np.sum(np.abs(drifts) < 2) <= 2


@pytest.mark.parametrize("ppm", [-50, 50])
def test_joint_fit_recovers_drift_and_shift_in_white_noise(ppm):
    """Known shift (-0.3 s) and drift over 16 noisy 10-min blocks: (almost) no block stuck at 0 ppm, median within
    15 ppm (linear lag interpolation: 4 and 6 of 16 blocks at 0 +- 1 ppm, median error -4 and -18 ppm)."""
    rng = np.random.default_rng(0)
    lags, grid = np.arange(-80, 41), np.arange(-100, 101.0)
    fits = [joint_fit(*_white_noise_scores(rng, 600, -0.3, ppm, 1.5, lags), lags, 128, 640, drift_grid_ppm=grid)
            for _ in range(16)]
    drifts = np.array([f["drift_ppm"] for f in fits])
    assert np.sum(np.abs(drifts) < 1) <= 1
    assert abs(np.median(drifts) - ppm) < 15
    assert np.median([f["onset"] / 128 for f in fits]) == pytest.approx(-0.3, abs=0.01)


def test_joint_fit_exact_without_noise():
    lags = np.arange(-80, 41)
    scores, starts = _white_noise_scores(np.random.default_rng(0), 1200, -0.3, 20, 1, lags)
    scores -= _white_noise_scores(np.random.default_rng(0), 1200, -0.3, 20, 0, lags)[0]   # the noise
    fit = joint_fit(scores, starts, lags, 128, 640, drift_grid_ppm=np.arange(-100, 101.0))
    assert fit["drift_ppm"] == pytest.approx(20, abs=0.1)        # linear lag interpolation: 18.9
    assert fit["onset"] / 128 == pytest.approx(-0.3, abs=0.002)
