# harshaiyahav2025: selective attention to an audiovisual lecture with a competing talker (OSF bzean, CND)

23 participants x 40-41 trials (~25 s each), 64-channel EEG shared **preprocessed: 1-20 Hz, 100 Hz, ICA-cleaned,
linked-mastoid reference**, as CND `.mat` files with the authors' 100 Hz envelopes of both talkers. No audio, no
raw EEG, no triggers. Hebrew.

## 1. Source
- OSF project bzean (https://osf.io/bzean/), created 2024-12-19; one folder `dataCND/` (23 `dataSub<N>.mat`, 23
  `dataStim<N>.mat`, `README.txt`), 1.2 GB. No wiki, no components, no linked projects.
- **Licence: unknown.** The OSF node has no licence (`node_license: null`) and the README names none. The paper is
  CC BY 4.0, which covers the article only.
- Paper: Har-shai Yahav P, Rabinovitch E, Korisky A, Vaknin Harel R, Bleichner M, Zion Golumbic E (2025). Neural
  speech tracking during selective attention: a spatially realistic audiovisual study. *eNeuro* 12(6),
  doi:10.1523/ENEURO.0132-24.2025. The README cites the bioRxiv preprint (doi:10.1101/2023.12.27.573349). The PDF
  has no data availability statement and no code link.
- No shared code.

## 2. Layout
- `dataSub<N>.mat` (MATLAB 5): `eeg.data` {1 x ntrials} of [samples x 64] float64, `eeg.fs` = 100,
  `eeg.chanlocs` (EEGLAB struct: labels, X/Y/Z, sph_*, theta/radius, urchan).
- `dataStim<N>.mat`: `stim.data` {3 x ntrials}: rows `names` = 'Target Envelope', 'Non-target Envelope',
  'All features' (row 3 = [target, non-target] as two columns, checked equal in every trial, so redundant);
  `stim.fs` = 100; `stim.condIdxs` (1 = 'First half', 2 = 'Second half'); `stim.stimIdxs` = 1..ntrials.
- Subjects 1-24 without 19 (paper: 24 recorded, one excluded for technical problems during recording; N = 23).
- **`stimIdxs` does not identify the stimulus**: it is the trial position, and the same index is a different
  segment in the two counterbalancing groups. Segments must be identified by content (section 3).

## 3. Stimulus <-> trial mapping (verified by envelope content)
Design (paper, Methods): two ~20-min video lectures (one male, one female talker) cut into segments of 22-40 s.
The target lecture is shown as video with audio from a loudspeaker behind the monitor (front); the non-target
lecture is audio only from a loudspeaker on the left (~95 cm both). The non-target starts 3 s after the target with
a 2 s ramp-up. Target segments: the first 21 of a lecture; non-target segments: the last 21 of the other lecture,
both in order. At half-time the roles swap (target lecture becomes the non-target and vice versa); the starting
lecture is counterbalanced.

Envelope hashes over all 939 trials give:
- 42 distinct target envelopes and 42 distinct non-target envelopes, none shared between the two roles; every target
  envelope always comes with the same non-target envelope; every envelope is identical across subjects.
- Two groups. **Group A** (subjects 1, 3, 5, 7, 9, 11, 13, 15, 17, 21, 23; 11): first half lecture L1 is the
  target. **Group B** (2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24; 12): first half L2 is the target. Which lecture
  is the male or female talker is **unknown** (envelopes only).
- Naming used here: `L1s01..L1s21` = the 21 target segments of L1 (likewise L2); each is always paired with one
  non-target segment from the end of the other lecture (L2e01..L2e21 / L1e01..L1e21, same k).
- Full design (41 trials) per group, trial index -> segment:
  - group A: trials 0-19 (cond 1) = L1s02..L1s21; trial 20 (cond 2) = L2s01; trials 21-40 = L2s02..L2s21.
  - group B: trials 0-19 (cond 1) = L2s02..L2s21; trial 20 (cond 2) = L1s01; trials 21-40 = L1s02..L1s21.
  - The trials 21-40 of one group are exactly trials 0-19 of the other (same envelopes, same lengths). The extra
    second-half trial (index 20) has no counterpart: it is segment 1 of the second-half lecture, i.e. **the first
    trial of the experiment was dropped, but the trial right after the switch was kept**. The paper excluded both
    ("40 trials analysed"; README also says 40); the shipped data have 41 (inference from the ordering; the s01
    numbering assumes the dropped trial is the very first segment, which the paper's exclusion rule implies).
- Four subjects have 40 trials (undocumented), each missing a different trial:
  - sub 13 (A): no L1s02 (the first trial of the first half).
  - sub 14 (B): no L2s02 (the first trial of the first half).
  - sub 22 (B): no L1s21 (the last trial).
  - sub 24 (B): no L2s14 (first-half trial 12).
  The adaptor should map trials by envelope content (or by matching to the group reference sequence), never by
  position.
- **`stim.condIdxs` is one entry short in subjects 13, 14 and 24** (39 entries for 40 trials: 19 x 1 then 20 x 2,
  while the data hold 19 first-half and 21 second-half trials); in sub 22 it has 40 entries and is correct. Found
  while writing the adaptor. Mapping by position through `condIdxs` silently drops the last trial (L?s21) of
  these three subjects. The adaptor takes the half from content instead (the first trial's lecture is the
  first-half target) and checks it against `condIdxs` where the lengths agree (20 subjects).

## 4. Speech features available
- Only the authors' envelopes at 100 Hz: broadband envelope from 20 bands equally spaced on the Liberman cochlear
  map between 100 and 10000 Hz, |Hilbert| per band, summed, downsampled to 100 Hz (paper, "EEG preprocessing and
  speech tracking"). Arbitrary scale; small negative values occur (resampling). Spectrum: no high-pass (flat down
  to 0.4 Hz), falls ~38 dB from 1 Hz to 49 Hz.
- Each envelope is already cut to the trial window (same length as the EEG trial, see section 6), so it is a
  per-trial excerpt, not the full segment. Because the cut of a segment is the same for every subject, one shared
  stimulus per segment and role is safe (no `data_fn` collision).
- No audio, no video (the target is audiovisual), no transcripts or word/phoneme annotations. Not found anywhere
  public (OSF has only `dataCND`; the paper has no availability statement).

## 5. Neural data
- BioSemi ActiveTwo, 64 scalp channels, recorded at 2048 Hz (paper). Two mastoid electrodes as reference; four EOG
  electrodes; on-ear microphone audio was also recorded (paper: "outside the scope"). **Only the 64 scalp channels
  are shared**: no mastoids, EOG, microphone or trigger channel.
- Preprocessing before sharing (README + paper; the README matches the paper): re-referenced to linked mastoids,
  0.5-40 Hz 4th-order zero-phase Butterworth, gross artefacts removed by visual inspection, ICA (eye movements,
  heartbeat), noisy channels interpolated (`ft_channelrepair`), cut into trials, **1-20 Hz** zero-phase Butterworth
  ("1-second padding"), downsampled to 100 Hz. Confirmed in the data: EEG PSD drops ~25 dB from 10 to 25 Hz and
  ~23 dB from 2 Hz to 0.6 Hz, so the shipped data are the 1-20 Hz stage.
- Units as shipped: µV (inferred: channel SD 2.5-16 per subject after 1-20 Hz, 99.9th percentile of |x| 20-87,
  max 45-357). Scale by 1e-6 to V. No NaNs, no flat channels; the four subjects with 40 trials are not otherwise
  odd. Not average-referenced (mean over channels is ~half the channel SD).
- Channels: BioSemi 64 (10-20 names). Four labels need renaming to MNE `standard_1005`: `T7 (T3)` -> `T7`,
  `T8 (T4)` -> `T8`, `Iz (inion)` -> `Iz`, `Afz` -> `AFz`; then all 64 are in `standard_1005`. Same order and labels
  in every subject. Opens as an MNE `RawArray` (64 x n, 100 Hz) without problems.
- Positions: `chanlocs` is the same idealised spherical template for every subject (not digitised); its directions
  differ from `standard_1005` by 20 deg (median). No head-shape digitisation.

## 6. Alignment
- **No triggers or stimtrack shipped.** The paper does not describe triggers (presentation in OpenSesame, video +
  audio via loudspeakers); trigger type **unknown**. The authors aligned S and R ("aligned in time") before sharing.
- In all 939 trials the EEG has exactly as many samples as both envelopes. So trial durations were set by the
  authors from the stimulus, and carry no independent timing information.
- **Trials start 5 s after the target onset (inferred).** The paper drops the first 5 s of every trial (target
  onset, non-target onset at 3 s and its 2 s ramp). Evidence that the shared trials are already cut: trial
  durations are 18.25-30.39 s (mean 25.4 s) while the segments are 22-40 s (means 31.8 and 30.7 s); the
  non-target envelope has neither 3 s of silence nor a ramp at the start (first second at ~1.1 x its median
  level, like the rest). Where each trial ends relative to the target offset is **unknown** (the last second of
  both envelopes is usually still speech).
- Independent check of the alignment, all 23 subjects: cross-correlation of the half-wave rectified envelope
  derivative with the EEG (RMS over channels, lags -4..+4 s, per half and stream). Grand-average peak at +70 ms
  (target, both halves) and +90 ms (non-target, both halves); nothing at +-3 s (main peak 1.8-2.4 x the largest
  peak outside -0.5..1 s). So both envelopes are sample-aligned with the EEG as shipped, and the non-target
  envelope already includes its 3 s delay. Per subject the peak is in 0-400 ms for 12-17 of 23 (short, 1-20 Hz
  data).
- Proposed: take trials as shipped, stimulus onset = sample 0 of the trial (`alignment_method` = `none`, i.e. the
  authors' alignment; `trigger_type` = `unknown (not described; OpenSesame)`; `jitter_ms` = null; no drift
  correction).
- Plausible validation tier: **`low` only** (100 Hz, 1-20 Hz, envelopes at 100 Hz). MLR and brainstem tiers are
  impossible with these data.

## 7. Cross-subject duration check
- Not possible: no triggers, and EEG trial lengths equal the envelope lengths by construction in all 939 trials.
  Drift and jitter cannot be estimated. For scale: with trials <= 30.4 s, 50 ppm of drift would be 1.5 ms, well
  below one 10 ms sample. Onset jitter of video/audio playback in OpenSesame is unknown.

## 8. Data size
- 23 participants, 939 trials (19 x 41 + 4 x 40), 6.62 h in total; 0.288 h (17.3 min) per participant, range
  16.9-17.4 min. Per half: first ~8.5 min, second ~8.9 min. The two talkers are simultaneous (counted once).
  These are the recorded (shared) durations: the first 5 s of each trial and the dropped first trial are not
  included (the full experiment would be ~42 x ~31 s = ~22 min).

## 9. Upstream issues
- README: "40 trials"; shipped are 41 trials for 19 subjects (incl. the trial after the talker switch that the
  paper excluded) and 40 for subjects 13, 14, 22, 24, each missing a different, undocumented trial.
- README: "`stim.names`: Target and Non-target"; there is a third row, 'All features' (both columns).
- `stim.stimIdxs` is the trial position, not a stimulus identifier; there is no segment or lecture/talker label.
- `stim.condIdxs` has one entry too few in subjects 13, 14 and 24 (section 3).
- No licence on the OSF project.

## 10. Open questions (recommended defaults in brackets)
1. Licence unknown (none on OSF). [Standardise for internal use, record licence `unknown (none on OSF; article CC BY
   4.0)`; ask the authors before redistributing.]
2. Sample rate: the default 1000/1024 Hz cannot apply. [Keep 100 Hz as shipped, no upsampling; envelopes stay at
   100 Hz.]
3. Stimulus type: envelopes only. [`feature_name` describing the authors' envelope (e.g. `envelope_authors_100Hz`);
   two stimuli per trial, `target` and `nontarget`, both starting at trial sample 0; skip 'All features'.]
4. Stimulus naming: by segment, identified by content. [`L1s02`...; non-target named by its pairing, e.g.
   `L1s02_nontarget`, or by its own segment `L2e02`; derive the table from subjects 1 (group A) and 2 (group B).
   L1/L2 talker sex unknown: leave unlabelled.]
5. Trial after the switch (index 20, segment s01 of the second-half lecture), excluded in the paper but shipped.
   [Keep it, flagged in the trial notes as "first trial after the talker switch; excluded in the paper".]
6. Conditions: first half vs second half; also attended lecture L1/L2 and group A/B. [Condition = `first_half` /
   `second_half`; record target lecture and group in the trial metadata; validate per half and per stream.]
7. The 5 s cut at the trial start is inferred, not documented. [Accept; state in the provenance notes that trial
   sample 0 is ~5 s after target onset and ~2 s after non-target onset.]
8. Reference and channels: linked mastoids, mastoids not shipped. [Keep as shipped, record the reference as
   `linked mastoids (applied by the authors; mastoid channels not shared)`; rename the four labels; use
   `standard_1005` positions, noting they are template positions.]
9. Raw 2048 Hz BDF data, audio, video, triggers and microphone channels are not public. [Proceed with the CND
   release; optionally ask the authors (corresponding author listed in README) for raw data and audio, which would
   allow higher validation tiers and a real alignment check.]
   Decided by the user (2026-11-21): standardise the CND release with the authors' envelopes.

## 11. Adaptor (implemented with the defaults of section 10)
- Segment table built at parse time from subjects 1 (group A) and 2 (group B), keyed on an MD5 of the
  (target, non-target) envelope pair; the two reference subjects must agree on the 20 shared segments and give 42
  distinct pairs, otherwise the adaptor raises. Every trial of every subject must hit the table.
- Stimuli: `L<l>s<k>` (target, attended) and `L<other>e<k>` (non-target), feature `envelope` (renamed from
  `envelope_authors_100Hz` on 2026-11-22: the validator and other tools only take `audio`/`envelope`; broderick2019
  also uses `envelope` for authors' envelopes),
  `{"fs": 100, "data": (1, n)}` float32, both starting at trial sample 0. 'All features' is skipped.
- Trial number = experiment trial: first half s02..s21 -> 2..21, second half s01..s21 -> 22..42 (trial 1 was
  dropped by the authors). Condition `first_half` / `second_half`.
- EEG: 64 x n at 100 Hz, scaled 1e-6 to V, labels renamed, `standard_1005` template positions. Per-trial provenance
  (alignment_method `none`, trigger_type unknown, group, target lecture, segment names, shipped trial index, notes
  incl. the post-switch flag on trial 22) is stored as JSON in `raw.info["description"]`.
- Pilot (all 23 subjects): 939 trials (19 x 41, 4 x 40), 6.62 h, 84 envelope files, all at 100 Hz, durations
  18.25-30.39 s (mean 25.39 s); EEG and both envelopes have equal lengths in every trial; groups and missing
  trials as in section 3. No trial uses a fallback alignment (all `none`).

## 12. Timing check: match-mismatch DNN offset (2026-11-22, note only)
The `fs128_1020-64_broadband` classifier (trained on accou2023; `cnsp_datasets.align.scan.lag_scores`, script
`tmp/review/scripts/dnn_offsets.py`) scored 5 s windows of 100 random trials over stimulus lags of +-500 ms, with
the target (attended) envelope. Offsets are relative to accou2023 (self-check +0.6 ms); negative = neural response
later than in accou2023.

| set | subjects / trials | offset | 95% CI (bootstrap over subjects) |
|---|---|---|---|
| all trials | 23 / 100 | -15.6 ms | -22.5 .. -10.7 |
| first half | 23 / 100 | -20.7 ms | -25.4 .. -15.5 |
| second half | 23 / 100 | -18.5 ms | -26.6 .. -13.9 |

Both halves agree, and the pooled lag scan has a single sharp peak with accou2023's side-lobe shape. The size is
what a response-latency difference alone gives: competing speech and speech in noise score about -15 ms in other
datasets even with measured onsets (PLAN.md 4b), and here the regressor is the authors' 100 Hz envelope of 1-20 Hz
filtered EEG, not a Hilbert envelope of audio. So this is not evidence of a trial-cut error; the cut is not
changed. A constant cut error of a few tens of ms cannot be excluded either (no triggers or audio; section 6).

## 13. Validation (2026-11-22) and tooling gaps
- Tier **`low`** (`validation.json`), average reference (applied by the validator; shipped as linked mastoids).
  Forward (repo validator, attended): median r 0.0137, 12/23 above both nulls; ignored 0.0094, 8/23; attended >
  ignored 15/23 (Wilcoxon p = 0.045). Backward: attended 0.049, ignored 0.031, attended > ignored 20/23
  (p = 2.4e-4), decoding accuracy 0.70 per trial (0.55-0.85). Lag sweep (31.25 ms steps) peaks at 0 s for both
  streams, overall and per half.
- Subjects 3, 4, 15, 16, 23 fail both forward nulls (attended, all trials); 3, 7, 12 have backward r ignored >=
  attended.
- Validator gaps found:
  1. `cnsp_datasets.validate` has no backward model and no backward nulls. The backward results come from the
     review script `tmp/review/scripts/harshaiyahav2025_backward.py` (port of `narayanan_labels.py`), without a
     null distribution.
  2. `pick_stimulus` only accepts the features `audio` / `envelope`. Resolved here by renaming the feature from
     `envelope_authors_100Hz` to `envelope` (2026-11-22, section 11).

## 14. Coherence (2026-11-22)
EEG-envelope coherence (average reference, 5 s Hann windows, 4 s overlap; one global circular-shift surrogate per
trial; per-subject complex average, then complex average over subjects, |.|, channel mean;
`tmp/review/scripts/coherence_batch.py`). The data are 100 Hz, so the 128 Hz and native analyses are identical (no
upsampling). Ratio to the surrogate per band, 23 subjects:

| stream | 0.2-1 Hz | 1-4 Hz | 4-8 Hz | 8-15 Hz | 15-30 Hz |
|---|---|---|---|---|---|
| attended (target) | 2.30 | 1.77 | 1.92 | 1.47 | 1.08 |
| ignored (non-target) | 2.04 | 1.66 | 1.61 | 1.16 | 1.10 |

Coherence is above the surrogate up to ~15 Hz (the authors' 1-20 Hz filter), attended > ignored above 4 Hz.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**medium**: Authors' CND trials, no triggers/audio; DNN -15.6 ms attributed to competing-speech response latency, not a cut error; lag sweep peaks at 0; low tier.

## Restructure 2026-11-25 (not yet re-validated on data)
- BaseAdaptor only (no other change).
