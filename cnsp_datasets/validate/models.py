"""
Forward TRF models for validation: a single stimulus feature predicting every channel.

Solved directly from circular (per-trial) correlations, so circularly shifted stimulus nulls are index shifts of one
cross-correlation. Regularisation is relative: lambda = alpha * stimulus variance (the mean eigenvalue of the lagged
stimulus covariance).
"""
import numpy as np
from scipy.fft import irfft, rfft
from scipy.linalg import toeplitz


def corr(a, b):
    """Column-wise Pearson correlation of two (n, V) arrays."""
    a, b = a - a.mean(0), b - b.mean(0)
    return (a * b).sum(0) / np.sqrt((a ** 2).sum(0) * (b ** 2).sum(0))


def autocorr(s, n_lags):
    """Circular autocorrelation of s at lags 0 .. n_lags - 1."""
    return irfft(np.abs(rfft(s)) ** 2, n=len(s))[:n_lags]


def xcorr(x, s, lags, shifts):
    """
    Circular cross-correlation g[c, k] = sum_t x[c, t] s[t - k] at k = lags + shift, for each shift.

    Shift 0 is the given alignment; shift k equals using np.roll(s, k), so circular-shift nulls cost nothing extra.
    Returns (len(shifts), channels, len(lags)).
    """
    g = irfft(rfft(x, axis=-1) * np.conj(rfft(s)), n=x.shape[-1], axis=-1)
    return g[:, (np.asarray(shifts)[:, None] + lags[None, :]) % x.shape[-1]].transpose(1, 0, 2)


def convolve(s, trf, lags, n):
    """Circular prediction sum_k trf[..., k] s(t - lags[k]) for s (n,) and trf (..., C, L); returns (..., C, n)."""
    k = np.zeros(trf.shape[:-1] + (n,))
    k[..., np.asarray(lags) % n] = trf
    return irfft(rfft(k, axis=-1) * rfft(s), n=n, axis=-1)


def peak_shift(x, pred, max_shift):
    """
    Shift d (samples; sub-sample by parabolic interpolation) maximising sum_c sum_t x_c(t) pred_c(t - d),
    for |d| <= max_shift; NaN if the maximum is at the search edge (no peak within the range).

    Positive d: x fits best with the prediction delayed by d.
    """
    n = x.shape[-1]
    g = irfft((rfft(x, axis=-1) * np.conj(rfft(pred, axis=-1))).sum(0), n=n)
    d = np.arange(-max_shift, max_shift + 1)
    y = g[d % n]
    i = int(np.argmax(y))
    if i in (0, len(y) - 1):
        return np.nan
    a, b, c = y[i - 1:i + 2]  # b is the maximum, so the vertex lies within half a sample of d[i]
    return float(d[i] + (0.5 * (a - c) / (a - 2 * b + c) if a - 2 * b + c < 0 else 0.0))


def forward_trf(acorr, xc, alpha=1.0):
    """Ridge forward TRFs (..., channels, lags) from summed autocorrelation and cross-correlations."""
    A = toeplitz(acorr) + alpha * acorr[0] * np.eye(len(acorr))
    return xc @ np.linalg.inv(A)
