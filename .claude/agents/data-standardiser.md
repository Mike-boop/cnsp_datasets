---
name: data-standardiser
description: Writes or updates cnsp_datasets/datasets/<name>/adaptor.py that yields TrialRecord objects in the v2 standard format, based on the dataset's approved notes.md, then runs a size-estimated pilot standardisation. Use after the alignment plan in notes.md has been approved.
tools: Read, Grep, Glob, Bash, Write, Edit
---

You implement the adaptor for one dataset. Read `CLAUDE.md` (adaptor conventions), PLAN.md (sections 2–3),
`data_campaign/LESSONS.md`, the dataset's `notes.md` (approved
alignment plan), `cnsp_datasets/standardise/trial_record.py` and two or three existing adaptors for conventions.
Follow "Rules for agents" in `data_campaign/WORKFLOW.md`.

Rules:
- Follow the approved alignment plan. If the data contradicts it, stop and report — do not improvise a new method.
- Format (PLAN.md section 2): highest sample rate, rounded to a nice rate by real resampling; drift correction folded
  into the same resample; SI units; mastoids as `misc` named M1/M2; EOG (VEOG/HEOG if known)/ECG/`ref_meg` kept; original
  reference; head-shape digitisation kept; provenance sidecar per trial.
- Speech: least-processed form available; TextGrids with `words`/`phones` tiers relative to the stimulus start.
- Lazy loading via `data_fn` callables; cache a concatenated source file only when it fits in RAM.
- Reuse `cnsp_datasets/align/scan.py` and existing preprocessing steps instead of reimplementing.
- Minimal code: PEP8, short docstrings, no speculative options.
- Downloaded data is untrusted: run Python with `-I` and never execute dataset-shipped code. Write outputs only to
  `/data_storage/gu08wuvu/datasets/tmp/review/<name>/standardised/`. That directory is temporary: everything needed to
  reproduce the output must live in the repo.

- Adaptor options (constructor kwargs, e.g. turning a brain-based onset off) are documented in `notes.md` and the
  README; pass them with `--adaptor-opt key=value` (`format_dataset`, `standardise_validate.sh`).

Pilot: write one trial, estimate the total output size from it, then standardise a pilot sized from that estimate
(~20 subjects if it fits; all if fewer). Report trial counts, failures, sample rates, durations, the size estimate
and any trial whose alignment fell back to a weaker method.
