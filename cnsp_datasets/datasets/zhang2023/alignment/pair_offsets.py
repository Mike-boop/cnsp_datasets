"""
Per-pair DNN offsets from the dnn_scan caches -> pair_offsets.csv.

A pair is the two presentations of one stimulus pair (the same two files) in one subject. Each
presentation is a separate EEG recording; its curve is the mean window score per lag (lags with >= 50% of the
windows valid). Pooled over both presentations, the peak z (peak minus median, over the SD across lags) is compared
with null pairs (the same computed with the mismatched-source scores, pairs with window counts within x0.5-2).
Confident: pooled p < 0.01 and the two presentations' own peaks within 0.25 s.
Usage: python -m cnsp_datasets.datasets.zhang2023.alignment.pair_offsets <scan_dir> [figure.png]
"""
import collections
import csv
import glob
import os
import sys

import numpy as np

from cnsp_datasets.datasets.zhang2023.alignment.splices import FS_EEG as FS, HERE

P_MAX, AGREE_S = 0.01, 0.25


def _sums(scores):
    s = scores.astype(float)
    return np.nansum(s, 1), np.sum(np.isfinite(s), 1)


def _peak(total, count, lags):
    ok = count >= 0.5 * count.max()
    c = np.where(ok, total / np.maximum(count, 1), np.nan)
    i = np.nanargmax(c)
    return lags[i], (c[i] - np.nanmedian(c)) / np.nanstd(c)


def pair_rows(scan_dir):
    trials, lags = {}, None
    for path in sorted(glob.glob(os.path.join(scan_dir, "S*_t*.npz"))):
        d = np.load(path)
        if int(d["n"]) < 4:
            continue
        lags = d["lags"]
        key = os.path.basename(path)[:-4]
        trials[key] = dict(files=tuple(sorted(d["names"][:2])), n=int(d["n"]),
                           **{k: _sums(d[k]) for k in ("att", "null0", "null1")})
    groups = collections.defaultdict(list)
    for key, t in trials.items():
        groups[(key[:3], t["files"])].append(key)
    rows = []
    for (subject, files), keys in sorted(groups.items()):
        if len(keys) != 2:
            continue
        a, b = sorted(keys)
        for stim in ("att", "null0", "null1"):
            total = trials[a][stim][0] + trials[b][stim][0]
            count = trials[a][stim][1] + trials[b][stim][1]
            lag, z = _peak(total, count, lags)
            rows.append(dict(subject=subject, trial_a=int(a[5:]), trial_b=int(b[5:]), stim=stim,
                             lag_samples=int(lag), lag_s=lag / FS, z=z,
                             lag_a_s=_peak(*trials[a][stim], lags)[0] / FS,
                             lag_b_s=_peak(*trials[b][stim], lags)[0] / FS,
                             n_windows=trials[a]["n"] + trials[b]["n"]))
    nulls = [r for r in rows if r["stim"] != "att"]
    for r in rows:
        ref = np.array([q["z"] for q in nulls if q is not r and 0.5 <= q["n_windows"] / r["n_windows"] <= 2])
        r["p"] = (1 + np.sum(ref >= r["z"])) / (1 + len(ref))
        r["confident"] = bool(r["p"] < P_MAX and abs(r["lag_a_s"] - r["lag_b_s"]) <= AGREE_S)
    return rows


def main(scan_dir, figure=None):
    rows = pair_rows(scan_dir)
    att = [r for r in rows if r["stim"] == "att"]
    nul = [r for r in rows if r["stim"] != "att"]
    print(f"pairs {len(att)}: confident {sum(r['confident'] for r in att)}; "
          f"null pairs confident {sum(r['confident'] for r in nul)} of {len(nul)}")
    fields = ["subject", "trial_a", "trial_b", "lag_samples", "lag_s", "z", "p", "lag_a_s", "lag_b_s", "n_windows",
              "confident"]
    with open(os.path.join(HERE, "pair_offsets.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in att:
            w.writerow({**r, **{k: round(r[k], 4) for k in ("lag_s", "z", "p", "lag_a_s", "lag_b_s")}})
    if figure:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        subjects = sorted({r["subject"] for r in att})
        fig, axs = plt.subplots(4, 6, figsize=(18, 10), squeeze=False, sharey=True)
        for ax, s in zip(axs.ravel(), subjects):
            for r in (r for r in att if r["subject"] == s):
                col = "tab:green" if r["confident"] else "0.75"
                ax.plot([r["trial_a"], r["trial_b"]], [r["lag_a_s"], r["lag_b_s"]], "-", color=col, lw=1)
                ax.scatter([(r["trial_a"] + r["trial_b"]) / 2], [r["lag_s"]], color=col,
                           s=10 + 6 * max(r["z"] - 2, 0) ** 2, zorder=3)
            ax.axhline(0, color="r", lw=0.5)
            ax.set_title(f"{s}: {sum(r['confident'] for r in att if r['subject'] == s)} confident pairs", fontsize=8)
        for ax in axs.ravel()[len(subjects):]:
            ax.axis("off")
        fig.suptitle("zhang2023 DNN pair offsets (dot: pooled; line: the two presentations; green: confident)")
        fig.supxlabel("trial")
        fig.supylabel("lag (s); negative = EEG later than the shipped pairing")
        plt.tight_layout()
        plt.savefig(figure, dpi=90)


if __name__ == "__main__":
    main(*sys.argv[1:3])
