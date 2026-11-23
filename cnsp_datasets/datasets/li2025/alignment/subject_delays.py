"""
li2025: per-subject onset delay by template match; writes the adaptor's default table (../onset.csv).

usage: python -m cnsp_datasets.datasets.li2025.alignment.subject_delays <download dir> <trf_weights dir> <out dir>
Template: group A's onset-corrected TRF (trf_weights.py, mean over subjects, channels good in all subjects, lags
-0.2..+0.6 s). Each subject's uncorrected TRF is refitted over the wider MATCH_LAGS (-1.5..+2.5 s; common.match_trfs,
cached in <out>/match_trfs), so delays of 0..1.9 s can be searched. The delay of a TRF is its best match to the
template (common.match_curve / match_delay). Per subject: delay and peak r of the whole-recording TRF, median and MAD
of the five parts' delays (each part matched only within common.PART_WINDOW = 0.3 s of the whole-recording delay, so
a weak part cannot lock onto a far peak; sub-54, truncated: two halves of its 698 s) and, for group A, the delay
against a leave-one-subject-out template (circularity check). Unreliable (peak r < MIN_R or parts MAD > MAX_MAD):
the group's delay (adaptor ONSET_DELAY_S), flagged. Ambiguous (adopted delays only): another local maximum of the
match curve, search edges included, within AMBIG_R of the best r and more than AMBIG_S away (flagged, delay kept).
<out>: subject_delays.png, part_delays.json (input of drift.py) and heldout_delays.json (delays from parts 1,3,5 and
from 2,4, input of heldout.py).
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from cnsp_datasets.datasets.li2025.adaptor import ONSET_CSV, ONSET_DELAY_S
from cnsp_datasets.datasets.li2025.alignment.common import (CANDS, FS, WIN, group, load_weights, match_curve,
                                                             match_delay, match_trfs)

# MIN_R, MAX_MAD, AMBIG_R, AMBIG_S and common.PART_WINDOW: keep in sync with adaptor.SUBJECT_METHOD
MIN_R = 0.15
MAX_MAD = 0.05  # s
AMBIG_R = 0.15  # a second peak this close to the best match r ...
AMBIG_S = 0.1  # ... and this far from it (s) flags the delay as ambiguous
SPLITS = {"135": [0, 2, 4], "24": [1, 3]}  # held-out test: estimate on one set of parts, score on the other
TRUNCATED = 54


def second_peak(c):
    """Delay (s) and r of the best other local maximum (edges included) of match curve c more than AMBIG_S away."""
    edges = [i for i, j in ((0, 1), (len(c) - 1, len(c) - 2)) if c[i] >= c[j]]
    k = np.array([i for i in list(find_peaks(c)[0]) + edges if abs(i - c.argmax()) > AMBIG_S * FS])
    if not len(k):
        return None, None
    k = k[np.argmax(c[k])]
    return k / FS, float(c[k])


def estimate(template, W, parts):
    """
    Match of a TRF and of its parts: delay (s), peak r, at search edge, parts' delays (each within PART_WINDOW of the
    TRF's delay), their median and MAD (s), curves.
    """
    c = match_curve(template, W)
    delay = match_delay(c)
    pc = [match_curve(template, p) for p in parts]
    part_delays = np.array([match_delay(x, near=delay) for x in pc])
    med = float(np.median(part_delays))
    return dict(delay=delay, r=float(c.max()), edge=bool(c.argmax() == len(c) - 1), part_delays=part_delays,
                parts_median=med, parts_mad=float(np.median(np.abs(part_delays - med))), curve=c, part_curves=pc)


def adopt(e, g):
    """Adopted delay (s) and the reasons for falling back to the group delay (empty if none)."""
    reasons = []
    if e["r"] < MIN_R:
        reasons.append(f"peak r {e['r']:.2f} < {MIN_R}")
    if e["parts_mad"] > MAX_MAD:
        reasons.append(f"parts MAD {e['parts_mad'] * 1e3:.0f} ms > {MAX_MAD * 1e3:.0f}")
    return (ONSET_DELAY_S[g] if reasons else round(e["delay"], 3)), reasons


def main(argv):
    src, weights, out = argv[:3]
    os.makedirs(out, exist_ok=True)
    _, common, stack = load_weights(weights)
    trfs = match_trfs(src, common, os.path.join(out, "match_trfs"))
    A = stack("A", "w_corrected")
    A_subs = [s for s in trfs if group(s) == "A"]
    assert len(A_subs) == len(A), "trf_weights and the download disagree on group A"
    template = A.mean(0)[WIN].ravel()
    loso = {s: np.delete(A, i, 0).mean(0)[WIN].ravel() for i, s in enumerate(A_subs)}

    rows, curves, part_delays = [], {}, {}
    for s, (whole, parts, centres) in trfs.items():
        g = group(s)
        e = estimate(template, whole, parts)
        el = estimate(loso[s], whole, parts) if s in loso else None
        curves[s] = dict(full=e["curve"], parts=e["part_curves"], loso=None if el is None else el["curve"])
        delay, reasons = adopt(e, g)
        d2, r2 = second_peak(e["curve"])
        ambiguous = not reasons and d2 is not None and r2 >= e["r"] - AMBIG_R
        part_delays[s] = dict(group=g, delay_s=e["delay"], fallback=bool(reasons), centres_s=centres.tolist(),
                              part_delays_s=e["part_delays"].tolist())
        rows.append(dict(subject=s, group=g, delay_s=delay,
                         method=f"fallback to group {g} delay ({'; '.join(reasons)})" if reasons else "",
                         match_r=round(e["r"], 3), match_delay_s=round(e["delay"], 3), match_at_edge=e["edge"],
                         parts_median_s=round(e["parts_median"], 3), parts_mad_ms=round(e["parts_mad"] * 1e3, 1),
                         n_parts=len(parts), fallback=bool(reasons), onset_ambiguous=ambiguous,
                         second_peak_s=None if d2 is None else round(d2, 3),
                         second_peak_r=None if d2 is None else round(r2, 3),
                         loso_delay_s=None if el is None else round(el["delay"], 3),
                         loso_r=None if el is None else round(el["r"], 3),
                         loso_at_edge=None if el is None else el["edge"]))
    df = pd.DataFrame(rows)
    df.to_csv(ONSET_CSV, index=False)
    print(df.drop(columns="method").to_string(index=False))
    with open(os.path.join(out, "part_delays.json"), "w") as f:
        json.dump(part_delays, f, indent=1)

    # held-out: delays from a subset of the parts (TRF = mean of the per-part fits, not one refit); variant "loso"
    # matches group A against its leave-one-out template; sub-54 (two halves only) left out
    heldout = {}
    for name, idx in SPLITS.items():
        for variant in ("full", "loso"):
            d = {}
            for s, (_, parts, _) in trfs.items():
                if s == TRUNCATED:
                    continue
                P = parts[idx]
                e = estimate(loso[s] if variant == "loso" and s in loso else template, P.mean(0), P)
                delay, reasons = adopt(e, group(s))
                d[s] = dict(delay=delay, r=e["r"], fallback=bool(reasons))
            heldout[f"{name}_{variant}"] = d
    with open(os.path.join(out, "heldout_delays.json"), "w") as f:
        json.dump(heldout, f, indent=1)
    plot(df, curves, CANDS / FS, os.path.join(out, "subject_delays.png"))


def plot(df, curves, d_s, png):
    """One panel per subject: match curves (whole recording, leave-one-out, parts), adopted and group delays."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nc = 6
    nr = int(np.ceil(len(df) / nc))
    fig, ax = plt.subplots(nr, nc, figsize=(3.2 * nc, 2.4 * nr), sharex=True, sharey=True)
    for a, row in zip(ax.flat, df.itertuples()):
        c = curves[row.subject]
        for p in c["parts"]:
            a.plot(d_s, p, color="0.7", lw=0.7)
        a.plot(d_s, c["full"], "k", lw=1.5)
        if c["loso"] is not None:
            a.plot(d_s, c["loso"], "C2", lw=1)
        a.axvline(ONSET_DELAY_S[row.group], color="C1", ls=":", lw=1)
        a.axvline(row.delay_s, color="C3" if row.fallback else "C0", lw=1)
        a.axhline(0, color="k", lw=0.4)
        a.set_title(f"sub-{row.subject} ({row.group}): {row.delay_s:.3f} s, r {row.match_r:.2f}"
                    + (" FALLBACK" if row.fallback else "") + (" AMBIGUOUS" if row.onset_ambiguous else ""),
                    fontsize=8, color="C3" if row.fallback else "k")
    for a in ax.flat[len(df):]:
        a.axis("off")
    for a in ax[-1]:
        a.set_xlabel("delay d (s)")
    for a in ax[:, 0]:
        a.set_ylabel("match r")
    handles = [plt.Line2D([], [], color="k", label="whole recording"),
               plt.Line2D([], [], color="C2", label="leave-one-out template (A)"),
               plt.Line2D([], [], color="0.7", label="parts"),
               plt.Line2D([], [], color="C0", label="adopted delay"),
               plt.Line2D([], [], color="C3", label="adopted (fallback)"),
               plt.Line2D([], [], color="C1", ls=":", label="group delay")]
    fig.legend(handles=handles, loc="lower right", fontsize=9)
    fig.suptitle("li2025: per-subject onset delay, match to group A's corrected TRF (analysis only)")
    fig.tight_layout()
    fig.savefig(png, dpi=90)


if __name__ == "__main__":
    main(sys.argv[1:])
