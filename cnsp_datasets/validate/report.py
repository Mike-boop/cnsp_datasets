"""Summary JSON and diagnostic figure for a validation run."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from cnsp_datasets.validate.checks import HF, LOW, TIERS  # noqa: E402

TRUE, NULL, INK = "#2a78d6", "#a3a29c", "#52514e"


def _style(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=10)
    ax.set_xlabel(xlabel, color=INK)
    ax.set_ylabel(ylabel, color=INK)
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.spines[["top", "right"]].set_visible(False)


def plot(result, path):
    """Four panels: per-subject scores vs nulls, lag sweep, MLR and brainstem TRF GFP."""
    subjects = result["subjects"]
    fig, axs = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")

    low = [s for s in subjects if "low" in s]
    ax = axs[0, 0]
    for i, s in enumerate(low):
        lo, hi = np.percentile(s["low"]["null_circ"], [5, 95])
        ax.plot([i, i], [lo, hi], color=NULL, linewidth=4, solid_capstyle="round")
        ax.plot(i, s["low"]["r"], "o", color=TRUE, markersize=6)
    ax.set_xticks(range(len(low)), [s["subject"] for s in low], fontsize=7)
    ax.plot([], [], color=NULL, linewidth=4, label="circular-shift null (5-95%)")
    ax.plot([], [], "o", color=TRUE, label="cross-validated r")
    ax.legend(frameon=False, fontsize=8)
    _style(ax, f"Backward model {LOW['band'][0]}-{LOW['band'][1]} Hz", "subject", "r")

    ax = axs[0, 1]
    for s in low:
        ax.plot(s["low"]["sweep_s"], s["low"]["sweep_r"], color=NULL, linewidth=0.75)
    if low:
        ax.plot(low[0]["low"]["sweep_s"], np.mean([s["low"]["sweep_r"] for s in low], 0), color=TRUE, linewidth=2,
                label="mean over subjects")
        ax.axvline(0, color=INK, linewidth=0.75, linestyle="--")
        ax.legend(frameon=False, fontsize=8)
    _style(ax, "Lag sweep (+d: stimulus delayed by d)", "stimulus shift (s)", "r")

    for ax, (tier, cfg) in zip(axs[1], TIERS.items()):
        res = [s for s in subjects if tier in s]
        if res:
            lags = np.array(res[0][tier]["lags_s"]) * 1e3
            win = cfg["window"][res[0]["modality"]]
            ax.axvspan(win[0] * 1e3, win[1] * 1e3, color=TRUE, alpha=0.1, linewidth=0, label="latency window")
            ax.axvspan(HF["noise"][0] * 1e3, HF["noise"][1] * 1e3, color=NULL, alpha=0.15, linewidth=0,
                       label="noise window")
            norm = [np.median(s[tier]["null_gfp_95"]) for s in res]
            ax.plot(lags, np.mean([np.array(s[tier]["null_gfp_95"]) / n for s, n in zip(res, norm)], 0),
                    color=NULL, linewidth=1.5, label="null 95th percentile")
            ax.plot(lags, np.mean([np.array(s[tier]["gfp"]) / n for s, n in zip(res, norm)], 0),
                    color=TRUE, linewidth=2, label="TRF")
            ax.legend(frameon=False, fontsize=8)
        _style(ax, f"Forward TRF {cfg['band'][0]}-{cfg['band'][1]} Hz ({tier})", "lag (ms)",
               "GFP (relative to median null)")

    tier = result["summary"]["validation_tier"]
    fig.suptitle(f"Validation tier: {tier}", x=0.01, ha="left", fontsize=12)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def save(result, json_path, fig_dir=None):
    """Write the full result to json_path and, if fig_dir is given, the diagnostic figure."""
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(result, indent=1))
    if fig_dir is not None:
        Path(fig_dir).mkdir(parents=True, exist_ok=True)
        plot(result, Path(fig_dir) / "validation.png")
