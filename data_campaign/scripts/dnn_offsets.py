"""
Constant timing offset of each reviewed dataset relative to accou2023 (the data the match-mismatch classifiers were
trained on), from lag scans of the fs128_1020-64 broadband classifier (cnsp_datasets.align.scan.lag_scores).

Per trial: EEG prepared with the classifier's own steps (high-pass, interpolation onto the 64-channel 10-20 montage,
128 Hz), envelope with its stimulus steps (Hilbert envelope + resampling; shipped envelopes skip the Hilbert step),
both z-scored and cropped to the shorter one; lag scan over +/-500 ms, score averaged over 5 s windows (1 s hop).
Per dataset: curves pooled over trials (weighted by windows); offset = sub-sample peak; CI by bootstrapping subjects.
Sign (as lag_scores): a positive lag means the stimulus must be moved earlier to match the EEG as in training, i.e.
the neural data are EARLY relative to accou2023 (negative = late).
Usage: dnn_offsets.py <out_dir> [names...]
"""
import json
import os
import random
import re
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from scipy.stats import zscore  # noqa: E402

from cnsp_datasets.align.scan import lag_scores, peak_offset  # noqa: E402
from cnsp_datasets.align.specs import load_classifier  # noqa: E402
from cnsp_datasets.preprocess.base import get_stim_array  # noqa: E402
from cnsp_datasets.preprocess.neural import ResampleNeural  # noqa: E402
from cnsp_datasets.standardise.flat_sink import FlatSourceV1  # noqa: E402
from cnsp_datasets.standardise.format_dataset import get_adaptor_class  # noqa: E402

MODEL = "/home/gu08wuvu/cnsp_datasets/playground/accou2023/classifiers/fs128_1020-64_broadband.pt"
T = "/data_storage/gu08wuvu/datasets/tmp/review"
MAX_TRIALS, MAX_LAG_S, HOP_S, N_BOOT = 100, 0.5, 1.0, 1000
MAX_TRIALS_ANCHOR = 15  # accou2023 trials are 15 min and slow to prepare
device = "cuda" if torch.cuda.is_available() else "cpu"
model, spec, _ = load_classifier(MODEL, device)
FS, SEG = spec.fs, round(spec.segment_length * spec.fs)
LAGS = np.arange(-round(MAX_LAG_S * FS), round(MAX_LAG_S * FS) + 1)


def flat(path):
    return lambda: list(FlatSourceV1(path, assume_first_attended=True).iter_trials())


def bentum(condition):
    root = "/data_storage/gu08wuvu/datasets/bentum2023/downloaded"
    return lambda: [r for r in get_adaptor_class("bentum2023")(root).parse() if r.condition == condition]


def flat_condition(path, condition):
    return lambda: [r for r in FlatSourceV1(path, assume_first_attended=True).iter_trials() if r.condition == condition]


def herrmann_snr(lo, hi):
    """herrmann2025 babble trials with lo <= SNR (dB, from the mixture's name <Title>_L<SNR>) <= hi."""
    def snr(r):
        return float(next(m[1] for s in r.stimulus if (m := re.search(r"_L(-?[0-9.]+)$", s.name))))
    path = f"{T}/herrmann2025/standardised"
    return lambda: [r for r in FlatSourceV1(path, assume_first_attended=True).iter_trials()
                    if r.condition == "babble" and lo <= snr(r) <= hi]


DATASETS = {
    "accou2023 (training data)": flat("/data_storage/gu08wuvu/datasets/accou2023/standardised-flat"),
    "weissbart2019": flat(f"{T}/weissbart2019/standardised"),
    "das2019": flat(f"{T}/das2019/standardised"),
    "fuglsang2018": flat(f"{T}/fuglsang2018/standardised"),
    "brennan2018": flat(f"{T}/brennan2018/standardised"),
    "broderick2019_natural": flat(f"{T}/broderick2019/broderick2019_natural/standardised"),
    "broderick2019_cocktail (attended)": flat(f"{T}/broderick2019/broderick2019_cocktail/standardised"),
    "bentum2023_dialogue": bentum("spontaneous-dialogue"),
    "bentum2023_news": bentum("news-broadcast"),
    "bentum2023_story": bentum("read-aloud-story"),
    "guilleminot2021_A": flat_condition(f"{T}/guilleminot2021/standardised", "A"),
    "guilleminot2021_AT_0": flat_condition(f"{T}/guilleminot2021/standardised", "AT_0"),
    "guilleminot2021_AT_m60": flat_condition(f"{T}/guilleminot2021/standardised", "AT_m60"),
    "guilleminot2021_AT_m120": flat_condition(f"{T}/guilleminot2021/standardised", "AT_m120"),
    "guilleminot2021_AT_m180": flat_condition(f"{T}/guilleminot2021/standardised", "AT_m180"),
    "guilleminot2021_AT_60": flat_condition(f"{T}/guilleminot2021/standardised", "AT_60"),
    "guilleminot2021_AT_mismatched": flat_condition(f"{T}/guilleminot2021/standardised", "AT_mismatched"),
    "varano2022_A_sin": flat_condition(f"{T}/varano2022/standardised", "A_sin"),
    "varano2022_AV_natural_sin": flat_condition(f"{T}/varano2022/standardised", "AV_natural_sin"),
    "varano2022_AV_cartoon_sin": flat_condition(f"{T}/varano2022/standardised", "AV_cartoon_sin"),
    "varano2022_AV_edge_sin": flat_condition(f"{T}/varano2022/standardised", "AV_edge_sin"),
    "varano2022_AV_disk_sin": flat_condition(f"{T}/varano2022/standardised", "AV_disk_sin"),
    "varano2022_AV_mismatchdisk_sin": flat_condition(f"{T}/varano2022/standardised", "AV_mismatchdisk_sin"),
    "etard2019_natural": flat_condition(f"{T}/etard2019/standardised", "natural"),
    "etard2019_sin_lowSNR": flat_condition(f"{T}/etard2019/standardised", "sin_lowSNR"),
    "etard2019_sin_mediumSNR": flat_condition(f"{T}/etard2019/standardised", "sin_mediumSNR"),
    "etard2019_sin_highSNR": flat_condition(f"{T}/etard2019/standardised", "sin_highSNR"),
    "etard2019_competing_fM": flat_condition(f"{T}/etard2019/standardised", "competing_fM"),
    "etard2019_competing_fF": flat_condition(f"{T}/etard2019/standardised", "competing_fF"),
    "etard2019_foreign_quiet": flat_condition(f"{T}/etard2019/standardised", "foreign_quiet"),
    "etard2019_foreign_lowSNR": flat_condition(f"{T}/etard2019/standardised", "foreign_lowSNR"),
    "etard2019_foreign_mediumSNR": flat_condition(f"{T}/etard2019/standardised", "foreign_mediumSNR"),
    "etard2019_foreign_highSNR": flat_condition(f"{T}/etard2019/standardised", "foreign_highSNR"),
    "jehn2025_th_natural_fR_nh": flat_condition(f"{T}/jehn2025_th/standardised", "natural_fR_nh"),
    "jehn2025_th_natural_fL_nh": flat_condition(f"{T}/jehn2025_th/standardised", "natural_fL_nh"),
    "jehn2025_th_competing_fR_nh": flat_condition(f"{T}/jehn2025_th/standardised", "competing_fR_nh"),
    "jehn2025_th_competing_fL_nh": flat_condition(f"{T}/jehn2025_th/standardised", "competing_fL_nh"),
    "jehn2025_ha_natural_fR_hi": flat_condition(f"{T}/jehn2025_ha/standardised", "natural_fR_hi"),
    "jehn2025_ha_natural_fL_hi": flat_condition(f"{T}/jehn2025_ha/standardised", "natural_fL_hi"),
    "jehn2025_ha_competing_fR_hi": flat_condition(f"{T}/jehn2025_ha/standardised", "competing_fR_hi"),
    "jehn2025_ha_competing_fL_hi": flat_condition(f"{T}/jehn2025_ha/standardised", "competing_fL_hi"),
    "jehn2025_ci_natural_fR_ci": flat_condition(f"{T}/jehn2025_ci/standardised", "natural_fR_ci"),
    "jehn2025_ci_natural_fL_ci": flat_condition(f"{T}/jehn2025_ci/standardised", "natural_fL_ci"),
    "jehn2025_ci_competing_fR_ci": flat_condition(f"{T}/jehn2025_ci/standardised", "competing_fR_ci"),
    "jehn2025_ci_competing_fL_ci": flat_condition(f"{T}/jehn2025_ci/standardised", "competing_fL_ci"),
    "narayanan2021_fL": flat_condition(f"{T}/narayanan2021/standardised", "competing-fL-hrtf"),
    "narayanan2021_fR": flat_condition(f"{T}/narayanan2021/standardised", "competing-fR-hrtf"),
    "narayanan2021_fL_driftcorr": flat_condition(f"{T}/narayanan2021/driftcorr/standardised", "competing-fL-hrtf"),
    "narayanan2021_fR_driftcorr": flat_condition(f"{T}/narayanan2021/driftcorr/standardised", "competing-fR-hrtf"),
    "herrmann2025_clear": flat_condition(f"{T}/herrmann2025/standardised", "clear"),
    "herrmann2025_babble_hiSNR": herrmann_snr(23, 60),
    "herrmann2025_babble_midSNR": herrmann_snr(2, 20),
    "herrmann2025_babble_lowSNR": herrmann_snr(-7, -1),
    "harshaiyahav2025": flat(f"{T}/harshaiyahav2025/standardised"),
    "harshaiyahav2025_first_half": flat_condition(f"{T}/harshaiyahav2025/standardised", "first_half"),
    "harshaiyahav2025_second_half": flat_condition(f"{T}/harshaiyahav2025/standardised", "second_half"),
    "momenian2024": flat(f"{T}/momenian2024/standardised"),
    "holtze2021": flat(f"{T}/holtze2021/standardised"),
    "holtze2021_omni": lambda: [r for r in FlatSourceV1(f"{T}/holtze2021/standardised", assume_first_attended=True)
                                .iter_trials() if r.condition.endswith("-omni")],
    "holtze2021_beam": lambda: [r for r in FlatSourceV1(f"{T}/holtze2021/standardised", assume_first_attended=True)
                                .iter_trials() if r.condition.endswith("-beam")],
}


def prepare(record):
    raw = record.neural_data_fn()
    raw.load_data(verbose="ERROR")
    raw.pick("eeg")
    nopos = [c["ch_name"] for c in raw.info["chs"] if not np.isfinite(c["loc"][:3]).all() or not np.any(c["loc"][:3])]
    raw.drop_channels(nopos)  # montage interpolation needs positions (momenian2024: F11/F12/FT11/FT12/CB1/CB2)
    if raw.info["sfreq"] != FS:
        raw = ResampleNeural(FS).run(raw)
    for step in spec.eeg_steps():
        raw = step.run(raw)
    attended = next(s.name for s in record.stimulus if s.is_attended and s.modality == "audio")
    stim = sorted([s for s in record.stimulus if s.name == attended and (s.feature_name == "audio" or s.feature_name.startswith("envelope"))],
                  key=lambda s: s.feature_name != "audio")[0]
    shipped_env = stim.feature_name.startswith("envelope")
    data = stim.data_fn()
    data = {"fs": data["fs"], "data": np.atleast_2d(get_stim_array(data)).astype(float)}
    steps = spec.stim_steps()
    for step in steps[1:] if shipped_env else steps:  # shipped envelopes skip the Hilbert step
        data = step.run(data)
    story = np.atleast_2d(get_stim_array(data)).mean(0, keepdims=True)
    eeg = raw.get_data()
    n = min(eeg.shape[1], story.shape[1])
    return zscore(eeg[:, :n], axis=-1).astype(np.float32), zscore(story[:, :n], axis=-1).astype(np.float32)


def run(name, out):
    records = DATASETS[name]()
    random.Random(0).shuffle(records)
    records = records[:MAX_TRIALS_ANCHOR if name.startswith('accou') else MAX_TRIALS]
    print(f"=== {name}: {len(records)} trials", flush=True)
    curves = defaultdict(list)  # subject -> [(n_windows, curve)]
    cache = f"{out}/cache/{name.split(' ')[0]}"
    os.makedirs(cache, exist_ok=True)
    for i, r in enumerate(records):
        path = f"{cache}/sub-{r.subject}_ses-{r.session}_trial-{r.trial}_{r.condition}.npz"
        if os.path.exists(path):  # resume after a crash
            d = np.load(path)
            curves[r.subject].append((int(d["n"]), d["curve"]))
            continue
        try:
            eeg, story = prepare(r)
            scores, starts = lag_scores(model, eeg, story, LAGS, SEG, round(HOP_S * FS), device=device)
        except Exception as e:  # noqa: BLE001 - logged and skipped
            print(f"{name}: trial {i + 1} (sub {r.subject}) FAILED: {type(e).__name__}: {e}", flush=True)
            continue
        np.savez(path, n=len(starts), curve=scores.mean(1))
        curves[r.subject].append((len(starts), scores.mean(1)))
        best = 1e3 * (LAGS[0] + peak_offset(scores.mean(1))) / FS
        print(f"{name}: trial {i + 1} (sub {r.subject}) done, peak {best:+.0f} ms", flush=True)
    subs = sorted(curves)
    per_sub = np.array([np.average([c for _, c in curves[s]], axis=0, weights=[w for w, _ in curves[s]]) for s in subs])
    pooled = per_sub.mean(0)
    offset = 1e3 * (LAGS[0] + peak_offset(pooled)) / FS
    rng = np.random.default_rng(0)
    boot = [1e3 * (LAGS[0] + peak_offset(per_sub[rng.integers(0, len(subs), len(subs))].mean(0))) / FS
            for _ in range(N_BOOT)]
    res = dict(name=name, n_subjects=len(subs), n_trials=sum(len(v) for v in curves.values()), offset_ms=offset,
               ci95_ms=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
               subject_offsets_ms=[1e3 * (LAGS[0] + peak_offset(c)) / FS for c in per_sub])
    np.savez(f"{out}/{name.split(' ')[0]}.npz", lags_ms=1e3 * LAGS / FS, pooled=pooled, per_subject=per_sub)
    json.dump(res, open(f"{out}/{name.split(' ')[0]}.json", "w"), indent=1)
    print(f"=== {name}: offset {offset:+.1f} ms (95% CI {res['ci95_ms'][0]:+.1f} .. {res['ci95_ms'][1]:+.1f})", flush=True)
    return res


def overview(results, out):
    fig, axs = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    cmap = plt.get_cmap("tab10")
    for i, r in enumerate(results):
        d = np.load(f"{out}/{r['name'].split(' ')[0]}.npz")
        c = d["pooled"]
        axs[0].plot(d["lags_ms"], (c - np.median(c)) / (c.max() - np.median(c)), color=cmap(i % 10), linewidth=1.5,
                    label=r["name"])
    axs[0].axvline(0, color="#52514e", linewidth=0.8)
    axs[0].set_xlabel("lag (ms; − = neural data late vs accou2023)", color="#52514e")
    axs[0].set_ylabel("classifier score (scaled)", color="#52514e")
    axs[0].set_title("lag scans, pooled over subjects", loc="left", fontsize=10)
    axs[0].legend(frameon=False, fontsize=7)
    y = np.arange(len(results))
    off = np.array([r["offset_ms"] for r in results])
    ci = np.array([r["ci95_ms"] for r in results])
    axs[1].errorbar(off, y, xerr=[off - ci[:, 0], ci[:, 1] - off], fmt="o", color="#2a78d6", capsize=3)
    axs[1].set_yticks(y, [f"{r['name']} (n={r['n_subjects']})" for r in results], fontsize=8)
    axs[1].axvline(0, color="#52514e", linewidth=0.8)
    axs[1].set_xlabel("offset (ms), 95% CI over subjects", color="#52514e")
    axs[1].set_title("constant offset relative to accou2023", loc="left", fontsize=10)
    for a in axs:
        a.grid(alpha=0.25, linewidth=0.5)
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"Dataset timing offsets from the {spec.name} match-mismatch classifier", x=0.01, ha="left", fontsize=12)
    fig.savefig(f"{out}/offsets.png", dpi=120)


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    results = []
    for name in sys.argv[2:] or DATASETS:
        try:
            results.append(run(name, out))
        except Exception as e:  # noqa: BLE001 - keep going
            print(f"=== {name} FAILED: {type(e).__name__}: {e}", flush=True)
        if results:
            overview(results, out)
    json.dump(results, open(f"{out}/offsets.json", "w"), indent=1)
