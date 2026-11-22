# cnsp_datasets: instructions for Claude

The repository downloads public continuous-speech M/EEG datasets, aligns the neural data with the stimuli
(onsets, clock drift), stores both in one standard format and validates the result by modelling. The repository is
the product: every standardisation must be reproducible from code alone. Data is never kept here long term.

## Start of a session
1. This file.
2. `data_campaign/HANDOVER.md`: running jobs, the current task, next steps (overwritten each session).
3. `data_campaign/STATUS.md`: one row per dataset, open decisions.

As needed:
- `data_campaign/README.md`: the user's brief for the campaign.
- `data_campaign/WORKFLOW.md`: the per-dataset steps, from download to deletion.
- `data_campaign/LESSONS.md`: the checklist of mistakes already made once.
- `PLAN.md`: the standard format, the alignment rules and the validation tiers (the spec).
- `cnsp_datasets/datasets/<name>/notes.md`: per-dataset findings; read it before touching an adaptor.

## Where things are
- **Checkouts.** `/home/gu08wuvu/cnsp_datasets` is on `main`. `/home/gu08wuvu/cnsp_datasets_dev` is a worktree on
  `dev`; new datasets are built there.
- **Branches.**
  - `main`: public, reviewed datasets plus all infrastructure (docs, `.claude/`, `data_campaign/`).
  - `dev`: main + new and experimental datasets.
  - `internal`: main + non-public datasets.
  - Infrastructure changes go on `main` first and are then merged into `dev`/`internal`.
  - After a merge, check that the branch-only datasets survived: git rename detection once silently deleted
    `jehn2024`.
- **Scratch.** `/data_storage/gu08wuvu/datasets/tmp/review/<dataset>/` (`download/`, `standardised/`, `validation/`,
  figures, logs). Everything in `tmp` gets deleted.
  - The rest of `/data_storage/gu08wuvu/datasets/` is the user's and read-only; `.claude/hooks/storage_guard.py`
    enforces this.
- **Papers and spreadsheet.** `data_campaign/papers/<id>.pdf` and `data_campaign/cnsp-datasets-revised.xlsx`. Both
  are git-ignored.
- **Scripts.** Reusable ones are in `data_campaign/scripts/`. One-off, per-dataset ones go in
  `tmp/review/scripts/`, never in the session scratchpad.
- **Credentials.** `secrets.json` (git-ignored; older keys are in `tmp/api_keys.json`). Never print them.

## Running code
- **Python.** Use `/home/gu08wuvu/cnsp_datasets/.venv/bin/python -I`, and in scripts
  `sys.path.insert(0, "/home/gu08wuvu/cnsp_datasets_dev")` (or the checkout you mean).
  - `-I` matters because a data or script folder can shadow the stdlib (a stray `inspect.py` broke `import mne`).
  - `python -c` puts the cwd first on `sys.path`.
  - Run from the worktree, never from inside a data folder.
- **Untrusted downloads.** Give each download its own empty directory, and never run code shipped with a dataset:
  read it, port the logic.
- **Long jobs.**
  - Launch with `setsid nohup ... & disown`, make them resumable (cache per trial or run) and keep the log next to
    the results.
  - Up to ~3 heavy jobs in parallel, ≤ 4 threads each, ~20 GB RAM in total. Check `uptime` / `free -g` first.
- **Killing jobs.** Never `pkill -f` / `pgrep -f` with a pattern that is in your own command line: it kills the
  tool's shell. Use `ps -eo pid,args | awk '/[p]attern/'`.

## Ground rules (from the user)
- **Ask before anything data-altering**, and back it with per-subject plots. This covers:
  - onset or drift corrections;
  - resampling choices;
  - deleting downloads or standardised data;
  - pushing.

  Constant DNN offsets are documented in the notes, not applied.
- **Git.**
  - Pushes need explicit approval.
  - Commit with explicit paths (`git add -- <paths>`), never `git add -A` (`.venv` is an untracked symlink in the
    worktree).
- **Storage.** `tmp` stays under 1 TB. Up to 2 TB only for data already scheduled for deletion, and only with the
  user's sign-off.
- **Zenodo** (promised to its moderators):
  - at most 3 concurrent downloads and 1-2 datasets per day;
  - log each one with its date in `data_campaign/HANDOVER.md`;
  - check access with one request first, and never work around a block.
- **Downloads.** Manual downloading is the worst case. If a source needs a key, ask the user to put it in
  `secrets.json`.
- **Notes as you go.** Anything that explains a choice in the adaptor goes into the dataset's `notes.md` as soon as
  it is established, because `tmp` is deleted. User-facing documentation goes in `README.md` next to it.
- **Report with figures.** Give the path of every figure, under `tmp/review/<dataset>/`.
- **Keep the records current.** When a dataset's state changes, update `data_campaign/STATUS.md` and the
  spreadsheet:
  - `incorporated` and `candidates` tabs, columns `repo_name` … `status_updated`;
  - move a row from `candidates` to `incorporated` when the dataset is done;
  - edit it with openpyxl.

  At the end of a session, or when asked, rewrite `data_campaign/HANDOVER.md`.

## Conventions for adaptors (details in PLAN.md and WORKFLOW.md)
- **Neural data.**
  - SI units.
  - Original reference.
  - Original subject names.
  - Mastoids named M1/M2.
  - EOG as VEOG/HEOG when the direction is known, otherwise EOG.
  - Peripherals kept; unused ports dropped.
  - Each EEG system in its own file.
- **Bad channels.** Keep them in the data and list them in `info['bads']`. Analysis code must exclude them itself:
  `raw.pick("eeg")` keeps bads.
- **Rates.** Output at 1000 or 1024 Hz (whichever resamples with fewer artefacts). Keep native rates ≤ 1024 Hz;
  never upsample.
- **Stimuli.**
  - Continuous stimuli only (music counts; clicks don't). No visual stimuli for now.
  - Don't cut stimuli to the neural data: the longer signal is cut at the point of use.
  - Model-derived regressors are off by default.
- **Drift.** Hardware-derived drift correction is on by default, folded into the single resample.
