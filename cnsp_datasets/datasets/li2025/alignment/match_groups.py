"""
li2025: find the group-B onset delay that best matches group B's multichannel TRF to group A's corrected TRF.

usage: python -m cnsp_datasets.datasets.li2025.alignment.match_groups <trf_weights dir> <out dir>
Group averages per channel (rigid helmet, channels matched by name, channels good in all subjects). Template: A's TRF
with A's delay applied, lags -0.2..+0.6 s. For each candidate B delay d (0..0.8 s, one 64 Hz sample steps), B's
uncorrected TRF is read at lags (template lag + d) and the space-time correlation with the template is computed.
Bootstrap over B subjects (1000) gives a CI for the best d. Also overlays A and B at the best d and at 0.30/0.42/0.55 s.
"""
import json
import os
import sys

import mne
import numpy as np

from cnsp_datasets.datasets.li2025.alignment.common import FS, load_weights

REFERENCE_DELAYS = {0.30: "C2", 0.42: "C4", 0.55: "C1"}


def main(argv):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    src, out = argv[:2]
    os.makedirs(out, exist_ok=True)
    data, common, stack = load_weights(src)
    lags = data[0]["lags_s"]
    A_sub = stack("A", "w_corrected")
    A = A_sub.mean(0)
    Bsub = stack("B", "w_uncorrected")
    win = (lags >= -0.2) & (lags <= 0.6)
    i0 = np.where(win)[0]
    tmpl = A[win].ravel()
    cands = np.arange(0, round(0.8 * FS) + 1)

    def score(B):
        return np.array([np.corrcoef(tmpl, B[i0 + k].ravel())[0, 1] for k in cands])

    r = score(Bsub.mean(0))
    best = cands[np.argmax(r)] / FS
    rng = np.random.default_rng(0)
    boot = [cands[np.argmax(score(Bsub[rng.integers(0, len(Bsub), len(Bsub))].mean(0)))] / FS for _ in range(1000)]
    ci = np.percentile(boot, [2.5, 97.5])
    res = dict(best_delay_s=float(best), r_best=float(r.max()), ci95_s=ci.tolist(), n_A=len(A_sub), n_B=len(Bsub),
               channels=len(common), r_at={f"{d:.2f}": float(r[round(d * FS)]) for d in REFERENCE_DELAYS},
               delays_s=(cands / FS).tolist(), r=r.tolist())
    with open(os.path.join(out, "match_groups.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("delays_s", "r")}, indent=1))

    info = mne.create_info(common, 1.0, "mag")
    locs = {c: loc for d in data for c, loc in zip(d["ch_names"], d["ch_locs"])}
    for ch in info["chs"]:
        ch["loc"] = locs[ch["ch_name"]]
    delay_A = next(float(d["delay_s"]) for d in data if str(d["group"]) == "A")
    Bm = Bsub.mean(0)
    fig = plt.figure(figsize=(15, 10))
    gs = fig.add_gridspec(3, 4)
    ax = fig.add_subplot(gs[0, :2])
    ax.plot(cands / FS, r, "k")
    ax.axvline(best, color="C3", label=f"best {best:.3f} s (95% CI {ci[0]:.2f}-{ci[1]:.2f})")
    for d, c in REFERENCE_DELAYS.items():
        ax.axvline(d, color=c, ls="--", label=f"{d:.2f} s: r {r[round(d * FS)]:.2f}")
    ax.set_xlabel("group B delay (s)")
    ax.set_ylabel("space-time r with A template")
    ax.legend(fontsize=8)
    ax.set_title("match of B's TRF to A's corrected TRF (-0.2..0.6 s, common channels)")
    gA = np.sqrt((A ** 2).mean(1))
    gB = np.sqrt((Bm ** 2).mean(1))
    ax2 = fig.add_subplot(gs[0, 2:])
    ax2.plot(lags, gA / gA.max(), "C0", lw=2, label=f"A corrected ({delay_A:.2f} s)")
    for d, c in {best: "C3", **REFERENCE_DELAYS}.items():
        ax2.plot(lags - d, gB / gB.max(), c, lw=1, label=f"B delayed {d:.2f} s")
    ax2.set_xlim(-0.4, 0.8)
    ax2.axvline(0, color="k", lw=0.6)
    ax2.set_xlabel("lag (s)")
    ax2.legend(fontsize=8)
    ax2.set_title("GFP (normalised)")
    pk_t = sorted({0.094, 0.25, round(float(lags[i0][np.argmax(gA[win])]), 3)})
    for j, t in enumerate(pk_t[:4]):
        ia = np.argmin(np.abs(lags - t))
        ib = np.argmin(np.abs(lags - (t + best)))
        for row, (W, k, lab) in enumerate(((A, ia, "A"), (Bm, ib, f"B (+{best:.2f} s)"))):
            tax = fig.add_subplot(gs[1 + row, j])
            mne.viz.plot_topomap(W[k] / np.abs(W).max(), info, axes=tax, show=False, vlim=(-1, 1), cmap="RdBu_r",
                                 contours=4)
            tax.set_title(f"{lab} at {t * 1000:+.0f} ms", fontsize=9)
    fig.suptitle("li2025: aligning group B to group A by multichannel TRF match (analysis only)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "match_groups.png"), dpi=100)


if __name__ == "__main__":
    main(sys.argv[1:])
