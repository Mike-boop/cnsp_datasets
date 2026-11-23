"""li2025: group-average butterfly plots of the multichannel envelope TRFs, with topomaps at the GFP peaks.

usage: python -m cnsp_datasets.datasets.li2025.alignment.butterfly <trf_weights dir> <out png>
Reads sub-XX.npz from trf_weights.py. Rigid helmet, so channels are matched by name; each channel is averaged
over the subjects in which it is good. Panels: group A (sub-31..47) / B (sub-48..60) x uncorrected / corrected.
Topomaps at the two largest GFP maxima (|lag| <= 1.35 s, >= 150 ms apart), on a shared colour scale per panel.
"""
import glob
import os
import sys

import mne
import numpy as np
from scipy.signal import find_peaks

from cnsp_datasets.datasets.li2025.adaptor import GROUP_LABEL
from cnsp_datasets.datasets.li2025.alignment.common import FS


def main(argv):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    src, out = argv[:2]
    files = sorted(glob.glob(os.path.join(src, "sub-*.npz")))
    data = [np.load(f) for f in files]
    names = sorted({c for d in data for c in d["ch_names"]})
    locs = {}
    for d in data:
        for c, loc in zip(d["ch_names"], d["ch_locs"]):
            locs.setdefault(c, loc)
    info = mne.create_info(names, 1.0, "mag")
    for ch in info["chs"]:
        ch["loc"] = locs[ch["ch_name"]]
    lags = data[0]["lags_s"]
    fig = plt.figure(figsize=(16, 13))
    outer = fig.add_gridspec(4, 1, hspace=0.45)
    row = 0
    for g, lab in GROUP_LABEL.items():
        sub = [d for d in data if str(d["group"]) == g]
        for cond in ("uncorrected", "corrected"):
            acc, cnt = np.zeros((len(lags), len(names))), np.zeros(len(names))
            for d in sub:
                idx = [names.index(c) for c in d["ch_names"]]
                acc[:, idx] += d[f"w_{cond}"]
                cnt[idx] += 1
            W = acc / np.maximum(cnt, 1)
            W = W[:, cnt > 0]
            good = [n for n, k in zip(names, cnt) if k > 0]
            gfp = np.sqrt((W ** 2).mean(1))
            ok = np.abs(lags) <= 1.35
            pk, _ = find_peaks(np.where(ok, gfp, 0), distance=int(0.15 * FS))
            pk = sorted(pk[np.argsort(gfp[pk])[::-1][:2]])
            gs = outer[row].subgridspec(1, 4, width_ratios=[5, 1, 1, 0.08], wspace=0.3)
            ax = fig.add_subplot(gs[0])
            ax.plot(lags, W, lw=0.5, alpha=0.6)
            ax.plot(lags, gfp, "k", lw=2, label="GFP")
            ax.axvline(0, color="r", lw=0.6)
            for p in pk:
                ax.axvline(lags[p], color="k", ls="--", lw=0.8)
            d_ = "" if cond == "uncorrected" else f", stimulus delayed {float(sub[0]['delay_s']):.2f} s"
            ax.set_title(f"group {g} ({lab}, n={len(sub)}), {cond}{d_}", fontsize=10)
            ax.set_xlim(lags[0], lags[-1])
            ax.set_ylabel("TRF weight (z units)")
            if row == 3:
                ax.set_xlabel("lag (s; > 0: MEG after the sound as placed)")
            sub_info = mne.pick_info(info, [names.index(n) for n in good])
            vmax = np.abs(W[pk]).max() if pk else 1
            for k, p in enumerate(pk):
                tax = fig.add_subplot(gs[1 + k])
                im, _ = mne.viz.plot_topomap(W[p], sub_info, axes=tax, show=False, vlim=(-vmax, vmax), cmap="RdBu_r",
                                             sensors=True, contours=4)
                tax.set_title(f"{lags[p] * 1000:+.0f} ms", fontsize=9)
            if pk:
                fig.colorbar(im, cax=fig.add_subplot(gs[3]))
            row += 1
    fig.suptitle(f"li2025: group-average 0.5-8 Hz envelope TRFs ({len(names)} OPM magnetometers, HFC; analysis only)",
                 fontsize=12)
    fig.savefig(out, dpi=100, bbox_inches="tight")
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
