"""
Ridge models for validation.

Backward decoders are solved matrix-free by preconditioned conjugate gradients, adapted from trf-toolkit
(trf_toolkit.models.fourier.pcg_ridge): the lagged covariance is block-Toeplitz, so products with it are done by
FFT along the lag axis, and a circulant approximation gives the preconditioner. The (channels * lags)^2 covariance
is never formed or factorised. Edge effects (zero padding) are ignored: the lagged autocorrelations are treated as
exactly Toeplitz, an O(lags / samples) approximation.

Forward TRFs of a single stimulus feature are solved directly from circular correlations.
Regularisation is relative: lambda = alpha * mean eigenvalue of the lagged covariance.
"""
import numpy as np
from scipy.fft import irfft, next_fast_len, rfft
from scipy.linalg import toeplitz
from scipy.signal import get_window


def corr(a, b):
    """Column-wise Pearson correlation of two (n, V) arrays."""
    a, b = a - a.mean(0), b - b.mean(0)
    return (a * b).sum(0) / np.sqrt((a ** 2).sum(0) * (b ** 2).sum(0))


# --------------------------------------------------------------------------- backward models (PCG)

def lagged_stats(x, Y, n_lags, b_lags=None):
    """
    Lagged statistics of neural data x (channels, n) for decoders y(t) = sum_j w[:, j] . x[:, t + j].

    Returns A (n_lags, channels, channels), A[d] = sum_u x(u) x(u + d)', and B (channels, len(b_lags), V),
    B[:, i] = sum_t x(t + b_lags[i]) Y(t); b_lags defaults to 0 .. n_lags - 1.
    """
    n = x.shape[1]
    b_lags = range(n_lags) if b_lags is None else b_lags
    A = np.stack([x[:, :n - d] @ x[:, d:].T for d in range(n_lags)])
    B = np.stack([x[:, j:] @ Y[:n - j] if j >= 0 else x[:, :n + j] @ Y[-j:] for j in b_lags], axis=1)
    return A, B


def _symbol(A, n_fft, taper=None):
    """DFT over the lag axis of the block-Toeplitz kernel G(m) = A(-m), m = -(L-1) .. L-1 (wrapped onto n_fft)."""
    L = len(A)
    G = np.concatenate([A[:0:-1], A.transpose(0, 2, 1)])
    if taper:
        G = G * get_window(taper, 2 * L - 1, fftbins=False)[:, None, None]
    grid = np.zeros((n_fft,) + A.shape[1:])
    np.add.at(grid, np.arange(-(L - 1), L) % n_fft, G)
    return rfft(grid, axis=0)


def _conv(S, n_fft, V):
    """Circular convolution along the lag axis with symbol S (n_freqs, C, C); V (C, L, K)."""
    Vf = rfft(V, n=n_fft, axis=1).transpose(1, 0, 2)
    return irfft(S @ Vf, n=n_fft, axis=0)[:V.shape[1]].transpose(1, 0, 2)


def _pcg(matvec, precond, B, tol=1e-6, max_iter=500):
    """Preconditioned conjugate gradients for an SPD operator, independent systems per column of B (C, L, K)."""
    ax = (0, 1)
    X = np.zeros_like(B)
    R = B.copy()
    Z = precond(R)
    P = Z.copy()
    rz = np.sum(R * Z, axis=ax)
    bnorm = np.sqrt(np.sum(B * B, axis=ax))
    bnorm = np.where(bnorm > 0, bnorm, 1.0)
    for it in range(1, max_iter + 1):
        AP = matvec(P)
        pap = np.sum(P * AP, axis=ax)
        step = np.divide(rz, pap, out=np.zeros_like(rz), where=pap > 0)
        X += step * P
        R -= step * AP
        if np.all(np.sqrt(np.sum(R * R, axis=ax)) <= tol * bnorm):
            return X, it
        Z = precond(R)
        rz_new = np.sum(R * Z, axis=ax)
        beta = np.divide(rz_new, rz, out=np.zeros_like(rz), where=rz > 0)
        P = Z + beta * P
        rz = rz_new
    return X, max_iter


def ridge_pcg(A, B, alpha=1.0, tol=1e-6):
    """Solve (T(A) + lambda I) W = B, T the block-Toeplitz lagged covariance; W (channels, lags, V)."""
    L = len(A)
    lam = alpha * np.trace(A[0]) / A.shape[1]
    n = next_fast_len(2 * L - 1, real=True)
    S = _symbol(A, n)
    n_p = next_fast_len(2 * L, real=True)
    e, U = np.linalg.eigh(_symbol(A, n_p, taper="hann"))
    M_inv = (U / (np.clip(e, 0, None) + lam)[:, None, :]) @ np.conj(U.transpose(0, 2, 1))
    return _pcg(lambda V: _conv(S, n, V) + lam * V, lambda R: _conv(M_inv, n_p, R), B, tol)[0]


def spectral_grid(n_lags):
    """Grid size N, autocorrelation lags 0 .. M and cross-correlation lags of the spectral solver."""
    N = next_fast_len(4 * n_lags, real=True)
    lo = (n_lags - 1) // 2 - N // 2
    return N, (N - 1) // 2, np.arange(lo, lo + N)


def ridge_spectral(A, B, b_lags, n_lags, alpha=1.0):
    """
    Spectral ridge (trf_toolkit.models.fourier, solver='spectral'): per-bin solves on a circular grid.

    A (M + 1, C, C) autocorrelations (Bartlett-tapered), B (C, N, V) cross-correlations at b_lags (see
    spectral_grid). The lag window is not imposed a priori; the solution is read out at lags 0 .. n_lags - 1.
    """
    N = len(b_lags)
    lam = alpha * np.trace(A[0]) / A.shape[1]
    S = _symbol(A, N, taper="bartlett")
    grid = np.zeros((N,) + B.transpose(1, 0, 2).shape[1:])
    grid[np.asarray(b_lags) % N] = B.transpose(1, 0, 2)
    e, U = np.linalg.eigh(S)
    Z = np.conj(U.transpose(0, 2, 1)) @ rfft(grid, axis=0)
    H = U @ (Z / (e + lam)[:, :, None])
    return irfft(H, n=N, axis=0)[:n_lags].transpose(1, 0, 2)


def reconstruct(x, w):
    """Decoder output sum_j w[:, j] . x[:, t + j] for x (channels, n), w (channels, lags)."""
    n = x.shape[1]
    r = np.zeros(n)
    for j in range(w.shape[1]):
        r[:n - j] += w[:, j] @ x[:, j:]
    return r


def backward_cv(neural, targets, n_lags, n_folds=5, alpha=1.0, solver="pcg"):
    """
    Cross-validated decoding of every target column from lagged neural data, scored per held-out trial.

    neural: list of (channels, n_i) arrays (zero-mean), one per trial; targets: list of (n_i, V) arrays.
    Trials are split into contiguous folds; solver is 'pcg' (exact) or 'spectral'. Returns scores (trials, V)
    (Pearson r from held-out lagged statistics) and the held-out reconstructions of target column 0.
    """
    if solver == "spectral":
        N, M, b_lags = spectral_grid(n_lags)
        stats = [lagged_stats(x, y, M + 1, b_lags) for x, y in zip(neural, targets)]
        own = slice(-b_lags[0], -b_lags[0] + n_lags)  # columns of B at lags 0 .. n_lags - 1
        solve = lambda A, B: ridge_spectral(A, B, b_lags, n_lags, alpha)  # noqa: E731
    else:
        stats = [lagged_stats(x, y, n_lags) for x, y in zip(neural, targets)]
        own = slice(None)
        solve = lambda A, B: ridge_pcg(A, B, alpha)  # noqa: E731
    A_tot, B_tot = sum(s[0] for s in stats), sum(s[1] for s in stats)
    n = next_fast_len(2 * n_lags - 1, real=True)
    scores = np.zeros((len(neural), targets[0].shape[1]))
    recon = [None] * len(neural)
    for idx in np.array_split(np.arange(len(neural)), min(n_folds, len(neural))):
        W = solve(A_tot - sum(stats[i][0] for i in idx), B_tot - sum(stats[i][1] for i in idx))
        for i in idx:
            A, B = stats[i][0][:n_lags], stats[i][1][:, own]
            spy = np.einsum("clv,clv->v", W, B)
            spp = np.einsum("clv,clv->v", W, _conv(_symbol(A, n), n, W))
            scores[i] = spy / np.sqrt(spp * (targets[i] ** 2).sum(0))
            recon[i] = reconstruct(neural[i], W[:, :, 0])
    return scores, recon


# --------------------------------------------------------------------------- forward TRFs (circular)

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


def forward_trf(acorr, xc, alpha=1.0):
    """Ridge forward TRFs (..., channels, lags) from summed autocorrelation and cross-correlations."""
    A = toeplitz(acorr) + alpha * acorr[0] * np.eye(len(acorr))
    return xc @ np.linalg.inv(A)
