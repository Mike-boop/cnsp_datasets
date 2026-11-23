# PLAN: cnsp_datasets v2 (agentic)

Goal: download public continuous-speech M/EEG datasets, align the neural data with the speech (best effort,
including clock drift correction), and store both in one standard format with common preprocessing utilities.
Most of the time goes into understanding each dataset; v2 hands that work to agents, with a human checkpoint and
objective validation before anything counts as done.

## 1. Scope of v2

**In**
- Sensor-level M/EEG. Head-shape digitisation is kept in the `.fif` files when available.
- Speech at the least-processed level available: raw audio > envelope (if only that was shared). Plus transcripts
  and word/phoneme annotations as TextGrids, when shared.
- Datasets without speech are still standardised (`stimulus=[]`, with the reason in the metadata).
- Best-effort alignment and drift correction from start/end triggers or stimtrack channels.
- Preprocessing as already implemented: band-pass filtering, decimation, fast Hilbert envelope
  (`HilbertEnvelope`), gammatone + half-wave rectification cochlear model (`GammatoneEnvelope`, non-linearity
  `'hwr'`).

**Out (for now)**
- Anatomy and source localisation (`AnatRecord` stays, unused).
- CND output: `cnd_sink.py` is deprecated and will be removed; third parties can convert.
- Applying brain-based alignment (DNN, TRF, decoders) in adaptors by default, except when a dataset is unusable
  without it (section 3, "Brain-based corrections"). Otherwise `cnsp_datasets/align/` is used to check timing and,
  for poorly aligned data, to estimate onsets/drift that are documented (json/csv in the dataset folder), not
  applied.

## 2. Standard format

### Neural data
- **Sample rate:** native rates up to 1024 Hz are kept (never upsample). Higher rates are resampled to 1000 or
  1024 Hz, whichever gives fewer artefacts (1000 Hz for 10/25 kHz recordings). Fractional rates are resampled to the
  nearest "nice" rate (e.g. 1017.25 Hz → 1024 Hz). This is a real resample, not a relabel.
  When drift correction is applied, it happens in the *same* resample (one corrected ratio, one interpolation).
- **Units:** MNE stores SI internally (V, T), and so does `.fif`. "Standardised units" means each adaptor scales
  correctly into SI at load time, so that all EEG reads in µV and all MEG in fT when displayed. The validator
  checks this (section 5).
- **Channel types:**
  - scalp EEG: `eeg`
  - mastoids and other external EEG electrodes: `misc` (MNE has no "external" type), also listed as external
    sensors in the metadata. Mastoids are kept and named `M1`/`M2`.
  - EOG: `eog`, named `VEOG`/`HEOG` when the direction of the setup is known, otherwise `EOG`; ECG: `ecg`. Keep
    all peripherals (EOG, ECG, others).
  - MEG reference sensors: `ref_meg`
  - stimtrack (audio copy or envelope recorded with the M/EEG): `stim`/`misc`, described in the metadata
- **Channels kept and dropped:** drop completely unused channels (e.g. disconnected peripheral ports). Channels that
  are flat or carry only electrical noise for a participant stay in the data and are listed in `info['bads']`.
- **Files:** EEG from several simultaneous EEG systems goes in separate files (avoids MNE re-referencing
  problems). Simultaneous EEG and MEG can share one `.fif` file.
- **Subjects and sessions:** keep the original subject names (no renumbering); label sessions as accurately as the
  data allow.
- **Reference:** keep the original reference; record it in the metadata. Do not re-reference during
  standardisation.
- **Memory:** load lazily (`data_fn` callables). Exception: datasets that ship all trials in one concatenated
  file (e.g. schueller2024 on Zenodo) cache the loaded file in the adaptor (shared loader / `lru_cache`) rather
  than reloading it per trial. Only do this when the file fits comfortably in RAM (rule of thumb: < 16 GB).

### Speech
- Visual stimuli are not standardised for now (future version); the M/EEG and the audio of multimodal trials are.
- Audio as shipped (sample rate untouched); envelopes only when audio is unavailable (`feature_name` says which).
- TextGrids: tiers named `words` and `phones`; times are relative to the start of the stimulus file.
- Transcripts as UTF-8 text.

### Provenance sidecar (per trial, JSON)
Users need this most when deciding whether a dataset supports high-frequency analysis.

| field | example |
|---|---|
| `alignment_method` | `hw_trigger`, `sw_trigger`, `stimtrack_xcorr`, `onset_only`, `dnn`, `brain_trf`, `none` |
| `trigger_type` | `hardware`, `software`, `unknown`, with the source (paper/README/inferred) |
| `drift_ppm` | estimated clock drift; `null` if not estimated |
| `jitter_ms` | estimated onset jitter; `null` if not estimated |
| `validation_tier` | highest tier passed: `none`, `low`, `mlr`, `brainstem` (section 5) |
| `notes` | anything a user should know |

`alignment_method` values (checked by `standardise/provenance.py`):
- `hw_trigger` / `sw_trigger`: onsets (and drift, if estimated) from hardware / software triggers.
- `stimtrack_xcorr`: onsets and drift from cross-correlating a recorded audio copy (stimtrack, aux) with the stimulus.
- `onset_only`: one onset per trial (a start marker, or the authors' epochs cut at stimulus onset); no drift
  estimate.
- `dnn`: onsets or drift applied from a match-mismatch DNN (`align/`).
- `brain_trf`: onsets or drift applied from the neural response itself (TRFs, decoders, template matching), only
  under the rule in section 3 ("Brain-based corrections").
- `none`: not aligned.

Dataset-level metadata: licence, citation(s), DOI, units as shipped, original reference, channel list and
external sensors, stimulus availability.

## 3. Alignment

- **Hardware-derived corrections are applied by default** (user): onsets and drift measured from an audio copy
  (stimtrack, aux), hardware triggers or other acquisition hardware are on by default unless validation casts doubt
  on them.
- **Brain-based corrections** (DNN, TRF, decoder offsets and drift) are documented in `notes.md`, not applied, with
  one exception (user, 2026-11-23): when a dataset is unusable without them (e.g. the shipped onset misses the sound
  by hundreds of ms), the brain-based alignment is applied by default, an adaptor option turns it off, and the
  dataset is graded `poor`. `alignment_method` is then `dnn` or `brain_trf`. Examples:
  - li2025: 0.80 s for sub-31..47 and 0.42 s for sub-48..60, from population TRFs; group B aligned to group A's
    TRF by multichannel template matching (`brain_trf`);
  - chen2026: per-chapter EEG latency;
  - chen2023: drift;
  - hassan2026: DNN onset.
- **Triggers:** use start/end triggers where available. Whether triggers are hardware or software is often
  undocumented; record what is known and how.
- **Drift vs jitter:** when several participants heard the same stimulus, compare trigger-derived durations with the
  stimulus duration across subjects and trials. Drift scales with trial length (ppm); jitter does not. Fit both
  (duration error = drift·length + noise) so drift is not counted as jitter. Software-trigger jitter limits
  high-frequency analyses, so the estimate goes in the provenance sidecar.
- **Stimtrack channels:** cross-correlate with the audio or the matching feature to get the onset, and use the
  start/end to check drift. Some stimtracks are not audio (brennan2018 looks like an envelope or half-wave-rectified
  audio); the explorer establishes what each one contains.
- **Per condition:** extract and align each condition separately (e.g. A, AV, tactile, mismatched, dialogue vs
  story), and report onset offsets, drift and the validation lag sweep per condition. Conditions can use different
  playback code, buffers or delays (guilleminot2021: tactile buffers shifted by the delay or rolled for mismatched
  trials), so a pooled estimate can hide a condition-specific error.
- Reuse `align/scan.py` (`lag_scores`, `joint_fit`, `pooled_drift`, `refine_onset`, `correct_drift`) where it fits.

### Alignment grades
Every dataset gets one grade, recorded in `data_campaign/STATUS.md` (`alignment` column), the spreadsheet
(`alignment_quality`) and the dataset's `notes.md`, with one line of evidence:
- `good`: onsets (and drift, if corrected) come from hardware and were verified, e.g. a stimtrack or audio copy, or
  hardware triggers checked against one;
- `medium`: the trigger source is unknown or software, the shipped timing is kept, and validation confirms it (at
  least the low tier, a plausible TRF latency, nothing at negative lags, no correction needed);
- `poor`: onsets or drift are estimated from the neural data (a brain-based correction, applied or only documented
  as an offset);
- `none`: not assessable (e.g. no stimulus).

The weakest part decides: hardware onsets with brain-based drift are `poor`.

## 4. Agents and workflow

```
main session: download (background job + log monitoring)
   → data-explorer  → notes.md + alignment plan
   → HUMAN CHECKPOINT: approve the alignment plan
   → data-standardiser → adaptor.py, pilot run (size estimated from one trial; ~20 subjects if it fits)
   → validator  → validation report (pass/fail per tier)
   → reviewer   → style review of the adaptor
   → full standardisation run
   → data-documenter → dataset documentation
```

| agent | job | writes |
|---|---|---|
| (main session) | dispatches downloads in the background, monitors the log, reports when there are many failures (with log excerpt and message) | nothing in the repo |
| `data-explorer` | works out the dataset structure (template below); reads any shared code and READMEs | `datasets/<name>/notes.md` |
| `data-standardiser` | writes the adaptor (`TrialRecord`s), following the explorer's notes and any shared usage code | `datasets/<name>/adaptor.py` |
| `validator` | runs the objective checks in section 5 and reports numbers, never impressions | `datasets/<name>/validation.json` (figures in `tmp/review/<name>/validation/`) |
| `reviewer` | PEP8, minimalistic style, docstrings present and short; reports findings, does not edit | review comments |
| `data-documenter` | user-facing documentation: content, provenance, caveats, licence, citation | dataset docs |

Agents say "unknown" rather than guess. Uncertain alignment decisions go to the human checkpoint.

### Explorer report template (`notes.md`)
1. **Source:** DOI, licence, citation, related paper(s) (`data_campaign/papers/<id>.pdf`), shared code.
2. **Layout:** where neural files, stimuli and annotations live; file formats.
3. **Stimulus ↔ trial mapping:** subjects, conditions, how each recording maps to stimulus files; same stimuli
   across subjects? Missing or incomplete data.
4. **Speech features available:** raw audio (preferred) or only derived features / transcript / word or phoneme
   annotations.
5. **Neural data:** modality, sample rate, units as shipped, channel list (scalp, mastoids, EOG, ECG, MEG
   reference sensors, stimtrack), reference, head-shape digitisation.
6. **Alignment:** trigger codes and meaning; hardware or software (documented / inferred / unknown; software
   triggers can have a random offset to the sound onset, mean + jitter); stimtrack content (a recorded audio channel
   usually gives precise onsets and drift; a second sound channel sent only to the acquisition system gives highly
   accurate ones); insert-earphone tube latency (often unknown); proposed alignment and drift-correction method.
7. **Cross-subject duration check:** trigger-derived durations vs stimulus durations; drift/jitter estimate if
   possible, per condition.
8. **Open questions** for the human checkpoint.

## 4b. Review checklist

Moved to `data_campaign/LESSONS.md` (with the lessons from later batches). The step-by-step
workflow per dataset, including coherence, DNN checks, data size and clean-up, is `data_campaign/WORKFLOW.md`.

## 5. Validation (objective)

Run on a pilot of ~20 subjects (or all subjects, if fewer) before committing to the full job.

1. **Sanity:** neural trial duration ≈ stimulus duration (after drift correction) for every trial; per-modality
   amplitude in a plausible range after a high-pass (catches unit/scaling errors); no all-flat or all-NaN channels.
2. **Low-frequency tier (`low`): forward model, 0.5–8 Hz** (envelope → every channel). Cross-validated
   (leave-one-trial-out within subject), reporting the per-channel correlation between prediction and recording,
   per subject and as a population distribution. Backward models (envelope reconstruction) are an optional extra,
   e.g. for attention contrasts. Objective pass criteria:
   - above a null distribution built from mismatched stimuli (other trials' envelopes) and circular shifts, per
     subject and at population level;
   - **lag sweep:** prediction score as a function of a global stimulus shift (e.g. ±1 s): the peak must sit
     at 0 lag within tolerance. A non-zero peak measures a constant offset error directly.
   - comparable with hand-aligned reference datasets (section 6).
   - all of the above reported per condition as well as pooled (see section 3, "Per condition").
3. **Middle-latency tier (`mlr`): forward TRF, 30–60 Hz, window 18–45 ms** (TODO: confirm window).
   Rather than judging the shape by eye: SNR of the TRF in the latency window against the RMS at negative lags
   (noise floor), with a bootstrap or permutation test across subjects. Pass = significant.
4. **Brainstem tier (`brainstem`): forward TRF, 30–250 Hz** (half-wave-rectified feature, sufficient sample rate).
   Same SNR test, with a modality-specific window:
   - EEG: 4–9 ms (ABR wave V region).
   - MEG: no ABR expected; test the 30–250 Hz response at 28–45 ms instead. For MEG, this tier therefore shows
     high-frequency cortical alignment, not brainstem alignment.

Latency windows are parameters of the validation scripts, not hard-coded.

Per trial, the highest tier passed goes into `validation_tier`. The validator reports numbers, null
distributions and figures for the human; it does not decide alignment quality from TRF shapes.

## 6. Order of work

Steps 1-4 of the original order (plan, agents, validation scripts, calibration on hand-aligned datasets,
new datasets) are done; new datasets continue through the campaign (`data_campaign/`). Still to do: remove
`cnd_sink.py`; a DNN aligner trained on the validator's lag sweeps and the stimtrack datasets.

## 7. Storage

The repository is the product: standardisation must be reproducible from code alone (downloaded and run on the
HPC server). Data is never kept long term here.

- `/data_storage/gu08wuvu/datasets/tmp/` is a working directory only:
  `tmp/review/<dataset>/{download,standardised,validation}`. Up to 1 TB while working (2 TB with the user's
  sign-off for data already scheduled for deletion).
- When a dataset is done, delete its download and standardised data (ask first). Before that, commit the small artefacts to the repo:
  `notes.md`, `adaptor.py` and the validation summary (`datasets/<name>/validation.json`, plus key figures if
  small).
- Never keep standardised data unless a later step in progress needs it.
- Existing downloads in `/data_storage/gu08wuvu/datasets/` are **read-only**: read from them instead of
  re-downloading.
- Enforced by `.claude/hooks/storage_guard.py` (PreToolUse): blocks writes outside `tmp/` under the datasets
  root, and blocks download/standardise commands while `tmp/` exceeds its limit (1 TB; a user-approved window is
  set in env `CNSP_TMP_LIMIT_GB` or the file `tmp/TMP_LIMIT_GB`).
- **Vault backup** (user, 2026-11-23): the raw data of DRUM and Zenodo downloads (slow, time out, rate-limit) are
  backed up to the NHR vault (`csnhr:/home/vault/iwpm/iwpm104h/<dataset>`) before anything local is deleted:
  manifest (paths, sizes, md5) + rsync, then check every file's size with `stat` (readdir on `/home/vault` is
  unreliable). chen2026 (SciDB) was backed up on request. Other sources are re-downloaded when needed.

### Zenodo usage limits (promised to the Zenodo moderators, 2026-11-21)
Zenodo blocked this server (HTTP 403, "unusual traffic") on 2026-11-21, and again on 2026-11-23 at 21:09 after an
access test had passed at ~20:30. The user promised:
- **at most three concurrent file downloads** from Zenodo at a time (`download_dataset` caps `max_workers` at 3
  for Zenodo sources; keep any other script at <= 3 too);
- **at most 1-2 Zenodo datasets downloaded per day** (log each one, with the date, in `data_campaign/HANDOVER.md`
  so other sessions can count).
Check access with a single request before starting; never work around a block (no user-agent changes, proxies or
other hosts). On a block, stop and report, and never retry from another machine. While
`tmp/review/ZENODO_BLOCKED` exists, `.claude/hooks/command_guard.py` blocks commands that contact Zenodo.
- Scripts that contact Zenodo identify themselves in the User-Agent (the tool's name; contact details only as the
  user configures them).
- An archival copy of the Zenodo datasets is pulled separately by the user's `zenodo_slowpull`
  (github.com/Mike-boop/zenodo_slowpull): one connection, rate limit, daily budget, md5, resume, hard stop on 403.
  It runs on the vault node, not from this server.

## 8. Future work

- **BIDS re-uploads of weissbart2019 and etard2019** (the user moderates their Zenodo records): EEG-BIDS with the
  StimTrack `Sound` channel kept, the stimuli as played (etard: per-condition English sentences for
  lb/mb/hbDutch, which the current release copies from cleanDutch; noise/babble tracks), onsets/events from the
  stimtrack, drift estimates, and other material missing from the convenience releases (weissbart `onsets.mat`,
  transcripts and word-level features). Sources: original Zenodo records 7086168 (weissbart) and 7086209 (etard).
- **Drift and offset parameters applied by adaptors.** Estimate clock drift from stimtrack/aux channels where they
  exist (Theil-Sen through windowed lags, as `jehn2025_base/drift.py` and `tmp/review/scripts/guilleminot_drift.py`),
  store the values at dataset, session and trial level with each dataset, and let every adaptor apply them optionally
  (one `drift_correction` option with a shared resampling helper, like bentum2023 and jehn2025 now). Same for constant
  offsets estimated without a stimtrack (match-mismatch DNN vs accou2023): das2019 ~-80 ms, bentum2023 ~-68 ms,
  broderick2019 cocktail ~-45 ms are documented in their notes but not applied.
- **Interpolation method for drift correction.** Let the shared resampling helper take `interpolation="spline" |
  "linear"`. accou2023 uses the authors' linear interpolation, the others a quintic spline (`to_audio_clock`).
  Compared on accou2023 (12 subjects, 111 runs, 2026-11-20, `tmp/review/accou2023/resample_compare/`): linear
  interpolation scales the EEG by sqrt((2 + cos w) / 3) on average (0.97 at 100 Hz, 0.88 at 200 Hz, 0.77 at 300 Hz),
  signal and noise alike, so 30-300 Hz TRF SNR (2.39 vs 2.34), per-subject SNR and 1024 Hz coherence did not
  change; only absolute TRF amplitudes above ~100 Hz are smaller. No timing difference. Spline costs a few seconds
  and ~0.5 GB more per run.
- **Annotations in the standardised data.** Always carry word/phoneme alignments when they exist or can be made
  (e.g. guilleminot2021 tactile-condition TextGrids).
- **Authors' quality ratings in the standardised data.** Adaptors include all data, but the authors' own exclusions
  are lost on the way, so users cannot reproduce them. Cases so far:
  - bentum2023 rates blocks "bad" (103) or "doubtfull" (198). They are included by default; `exclude_usability`
    skips them.
  - brennan2018 excluded subjects in the original study (028, 029, 031, 033, 046, 047; 047 for noise). They are
    included, and their events.tsv has no word onsets.

  Option: carry such flags per trial or subject (e.g. in the provenance sidecar) so users can filter.

### Second pass (later)
- **varano2022 audio cut.** `_make_audio_loader` cuts `AVbook/A/<part>.wav` to the trial's EEG length, which only
  shortens the 95 mismatched AV trials (EEG stops at the shorter video). The stimulus is named by the part alone, so
  the stored `audio/<part>` is whichever trial was written first: if a mismatched trial came first, the matched
  trials that play the same part (other subjects, A/AV conditions) get the shortened audio too (onsets unaffected;
  their tail is lost). The `visual` stimulus used the same loader. The TextGrids were not cut. Cut removed from
  the adaptor 2026-11-20; still to do: re-standardise (needs `data_2020.zip` again; also lets varano be
  validated with an average reference). Check the old standardisation's `audio/*.npz` lengths against the wavs if
  it still exists anywhere.
- Same check for other adaptors whose stimulus loaders take trial-specific arguments: bentum2023 builds each block's
  audio from the block's file list and gaps (named by the wav file; confirm every block with that name has the same
  list), guilleminot2021 tactile (delay/roll are in the name: fine).
- **pkueeg2025 drift (NeuroScan days 1-2).** The adaptor applies the marker-based 76.8 ppm; brain-based estimates
  on uncorrected data give ~47 ppm (DNN lag slope) and ~22 ppm (backward-decoder lag slope), and the DNN residual
  on the corrected pilot suggests the marker value overshoots. Kept at 76.8 ppm for now (user, 2026-11-22); the
  alternatives, the weissbart2019 reference check and candidate scores are in `datasets/pkueeg2025/notes.md`
  ("Drift re-estimation"). Decide the value, and check whether the marker clock is the stimulus PC's rather than the
  sound card's.
- **Constant onset offsets documented, not applied** (user, 2026-11-22): pkueeg2025 (~-75 ms NeuroScan, ~-42 ms
  Neuracle, DNN vs accou2023) and wang2025 (~-0.19 s, DNN + TRF), alongside das2019 / bentum2023 /
  broderick2019_cocktail (section 8). Applied because the data are unusable without them: li2025, chen2026,
  chen2023 drift, hassan2026 (section 3, "Brain-based corrections").
