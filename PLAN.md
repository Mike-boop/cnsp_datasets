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
- DNN-based alignment (`cnsp_datasets/align/`): planned for this edition, but after the pipeline below works.

## 2. Standard format

### Neural data
- **Sample rate:** the highest available. Fractional rates are resampled to the nearest "nice" rate
  (e.g. 1017.25 Hz → 1024 Hz; nice = 250·2ⁿ, 256·2ⁿ, 500·2ⁿ, 1000·2ⁿ). This is a real resample, not a relabel.
  When drift correction is applied, it happens in the *same* resample (one corrected ratio, one interpolation).
- **Units:** MNE stores SI internally (V, T), and so does `.fif`. "Standardised units" means each adaptor scales
  correctly into SI at load time, so that all EEG reads in µV and all MEG in fT when displayed. The validator
  checks this (section 5).
- **Channel types:**
  - scalp EEG: `eeg`
  - mastoids and other external EEG electrodes: `misc` (MNE has no "external" type), also listed as external
    sensors in the metadata
  - EOG: `eog`; ECG: `ecg`
  - MEG reference sensors: `ref_meg`
  - stimtrack (audio copy or envelope recorded with the M/EEG): `stim`/`misc`, described in the metadata
- **Reference:** keep the original reference; record it in the metadata. Do not re-reference during
  standardisation.
- **Memory:** load lazily (`data_fn` callables). Exception: datasets that ship all trials in one concatenated
  file (e.g. schueller2024 on Zenodo) cache the loaded file in the adaptor (shared loader / `lru_cache`) rather
  than reloading it per trial. Only do this when the file fits comfortably in RAM (rule of thumb: < 16 GB).

### Speech
- Audio as shipped (sample rate untouched); envelopes only when audio is unavailable (`feature_name` says which).
- TextGrids: tiers named `words` and `phones`; times are relative to the start of the stimulus file.
- Transcripts as UTF-8 text.

### Provenance sidecar (per trial, JSON)
Users need this most when deciding whether a dataset supports high-frequency analysis.

| field | example |
|---|---|
| `alignment_method` | `hw_trigger`, `sw_trigger`, `stimtrack_xcorr`, `onset_only`, `dnn`, `none` |
| `trigger_type` | `hardware`, `software`, `unknown`, with the source (paper/README/inferred) |
| `drift_ppm` | estimated clock drift; `null` if not estimated |
| `jitter_ms` | estimated onset jitter; `null` if not estimated |
| `validation_tier` | highest tier passed: `none`, `low`, `mlr`, `brainstem` (section 5) |
| `notes` | anything a user should know |

Dataset-level metadata: licence, citation(s), DOI, units as shipped, original reference, channel list and
external sensors, stimulus availability.

## 3. Alignment

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

## 4. Agents and workflow

```
main session: download (background job + log monitoring)
   → data-explorer  → notes.md + alignment plan
   → HUMAN CHECKPOINT: approve the alignment plan
   → data-standardiser → adaptor.py, pilot run (~20 subjects)
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
| `validator` | runs the objective checks in section 5 and reports numbers, never impressions | `datasets/<name>/validation.json` (figures in `tmp/<name>/validation/`) |
| `reviewer` | PEP8, minimalistic style, docstrings present and short; reports findings, does not edit | review comments |
| `data-documenter` | user-facing documentation: content, provenance, caveats, licence, citation | dataset docs |

Agents say "unknown" rather than guess. Uncertain alignment decisions go to the human checkpoint.

### Explorer report template (`notes.md`)
1. **Source:** DOI, licence, citation, related paper(s), shared code.
2. **Layout:** where neural files, stimuli and annotations live; file formats.
3. **Stimulus ↔ trial mapping:** how each recording maps to stimulus files; same stimuli across subjects?
4. **Speech features available:** raw audio / envelope / transcript / word or phoneme annotations.
5. **Neural data:** modality, sample rate, units as shipped, channel list (scalp, mastoids, EOG, ECG, MEG
   reference sensors, stimtrack), reference, head-shape digitisation.
6. **Alignment:** trigger codes and meaning; hardware or software (documented / inferred / unknown); stimtrack
   content; proposed alignment and drift-correction method.
7. **Cross-subject duration check:** trigger-derived durations vs stimulus durations; drift/jitter estimate if
   possible, per condition.
8. **Open questions** for the human checkpoint.

## 4b. Review checklist (lessons from the 2026-11 adaptor review)

Each item below caught a real error in at least one dataset. Run through them for every dataset.

**Timing and drift**
- Look for a stimtrack, aux or Sound channel in every download. If the convenience release dropped it, look for
  the original record with the raw recordings (weissbart2019 and etard2019 dropped `Sound`; their original Zenodo
  records 7086168 and 7086209 have it).
- Estimate drift wherever the stimulus is recorded with the EEG: Theil-Sen line through lags in ~10 s windows
  (`datasets/jehn2025_base/drift.py`). Two endpoint windows are fragile: periodic side peaks in band-passed speech
  or a ~100 Hz tactile carrier give ms-sized jumps. Authors rarely correct drift (jehn2025 26.7 ppm, bentum2023
  33.6 ppm). Plot per-subject drift before proposing a correction; clusters can differ (jehn2025: ~18 ppm for a
  run of subjects).
- Measure onsets from the stimtrack and compare with the markers: markers can be late or missing (guilleminot2021:
  one marker 2.39 s late; trials started during a recording pause had none).
- Check BrainVision `New Segment` annotations (recording pauses: MNE joins segments without a gap) and trials that
  run past the end of the recording.
- Nominal file durations rounded to ms add up over concatenated stimuli (bentum2023); use exact durations.

**Mapping and labels**
- Verify the trial -> stimulus mapping with an independent signal: trial duration vs wav duration (exact to the ms
  in varano2022), recording order (`first_samp`, `meas_date`), stimtrack correlation, experiment logs.
- Verify condition labels against the authors' code and the actual stimuli, not just the readme: varano2022 had
  cartoon/edge swapped; etard2019 SNR labels are unverified (the wavs do not carry the presented level).
- Verify the attended side/ear per subject from stimtrack channels (jehn2025: three subjects with swapped sides).
- Readmes and helper files can be wrong: varano2022 condorder README (`trial_index`), jehn2025 code table,
  etard2019 English sentences/onsets copied from another condition by `align_data.py`.
- Check every file, not one (channel lists, lengths, annotations).

**Stimuli**
- Include everything that was played, as separate stimuli: noise/babble tracks, distractors, tactile signals
  (guilleminot2021 mismatched trials used the tactile buffer rolled by a quarter), embedded sentences.
- Do not cut stimuli to the EEG: by convention the longer signal is cut where the data are used. Check instead
  that both start at the same time.

**Validation and interpretation**
- Validate with an average reference (`--reference average`, the default of `tmp/review/standardise_validate.sh`)
  so tiers and SNRs compare across datasets. The validator's own default is no re-referencing, which changes the
  numbers a lot (weissbart2019 30-250 Hz SNR 1.54 average vs 2.46 with the recorded ear reference). Record the
  reference with every result.
- Validate per condition (section 3) and look at the TRF plots, not only p-values: a stimulus-locked ripple at all
  lags (guilleminot2021 30-60 Hz) can pass the MLR test.
- DNN offsets relative to accou2023: clean speech within +-5 ms; speech in noise ~-15 ms even with measured onsets
  (response latency, not timing error).

**Data size (record for every dataset)**
- Number of participants and hours per participant (mean, min-max), overall and per condition, estimated from the
  stimuli: each trial counts its longest stimulus (simultaneous streams once), summed per participant
  (`tmp/review/scripts/data_size.py`, headers only; adds rows to `tmp/review/data_size.csv`). Put the numbers in
  the dataset's `notes.md` and in `tmp/review/data_size.md`. Measure before deleting standardised data.
- Check a few trials' neural duration against their stimulus: stimuli are not cut to the EEG (the longer signal is
  cut at the point of use), so the estimate is too high where only part of a stimulus was played (das2019: 2-min
  repeat trials carry the full 6.5-min track, 2.3 h estimated vs ~1.3 h recorded). Report the recorded figure then.
- A stimulus's `data_fn` must depend only on its (modality, name, feature): the sink writes one file per name, shared
  by all trials, and the first trial written wins. Anything trial-specific (cut, shift, resampling) needs its own
  name or belongs in the trial (varano2022 cuts the audio per trial; see section 8, second pass).

**Running the work**
- Long jobs detached and resumable (cache per trial/session); a server reboot killed every job once.
- After relabelling conditions or changing an adaptor, move the dataset's caches aside before re-running: caches
  keyed by subject/trial/condition silently return the old results (etard2019 DNN offsets after the SNR relabel).
- Downloads can stop silently: use resumable retries (`curl -C -`) and check the final size.
- Keep scripts and results out of the session scratchpad (`tmp/review/scripts`).

**Notes as you go (the repo is the record)**
- Write every finding that explains a choice in the code into the repo's `cnsp_datasets/datasets/<name>/notes.md`
  as soon as it is established, not only at the end: mapping and its verification, file/label/polarity fixes,
  units and gains, skipped trials and why, drift, upstream errors (with the evidence: numbers, script names). Point
  to it from the adaptor's docstring. `tmp/` is deleted when a dataset is done; anything only there is lost.
- `tmp/review/<name>/notes.md` holds review results and file pointers only. Issues to report to dataset authors
  are collected in `tmp/review/upstream_issues.md` and also go in the dataset's repo notes (section "Upstream
  issues").

## 5. Validation (objective)

Run on a pilot of ~20 subjects (or all subjects, if fewer) before committing to the full job.

1. **Sanity:** neural trial duration ≈ stimulus duration (after drift correction) for every trial; per-modality
   amplitude in a plausible range after a high-pass (catches unit/scaling errors); no all-flat or all-NaN channels.
2. **Low-frequency tier (`low`): backward model, 0.5–8 Hz.** Cross-validated envelope reconstruction
   (leave-one-trial-out within subject), reporting Pearson r per subject and the population distribution. Objective
   pass criteria:
   - above a null distribution built from mismatched stimuli (other trials' envelopes) and circular shifts, per
     subject and at population level;
   - **lag sweep:** reconstruction score as a function of a global stimulus shift (e.g. ±1 s): the peak must sit
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

1. This plan, the agent definitions (`.claude/agents/`) and the storage guard (`.claude/settings.json`).
2. Validation scripts (section 5).
3. Calibration: run the pipeline on 2–3 datasets already aligned by hand (e.g. bentum2023, fuglsang2018,
   weissbart2019). Do the agents reproduce the hand-made adaptors, and what scores do the checks give?
4. New datasets, one at a time.
5. Remove `cnd_sink.py`.
6. DNN aligner (`cnsp_datasets/align/`); the validator's lag sweeps and stimtrack datasets provide training and
   evaluation targets.

## 7. Storage

The repository is the product: standardisation must be reproducible from code alone (downloaded and run on the
HPC server). Data is never kept long term here.

- `/data_storage/gu08wuvu/datasets/tmp/` is a working directory only:
  `tmp/<dataset>/{download,standardised,validation}`. Up to 1 TB while working (raised from 500 GB on 2026-11-20).
- When a dataset is done, delete `tmp/<dataset>` entirely. Before that, commit the small artefacts to the repo:
  `notes.md`, `adaptor.py` and the validation summary (`datasets/<name>/validation.json`, plus key figures if
  small).
- Never keep standardised data unless a later step in progress needs it.
- Existing downloads in `/data_storage/gu08wuvu/datasets/` are **read-only**: read from them instead of
  re-downloading.
- Enforced by `.claude/hooks/storage_guard.py` (PreToolUse): blocks writes outside `tmp/` under the datasets
  root, and blocks download/standardise commands while `tmp/` exceeds 1 TB.

### Zenodo usage limits (promised to the Zenodo moderators, 2026-11-21)
Zenodo blocked this server (HTTP 403, "unusual traffic") on 2026-11-21. The user promised:
- **at most three concurrent file downloads** from Zenodo at a time (`download_dataset` caps `max_workers` at 3
  for Zenodo sources; keep any other script at <= 3 too);
- **at most 1-2 Zenodo datasets downloaded per day** (log each one, with the date, in the review handover so
  other sessions can count).
Check access with a single request before starting; never work around a block (no user-agent changes, proxies or
other hosts).

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
- **pkueeg2025 drift (NeuroScan days 1-2).** The adaptor applies the marker-based 76.8 ppm; brain-based estimates
  on uncorrected data give ~47 ppm (DNN lag slope) and ~22 ppm (backward-decoder lag slope), and the DNN residual
  on the corrected pilot suggests the marker value overshoots. Kept at 76.8 ppm for now (user, 2026-11-22); the
  alternatives, the weissbart2019 reference check and candidate scores are in `datasets/pkueeg2025/notes.md`
  ("Drift re-estimation"). Decide the value, and check whether the marker clock is the stimulus PC's rather than the
  sound card's.
- **Constant onset offsets documented, not applied** (user, 2026-11-22): pkueeg2025 (~-75 ms NeuroScan, ~-42 ms
  Neuracle, DNN vs accou2023) and wang2025 (~-0.19 s, DNN + TRF), alongside das2019 / bentum2023 /
  broderick2019_cocktail (section 8).
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
