"""
Summarise <work dir>/scalp_vs_ceegrid/*.json (scalp_vs_ceegrid.py): alignment/ceegrid_onsets.csv for the adaptor,
summary json and figures in <work dir>.

    python -m cnsp_datasets.datasets.holtze2021.alignment.scalp_vs_ceegrid_summary <work dir>
"""
import csv
import glob
import json
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ceegrid_onsets.csv")  # overwritten


def main(R: str) -> None:
    """Write CSV (the committed table read by the adaptor) and the summary json/figures in R."""
    os.makedirs(f"{R}/figures", exist_ok=True)
    res = []
    for path in sorted(glob.glob(f"{R}/scalp_vs_ceegrid/bjh*.json")):
        with open(path) as f:
            res.append(json.load(f))
    rows = []
    for x in res:
        for b in x["blocks"]:
            rows.append(dict(ds004015=x["ds004015"], ds003516=f"sub-{x['bjh']:03d}", block=b["block"],
                             start_trigger_ds004015_s=round(x["st15"][b["block"] - 1], 3),
                             start_trigger_ds003516_s=round(x["st16"][b["block"] - 1], 3),
                             lag_ms=round(float(np.median(b["win_lag_ms"])), 2),
                             block_xcorr_lag_ms=round(b.get("block_xcorr_lag_ms", b["lag_ms"]), 2), peak_z=round(b["peak_z"], 1),
                             win_lag_sd_ms=round(float(np.std(b["win_lag_ms"])), 2),
                             drift_xcorr_ppm=round(b["drift_ppm"], 2), drift_line_ppm=round(b["line_ppm"], 2),
                             line_coherence=round(b["line_coh"], 3)))
    with open(CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    lag = np.array([r["lag_ms"] for r in rows])
    z = np.array([r["peak_z"] for r in rows])
    dx = np.array([r["drift_xcorr_ppm"] for r in rows])
    dl = np.array([r["drift_line_ppm"] for r in rows])
    coh = np.array([r["line_coherence"] for r in rows])
    sub_mean = {x["bjh"]: np.mean([np.median(b["win_lag_ms"]) for b in x["blocks"]]) for x in res}
    within = np.concatenate([[np.median(b["win_lag_ms"]) - sub_mean[x["bjh"]] for b in x["blocks"]] for x in res])
    summ = dict(n_sessions=len(res), n_blocks=len(rows), lag_median_ms=float(np.median(lag)),
                lag_range_ms=[float(lag.min()), float(lag.max())], lag_iqr_ms=np.percentile(lag, [25, 75]).tolist(),
                subject_mean_lag_sd_ms=float(np.std(list(sub_mean.values()))), within_subject_block_sd_ms=float(np.std(within)),
                peak_z_min=float(z.min()), drift_xcorr_median_ppm=float(np.median(dx)), drift_xcorr_iqr=np.percentile(dx, [25, 75]).tolist(),
                drift_line_median_ppm=float(np.median(dl[coh > 0.5])), drift_line_iqr=np.percentile(dl[coh > 0.5], [25, 75]).tolist(),
                line_coh_median=float(np.median(coh)))
    with open(f"{R}/scalp_vs_ceegrid_summary.json", "w") as f:
        json.dump(summ, f, indent=1)
    print(json.dumps(summ, indent=1))
    # summary figure
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
    for i, x in enumerate(res):
        ax[0].plot([i] * len(x["blocks"]), [np.median(b["win_lag_ms"]) for b in x["blocks"]], "o", ms=4)
    ax[0].set(xticks=range(len(res)), xticklabels=[f"bjh{x['bjh']:02d}" for x in res], ylabel="cEEGrid lag vs scalp (ms)",
              title=f"per-block lag (median {np.median(lag):.1f} ms)")
    ax[0].tick_params(axis="x", rotation=90)
    m = coh > 0.5
    ax[1].scatter(dx[m], dl[m], s=12)
    ax[1].set(xlabel="drift from windowed xcorr (ppm)", ylabel="drift from 50 Hz phase (ppm)",
              title=f"cEEGrid vs scalp drift per block ({m.sum()} blocks with line coherence > 0.5)")
    ax[2].hist(z, 30)
    ax[2].set(xlabel="xcorr peak z", title="peak strength")
    fig.tight_layout()
    fig.savefig(f"{R}/figures/scalp_vs_ceegrid_summary.png", dpi=110)
    # per-subject figures
    for x in res:
        fig, ax = plt.subplots(1, 2, figsize=(12, 4))
        for b in x["blocks"]:
            ax[0].plot(b["win_t"], b["win_lag_ms"], ".-", label=f"block {b['block']}: {np.median(b['win_lag_ms']):.1f} ms, "
                       f"{b['drift_ppm']:.1f} / {b['line_ppm']:.1f} ppm")
        ax[0].set(xlabel="time in block (s)", ylabel="lag (ms)", title=f"bjh_s{x['bjh']:02d} (ds003516 sub-{x['bjh']:03d} / "
                  f"ds004015 {x['ds004015']}): 60-s window lags")
        ax[0].legend(fontsize=7)
        ax[1].bar(range(1, 6), [b["peak_z"] for b in x["blocks"]])
        ax[1].set(xlabel="block", ylabel="xcorr peak z")
        fig.tight_layout()
        fig.savefig(f"{R}/figures/scalp_vs_ceegrid_bjh{x['bjh']:02d}.png", dpi=90)
        plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1])
