"""
Validate a dataset straight from its adaptor or from a standardised (flat) directory.

    python -m cnsp_datasets.validate weissbart2019 --download-dir DIR --picks eeg --reference average \
        --json cnsp_datasets/datasets/weissbart2019/validation.json --fig-dir <tmp>/weissbart2019/validation
"""
import argparse
import json
import os

os.environ.setdefault("MNE_DONTWRITE_HOME", "true")  # threads otherwise race on ~/.mne/mne-python.json

from cnsp_datasets.standardise.flat_sink import FlatSourceV1
from cnsp_datasets.standardise.format_dataset import get_adaptor_class
from cnsp_datasets.validate import group_by_subject, report, validate


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dataset")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--download-dir", help="run the dataset's adaptor on this download")
    src.add_argument("--standardised-dir", help="read a FlatSinkV1 directory")
    p.add_argument("--first-attended", action="store_true", help="standardised dir: first stimulus is attended")
    p.add_argument("--picks", default="eeg", help="channels passed to raw.pick(), e.g. eeg, meg, mag")
    p.add_argument("--reference", default=None, help="'average' or comma-separated channel names")
    p.add_argument("--n-subjects", type=int, default=20, help="pilot size (0: all subjects)")
    p.add_argument("--n-jobs", type=int, default=4)
    p.add_argument("--tiers", default="low,mlr,brainstem", help="comma-separated tiers to run")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--json", required=True)
    p.add_argument("--fig-dir")
    args = p.parse_args(argv)

    if args.download_dir:
        records = get_adaptor_class(args.dataset)(download_dir=args.download_dir).parse()
    else:
        records = FlatSourceV1(args.standardised_dir, assume_first_attended=args.first_attended).iter_trials()
    reference = args.reference.split(",") if args.reference and args.reference != "average" else args.reference

    subjects = group_by_subject(records, args.n_subjects or None, args.seed)
    result = validate(subjects, args.picks, reference, args.n_jobs, args.seed, args.tiers.split(","))
    result["config"]["dataset"] = args.dataset
    report.save(result, args.json, args.fig_dir)
    print(json.dumps(result["summary"], indent=1))


if __name__ == "__main__":
    main()
