import numpy as np
import torch
import torch.nn.functional as F

from cnsp_datasets.align.classifiers import SimilarityDetector


@torch.no_grad()
def model_features(model: SimilarityDetector, eeg: torch.Tensor, stim: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    '''
    Run the EEG and stimulus towers of a SimilarityDetector over whole recordings.

    The towers are convolutions without padding, so feature sample u depends only on input samples
    u .. u + receptive_field - 1. Slicing these features therefore gives exactly what the model
    computes for a segment, and any segment and lag can be scored without re-running the towers.

    eeg: (channels, time), stim: (features, time). Returns (filters, time - receptive_field + 1) each.
    '''
    e = model.eeg_spatial_filter(eeg[None])
    s = stim[None]
    for i in range(model.n_layers):
        e = model.activation(model.eeg_projections[i](e))
        s = model.activation(model.stimfeat_projections[i](s))
    return e[0], s[0]


@torch.no_grad()
def lag_scores(
        model: SimilarityDetector,
        eeg: np.ndarray,
        stim: np.ndarray,
        lags: np.ndarray,
        segment_length: int,
        hop: int,
        device: str = "cpu",
        window_batch: int = 64,
        ) -> tuple[np.ndarray, np.ndarray]:
    '''
    Model scores for EEG segments paired with stimulus segments at a range of lags.

    EEG segment [t, t + segment_length) is paired with stimulus segment [t + lag, t + lag + segment_length),
    so a positive best lag means the stimulus has to be moved earlier by that many samples to match
    the EEG the way it was matched during training. Window onsets t are spaced by hop and chosen so that
    every lag stays inside both recordings, so all lags are scored on the same EEG windows.

    eeg: (channels, time) and stim: (features, time) at the model's sample rate, preprocessed as for
    training (e.g. SessionDataset.eeg / .story), aligned at sample 0. lags, segment_length and hop are
    in samples.

    Returns (scores, starts): scores (n_lags, n_windows) and the EEG window onsets in samples.
    '''
    model.eval()
    lags = np.asarray(lags, dtype=int)
    E, S = model_features(
        model,
        torch.as_tensor(eeg, dtype=torch.float32, device=device),
        torch.as_tensor(stim, dtype=torch.float32, device=device),
    )
    receptive_field = eeg.shape[-1] - E.shape[-1] + 1
    win = segment_length - receptive_field + 1
    if win < 1:
        raise ValueError(f"segment_length {segment_length} is shorter than the model's receptive field {receptive_field}")

    first = max(0, -lags.min())
    last = min(eeg.shape[-1], stim.shape[-1] - lags.max()) - segment_length
    starts = np.arange(first, last + 1, hop)
    if len(starts) == 0:
        raise ValueError("Recording is too short for this segment length and lag range")

    E_windows = E.unfold(1, win, 1)  # (filters, n_onsets, win): a view, nothing copied
    S_windows = S.unfold(1, win, 1)
    scores = torch.empty(len(lags), len(starts))
    for b in range(0, len(starts), window_batch):
        t = torch.as_tensor(starts[b:b + window_batch], device=device)
        e = F.normalize(E_windows[:, t].permute(1, 0, 2), dim=-1)  # (windows, filters, win)
        for i, lag in enumerate(lags):
            s = F.normalize(S_windows[:, t + int(lag)].permute(1, 0, 2), dim=-1)
            inner = e @ s.transpose(1, 2)
            scores[i, b:b + window_batch] = model.linear(inner.flatten(start_dim=1)).squeeze(-1).cpu()
    return scores.numpy(), starts


# ------------------------------------------------------------------------------------------------------------
# Alignment: onset and drift from lag scans
# ------------------------------------------------------------------------------------------------------------

def peak_offset(curve: np.ndarray) -> float:
    '''Sub-sample index of the maximum of curve, by a parabola through it and its neighbours.'''
    curve = np.asarray(curve)
    k = int(curve.argmax())
    if k == 0 or k == len(curve) - 1:
        return float(k)
    y0, y1, y2 = curve[k - 1], curve[k], curve[k + 1]
    denom = y0 - 2 * y1 + y2
    return k + (0.5 * (y0 - y2) / denom if denom < 0 else 0.0)


def correct_drift(eeg: np.ndarray, drift_ppm: float, spline_order: int = 5) -> np.ndarray:
    '''
    Resample EEG (channels, time) so that the lag model lag(t) = onset + drift * t becomes a constant onset.

    With lag_scores' convention, EEG time t pairs with stimulus time t + onset + b t (b = drift_ppm * 1e-6). The
    corrected EEG at time u is the EEG at t = u / (1 + b), which pairs with stimulus time u + onset. Sample 0 is
    unchanged; nothing is extrapolated. Quintic splines keep high frequencies (~0.04% error at fs/5).
    '''
    from scipy.interpolate import make_interp_spline

    b = drift_ppm * 1e-6
    n = eeg.shape[-1]
    if b == 0 or n <= spline_order:
        return eeg
    ratio = 1 / (1 + b)                               # EEG samples per corrected sample
    n_out = int(np.floor((n - 1) / ratio)) + 1
    spline = make_interp_spline(np.arange(n), eeg, k=spline_order, axis=-1)
    return spline(np.arange(n_out) * ratio).astype(eeg.dtype, copy=False)


def upsample_lags(scores: np.ndarray, factor: int) -> np.ndarray:
    '''
    Band-limited (trigonometric) interpolation of scores (n_lags, ...) along the lag axis onto a grid `factor` times
    finer: (n_lags - 1) * factor + 1 rows, row factor * k equal to row k.

    The line through the first and last rows is removed first, so the periodic interpolant has no step at the wrap.
    Unlike linear interpolation, this keeps the noise variance the same at every fractional lag (exactly for an odd
    number of lags): linear interpolation halves white-noise variance half-way between samples.
    '''
    from scipy.signal import resample

    n = len(scores)
    if factor == 1 or n < 2:
        return scores
    shape = (-1,) + (1,) * (scores.ndim - 1)
    line = lambda w: (1 - w.reshape(shape)) * scores[0] + w.reshape(shape) * scores[-1]
    fine = resample(scores - line(np.linspace(0, 1, n)), n * factor, axis=0)[:(n - 1) * factor + 1]
    return (fine + line(np.linspace(0, 1, len(fine)))).astype(scores.dtype, copy=False)


def joint_fit(
        scores: np.ndarray,
        starts: np.ndarray,
        lags: np.ndarray,
        fs: float,
        segment_length: int,
        drift_grid_ppm: np.ndarray = np.arange(-150, 150.5, 0.5),
        n_chunks: int = 10,
        upsample: int = 8,
        ) -> dict:
    '''
    Onset and drift fitted jointly on the per-window scores (logits) of a lag scan.

    For every drift b on drift_grid_ppm and centre lag c, each window's score is read at its predicted lag
    c + b (t - t_centre) and averaged over windows; the (b, c) with the highest mean score wins, refined off the grid
    by a parabola along each axis. Scores are read off a lag axis upsampled `upsample` times by band-limited
    interpolation (upsample_lags), then linearly: plain linear interpolation between lag samples lowers the noise
    variance everywhere except at b = 0, which biased the drift towards 0 (chen2026). This uses every window, is not
    biased by large drifts (unlike best lags of segments), and needs no segment length. Uncertainty: jackknife over
    n_chunks contiguous chunks of windows (leave one chunk out). Memory: `upsample` times the scores; pass
    upsample=1 for scores already upsampled.

    scores (n_lags, n_windows), starts and lags from lag_scores; lags must be consecutive integers.
    Returns drift_ppm, centre_lag and onset (lag at t = 0; samples, fractional) with jackknife SEs, t_centre (s),
    n_windows, and the mean-score surface over (drift_grid_ppm, centre_lags), e.g. for pooled_drift.
    '''
    lags = np.asarray(lags)
    t = (starts + segment_length / 2) / fs
    t_centre = t.mean()
    dt = t - t_centre
    margin = int(np.ceil(np.abs(drift_grid_ppm).max() * 1e-6 * np.abs(dt).max() * fs)) + 1
    if 2 * margin >= len(lags):
        raise ValueError("Lag range too narrow for this drift grid")
    centre_lags = lags[margin:-margin]
    chunk_of = np.minimum((np.arange(len(t)) * n_chunks) // len(t), n_chunks - 1)
    chunk_starts = np.flatnonzero(np.diff(np.r_[-1, chunk_of]))
    counts = np.bincount(chunk_of, minlength=n_chunks)

    sums = np.empty((len(drift_grid_ppm), n_chunks, len(centre_lags)))
    cols = np.arange(len(t))
    fine = upsample_lags(np.asarray(scores), upsample)
    for j, b in enumerate(drift_grid_ppm):
        pos = (centre_lags[:, None] + b * 1e-6 * dt[None, :] * fs - lags[0]) * upsample  # index on the fine grid
        i0 = np.floor(pos).astype(int)
        f = pos - i0
        val = (1 - f) * fine[i0, cols] + f * fine[i0 + 1, cols]                # (centre lags, windows)
        sums[j] = np.add.reduceat(val, chunk_starts, axis=1).T

    def best(surface):
        jb, jc = np.unravel_index(np.argmax(surface), surface.shape)
        step = drift_grid_ppm[1] - drift_grid_ppm[0]
        return (drift_grid_ppm[jb] + (peak_offset(surface[:, jc]) - jb) * step,
                centre_lags[jc] + peak_offset(surface[jb, :]) - jc)

    surface = sums.sum(axis=1) / len(t)
    drift_ppm, centre_lag = best(surface)
    loo = np.array([best((sums.sum(axis=1) - sums[:, k]) / (len(t) - counts[k])) for k in range(n_chunks)])
    loo_onset = loo[:, 1] - loo[:, 0] * 1e-6 * t_centre * fs
    jack = lambda x: float(np.sqrt((n_chunks - 1) / n_chunks * ((x - x.mean()) ** 2).sum()))
    return dict(
        drift_ppm=float(drift_ppm), drift_se=jack(loo[:, 0]),
        centre_lag=float(centre_lag), centre_lag_se=jack(loo[:, 1]),
        onset=float(centre_lag - drift_ppm * 1e-6 * t_centre * fs), onset_se=jack(loo_onset),
        t_centre=float(t_centre), n_windows=len(t),
        surface=surface.astype(np.float32), centre_lags=centre_lags, drift_grid_ppm=np.asarray(drift_grid_ppm),
    )


def pooled_drift(fits: list[dict], fs: float) -> dict:
    '''
    One drift shared by several blocks of a recording (e.g. a session), with each block keeping its own onset.

    Uses the joint_fit surfaces (same drift grid): for each drift b, each block contributes its best mean score over
    centre lags, weighted by its number of windows; the b with the highest total wins (parabolic refinement).
    Uncertainty: jackknife over blocks. Returns drift_ppm, drift_se, and per block the centre lag and onset
    (samples) at the pooled drift.
    '''
    grid = fits[0]["drift_grid_ppm"]
    if any(not np.array_equal(f["drift_grid_ppm"], grid) for f in fits):
        raise ValueError("All fits must use the same drift grid")
    per_block = np.stack([f["surface"].max(axis=1) * f["n_windows"] for f in fits])   # (blocks, drifts)

    def best(total):
        j = int(np.argmax(total))
        return grid[j] + (peak_offset(total) - j) * (grid[1] - grid[0])

    drift = best(per_block.sum(axis=0))
    n = len(fits)
    se = np.nan
    if n > 1:
        loo = np.array([best(per_block.sum(axis=0) - per_block[k]) for k in range(n)])
        se = float(np.sqrt((n - 1) / n * ((loo - loo.mean()) ** 2).sum()))

    centre_lags, onsets = [], []
    for f in fits:
        row = np.array([np.interp(drift, grid, f["surface"][:, c]) for c in range(f["surface"].shape[1])])
        c = int(np.argmax(row))
        centre = f["centre_lags"][c] + peak_offset(row) - c
        centre_lags.append(centre)
        onsets.append(centre - drift * 1e-6 * f["t_centre"] * fs)
    return dict(drift_ppm=float(drift), drift_se=se, centre_lags=np.array(centre_lags), onsets=np.array(onsets))


def refine_onset(
        model: SimilarityDetector,
        eeg: np.ndarray,
        stim: np.ndarray,
        around: float,
        half_width: int,
        segment_length: int,
        hop: int,
        device: str = "cpu",
        n_chunks: int = 10,
        ) -> dict:
    '''
    Onset (constant lag, e.g. on drift-corrected EEG) to a fraction of a sample: scan lags around `around`
    (+- half_width samples), average over windows and fit a parabola through the peak. Uncertainty: jackknife over
    n_chunks contiguous chunks of windows. Also returns the curve and its peak prominence (peak minus median).
    '''
    lags = int(round(around)) + np.arange(-half_width, half_width + 1)
    scores, starts = lag_scores(model, eeg, stim, lags, segment_length, hop, device=device)
    chunk_of = np.minimum((np.arange(scores.shape[1]) * n_chunks) // scores.shape[1], n_chunks - 1)
    sums = np.stack([scores[:, chunk_of == k].sum(axis=1) for k in range(n_chunks)])
    counts = np.bincount(chunk_of, minlength=n_chunks)
    curve = sums.sum(axis=0) / counts.sum()
    onset = lags[0] + peak_offset(curve)
    loo = np.array([lags[0] + peak_offset((sums.sum(axis=0) - sums[k]) / (counts.sum() - counts[k]))
                    for k in range(n_chunks)])
    se = float(np.sqrt((n_chunks - 1) / n_chunks * ((loo - loo.mean()) ** 2).sum()))
    at_edge = peak_offset(curve) in (0, len(curve) - 1)
    return dict(onset=float(onset), onset_se=se, lags=lags, curve=curve, at_edge=bool(at_edge),
                prominence=float(curve.max() - np.median(curve)), scores=scores, starts=starts)
