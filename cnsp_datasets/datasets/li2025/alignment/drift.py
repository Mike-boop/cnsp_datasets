"""
li2025: brain-based clock drift, pooled over subjects, from the onset delay of each part of the recording.

usage: python -m cnsp_datasets.datasets.li2025.alignment.drift <part_delays.json> <out dir>
part_delays.json comes from subject_delays.py (template match of the five parts' wide-lag TRFs; sub-54: two halves).
Per subject (fallback subjects left out), the part delays are taken relative to the subject's own whole-recording
delay, which removes the spread of delays between subjects. Parts more than OUTLIER from it matched another peak
and are dropped. Pooled slope over the part centres (ppm; > 0: the delay grows, i.e. the MEG clock is fast relative
to the audio, as cnsp_datasets.standardise.clock), for all subjects and per group, with a bootstrap over subjects
(1000) for its 95% CI; Theil-Sen over all parts (none dropped) as a robustness check. Per-subject slopes are noisy
and shown for reference. Circular: the template is group A's own corrected TRF.
"""
import json
import os
import sys

import numpy as np
from scipy.stats import theilslopes

from cnsp_datasets.datasets.li2025.adaptor import GROUP_LABEL, N_TIMES

OUTLIER = 0.15  # s
N_BOOT = 1000


def points(subjects, drop=True):
    """Part centres (s) and delays relative to the whole recording (s) of these subjects, concatenated."""
    t, d = [], []
    for s in subjects:
        rel = np.array(s["part_delays_s"]) - s["delay_s"]
        keep = np.abs(rel) <= (OUTLIER if drop else np.inf)
        t += list(np.array(s["centres_s"])[keep])
        d += list(rel[keep])
    return np.array(t), np.array(d)


def ols_ppm(subjects):
    """Pooled OLS slope (ppm) of the kept points."""
    return float(np.polyfit(*points(subjects), 1)[0] * 1e6)


def theil_ppm(subjects):
    """Pooled Theil-Sen slope (ppm) of all points."""
    t, d = points(subjects, drop=False)
    return float(theilslopes(d, t)[0] * 1e6)


def pooled(subjects, rng):
    """Pooled OLS and Theil-Sen slopes (ppm) with bootstrap-over-subjects 95% CIs."""
    res = {}
    for name, f in (("ols", ols_ppm), ("theil_sen", theil_ppm)):
        boot = [f([subjects[i] for i in rng.integers(0, len(subjects), len(subjects))]) for _ in range(N_BOOT)]
        res[name] = dict(drift_ppm=f(subjects), ci95_ppm=np.percentile(boot, [2.5, 97.5]).tolist())
    return res


def fit_line(ax, subjects, ppm, label, **kw):
    """Pooled slope through the mean of the kept points, over the session."""
    tt, dd = points(subjects)
    t = np.array([0, N_TIMES / 1000])
    ax.plot(t / 60, ((t - tt.mean()) * ppm * 1e-6 + dd.mean()) * 1e3, label=label, **kw)


def main(argv):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path, out = argv[:2]
    os.makedirs(out, exist_ok=True)
    with open(path) as f:
        data = {int(k): v for k, v in json.load(f).items()}
    subs = {s: v for s, v in data.items() if not v["fallback"]}
    rng = np.random.default_rng(0)
    sets = {"all": list(subs), **{g: [s for s in subs if subs[s]["group"] == g] for g in "AB"}}
    res = {"outlier_s": OUTLIER, "excluded_fallback": sorted(set(data) - set(subs))}
    for name, ids in sets.items():
        sel = [subs[s] for s in ids]
        res[name] = dict(n=len(ids), parts_dropped=sum(len(s["part_delays_s"]) for s in sel) - len(points(sel)[0]),
                         **pooled(sel, rng))
        print(name, json.dumps(res[name]), flush=True)
    res["per_subject_ppm"] = {s: ols_ppm([subs[s]]) if len(points([subs[s]])[0]) > 1 else None for s in subs}
    with open(os.path.join(out, "drift.json"), "w") as f:
        json.dump(res, f, indent=1)

    fig, ax = plt.subplots(1, 2, figsize=(14, 4.8))
    for name, col in zip(sets, ["k", "C0", "C1"]):
        sel = [subs[s] for s in sets[name]]
        o = res[name]["ols"]
        label = (f"{GROUP_LABEL.get(name, name)} (n {res[name]['n']}): {o['drift_ppm']:+.1f} ppm "
                 f"(95% CI {o['ci95_ppm'][0]:+.1f}..{o['ci95_ppm'][1]:+.1f})")
        if name != "all":
            tt, dd = points(sel)
            ax[0].plot(tt / 60, dd * 1e3, "o", color=col, ms=3, alpha=0.5)
            ids = [s for s in sets[name] if res["per_subject_ppm"][s] is not None]
            ax[1].plot(ids, [res["per_subject_ppm"][s] for s in ids], "o", color=col, label=GROUP_LABEL[name])
        fit_line(ax[0], sel, o["drift_ppm"], label, color=col, lw=2 if name == "all" else 1.2)
    ax[0].axhline(0, color="0.6", lw=0.5)
    ax[0].set_xlabel("part centre (min)")
    ax[0].set_ylabel("part delay - whole-recording delay (ms)")
    ax[0].set_title(f"pooled drift (parts > {OUTLIER * 1e3:.0f} ms off dropped: {res['all']['parts_dropped']})")
    ax[0].legend(fontsize=8)
    ax[1].axhline(0, color="0.6", lw=0.5)
    ax[1].axhline(res["all"]["ols"]["drift_ppm"], color="k", lw=2, label="pooled, all")
    ax[1].set_xlabel("subject")
    ax[1].set_ylabel("drift (ppm)")
    ax[1].set_title("per-subject slopes (noisy)")
    ax[1].legend(fontsize=8)
    fig.suptitle("li2025: brain-based drift relative to each subject's own delay (analysis only, not applied; "
                 "template = group A, circular)")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "drift.png"), dpi=100)


if __name__ == "__main__":
    main(sys.argv[1:])
