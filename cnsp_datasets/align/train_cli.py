"""
Train one classifier variant (sample rate x montage x band) on a flat-standardised dataset and save its weights
with its ClassifierSpec (see specs.py).

    python -m cnsp_datasets.align.train_cli --fs 1024 --montage 1020-26 --band broadband \
        --data-dir /data_nfs/gu08wuvu/datasets/accou2023/standardised-flat --n-subjects 30 --out-dir classifiers

Writes <out-dir>/<spec name>.pt, e.g. classifiers/fs1024_1020-26_broadband.pt.
"""
import argparse
import datetime
import json
import sys

from cnsp_datasets.align.dataset import load_sessions
from cnsp_datasets.align.specs import BANDS, MONTAGES, REFERENCES, STIMULI, ClassifierSpec, save_classifier
from cnsp_datasets.align.train import train_classifier
from cnsp_datasets.standardise.flat_sink import FlatSourceV1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fs", type=int, default=1024)
    parser.add_argument("--montage", choices=list(MONTAGES), default="1020-26")
    parser.add_argument("--band", choices=BANDS, default="broadband")
    parser.add_argument("--n-layers", type=int, default=None, help="default: 3 for hf, fitted to fs for broadband")
    parser.add_argument("--reference", choices=REFERENCES, default="average")
    parser.add_argument("--stimulus", choices=STIMULI, default="envelope")
    parser.add_argument("--hp-cutoff", type=float, default=None, help="hf band high-pass (default min(fs/4, 80) Hz)")
    parser.add_argument("--exclude-subjects", type=int, nargs="*", default=[],
                        help="leave out these subjects before taking the first N (e.g. those without mastoid channels)")
    parser.add_argument("--data-dir", default="/data_nfs/gu08wuvu/datasets/accou2023/standardised-flat")
    parser.add_argument("--dataset-name", default="accou2023")
    parser.add_argument("--condition", default="natural", help="only trials with this condition ('' for all)")
    parser.add_argument("--n-subjects", type=int, default=30, help="the first N subjects")
    parser.add_argument("--mastoids", nargs=2, default=["A1", "A2"],
                        help="mastoid channels for linked-mastoid references ('none' for the recording reference)")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-dir", default="classifiers")
    args = parser.parse_args(argv)

    spec = ClassifierSpec(fs=args.fs, montage=args.montage, band=args.band, n_layers=args.n_layers,
                          reference=args.reference, stimulus=args.stimulus, hp_cutoff=args.hp_cutoff)
    print(f"{spec.name}: {json.dumps(spec.to_dict(), default=str)}", flush=True)

    records = [r for r in FlatSourceV1(args.data_dir).iter_trials()
               if not args.condition or r.condition == args.condition]
    subjects = sorted({r.subject for r in records} - set(args.exclude_subjects))[:args.n_subjects]
    records = sorted([r for r in records if r.subject in subjects], key=lambda r: (r.subject, r.trial))
    print(f"{len(records)} trials from {len(subjects)} subjects: {subjects}", flush=True)

    mastoids = tuple(None if m.lower() == "none" else m for m in args.mastoids)
    sessions = load_sessions(records, on_error="skip", **spec.session_kwargs(mastoids=mastoids))
    if not sessions:
        sys.exit("No sessions loaded")

    result = train_classifier(
        sessions, montage=None, fs=spec.fs, segment_length=spec.segment_length,
        mismatch_offset=spec.mismatch_offset, model_kwargs={"n_layers": spec.n_layers, **spec.extra_model_kwargs},
        batch_size=args.batch_size, epochs=args.epochs, lr=args.lr, seed=args.seed,
    )
    path = save_classifier(
        f"{args.out_dir}/{spec.name}.pt", result["model"], spec,
        dataset=args.dataset_name, data_dir=args.data_dir, condition=args.condition, subjects=subjects,
        n_sessions=len(sessions), mastoids=mastoids, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
        seed=args.seed, best_val_acc=result["best_val_acc"], test_acc=result["test_acc"], history=result["history"],
        trained_at=datetime.datetime.now().isoformat(timespec="seconds"),
    )
    print(f"saved {path}", flush=True)


if __name__ == "__main__":
    main()
