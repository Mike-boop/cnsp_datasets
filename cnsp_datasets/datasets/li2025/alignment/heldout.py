"""
li2025: held-out test of per-subject vs per-group onset delays with the validator's low tier (analysis only).

usage: python -m cnsp_datasets.datasets.li2025.alignment.heldout <download dir> <heldout_delays.json> <out dir>
       [n_jobs] [subjects, e.g. 43,48]
heldout_delays.json comes from subject_delays.py. Each shipped recording (onset="none") is preprocessed once (HFC
order 1 without MEG062, 0.1 Hz high-pass of the whole recording, 50/125 Hz harmonic notches; as the dataset
validation) and cut into the N_PARTS parts of common.match_trfs. Delays estimated on parts 1,3,5 are scored on parts
2,4 and vice versa; each scored part is cut in halves so the low tier can cross-validate. Runs per direction: shipped
(0), group (adaptor ONSET_DELAY_S), subject and subject_loso (group A matched to its leave-one-out template). The
audio heard at shipped time t is audio time t - delay. sub-54 is left out (two halves only; not in
heldout_delays.json). Per-subject results are cached in <out>/cache; each run is saved as
<out>/est<parts>_<run>/validation.json (+ plots), the r per run in <out>/heldout_summary.json.
"""
import json
import os
import pickle
import sys
from concurrent.futures import ThreadPoolExecutor

import mne
import numpy as np

from cnsp_datasets.datasets.li2025.adaptor import ONSET_DELAY_S, Li2025Adaptor, group
from cnsp_datasets.datasets.li2025.alignment.common import FS, N, N_PARTS
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord
from cnsp_datasets.validate import report
from cnsp_datasets.validate.checks import HF, LOW, TIERS, UNIT_RANGES, group_summary, validate_subject

NOTCH = sorted(set(np.arange(50, 500, 50)) | set(np.arange(125, 500, 125)))
PARTS = [(i[0] / FS, (i[-1] + 1) / FS) for i in np.array_split(np.arange(N), N_PARTS)]  # s, as common.match_trfs
SCORE_ON = {"135": [1, 3], "24": [0, 2, 4]}  # delays estimated on parts 1,3,5 -> scored on 2,4 (0-based) and back
RUNS = ("shipped", "group", "subject", "subject_loso")


def preprocess(raw):
    """HFC (order 1, MEG062 left out), 0.1 Hz high-pass and notches of the whole recording."""
    raw.load_data(verbose="ERROR")
    raw.info["bads"] = sorted(set(raw.info["bads"]) | {"MEG062"})
    raw.add_proj(mne.preprocessing.compute_proj_hfc(raw.info, order=1, verbose="ERROR")).apply_proj(verbose="ERROR")
    raw.filter(0.1, None, picks="mag", verbose="ERROR")
    raw.notch_filter(NOTCH, picks="mag", verbose="ERROR")
    return raw


def records(subject, raw, audio, est, delay):
    """Halves of the parts scored for direction est, with the audio delayed by delay (s)."""
    bounds = [(t0 + h * (t1 - t0) / 2, t0 + (h + 1) * (t1 - t0) / 2)
              for t0, t1 in (PARTS[k] for k in SCORE_ON[est]) for h in (0, 1)]
    recs = []
    for k, (t0, t1) in enumerate(bounds, 1):
        def neural(t0=t0, t1=t1):
            return raw.copy().crop(t0, t1 - 1 / raw.info["sfreq"])

        def stim(t0=t0, t1=t1):
            i0, i1 = round((t0 - delay) * audio["fs"]), round((t1 - delay) * audio["fs"])
            seg = np.zeros((audio["data"].shape[0], i1 - i0), dtype=audio["data"].dtype)
            lo, hi = max(i0, 0), min(i1, audio["data"].shape[1])
            seg[:, lo - i0:hi - i0] = audio["data"][:, lo:hi]
            return {"fs": audio["fs"], "data": seg}

        name = f"baba_d{round(delay * 1000)}_est{est}_seg{k}"  # the validator caches stimuli by name across subjects
        recs.append(TrialRecord(subject, 1, k, "audiovisual", "meg", [StimulusRecord("audio", name, stim, True,
                                                                                     "audio")], neural))
    return recs


def main(argv):
    src, delays_json, out = argv[:3]
    n_jobs = int(argv[3]) if len(argv) > 3 else 2
    only = {int(s) for s in argv[4].split(",")} if len(argv) > 4 else None
    with open(delays_json) as f:
        held = json.load(f)
    os.makedirs(os.path.join(out, "cache"), exist_ok=True)

    def delay(est, run, subject):
        if run == "shipped":
            return 0.0
        if run == "group":
            return ONSET_DELAY_S[group(subject)]
        return held[f"{est}_{'loso' if run == 'subject_loso' else 'full'}"][str(subject)]["delay"]

    runs = [(e, r) for e in SCORE_ON for r in RUNS]
    results = {r: [] for r in runs}
    cache, audio = {}, None
    for rec in Li2025Adaptor(src, onset="none").parse():
        if rec.subject == 54 or (only and rec.subject not in only):
            continue
        f = os.path.join(out, "cache", f"sub-{rec.subject}.pkl")
        if os.path.exists(f):
            with open(f, "rb") as fh:
                res = pickle.load(fh)
        else:
            if audio is None:
                audio = next(s for s in rec.stimulus if s.feature_name == "audio").data_fn()
            raw = preprocess(rec.neural_data_fn())
            with ThreadPoolExecutor(n_jobs) as pool:
                res = list(pool.map(lambda er: validate_subject(
                    records(rec.subject, raw, audio, er[0], delay(*er, rec.subject)), "mag", None, cache,
                    rec.subject, ["low"]), runs))
            with open(f, "wb") as fh:
                pickle.dump(res, fh)
        for r, x in zip(runs, res):
            results[r].append(x)

    summary = {}
    for (e, r), subs in results.items():
        d = os.path.join(out, f"est{e}_{r}")
        os.makedirs(d, exist_ok=True)
        cfg = dict(LOW=LOW, HF=HF, TIERS=TIERS, UNIT_RANGES=UNIT_RANGES, picks="mag", reference=None, seed=0,
                   tiers=["low"], dataset="li2025", preprocessing="hfc, high-pass 0.1 Hz, notch (validation only)",
                   heldout=f"delays estimated on parts {e}, scored on parts {[k + 1 for k in SCORE_ON[e]]}, run {r}")
        res = dict(config=cfg, summary=group_summary(subs, ["low"]), subjects=subs)
        report.save(res, os.path.join(d, "validation.json"), d)
        summary[f"est{e}_{r}"] = dict(mean_r=res["summary"]["low"]["mean_r"],
                                      r={s["subject"]: s["low"]["r"] for s in subs})
        print(f"est{e}_{r}: mean r {summary[f'est{e}_{r}']['mean_r']:.4f}", flush=True)
    with open(os.path.join(out, "heldout_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
