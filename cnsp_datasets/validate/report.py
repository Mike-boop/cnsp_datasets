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


def _trf_panel(ax, res, title, window=None, noise=None):
    """Mean over subjects of the TRF GFP relative to that subject's median null GFP at each lag (noise level = 1)."""
    if res:
        lags = np.array(max((s["lags_s"] for s in res), key=len)) * 1e3  # finest grid (mixed rates)
        if window is not None:
            ax.axvspan(window[0] * 1e3, window[1] * 1e3, color=TRUE, alpha=0.1, linewidth=0, label="latency window")
        if noise is not None:
            ax.axvspan(noise[0] * 1e3, noise[1] * 1e3, color=NULL, alpha=0.15, linewidth=0, label="noise window")
        rel = lambda key: np.mean([np.interp(lags, np.array(s["lags_s"]) * 1e3,  # noqa: E731
                                             np.array(s[key]) / np.array(s["null_gfp_50"])) for s in res], 0)
        ax.fill_between(lags, 1, rel("null_gfp_95"), color=NULL, alpha=0.3, linewidth=0,
                        label="null median to 95th percentile")
        ax.axhline(1, color=NULL, linewidth=1)
        ax.plot(lags, rel("gfp"), color=TRUE, linewidth=2, label="TRF")
        ax.legend(frameon=False, fontsize=8)
    _style(ax, title, "lag (ms)", "GFP / median null GFP")


def plot(result, path):
    """Four panels: 0.5-8 Hz encoding scores vs nulls, and the 0.5-8 Hz, MLR and brainstem TRF GFPs."""
    subjects = result["subjects"]
    fig, axs = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    band = f"{LOW['band'][0]}-{LOW['band'][1]} Hz"

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
    _style(ax, f"Forward model {band}: encoding score", "subject", "r (mean over channels)")

    _trf_panel(axs[0, 1], [s["low"] for s in low], f"Forward TRF {band} (envelope)")
    for ax, (tier, cfg) in zip(axs[1], TIERS.items()):
        res = [s for s in subjects if tier in s]
        window = cfg["window"][res[0]["modality"]] if res else None
        _trf_panel(ax, [s[tier] for s in res], f"Forward TRF {cfg['band'][0]}-{cfg['band'][1]} Hz ({tier})",
                   window, HF["noise"])

    title = result["config"].get("dataset", "")
    fig.suptitle(f"{title}  validation tier: {result['summary']['validation_tier']}", x=0.01, ha="left", fontsize=12)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def save(result, json_path, fig_dir=None):
    """Write the full result to json_path and, if fig_dir is given, the diagnostic figure."""
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(json_path).write_text(json.dumps(result, indent=1))
    if fig_dir is not None:
        Path(fig_dir).mkdir(parents=True, exist_ok=True)
        plot(result, Path(fig_dir) / "validation.png")
