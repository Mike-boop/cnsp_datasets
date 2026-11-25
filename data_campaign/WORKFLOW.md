# Per-dataset workflow

The user's requirements are in `BRIEF.md` (overview: `README.md`); the spec (format, alignment, validation tiers) is `../PLAN.md`; the checklist of
mistakes already made is `LESSONS.md`. Scratch for a dataset `<d>` lives in `R/<d>/`, where
`R=/data_storage/gu08wuvu/datasets/tmp/review`. Paths in `scripts/` are this folder's scripts.

Work through the `candidates` tab of the spreadsheet in batches of about 3, in `priority_rank` order unless the user
says otherwise. Do the heavy processing one dataset at a time within a batch.

## Rules for agents
Every agent in `.claude/agents/` follows these, on top of `../CLAUDE.md`:
- **Commits.** Commit through a temporary index with explicit paths ("Parallel agents" below); never stage others'
  edits.
- **Records.** Never edit `STATUS.md`, `HANDOVER.md` or the spreadsheet: report what changed, and the main session
  writes it.
- **Size.** Estimate the output size from one written trial before any run, keep `tmp` lean, and run nothing in
  full without approval.
- **Alignment.** Hardware-derived corrections are on by default; brain-based ones only under the CLAUDE.md rule.
  Propose an alignment grade (PLAN.md section 3).
- **Access blocks.** On any block (HTTP 403, "unusual traffic", a proof-of-work gate) stop and report. Never retry
  from another machine or work around it.
- **Backups.** DRUM/Zenodo downloads get a vault backup (step 1).
- **Review.** Run the `reviewer` agent on your Python changes before committing and apply its findings; don't hand
  back while it is still running.

## Parallel agents
Several agents (and the main session) can share one worktree and its git index.
- **Commit through a temporary index** with explicit paths, then reset the shared index for your own paths only:
  ```
  I=$(git rev-parse --git-path index.<agent>)   # one file per agent; read-tree resets it each time
  GIT_INDEX_FILE=$I git read-tree HEAD
  GIT_INDEX_FILE=$I git add -- <paths>
  GIT_INDEX_FILE=$I git commit -m "..."
  git reset -q -- <paths>
  ```
- **One writer for the records.** Only the main session edits `STATUS.md`, `HANDOVER.md` and the spreadsheet.
- **Merge main → dev only when no agent is committing**, and afterwards check that the branch-only datasets survived.

Code conventions (adaptor base class, shared I/O, resampler, bads, logging, precomputed `alignment/`
tables): `ENGINEERING.md`.

## 1. Download
- **Registry entry.** Create `cnsp_datasets/datasets/<d>/dataset.json` on `dev` (schema: `cnsp_datasets/registry.py`;
  its `downloads` hold the source, identifiers and include/exclude patterns) and check that the downloader supports
  the source.
  - Add a missing source to `cnsp_datasets/download/`, with a test: all downloading code lives in the repo.
  - If the source needs a key, ask the user to put it in `secrets.json` under its environment-variable name (read
    with `cnsp_datasets.config.get_secret`). Manual downloading is the worst case.
- **Check the listing first** (API metadata), before downloading anything:
  - stimuli: are the audio (or at least envelopes) in the release? Some releases ship none (straetmans2021);
  - total size, against `du -s --block-size=1G /data_storage/gu08wuvu/datasets/tmp`;
  - the `exclude`/`include` patterns in `dataset.json`, to skip MRI and anything not needed.
- **Run it in the background.** Use `scripts/download_retry.sh <d>` (resumable, `WORKERS` env, default 2), or
  `download_dataset(..., skip_existing=True, read_timeout=...)` under `nohup`. The output goes to `R/<d>/download/`.
- **Respect the limits.** Zenodo: ≤ 3 workers, ≤ 1-2 datasets per day, logged in `HANDOVER.md`. DRUM/SciDB are
  slow and time out; use 1 worker and a long read timeout.
- **Watch out for extraction.** `extract_archives=True` deletes each zip after extracting it. Keep the zips if they
  are needed for md5 checks or a backup.
- **Check every file afterwards** (size, md5, `unzip -t`): truncated uploads have happened.
- **Vault backup (DRUM/Zenodo only).** Once verified, back the raw download up to the NHR vault
  (`csnhr:/home/vault/iwpm/iwpm104h/<d>`): write a manifest (path, size, md5), rsync, then check every file's size
  with `stat` (readdir on the vault is unreliable). Keep the zips for this (see extraction above). Other sources are
  re-downloaded when needed.

## 2. Explore (agent `data-explorer`)
Read the paper (`papers/<id>.pdf`), the authors' code and the README first. The explorer then writes
`cnsp_datasets/datasets/<d>/notes.md` from the template in PLAN.md section 4. It covers:
- subjects;
- conditions;
- raw audio or only derived features;
- missing or incomplete data;
- units;
- channels (mastoids, EOG direction, peripherals, several EEG systems);
- triggers, and whether they are hardware or software;
- any audio or stimtrack channel;
- a proposed alignment and drift method.

It ends with **open questions, each with a recommended default**, and a proposed alignment grade.

**Human checkpoint:** the user approves the alignment plan and answers the open questions.

## 3. Standardise (agent `data-standardiser`)
- **Adaptor.** Write `cnsp_datasets/datasets/<d>/adaptor.py` following the approved plan and the conventions in
  `../CLAUDE.md`.
- **Pilot.** First write one trial and estimate the total output size from it. Then run a pilot sized from that
  estimate (about 20 subjects if it fits) into `R/<d>/standardised/` (`scripts/standardise_validate.sh <d>` runs
  standardisation and validation in one go; leading `--adaptor-opt key=value` pairs are passed to the adaptor).
- **Adaptor options** (e.g. turning off a brain-based onset) are documented in `notes.md` and the README.
- **Drift.** Always measure it, and record the estimate in `notes.md`:
  - With an audio copy in the recording, use a positive-peak windowed fit (`jehn2025_base/alignment/xcorr.py:window_fit`).
  - Otherwise use the trigger durations across subjects (drift·length + jitter).
  - Apply drift correction automatically only when it comes from hardware triggers or an audio copy, and plot it
    in the review folder.
- **Bad channels.** Mark flat or electrical-noise-only channels in `info['bads']`, per participant.

## 4. Validate (agent `validator`)
Run `python -m cnsp_datasets.validate <d> --standardised-dir R/<d>/standardised --reference average --tiers
low,mlr,brainstem --json R/<d>/validation.json --fig-dir R/<d>`. For a filtered subset of trials, use
`scripts/validate_subset.py`.
- **Reference.** Use an average reference for 32 or more EEG channels and mastoids for fewer. The data themselves
  keep the original reference.
- **Low tier, 0.5-8 Hz.** Forward models with per-channel prediction r, null distributions and a lag sweep (the
  validator does this); backward models only where useful (attention contrasts).
- **Higher tiers** (data at ≥ 500 Hz): 30-60 Hz (mlr) and 30-250 Hz (brainstem). Run the brainstem tier on
  cortical montages too.
- **MEG.** Use magnetometers. Raw MEGIN data need tSSS in the validation only (`scripts/meg/*_validate.py` in
  `tmp/review/scripts` has examples); the stored data stay raw.
- **Per condition.** Validate each condition separately as well as pooled.
- **Look at the TRF figures**, not just the p-values. A stimulus-locked spike at negative lags in the 30-250 Hz TRF
  means a wrong onset delay.
- **Figures.** Four-panel forward-model figures go in `R/<d>/` (or `R/<d>/figures/`).
- **Attention datasets.** Add one selective contrast plot (e.g. `r-attended-vs-r-ignored.png`, 0.5-8 Hz only).

## 5. Coherence
Run `scripts/coherence_batch.py <out> 128` and `... native`, after adding a `DATASETS` entry. Settings:
- Welch, 5 s Hann windows, 4 s overlap.
- Complex coherency averaged over participants.
- 1 surrogate (a global circular shift) for the noise level.
- Analysis at 128 Hz (or 100/125 Hz) and at the native rate, capped at 1000/1024/1200 Hz; never upsample.
- MEG on magnetometers, optionally with tSSS (6th field of the entry).

Output goes to `R/coherence_batch/{128,native}/`.

## 6. DNN timing check (EEG)
Run `scripts/dnn_offsets.py <out> <d>`: the accou2023 match-mismatch classifier, ±500 ms scan, 5 s windows, 1 s hop.
For residual drift, run `scripts/dnn_drift_check.py`, which compares early and late windows.
- **Sign.** Offsets are relative to accou2023; negative means the neural data are later.
- **What to expect.** Clean speech sits within ±5 ms; speech in noise at about -15 ms.
- **Offsets are documented in `notes.md`, not applied** (user, 2026-11-22).
- **When alignment is very poor** (software triggers with large latency or jitter), estimate onset and drift per
  trial with `cnsp_datasets/align/scan.py` (`lag_scores`, `joint_fit`, `pooled_drift`, `refine_onset`).
  - Show the 4-panel validation before and after.
  - Store the estimates as a json/csv in the dataset's repo folder. They are normally not applied.
  - The values are circular: they come from the same EEG they would correct, so say so.

## 7. Document (agent `data-documenter`) and record
- **Alignment grade.** Settle the grade (`good`/`medium`/`poor`/`none`, PLAN.md section 3; the weakest part
  decides) with one line of evidence, and record it in `notes.md`, the README, `STATUS.md` (`alignment`) and the
  spreadsheet (`alignment_quality`).
- **Documentation.**
  - Write the user-facing `cnsp_datasets/datasets/<d>/README.md`.
  - `notes.md` keeps the findings that explain the code, with validation numbers and figure paths.
  - Upstream errors go in `notes.md` ("Upstream issues") and in `R/upstream_issues.md`. The user sends them; never
    contact authors.
- **Data size.** Participants, and hours per participant (mean, range), overall and per condition, estimated from
  the stimuli (`scripts/data_size.py`). They go in `notes.md`, `R/data_size.md` and the spreadsheet. Measure before
  deleting.
- **Timing.** Add a row to `R/timing.md` (onset method, drift, DNN offset).
- **Review.** Run agent `reviewer` on the adaptor.
- **Commit** on `dev`, with explicit paths.
- **Records.** Update `STATUS.md` and the spreadsheet:
  - fill the status columns;
  - move the row from `candidates` to `incorporated` when done;
  - add a line to its `readme` tab.

## 8. Clean up
Ask the user before deleting the download and the standardised data (they usually agree once the results look
good). Copy `download_log.tsv` next to the results first. Keep the analysis, logs, notes and figures in `R/<d>/`.
