"""
Residual drift and onset check with the accou2023 match-mismatch classifier (dnn_offsets.py's prepare/lag scan):
per trial, windows in the first EDGE_S seconds vs the last EDGE_S seconds; per subject and group, the pooled lag-scan
peak for early, late and all windows. late - early = residual drift over the trial (negative = neural data later at
the end, i.e. under-corrected drift). Cached per trial. Usage: dnn_drift_check.py <standardised> <out> <groupby>
groupby: 'session' (default) groups trials by session.
"""
import json
import os
import runpy
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, "/home/gu08wuvu/cnsp_datasets")
m = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dnn_offsets.py"))
from cnsp_datasets.standardise.flat_sink import FlatSourceV1  # noqa: E402

std, out = sys.argv[1], sys.argv[2]
EDGE_S = 60
FS, SEG, LAGS = m["FS"], m["SEG"], m["LAGS"]
os.makedirs(f"{out}/cache", exist_ok=True)
curves = defaultdict(lambda: defaultdict(list))  # (group, part) -> subject -> [(n, curve)]
durations = defaultdict(list)
for r in FlatSourceV1(std, assume_first_attended=True).iter_trials():
    g = f"session{r.session}"
    path = f"{out}/cache/sub-{r.subject}_ses-{r.session}_trial-{r.trial}.npz"
    if not os.path.exists(path):
        try:
            eeg, story = m["prepare"](r)
            scores, starts = m["lag_scores"](m["model"], eeg, story, LAGS, SEG, FS, device=m["device"])
        except Exception as e:  # noqa: BLE001
            print(f"sub {r.subject} ses {r.session} trial {r.trial} FAILED: {e}", flush=True)
            continue
        starts = np.asarray(starts) / FS
        np.savez(path, scores=scores, starts=starts, dur=eeg.shape[1] / FS)
        print(f"sub {r.subject} ses {r.session} trial {r.trial} done", flush=True)
    d = np.load(path)
    s, st, dur = d["scores"], d["starts"], float(d["dur"])
    durations[g].append(dur)
    for part, sel in (("early", st < EDGE_S), ("late", st > dur - EDGE_S - SEG / FS), ("all", st >= 0)):
        if sel.any():
            curves[(g, part)][r.subject].append((int(sel.sum()), s[:, sel].mean(1)))


def offset(c):
    return 1e3 * (LAGS[0] + m["peak_offset"](c)) / FS


res = {}
rng = np.random.default_rng(0)
for (g, part), subs in sorted(curves.items()):
    per = np.array([np.average([c for _, c in v], axis=0, weights=[w for w, _ in v]) for v in subs.values()])
    boot = [offset(per[rng.integers(0, len(per), len(per))].mean(0)) for _ in range(1000)]
    res[f"{g}_{part}"] = dict(n_subjects=len(per), offset_ms=offset(per.mean(0)),
                              ci95_ms=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                              subject_offsets_ms=[offset(c) for c in per])
for g in sorted({k[0] for k in curves}):
    e, l_ = res[f"{g}_early"], res[f"{g}_late"]
    span = float(np.mean(durations[g])) - EDGE_S - SEG / FS
    d = np.array(l_["subject_offsets_ms"]) - np.array(e["subject_offsets_ms"])
    res[f"{g}_late_minus_early"] = dict(ms=l_["offset_ms"] - e["offset_ms"], mean_span_s=span,
                                        residual_ppm=-(l_["offset_ms"] - e["offset_ms"]) / span * 1e3,
                                        per_subject_median_ms=float(np.median(d)))
json.dump(res, open(f"{out}/drift_check.json", "w"), indent=1)
for k, v in res.items():
    print(k, {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "subject_offsets_ms"})
