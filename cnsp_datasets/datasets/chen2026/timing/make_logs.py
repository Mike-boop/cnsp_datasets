"""
Write the two timing logs kept next to the adaptor (step 11, after make_timing_csv.py):
  ../onsets_optionB.csv  one row per listener x chapter: t0 (trigger fit), the option-B latency used by the adaptor
                         by default, the resulting onset, and whether it is the chapter's own estimate or the listener
                         median (with the estimate's SE and the listener spread).
  ../drift.csv           the EEG drift estimates per listener (Theil-Sen over decoder windows, 95% CI; per-listener
                         joint_fit value and SE) and the pooled values. Documented only: drift is NOT applied.
Inputs: ../timing.csv and $CHEN2026_WORK/align/summary/sub-XX.json (analyse_timing.py).
usage: python -I make_logs.py
"""
import glob
import json
import os
import sys

import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from settings import ALIGN, HERE, TIMING_CSV, usage  # noqa: E402

POOLED_PPM = 16.0  # median over listeners +15.8; inverse-variance joint_fit pool +16.5 +- 3.2 (sub-05 left out)


def main() -> None:
    usage(__doc__)
    t = pd.read_csv(TIMING_CSV, dtype={"sub": str})
    per = t["optionB_per_chapter"].astype(bool)
    o = pd.DataFrame({
        "sub": t["sub"], "story": t["story"], "chapter": t["chapter"], "file": t["file"], "t0_s": t["t0_s"],
        "latency_optionB_s": t["latency_optionB_s"], "onset_optionB_s": (t["t0_s"] + t["latency_optionB_s"]).round(4),
        "source": per.map({True: "chapter estimate (deviates > max(40 ms, 3 SE))", False: "listener median"}),
        "chapter_estimate_s": t["latency_s"], "chapter_rule": t["rule"], "chapter_se_ms": t["latency_se_ms"],
        "listener_median_s": t["listener_median_s"], "listener_rsd_ms": t["listener_latency_rsd_ms"]})
    o.to_csv(os.path.join(HERE, os.pardir, "onsets_optionB.csv"), index=False)
    rows = []
    for f in sorted(glob.glob(os.path.join(ALIGN, "summary", "sub-*.json"))):
        d = json.load(open(f))
        lo, hi = d["drift_theilsen_ci95"]
        rows.append(dict(sub=d["sub"], drift_theilsen_ppm=round(d["drift_theilsen_ppm"], 1), ci95_lo=round(lo, 1),
                         ci95_hi=round(hi, 1), joint_fit_ppm=round(d["drift_pooled_ppm"], 1),
                         joint_fit_se=round(d["drift_pooled_se"], 1), n_chapters=d["n_drift_chapters"],
                         note="uninformative (weak tracking)" if d["sub"] == "02" else
                         ("joint_fit stuck at 0 (excluded from the pool)" if d["sub"] == "05" else "")))
    dr = pd.DataFrame(rows)
    dr.loc[len(dr)] = dict(sub="pooled", drift_theilsen_ppm=round(dr.loc[dr["sub"] != "02", "drift_theilsen_ppm"]
                                                                    .median(), 1),
                           joint_fit_ppm=16.5, joint_fit_se=3.2,
                           note=f"dataset value {POOLED_PPM:+.0f} ppm: NOT applied (user, 2026-11-23). Every "
                                "listener's CI includes 0 and sub-05/08 sit near 0, so it is not a reliable "
                                "measurement; any drift is small (<= ~20 ms at the end of the longest chapter)")
    dr["n_chapters"] = dr["n_chapters"].astype("Int64")
    dr.to_csv(os.path.join(HERE, os.pardir, "drift.csv"), index=False)
    print(f"{len(o)} onsets ({int(per.sum())} chapter estimates), {len(dr)} drift rows")


if __name__ == "__main__":
    main()
