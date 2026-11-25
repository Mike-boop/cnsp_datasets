# Engineering notes: conventions and deferred work

Structure decided with the user on 2026-11-25 (first-pass learnings). Conventions here are binding for new and
revised adaptors; the "Deferred" list is work agreed but not yet done.

## Conventions
- **Dataset metadata.** Every dataset folder has `dataset.json` (`cnsp_datasets/registry.py`: schema, loader).
  Its `downloads` replace the old `download/dataset_registry.json`; extra downloads of one dataset are extra keys
  (`<name>_audio`, ...). Folders with only shared code (`simon_base`, `maddox_base`, `jehn2025_base`) have none.
- **Non-public datasets** live in the private repository `cnsp_datasets_fau` (same folder layout), found through
  `CNSP_DATASET_PACKAGES=cnsp_datasets_fau.datasets`. No `internal` branch.
- **Secrets and local paths.** `cnsp_datasets.config.get_secret(NAME)` / `get_path(NAME)`: environment variable
  first, then `secrets.json` / `paths.json` (`$CNSP_SECRETS` / `$CNSP_PATHS`, `~/.config/cnsp_datasets/`, repo
  root). Key names are the environment-variable names (HF_TOKEN, DRYAD_CLIENT_ID, RADBOUD_USERNAME, ...). Corpora
  that cannot be downloaded (IFADV, CGN) are paths: `CNSP_IFADV_DIR`, `CNSP_CGN_DIR`. Never secrets on the command
  line.
- **Adaptors** subclass `standardise.adaptor.BaseAdaptor`; options are validated with `choice`/`require` (no
  `assert`); variants are subclasses, not `functools.partial`. Globs are sorted.
- **Shared I/O** in `standardise/iohelpers.py`: `read_wav`/`audio_loader` (float32, any PCM width; `channel=`,
  `collapse_identical=`), `array_loader`, `status_edges`, `mark_bads`, `bads_for`, `flat_channels`,
  `rename_channels`, `textgrid`.
- **Resampling** only through `standardise/clock.py` (`crop_on_audio_clock`, `resample_on_audio_clock`,
  `to_audio_clock`): quintic spline after an anti-alias FIR; a recording that ends before its trial is logged.
- **Bad channels** stay in the data and are listed in `info["bads"]`: never `pick(..., exclude="bads")` or
  `pick_types` without `exclude=[]` in an adaptor.
  Bads a release already marks are kept: a dataset's own list is merged with them (`iohelpers.mark_bads`), never
  replaces them (user, 2026-11-25, for simon_base.crop_meg and in general).
- **Logging.** Library code logs through `logging.getLogger(__name__)`; `format_dataset` writes
  `<out>/standardise.log` (failed trials with tracebacks, truncated trials) and raises at the end if any trial
  failed. Adaptors never change MNE's log level; users set `MNE_LOGGING_LEVEL`.
- **Precomputed alignment.** Onsets, drifts and other alignment tables that need heavy or brain-based
  computation (DNN, TRF scans; anything needing torch) are precomputed and shipped in `<dataset>/alignment/`
  together with the scripts that make them (`python -m cnsp_datasets.datasets.<name>.alignment.<script>`). The
  adaptor only reads the tables; users can re-run or improve the scripts.
- **MNE is pinned** (pyproject.toml): li2025 and libribrain100 use `raw._raw_extras`; `tests/test_mne_private_api.py`
  must pass before the pin is raised.

## Deferred (agreed, not done)
- Standardised formats: FlatSinkV2 (short file names, `trials.tsv` / `stimuli.tsv` manifests with roles,
  original subject labels and content hashes; collisions of stimulus names become errors) and a BIDS sink (EEG as
  BrainVision via mne-bids, `run-` = trial, `acq-` = montage, stimuli in `/stimuli` referenced from events.tsv).
- Option names across adaptors (`drift_correction`, `onset`, `sfreq`, `subjects`): harmonise during the second
  pass, dataset by dataset, together with each README.
- Validation files: a schema for `validation.json` (user-facing format not decided yet).
- DNN alignment code (`cnsp_datasets/align/`, torch): integrate properly in a later round; until then adaptors
  read precomputed tables only (zhang2023, bentum2023, kern2022, li2022, hassan2026, ...).
- Heavy loading: `lru_cache` on instance methods (das2019, fuglsang2018, libribrain100) and `lru_cache(maxsize=1)`
  readers that assume parse order; find a better way to share heavy loading/preprocessing between trials.
- maddox_base `load_trial` drops channel info (all channels typed "eeg", no montage); revisit with the family.
- Remaining duplicated loaders (CND `.mat` readers, Broderick trio) beyond what the restructure migrated.
- A shared "basename -> path index that raises on duplicates" helper (das2019 and fuglsang2018 have the same code).
- Second pass: overlapping word timings (upstream; Broderick trio, nguyen2025, guilleminot2021, ...) are clipped
  with a warning in standardise.log (iohelpers.textgrid default, user 2026-11-25); look at those warnings.
- Second pass (user, 2026-11-25):
  - Montage files: jehn2024/jehn2025 (and any other dataset) ship `info_*.fif` only for channel names and
    positions. Store these in a lighter, readable format instead (e.g. BrainVision `.bvef`, or a small tsv/json
    of names + coordinates), read into an `mne` montage by the adaptor.
  - fuglsang2018: the `expinfos/*.mat` tables were pre-extracted (with `get_expinfos.m`) because scipy could not
    read the shipped FieldTrip/MATLAB files when the adaptor was written. Read them from the original release
    instead (pymatreader / h5py / scipy now), and drop the pre-stored tables.
  - schueller2024: process all three Zenodo sets (~58 participants), not just Set1 (see its notes.md).
  - Overlap trimming is written twice (bentum2023 `trim_overlaps`, momenian2024 `_trim`) and the {stem: path}
    index that raises on duplicates four times (das2019, fuglsang2018, bentum2023 `wav_index`, wang2022
    `annotation_files`): move to iohelpers. `jehn2025_base/alignment/xcorr.py` (used by five datasets) could move
    to a shared torch-free module.
  - wang2025 `alignment/onsets.csv` has no generator script in the repo (see its notes.md).
- Keep for now: `datasets.tsv`, `urls.txt`, README to-do list.
