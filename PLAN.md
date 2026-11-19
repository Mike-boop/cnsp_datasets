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
- Cut stimuli to what the EEG covers (varano2022 mismatched AV trials end with the shorter of audio and video).

**Validation and interpretation**
- Validate per condition (section 3) and look at the TRF plots, not only p-values: a stimulus-locked ripple at all
  lags (guilleminot2021 30-60 Hz) can pass the MLR test.
- DNN offsets relative to accou2023: clean speech within +-5 ms; speech in noise ~-15 ms even with measured onsets
  (response latency, not timing error).

**Running the work**
- Long jobs detached and resumable (cache per trial/session); a server reboot killed every job once.
- Downloads can stop silently: use resumable retries (`curl -C -`) and check the final size.
- Keep scripts and results out of the session scratchpad (`tmp/review/scripts`).

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
  `tmp/<dataset>/{download,standardised,validation}`. Up to 500 GB while working on a dataset.
- When a dataset is done, delete `tmp/<dataset>` entirely. Before that, commit the small artefacts to the repo:
  `notes.md`, `adaptor.py` and the validation summary (`datasets/<name>/validation.json`, plus key figures if
  small).
- Never keep standardised data unless a later step in progress needs it.
- Existing downloads in `/data_storage/gu08wuvu/datasets/` are **read-only**: read from them instead of
  re-downloading.
- Enforced by `.claude/hooks/storage_guard.py` (PreToolUse): blocks writes outside `tmp/` under the datasets
  root, and blocks download/standardise commands while `tmp/` exceeds 500 GB.
