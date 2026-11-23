# piazza2025: stories in three speech registers, L2 learners and native listeners (OSF ba3p4, CND)

50 participants (25 Spanish-L1 learners of English "L2L", 25 native English listeners "L1L") heard three stories,
each in five ~3 min parts, one story per speech register (L2 Accommodation "L2A", Native Directed Speech "NDS",
Slow-NDS), all in +16 dB multi-talker babble. 64-channel EEG shared **preprocessed: 1-8 Hz, 100 Hz** in CND
`.mat` files, from **two EEG systems** (L2L BrainVision at 1000 Hz, L1L BioSemi at 1024 Hz). The wavs as played
for NDS and Slow-NDS; L2A only as the authors' 100 Hz features. No raw EEG, no triggers. Standardised as two
datasets, `piazza2025_l1l` and `piazza2025_l2l` (shared code in `piazza2025_base`).

## 1. Source
- OSF project ba3p4 (https://osf.io/ba3p4/), "Are you talking to me? How the choice of speech register impacts
  listeners' hierarchical encoding of speech", public, last modified 2026-02-10. 162 files, 7.63 GB; no
  components. Downloaded 2026-11-23 with the registry entry `piazza2025` (osf); all 162 files matched OSF's size
  and md5.
- **Licence: unknown.** The OSF node has no licence (`node_license: null`); the readmes name none. The paper is
  CC BY 4.0, which covers the article only.
- Paper: Piazza G, Carta S, Ip EYJ, Pérez-Navarro J, Kalashnikova M, Martin CD, Di Liberto GM (2025). Are you
  talking to me? How the choice of speech register impacts listeners' hierarchical encoding of speech. *Imaging
  Neuroscience* 3, imag_a_00539, doi:10.1162/imag_a_00539 (`data_campaign/papers/piazza2025.pdf`).
- Shared code: `.mat Files/forwardTRF.m` (the CNSP forward-TRF example adapted to this dataset), R analysis
  scripts, stimulus statistics script. Read, not run.

## 2. Layout
- `data_CND/{L1L,L2L}/pre_dataSub<N>.mat` (N = 1-25): `eeg.data` {1 x 15 (13 for L2L 16)} of [samples x 64]
  float64, `eeg.fs` = 100, `eeg.deviceName` ('Biosemi' / 'BrainVision ActiCap'), `eeg.processingPipeline`
  ('Load', 'LPF', 'HPF'), L2L also `eeg.originalFs` = 1000. L1L files carry `eeg.chanlocs`; **L2L files have no
  channel labels**: the order is in `L2L/chanlocs64Brain.mat` (L1L: `L1L/BioSchanlocs64.mat`, same as the files).
- `data_CND/{L1L,L2L}/dataStim<N>.mat`: `stim.data` {12 x 15} at 100 Hz, rows `stim.names`: acoustic envelope,
  phonetic features (19), spectrogram (8 bands), surprisal, word onset, entropy and combinations, plus a shuffled
  surprisal control. `stim.condNames` = FDS, NDS, Slow_NDS (FDS = L2A, `.mat Files/ReadMe_.txt`),
  `stim.stimNames` = HOLE, Love, Guerrilla; `stim.condIdxs` / `stim.stimIdxs` give register and story per
  column, in blocks of five parts.
- `STIMULI/Audio/<Story>_{NDS,Slow_NDS}_p<k>_16dB.wav`: 30 wavs, 44.1 kHz mono int16 (speech + babble as
  played). **No L2A wavs.** Also rise-time tables and stimulus statistics (xlsx, R).
- `data_CND/ReadMe.txt`: "minimally preprocessed: interpolation of bad channels, bandpass filter at 1-8Hz,
  downsampled at 100 Hz"; lists the participants with fewer trials.
- `.mat Files/`: the authors' TRF weights (surprisal + envelope); `R analysis/`: per-subject metrics.

## 3. Stimulus <-> trial mapping (verified by trial length and by EEG)
Design (paper 2.4): each participant hears each story once and each register once (Latin square over story and
register), each story in five consecutive parts with comprehension questions after each part. The stim files'
columns are in presentation order; the EEG trials are in the same order.

- **The stim files are only relabellings**: each of the 45 (story, register, part) envelopes is byte-identical
  in every stim file that contains it (750 columns checked). The two groups use the same stimuli.
- **EEG trial length identifies the stimulus.** Every EEG trial is longer than its envelope by 92-100 samples
  (epochs end ~1 s after the audio; section 7). Per subject, the trial lengths fit exactly one of the nine
  register x story orders actually used (36 tested), for all 50 subjects.
- **Stim files of L1L 13, 14 and 15 do not belong to their EEG.** Their labelled orders give envelope lengths
  thousands of samples off the EEG. The length-derived designs are those of `dataStim14`, `dataStim15` and
  `dataStim16` (shifted by one). Independent check, leave-one-trial-out forward model (0-500 ms, mean r over
  channels): length-derived vs stim-file mapping 0.035 vs 0.004 (L1L 13), 0.049 vs -0.006 (L1L 14), 0.013 vs 0.011
  (L1L 15, a weak subject); controls L1L 12 and 16 are identical under both. The authors' `forwardTRF.m` uses
  `dataStim<N>` for `pre_dataSub<N>`, so their L1L 13-15 results probably used the wrong envelopes (section 9).
- Trial identity across all subjects: predicting each trial with each of the 45 envelopes (LOO TRF), the assigned
  envelope wins in 33% of trials (chance 2.2%; L1L 30%, L2L 36%), `checks/per_subject_peak_and_identity.png`.
- **Missing and placeholder trials** (readme, confirmed): L1L 4 trials 1-2, L1L 17, 19, 20 trial 1 and L2L 19
  trial 3 are 98-sample placeholders (failed recordings); L2L 16 has 13 trials, NDS parts 2-3 missing. Skipped.
- Records: `trial` = presentation position 1-15 (positions of missing trials are skipped, not renumbered),
  `condition` = register, story/part/register in the provenance. 370 (L1L) + 372 (L2L) trials.

## 4. Speech features available
- NDS and Slow-NDS: the wavs as played (speech + babble mixed at +16 dB; 44.1 kHz). Their Hilbert envelopes match
  the authors' envelopes at lag 0, r = 0.92-0.96 for all 30 parts (`checks/wav_vs_env.json`), so the wavs start
  at the same sample as the authors' features.
- L2A: only the authors' 100 Hz features. The adaptor stores the authors' acoustic envelope (`feature_name =
  'envelope'`, name `<Story>_L2A_p<k>`).
- No clean speech or babble track; no transcripts or TextGrids. Model-derived features (phonetic features,
  surprisal, entropy, word onsets, 100 Hz) are in the stim files but not standardised (off by default).
- Slow-NDS is NDS time-warped (dynamic time warping) to the L2A speech rate, so its part durations are close to
  L2A's: L2A minus Slow-NDS is 0-12 samples (100 Hz) for 11 of 15 parts, 29-52 for HOLE p1, Love p1 and
  Guerrilla p2, and 661 (6.6 s) for HOLE p4. These parts are what makes the design fit unique between L2A and
  Slow-NDS (swapping the two registers always changes one of them); the EEG identity checks agree.

## 5. Neural data
- 64 EEG channels, no EOG, no mastoids, no peripherals in the shipped data. Units µV (std ~5-20 µV), scaled to V.
- **L1L (experiment 2)**: Trinity College Dublin, BioSemi ActiveTwo, 64 ch at 1024 Hz; an external left-earlobe
  electrode "for offline referencing" (not shipped). Labels renamed `T7 (T3)` -> T7, `T8 (T4)` -> T8,
  `Iz (inion)` -> Iz, `Afz` -> AFz.
- **L2L (experiment 1)**: BCBL, two actiCAP 64-channel systems with BrainAmp DC, 0.05-500 Hz, 1000 Hz, online
  reference left earlobe (hardware).
- **L2L channel order: known for subjects 1-5 only.** The L2L EEG files carry either nothing (1, 18, 20-22), a
  generic FieldTrip plotting layout (`chanlocs.label`, 64 labels sorted front to back incl. FT10 but no Iz, plus
  COMNT/SCALE; 2-5, 7-17) or the EEGLAB labels of `chanlocs64Brain.mat` (6, 19, 23-25). Test: for each channel, is
  its most-correlated channel (average reference) among its 4 nearest standard_1005 neighbours under a labelling
  (`scripts/piazza2025_l2l_order.py`, `checks/l2l_channel_order.json`)? Correct labellings score 0.92-0.98 (L1L
  with BioSemi labels) and random ones 0.03-0.10.
  - `chanlocs64Brain.mat` order: 0.97-1.00 for L2L 1-5, 0.08-0.22 for L2L 6-25 (also for 6, 19, 23-25, whose own
    embedded labels are these).
  - The FieldTrip layout order, the L1L BioSemi order and the standard actiCAP 64 order: 0.00-0.20 for 6-25.
  - Matching each subject's correlation matrix to L2L 1-5 by quadratic assignment (`scripts/piazza2025_l2l_qap.py`)
    suggests a row-wise name-sorted order for 6-25 (Fp1 Fp2, AF3 AF4 AF7 AF8 AFz, F1-F8 Fz, ...). The best explicit
    version (`consensus_like` in `checks/l2l_sorted_orders.json`: rows sorted, Fpz after Fz, FCz before FC1,
    TP9/TP10 last) scores 0.69-0.83 for all of 6-25: close, not exact, and partly derived from the same data.
  - So the order of L2L 6-25 is unknown. The adaptor names their channels E01-E64 (file order) without positions
    (`channel_order_known: false` in the provenance); the envelope validation does not depend on labels.
- **Reference of the shipped data**: L2L left earlobe (paper); L1L unknown (not stated whether the earlobe
  reference was applied before sharing). Not average-referenced: the across-channel mean has ~0.85 of the mean
  channel std in every subject.
- **Preprocessing**: 1-8 Hz band-pass (zero-phase Butterworth per paper), resampled to 100 Hz. The readme says bad
  channels were interpolated. Interpolated channels are exact linear combinations of others, so they show as
  near-zero singular values (< 1e-4 of the largest; `checks/rank_deficiency.json`, `checks/interpolated.json`):
  L1L 20 (3), L2L 1, 5, 10 (1 each), L2L 12, 14 (2 each); full rank in the other 44 subjects. Which channel was
  interpolated is not identifiable (every channel of the dependent set fits exactly). No flat or NaN channels.
  `info['bads']` left empty (the interpolated channels hold no raw signal, but are not flat or noise).
- Template positions (standard_1005); no digitisation.
- Rate: 100 Hz kept (native shipped rate, never upsampled). Only the low tier can be tested.

## 6. Alignment
- Triggers: PsychoPy 2021 (v2.3) sent a trigger at the start of each trial "with contingent stimulus
  presentation" (paper 2.3), i.e. software triggers. Hardware/latency not described; triggers not shipped.
- The authors epoched at the trigger: EEG sample 0 = audio sample 0. Their `forwardTRF.m` cuts EEG and stimulus
  to the same length from sample 0 (`cndCutSameLength`); its "remove initial padding" block is commented out.
- Confirmed per subject: forward TRF of the envelope at lags -1 to +2.5 s peaks at 0-270 ms in 48 of 50 subjects
  (L1L 16 and L2L 19 have no clear peak: weak tracking), GFP flat at negative lags
  (`checks/wide_trf_gfp_per_subject.png`). Pooled envelope-EEG cross-correlation peaks at +120 ms (L1L 1) and
  +140 ms (L2L 1).
- **Proposed alignment: as shipped** (`alignment_method = sw_trigger`, onset = EEG sample 0). No correction is
  possible or proposed: no triggers, no raw recordings, no audio channel.
- Drift: not estimable (section 7). `drift_ppm = null`.

## 7. Cross-subject duration check
EEG trial length minus envelope length (samples at 100 Hz; `scripts/piazza2025_*`):
- L2L: 99-100 in every trial: epochs are stimulus duration + 1.00 s.
- L1L 9-25: 97-99. L1L 1-8: 92-97, and identical per stimulus across subjects with the same design (e.g. L1L 1 and
  2, L1L 5 and 8), so deterministic, not jitter: these epochs were set from durations 30-80 ms shorter than the
  shipped stimuli (perhaps an earlier stimulus version or a different duration source). Their TRF peaks are at
  normal latencies (50-160 ms, except L1L 5, 450 ms), so the onsets are unaffected as far as 100 Hz data show.
- No slope with trial length (Theil-Sen 0 ppm in both groups), but the epoch lengths are set by the authors, so
  this says nothing about drift.

## 8. Data size
Estimated from the stimulus durations of the trials present (L2A from the envelope length):
- All: 50 participants, 33.94 h; 40.7 min per participant (range 34.4-42.3).
- L1L: 16.93 h, 40.6 min (34.4-42.3). L2L: 17.01 h, 40.8 min (36.6-42.3).
- Per register: L2A 12.47 h (15.0 min/participant), NDS 9.06 h (10.9 min), Slow-NDS 12.41 h (14.9 min).
- Unique audio 2.05 h (L2A 45.2 min, NDS 33.0 min, Slow-NDS 45.1 min).

## 9. Upstream issues
- **L2L 6-25 channel order unknown**: `chanlocs64Brain.mat` fits only L2L 1-5; the labels embedded in L2L 6, 19,
  23-25 are the same (wrong for them); the FieldTrip layout in other files is a generic plotting layout (section 5).
- `L1L/dataStim13-15.mat` do not match `pre_dataSub13-15.mat` (section 3); the matching designs are those of
  `dataStim14`, `dataStim15` and `dataStim16`.
- L2L EEG files carry no channel labels (order only in `chanlocs64Brain.mat`).
- No L2A audio shared (only 100 Hz features), and no licence on the OSF node.

## 10. Open questions (recommended defaults in brackets)
0. L2L 6-25 channel order: ask the authors for the order of each file, or adopt the data-derived order?
   [Neutral names E01-E64 without positions until the authors answer.]
1. Two datasets (`piazza2025_l1l`, `piazza2025_l2l`) or one with renumbered subjects? [Two: different EEG
   systems, labs and populations; keeps the original subject numbers, like jehn2025 / yang2026.]
2. Use the length-derived mapping for L1L 13-15 instead of the shipped stim files? [Yes; flagged per trial as
   `stim_file_mismatch`.]
3. NDS/Slow-NDS as wav, L2A as the authors' envelope (PLAN: audio where available)? Or also store the authors'
   envelope for NDS/Slow-NDS so all registers have the same feature? [Wav only, per PLAN; the envelope could be
   added as a second stimulus if register comparisons need one feature type.]
4. Standardise the authors' model-derived features (phonetic features, surprisal, word onsets)? [No, off by
   default per the rules.]
5. Licence unknown: ask the authors? [Record as unknown; the user decides.]

## 11. Adaptor
`piazza2025_base/adaptor.py` (`Piazza2025Adaptor(download_dir, group)`), wrapped by `piazza2025_l1l` and
`piazza2025_l2l`, with the defaults of section 10.
- Per subject: the design from the EEG trial lengths (`_design`), compared with the stim file's labels
  (`stim_file_mismatch`); the L2A envelopes are read once from stim files whose labels fit their EEG.
- Channel labels: L1L from `BioSchanlocs64.mat` (equal to every L1L file's own `chanlocs`, checked in the first
  pilot run); L2L 1-5 from `chanlocs64Brain.mat`; L2L 6-25 E01-E64 without montage (section 5).
- EEG: 64 ch, µV -> V, 100 Hz, standard_1005 template montage, the authors' epochs unchanged (not cut to the
  stimulus). Provenance: `sw_trigger`, reference, story, register, part, shipped trial index.

## 12. Validation (2026-11-23, all 50 subjects)
Low tier only (100 Hz, 1-8 Hz shipped; mlr and brainstem not applicable). Repo validator, forward model 0.5-8 Hz,
**average reference**; NDS/Slow-NDS from the wavs' envelope, L2A from the authors' envelope. Per-condition runs
with `scripts/piazza2025_run.sh`. Results in `R/piazza2025/validation_<group>[_<register>]/`.

| set | trials | mean r | subjects > nulls | TRF GFP peak | pass |
|---|---|---|---|---|---|
| L1L pooled | 370 | 0.025 | 23/25 | 62 ms | low |
| L1L L2A / NDS / Slow-NDS | | 0.024 / 0.018 / 0.022 | 16 / 10 / 14 | 62 / 78 / 62 ms | low |
| L2L pooled | 372 | 0.032 | 21/25 | 156 ms (peaks ~60, 155, 240 ms) | low |
| L2L L2A / NDS / Slow-NDS | | 0.033 / 0.028 / 0.025 | 19 / 14 / 16 | 156 ms | low |

- Population p (circular shift / mismatched trials) 0.020 / 0.048 in every set (the validator's minimum).
- TRFs are at the noise floor at negative lags in both groups (`validation_l1l/validation.png`,
  `validation_l2l/validation.png`). Below the nulls: L1L 16 (r -0.006, no TRF peak in the wide-lag check), L1L 2 and
  25 near the null; L2L 10, 19, 21, 22.
- The relabelled L1L 13 and 14 score 0.027 and 0.053 (L1L 14 is the best L1L subject), supporting section 3.
- Validator jitter and drift estimates are noise at these r values and say nothing about timing.
- Not done: DNN timing check (the accou2023 classifier's preprocessing does not match 1-8 Hz, 100 Hz data) and
  coherence.
- A first pilot (moved to `R/piazza2025/v1/`) had standardised only L2L 1, 6, 18-25: L2L files embed different
  `chanlocs` structures and the old in-loader label check failed; fixed. L1L results were identical.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
- piazza2025_l1l: **medium**: Authors' 100 Hz epochs at the PsychoPy (software) start trigger; per-subject TRFs peak 0-270 ms, flat at negative lags; drift not estimable; low tier.
- piazza2025_l2l: **medium**: As piazza2025_l1l; low tier (21/25).
