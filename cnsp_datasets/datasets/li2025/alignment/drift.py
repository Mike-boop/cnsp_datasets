"""
li2025: brain-based clock drift from the onset delay in each part of the recording (template matching).

usage: python -m cnsp_datasets.datasets.li2025.alignment.drift <download dir> <trf_weights dir> <out dir> [n_parts]
Per subject (sub-54 left out), the uncorrected recording is split into n_parts (default 3, ~506 s each) and a ridge
envelope TRF (lags -1.5..+1.5 s, common.py preprocessing) is fitted per part (cached per subject). Template: group A's
onset-corrected TRF (trf_weights.py, mean over subjects, channels good in all subjects, lags -0.2..+0.6 s). The delay
of a TRF is the shift d (0..0.9 s, parabolic refinement) at which its lags d - 0.2..d + 0.6 s correlate best with the
template over space and time. Per group: delays of the subject-averaged TRF per part, slope over the part centres
(ppm; > 0: the delay grows, i.e. the MEG clock is fast relative to the audio, as cnsp_datasets.standardise.clock), and
a bootstrap over subjects (1000) for its 95% CI. Per-subject slopes are noisier and shown for reference.
"""
import json
import os
import sys

import numpy as np

from cnsp_datasets.align.scan import peak_offset
from cnsp_datasets.datasets.li2025.adaptor import GROUP_LABEL
from cnsp_datasets.datasets.li2025.alignment.common import (FS, LAGS, N, design, envelope, group, load_weights,
                                                             meg, regularised)


def part_trfs(src, out, common, n_parts):
    """Per-part TRFs (subjects x parts x lags x common channels), subjects, part centres (s); cached per subject."""
    cache = os.path.join(out, f"parts_{n_parts}")
    os.makedirs(cache, exist_ok=True)
    env = idx = X = regs = None
    parts, subs = [], []
    for sub, info, Y in meg(src):
        f = os.path.join(cache, f"sub-{sub:02d}.npz")
        if os.path.exists(f) and list(np.load(f)["common"]) == common:
            parts.append(np.load(f)["w"])
        else:
            if env is None:
                env = envelope(src)
                X = design(env)
                idx = np.array_split(np.arange(len(env)), n_parts)
                regs = [regularised(X[i]) for i in idx]
            cols = [info["ch_names"].index(c) for c in common]
            parts.append(np.array([np.linalg.solve(r, X[i].T @ Y[i][:, cols]) for i, r in zip(idx, regs)]))
            np.savez(f, w=parts[-1], common=np.array(common))
        subs.append(sub)
        print(sub, flush=True)
    centres = np.array([i.mean() / FS for i in np.array_split(np.arange(N), n_parts)])
    return np.array(parts), np.array(subs), centres


def main(argv):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    src, weights, out = argv[:3]
    n_parts = int(argv[3]) if len(argv) > 3 else 3
    os.makedirs(out, exist_ok=True)
    lags_s = LAGS / FS
    _, common, stack = load_weights(weights)
    win = np.where((lags_s >= -0.2) & (lags_s <= 0.6))[0]
    template = stack("A", "w_corrected").mean(0)[win].ravel()
    cands = np.arange(0, len(LAGS) - win[-1])  # shifts that keep the window within the fitted lags (0..0.9 s)

    def delay(W):
        """Best-matching delay (s) of a TRF (lags x common channels) to the template."""
        r = np.array([np.corrcoef(template, W[win + k].ravel())[0, 1] for k in cands])
        if r.argmax() == len(r) - 1:
            print("warning: best delay at the edge of the search range", flush=True)
        return peak_offset(r) / FS

    def slope_ppm(t, d):
        return float(np.polyfit(t, d, 1)[0] * 1e6)

    parts, subs, centres = part_trfs(src, out, common, n_parts)
    res = {"n_parts": n_parts, "part_centres_s": centres.tolist(), "channels": len(common)}
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.5))
    for g, col in zip("AB", ["C0", "C1"]):
        sel = np.array([group(s) == g for s in subs])
        P = parts[sel]
        d = [delay(P[:, k].mean(0)) for k in range(n_parts)]
        boot = []
        for _ in range(1000):
            b = P[rng.integers(0, len(P), len(P))].mean(0)
            boot.append(slope_ppm(centres, [delay(b[k]) for k in range(n_parts)]))
        per_sub = [slope_ppm(centres, [delay(p[k]) for k in range(n_parts)]) for p in P]
        res[g] = dict(n=int(sel.sum()), delays_s=d, drift_ppm=slope_ppm(centres, d),
                      ci95_ppm=np.percentile(boot, [2.5, 97.5]).tolist(), boot_sd_ppm=float(np.std(boot)),
                      per_subject_ppm=dict(zip(map(int, subs[sel]), per_sub)),
                      per_subject_median_ppm=float(np.median(per_sub)))
        print(g, json.dumps({k: v for k, v in res[g].items() if k != "per_subject_ppm"}), flush=True)
        ci = res[g]["ci95_ppm"]
        ax[0].plot(centres / 60, np.array(d) * 1e3, "o-", color=col,
                   label=f"{GROUP_LABEL[g]}: {res[g]['drift_ppm']:+.0f} ppm (95% CI {ci[0]:+.0f}..{ci[1]:+.0f})")
        ax[1].plot(subs[sel], per_sub, "o", color=col, label=GROUP_LABEL[g])
    with open(os.path.join(out, "drift.json"), "w") as f:
        json.dump(res, f, indent=1)
    ax[0].set_xlabel("part centre (min)")
    ax[0].set_ylabel("delay of the sound after the shipped onset (ms)")
    ax[0].set_title(f"group-average TRF delay per part ({n_parts} parts), template = group A corrected")
    ax[0].legend(fontsize=8)
    ax[1].axhline(0, color="k", lw=0.5)
    ax[1].set_xlabel("subject")
    ax[1].set_ylabel("drift (ppm)")
    ax[1].set_title("per-subject slopes (noisy)")
    ax[1].legend(fontsize=8)
    fig.suptitle("li2025: brain-based drift estimate (analysis only, not applied)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "drift.png"), dpi=100)


if __name__ == "__main__":
    main(sys.argv[1:])
