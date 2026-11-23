"""
li2025: population 0.5-8 Hz envelope TRF per recording group over lags -1.5..+1.5 s, with circular-shift nulls.

usage: python -m cnsp_datasets.datasets.li2025.alignment.poptrf <download dir> <out dir> [delay_A,delay_B s] [n_null]
The envelope is delayed by the group's delay before the design is built (default 0,0: the shipped onset). Uncorrected,
group A's GFP peaks at +0.92 s (-> 0.80 s delay with a ~0.1 s response latency); with the delays applied each group
should peak near +0.1 s. GFP = RMS over all subjects' channels of the ridge TRF from X'Y pooled per group.
"""
import json
import os
import sys

import numpy as np

from cnsp_datasets.datasets.li2025.adaptor import GROUP_LABEL
from cnsp_datasets.datasets.li2025.alignment.common import FS, LAGS, delayed, design, envelope, group, meg, regularised


def main(argv):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    src, out = argv[:2]
    delay = dict(zip("AB", [float(v) for v in (argv[2] if len(argv) > 2 else "0,0").split(",")]))
    n_null = int(argv[3]) if len(argv) > 3 else 20
    os.makedirs(out, exist_ok=True)
    env = envelope(src)
    shifts = np.concatenate([[0], np.random.default_rng(0).integers(30 * FS, len(env) - 30 * FS, n_null)])
    envs = {g: delayed(env, d) for g, d in delay.items()}
    X0 = {g: design(e) for g, e in envs.items()}
    xy = {g: [[] for _ in shifts] for g in delay}
    for sub, _, Y in meg(src):
        g = group(sub)
        for i, k in enumerate(shifts):  # nulls rebuilt per subject: slow but light on memory
            X = X0[g] if k == 0 else design(np.roll(envs[g], k))
            xy[g][i].append((X.T @ Y).T)
        print(sub, g, flush=True)

    lags_s = LAGS / FS
    res = {}
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for g, col in zip("AB", ["C0", "C1"]):
        reg = regularised(X0[g])
        gfp = np.array([np.sqrt((np.linalg.solve(reg, c.T) ** 2).mean(1)) for c in map(np.vstack, xy[g])])
        null50, null95 = np.median(gfp[1:], 0), np.percentile(gfp[1:], 95, 0)
        ratio = gfp[0] / null50
        peak = float(lags_s[np.argmax(ratio)])
        res[g] = dict(delay_s=delay[g], n=len(xy[g][0]), peak_s=peak, max_ratio=float(ratio.max()),
                      lags_s=lags_s.tolist(), ratio=ratio.tolist(), null95_ratio=(null95 / null50).tolist())
        ax.plot(lags_s, ratio, col,
                label=f"{GROUP_LABEL[g]}, delayed {delay[g]:.2f} s, n={res[g]['n']}: peak {peak:+.3f} s")
        ax.plot(lags_s, null95 / null50, col, ls=":", lw=0.8)
        print(g, "peak", peak, "max ratio", ratio.max(), flush=True)
    tag = f"{delay['A']:g}_{delay['B']:g}"
    with open(os.path.join(out, f"poptrf_{tag}.json"), "w") as f:
        json.dump(res, f)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel("lag (s; > 0: MEG after the sound as placed)")
    ax.set_ylabel("GFP / null median (dotted: null 95%)")
    ax.set_title("li2025: 0.5-8 Hz envelope TRF GFP per recording group")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"poptrf_{tag}.png"), dpi=100)


if __name__ == "__main__":
    main(sys.argv[1:])
