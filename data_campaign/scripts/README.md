# Campaign scripts

Reusable analysis scripts for the per-dataset workflow (`../WORKFLOW.md`), copied from `tmp/review/scripts/` on
2026-11-22. They are working tools for this server, not library code: paths are hard-coded
(`/data_storage/gu08wuvu/datasets/tmp/review`, the dev worktree on `sys.path`) and per-dataset settings live in the
`DATASETS` dicts at the top of `coherence_batch.py` and `dnn_offsets.py`; add an entry per dataset.

| script | step |
|---|---|
| `download_retry.sh <d>` | resumable download with retries (`WORKERS` env) |
| `standardise_validate.sh <d> [validate args]` | standardise `R/<d>/download` + validate (average reference); `CNSP_REPO` picks the checkout (default dev) |
| `validate_subset.py` | validate a filtered subset of an adaptor's trials |
| `coherence_batch.py <out> <128\|native> [names]` | envelope coherence, 5 s Hann / 4 s overlap, 1 surrogate |
| `dnn_offsets.py <out> [names]` | constant offset vs accou2023 (match-mismatch classifier) |
| `dnn_drift_check.py <standardised> <out> <groupby>` | early vs late windows: residual drift |
| `annot_trf.py` | TRF from annotation onsets to the audio envelope per 2-min window (checks rebuilt/retimed stimuli) |
| `data_size.py [folders]` | participants and hours per participant, from the stimuli |

One-off, per-dataset scripts stay in `tmp/review/scripts/`.
