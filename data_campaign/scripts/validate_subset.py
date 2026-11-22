"""Validate a subset of an adaptor's trials (the CLI validates all trials of the chosen subjects).

usage: validate_subset.py <dataset> <download dir> <out dir> <picks> <tiers> <python filter on record r> [n_jobs]
e.g.   validate_subset.py libribrain100 DIR OUT meg low,mlr "r.subject <= 12" 2
"""
import json, os, sys
sys.path.insert(0, "/home/gu08wuvu/cnsp_datasets_dev")
os.environ.setdefault("MNE_DONTWRITE_HOME", "true")
from cnsp_datasets.standardise.format_dataset import get_adaptor_class
from cnsp_datasets.validate import group_by_subject, report, validate

name, ddir, out, picks, tiers, flt = sys.argv[1:7]
n_jobs = int(sys.argv[7]) if len(sys.argv) > 7 else 2
records = [r for r in get_adaptor_class(name)(download_dir=ddir).parse()
           if eval(flt, {}, {"r": r}) and any(s.feature_name == "audio" for s in r.stimulus)]
print(len(records), "trials", flush=True)
os.makedirs(out, exist_ok=True)
res = validate(group_by_subject(records, None, 0), picks, None, n_jobs, 0, tiers.split(","))
res["config"].update(dataset=name, filter=flt)
report.save(res, f"{out}/validation.json", out)
print(json.dumps(res["summary"], indent=1))
