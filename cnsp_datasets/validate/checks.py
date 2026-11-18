"""
Objective alignment validation (PLAN.md section 5).

- sanity: neural vs stimulus duration, amplitude per channel type (unit errors), flat/NaN channels.
- low: 0.5-8 Hz forward model (envelope -> every channel), cross-validated per subject: held-out encoding r (mean
  over channels) against circular-shift and mismatched-stimulus nulls; per-trial offsets (jitter) and drift.
- mlr / brainstem: forward TRFs of the half-wave-rectified waveform; SNR of the latency window against negative
  lags, against circular-shift nulls.

Shift convention: an offset of +d s means the neural data fits best when the stimulus (prediction) is delayed by d s.
Per-trial offsets are relative to the subject's model trained on the other trials, so their spread estimates
trial-to-trial jitter; offsets of the two halves of a trial give its clock drift.
"""
import traceback
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from scipy.stats import zscore

from cnsp_datasets.validate.load import bandpass, load_neural, pick_stimulus, resampled, stimulus_feature
from cnsp_datasets.validate.models import autocorr, convolve, corr, forward_trf, peak_shift, xcorr

# TRFs are fitted over `lags` but only `valid` is plotted and scored: the edges of the fitted window are unreliable
LOW = dict(fs=64, band=(0.5, 8.0), lags=(-0.2, 0.6), valid=(-0.15, 0.5), alpha=1.0, n_folds=5, n_circ=50,
           n_mismatch=20, min_shift=5.0, offset_range=0.5)
HF = dict(fs=1000, lags=(-0.1, 0.1), valid=(-0.075, 0.075), noise=(-0.075, -0.02), n_null=100, min_shift=1.0,
          alpha=1.0)
TIERS = {
    "mlr": dict(band=(30, 60), window={"eeg": (0.018, 0.045), "meg": (0.018, 0.045)}),
    "brainstem": dict(band=(30, 250), window={"eeg": (0.004, 0.009), "meg": (0.028, 0.045)}),
}
# plausible median channel std after a 1 Hz high-pass, in SI units (V, T, T/m)
UNIT_RANGES = {"eeg": (1e-6, 2e-4), "mag": (1e-14, 1e-11), "grad": (1e-12, 1e-9)}
ALL_TIERS = ("low", "mlr", "brainstem")
DURATION_TOL = 1.0
ALPHA = 0.05


def p_value(true, null):
    """One-sided permutation p-value of true against null samples."""
    return float((1 + np.sum(np.asarray(null) >= true)) / (1 + len(null)))


def sanity(raw, x, fs, stim_len):
    """Durations, per-type median channel std after a 1 Hz high-pass, flat and NaN channel counts."""
    types = np.array(raw.get_channel_types())
    std = bandpass(np.nan_to_num(x), (1.0, 0.45 * fs), fs).std(-1)
    med = {t: float(np.median(std[types == t])) for t in np.unique(types)}
    return dict(
        neural_s=raw.n_times / raw.info["sfreq"], stim_s=stim_len / fs,
        median_std=med,
        n_flat=int(np.sum(std < 1e-3 * np.median(std))), n_nan=int(np.isnan(x).any(-1).sum()),
    )


def sanity_flags(trial):
    """Human-readable problems found by sanity()."""
    flags = []
    if abs(trial["neural_s"] - trial["stim_s"]) > DURATION_TOL:
        flags.append(f"duration differs by {trial['neural_s'] - trial['stim_s']:+.2f} s")
    for t, v in trial["median_std"].items():
        lo, hi = UNIT_RANGES.get(t, (0, np.inf))
        if not lo <= v <= hi:
            flags.append(f"{t} median std {v:.3g} outside [{lo:g}, {hi:g}]")
    if trial["n_flat"] or trial["n_nan"]:
        flags.append(f"{trial['n_flat']} flat, {trial['n_nan']} NaN channels")
    return flags


def _lag_samples(lags, fs):
    return np.arange(round(lags[0] * fs), round(lags[1] * fs) + 1)


def _valid(lags_s, valid):
    return (lags_s >= valid[0] - 1e-9) & (lags_s <= valid[1] + 1e-9)


def low_tier(neural, stims, names, fs, rng):
    """Cross-validated 0.5-8 Hz forward model for one subject: scores, nulls, TRF, per-trial offsets and drift."""
    lags = _lag_samples(LOW["lags"], fs)
    m = round(LOW["min_shift"] * fs)
    others = [[j for j, n in enumerate(names) if n != name] for name in names]
    n_mm = LOW["n_mismatch"] if all(others) else 0
    shifts = [np.concatenate([[0], rng.integers(m, len(s) - m, LOW["n_circ"])]) for s in stims]
    mism = [[np.resize(stims[j], len(s)) for j in rng.choice(o, n_mm)] if n_mm else [] for s, o in zip(stims, others)]
    ac = [autocorr(s, len(lags)) for s in stims]
    xc = [xcorr(x, s, lags, k) for x, s, k in zip(neural, stims, shifts)]  # (1 + n_circ, C, L) per trial
    ac_mm = [[autocorr(s, len(lags)) for s in ms] for ms in mism]
    xc_mm = [[xcorr(x, s, lags, [0])[0] for s in ms] for x, ms in zip(neural, mism)]

    n_var = 1 + LOW["n_circ"] + n_mm
    scores = np.zeros((len(neural), n_var))
    offsets = np.zeros((len(neural), 3))  # whole trial, first half, second half (samples)
    for idx in np.array_split(np.arange(len(neural)), min(LOW["n_folds"], len(neural))):
        train = np.setdiff1d(np.arange(len(neural)), idx)
        W = forward_trf(sum(ac[i] for i in train), sum(xc[i] for i in train), LOW["alpha"])
        W_mm = [forward_trf(sum(ac_mm[i][v] for i in train), sum(xc_mm[i][v] for i in train), LOW["alpha"])
                for v in range(n_mm)]
        for i in idx:
            x, n = neural[i], neural[i].shape[1]
            variants = [(np.roll(stims[i], k), w) for k, w in zip(shifts[i], W)] + list(zip(mism[i], W_mm))
            for v, (sv, w) in enumerate(variants):
                pred = convolve(sv, w, lags, n)
                scores[i, v] = corr(pred.T, x.T).mean()
                if v == 0:
                    h, r = n // 2, round(LOW["offset_range"] * fs)
                    offsets[i] = [peak_shift(x, pred, r), peak_shift(x[:, :h], pred[:, :h], r),
                                  peak_shift(x[:, h:], pred[:, h:], r)]

    mean = scores.mean(0)
    null_c, null_m = mean[1:1 + LOW["n_circ"]], mean[1 + LOW["n_circ"]:]
    half_s = np.array([x.shape[1] / 2 / fs for x in neural])
    keep = _valid(lags / fs, LOW["valid"])
    trf = forward_trf(sum(ac), sum(xc), LOW["alpha"])[..., keep]  # all trials: true + circular nulls
    gfp = np.sqrt((trf ** 2).mean(1))
    return dict(
        r=float(mean[0]), r_trials=scores[:, 0].tolist(), null_circ=null_c.tolist(), null_mismatch=null_m.tolist(),
        p_circ=p_value(mean[0], null_c), p_mismatch=p_value(mean[0], null_m) if n_mm else None,
        lags_s=(lags[keep] / fs).tolist(), gfp=gfp[0].tolist(),
        null_gfp_50=np.median(gfp[1:], 0).tolist(), null_gfp_95=np.percentile(gfp[1:], 95, 0).tolist(),
        peak_s=float(lags[keep][np.argmax(gfp[0])] / fs),
        trial_offsets_s=(offsets[:, 0] / fs).tolist(),
        drift_ppm=((offsets[:, 2] - offsets[:, 1]) / fs / half_s * 1e6).tolist(),
    )


def snr(trf, lags_s, window, noise):
    """RMS over channels and the latency window, relative to the RMS over the negative-lag noise window."""
    w = (lags_s >= window[0]) & (lags_s <= window[1])
    n = (lags_s >= noise[0]) & (lags_s <= noise[1])
    return np.sqrt((trf[..., w] ** 2).mean((-1, -2))) / np.sqrt((trf[..., n] ** 2).mean((-1, -2)))


def validate_subject(records, picks, reference, cache, seed, tiers=ALL_TIERS):
    """Run sanity checks and the requested tiers on one subject's trials."""
    rng = np.random.default_rng(seed)
    neural, stims, names, trials = [], [], [], []
    hf = {tier: dict(acorr=0, xcorr=0) for tier in TIERS}
    fs_hf, modality = None, "eeg"
    for record in records:
        info = dict(subject=record.subject, session=record.session, trial=record.trial)
        trials.append(info)
        try:
            stim = pick_stimulus(record)
            if stim is None:
                info["error"] = "no audio or envelope stimulus"
                continue
            raw = load_neural(record, picks, reference)
            modality = "meg" if {"mag", "grad"} & set(raw.get_channel_types()) else "eeg"

            x, fs = resampled(raw, LOW["fs"])
            s = stimulus_feature(stim, "low", fs, cache)
            info.update(sanity(raw, x, fs, len(s)), stimulus=stim.name)
            info["flags"] = sanity_flags(info)
            n = min(x.shape[1], len(s))
            neural.append(zscore(bandpass(x, LOW["band"], fs)[:, :n], axis=-1))
            stims.append(zscore(bandpass(s, LOW["band"], fs)[:n]))
            names.append(stim.name)
            info["low_index"] = len(neural) - 1

            if not set(TIERS) & set(tiers):
                continue
            x, fs_hf = resampled(raw, HF["fs"])
            s = stimulus_feature(stim, "hf", fs_hf, cache)
            if s is None:
                continue
            n = min(x.shape[1], len(s))
            lags = _lag_samples(HF["lags"], fs_hf)
            m = round(HF["min_shift"] * fs_hf)
            shifts = np.concatenate([[0], rng.integers(m, n - m, HF["n_null"])])
            for tier, cfg in TIERS.items():
                if tier not in tiers:
                    continue
                sb = zscore(bandpass(s[:n], cfg["band"], fs_hf))
                hf[tier]["acorr"] = hf[tier]["acorr"] + autocorr(sb, len(lags))
                xb = bandpass(x[:, :n], cfg["band"], fs_hf)
                hf[tier]["xcorr"] = hf[tier]["xcorr"] + xcorr(xb, sb, lags, shifts)
        except Exception as e:
            info["error"] = f"{type(e).__name__}: {e}"
            info["traceback"] = traceback.format_exc(limit=3)

    out = dict(subject=records[0].subject, trials=trials, modality=modality)
    if "low" in tiers and len(neural) >= 2:
        out["low"] = low_tier(neural, stims, names, LOW["fs"], rng)
        for i, t in enumerate(trials):
            if "low_index" in t:
                t["r"] = out["low"]["r_trials"][t["low_index"]]
                t["offset_s"] = out["low"]["trial_offsets_s"][t["low_index"]]
    if fs_hf is not None:
        lags_s = _lag_samples(HF["lags"], fs_hf) / fs_hf
        keep = _valid(lags_s, HF["valid"])
        lags_s = lags_s[keep]
        out["fs_hf"] = fs_hf
        for tier, cfg in TIERS.items():
            if not np.ndim(hf[tier]["xcorr"]):
                continue
            # (1 + nulls, ch, lags), trimmed to the lags unaffected by the edges of the fitted lag window
            trf = forward_trf(hf[tier]["acorr"], hf[tier]["xcorr"], HF["alpha"])[..., keep]
            ratio = snr(trf, lags_s, cfg["window"][modality], HF["noise"])
            gfp = np.sqrt((trf ** 2).mean(1))
            out[tier] = dict(
                snr=float(ratio[0]), null_snr=ratio[1:].tolist(), p=p_value(ratio[0], ratio[1:]),
                lags_s=lags_s.tolist(), gfp=gfp[0].tolist(), null_gfp_50=np.median(gfp[1:], 0).tolist(),
                null_gfp_95=np.percentile(gfp[1:], 95, 0).tolist(),
            )
    n_err = sum("error" in t for t in trials)
    r = out.get("low", {}).get("r", np.nan)
    print(f"subject {out['subject']}: {len(trials)} trials ({n_err} failed), r={r:.3f}",
          flush=True)
    return out


def group_summary(subjects, tiers=ALL_TIERS):
    """Population statistics and pass/fail per tier."""
    summary = {}
    low = [s["low"] for s in subjects if "low" in s]
    if low:
        r = np.array([s["r"] for s in low])
        null_c = np.array([s["null_circ"] for s in low]).mean(0)
        mm = [s["null_mismatch"] for s in low]
        null_m = np.array(mm).mean(0) if all(mm) else None
        gfp = np.mean([np.array(s["gfp"]) / np.array(s["null_gfp_50"]) for s in low], 0)
        # jitter: spread of trial offsets around each subject's median; drift: per-trial half-to-half change
        rel = np.concatenate([np.array(s["trial_offsets_s"]) - np.median(s["trial_offsets_s"]) for s in low])
        drift = np.concatenate([s["drift_ppm"] for s in low])
        summary["low"] = dict(
            n_subjects=len(low), mean_r=float(r.mean()), median_r=float(np.median(r)),
            p_circ=p_value(r.mean(), null_c), p_mismatch=p_value(r.mean(), null_m) if null_m is not None else None,
            frac_subjects_sig=float(np.mean([s["p_circ"] < ALPHA for s in low])),
            trf_peak_s=float(low[0]["lags_s"][np.argmax(gfp)]),
            jitter_sd_ms=float(1e3 * rel.std()), jitter_mad_ms=float(1e3 * 1.4826 * np.median(np.abs(rel))),
            drift_ppm_median=float(np.median(drift)),
            drift_ppm_se=float(1.2533 * drift.std() / np.sqrt(len(drift))),
        )
        summary["low"]["pass"] = bool(
            summary["low"]["p_circ"] < ALPHA and (null_m is None or summary["low"]["p_mismatch"] < ALPHA))
    for tier in TIERS:
        res = [s[tier] for s in subjects if tier in s]
        if not res:
            continue
        true = np.mean([s["snr"] for s in res])
        null = np.array([s["null_snr"] for s in res]).mean(0)
        summary[tier] = dict(
            n_subjects=len(res), mean_snr=float(true), p=p_value(true, null),
            frac_subjects_sig=float(np.mean([s["p"] < ALPHA for s in res])),
        )
        summary[tier]["pass"] = bool(summary[tier]["p"] < ALPHA)
    # tiers are cumulative: a higher tier only counts if every lower one that was run passed
    tier = "none"
    for t in (t for t in ALL_TIERS if t in tiers):
        if not summary.get(t, {}).get("pass"):
            break
        tier = t
    summary["validation_tier"] = tier
    summary["tiers_run"] = list(tiers)
    return summary


def validate(subjects, picks="data", reference=None, n_jobs=4, seed=0, tiers=ALL_TIERS):
    """
    Validate a dataset. subjects maps subject id to its TrialRecords (see load.group_by_subject).

    picks are passed to raw.pick() (e.g. 'eeg', 'meg'); reference ('average', channel names or None) is applied to
    the picked data before any check. tiers selects which of ALL_TIERS to run (sanity checks always run).
    Returns per-subject results and the population summary.
    """
    cache = {}
    with ThreadPoolExecutor(n_jobs) as pool:
        results = list(pool.map(
            lambda kv: validate_subject(kv[1], picks, reference, cache, seed + kv[0], tiers), subjects.items()))
    config = dict(LOW=LOW, HF=HF, TIERS=TIERS, UNIT_RANGES=UNIT_RANGES, picks=picks, reference=reference, seed=seed,
                  tiers=list(tiers))
    return dict(config=config, summary=group_summary(results, tiers), subjects=results)
