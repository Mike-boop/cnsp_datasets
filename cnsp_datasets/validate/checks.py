"""
Objective alignment validation (PLAN.md section 5).

- sanity: neural vs stimulus duration, amplitude per channel type (unit errors), flat/NaN channels.
- low: 0.5-8 Hz envelope backward model, cross-validated per subject, against circular-shift and mismatched-stimulus
  nulls; lag sweep (score vs global stimulus shift) and per-trial offsets.
- mlr / brainstem: forward TRFs of the half-wave-rectified waveform; SNR of the latency window against negative
  lags, against circular-shift nulls.

Shift convention: a peak or offset of +d s means the neural data fits best when the stimulus is delayed by d s.
The sweep detects a global offset but localises it only to within the decoder window (0-tmax), since any shift
that brings the response back into the window scores similarly. Per-trial offsets (relative to the subject's
decoder) are more precise and estimate trial-to-trial jitter.
"""
import traceback
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from scipy.stats import zscore

from cnsp_datasets.validate.load import bandpass, load_neural, pick_stimulus, resampled, stimulus_feature
from cnsp_datasets.validate.models import autocorr, backward_cv, corr, forward_trf, xcorr

LOW = dict(fs=64, band=(0.5, 8.0), tmax=0.25, alpha=1.0, n_circ=50, n_mismatch=20, min_shift=5.0,
           sweep=1.0, sweep_step=2, sweep_tol=0.1, offset_range=0.5)
# TRFs are fitted over `lags` but only `valid` is used: the edges of the fitted window are unreliable
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


def low_targets(stims, names, fs, rng):
    """Per-trial target matrices: true, circular shifts, mismatched stimuli, sweep shifts; and column slices."""
    m = round(LOW["min_shift"] * fs)
    sweep = np.arange(-round(LOW["sweep"] * fs), round(LOW["sweep"] * fs) + 1, LOW["sweep_step"])
    others = [[j for j, n in enumerate(names) if n != name] for name in names]
    n_mm = LOW["n_mismatch"] if all(others) else 0
    targets = []
    for s, oth in zip(stims, others):
        circ = [np.roll(s, k) for k in rng.integers(m, len(s) - m, LOW["n_circ"])]
        mism = [np.resize(stims[j], len(s)) for j in rng.choice(oth, n_mm)] if n_mm else []
        targets.append(np.column_stack([s] + circ + mism + [np.roll(s, d) for d in sweep]))
    n_c = LOW["n_circ"]
    cols = dict(circ=slice(1, 1 + n_c), mismatch=slice(1 + n_c, 1 + n_c + n_mm), sweep=slice(1 + n_c + n_mm, None))
    return targets, cols, sweep / fs


def trial_offset(recon, s, fs):
    """Shift (s) of the stimulus that best matches a reconstruction."""
    shifts = np.arange(-round(LOW["offset_range"] * fs), round(LOW["offset_range"] * fs) + 1)
    r = corr(np.column_stack([np.roll(s, d) for d in shifts]), recon[:, None].repeat(len(shifts), 1))
    return float(shifts[np.argmax(r)] / fs)


def low_tier(neural, stims, names, fs, rng):
    """Backward-model results for one subject."""
    targets, cols, sweep_s = low_targets(stims, names, fs, rng)
    scores, recon = backward_cv(neural, targets, round(LOW["tmax"] * fs) + 1, alpha=LOW["alpha"])
    mean = scores.mean(0)
    curve = mean[cols["sweep"]]
    return dict(
        r=float(mean[0]), r_trials=scores[:, 0].tolist(),
        null_circ=mean[cols["circ"]].tolist(), null_mismatch=mean[cols["mismatch"]].tolist(),
        p_circ=p_value(mean[0], mean[cols["circ"]]),
        p_mismatch=p_value(mean[0], mean[cols["mismatch"]]) if cols["mismatch"].stop > cols["mismatch"].start else None,
        sweep_s=sweep_s.tolist(), sweep_r=curve.tolist(), sweep_peak_s=float(sweep_s[np.argmax(curve)]),
        trial_offsets_s=[trial_offset(r, t[:, 0], fs) for r, t in zip(recon, targets)],
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
            lags = np.arange(round(HF["lags"][0] * fs_hf), round(HF["lags"][1] * fs_hf) + 1)
            m = round(HF["min_shift"] * fs_hf)
            shifts = np.concatenate([[0], rng.integers(m, n - m, HF["n_null"])])
            for tier, cfg in TIERS.items():
                if tier not in tiers:
                    continue
                sb = zscore(bandpass(s[:n], cfg["band"], fs_hf))
                hf[tier]["acorr"] = hf[tier]["acorr"] + autocorr(sb, len(lags))
                hf[tier]["xcorr"] = hf[tier]["xcorr"] + xcorr(bandpass(x[:, :n], cfg["band"], fs_hf), sb, lags, shifts)
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
        lags_s = np.arange(round(HF["lags"][0] * fs_hf), round(HF["lags"][1] * fs_hf) + 1) / fs_hf
        keep = (lags_s >= HF["valid"][0] - 1e-9) & (lags_s <= HF["valid"][1] + 1e-9)
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
                lags_s=lags_s.tolist(), gfp=gfp[0].tolist(), null_gfp_95=np.percentile(gfp[1:], 95, 0).tolist(),
            )
    n_err = sum("error" in t for t in trials)
    print(f"subject {out['subject']}: {len(trials)} trials ({n_err} failed), r={out.get('low', {}).get('r', np.nan):.3f}",
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
        curve = np.mean([s["sweep_r"] for s in low], 0)
        peak = float(low[0]["sweep_s"][np.argmax(curve)])
        offsets = np.concatenate([s["trial_offsets_s"] for s in low])
        summary["low"] = dict(
            n_subjects=len(low), mean_r=float(r.mean()), median_r=float(np.median(r)),
            p_circ=p_value(r.mean(), null_c), p_mismatch=p_value(r.mean(), null_m) if null_m is not None else None,
            frac_subjects_sig=float(np.mean([s["p_circ"] < ALPHA for s in low])),
            sweep_peak_s=peak, trial_offset_sd_s=float(offsets.std()),
        )
        summary["low"]["pass"] = bool(
            summary["low"]["p_circ"] < ALPHA and (null_m is None or summary["low"]["p_mismatch"] < ALPHA)
            and abs(peak) <= LOW["sweep_tol"])
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
