# karunathilake2023_aging: aging and continuous speech in noise, KIT MEG (DRUM, DSS components only)

Explorer notes (2026-11-22). Scripts: `tmp/review/karunathilake2023_aging/scripts/` (listed per finding).
Nothing below has been changed in the data; decisions for the human checkpoint are in section 8.

## 1. Source
- Data: DRUM (University of Maryland) item `91b2c409-8659-40fe-87dd-b701599b4841`,
  hdl `1903/29748`, DOI **10.13016/4goq-vs0z**. This is the DOI given in the paper's "Code and Data
  Availability" statement (the DOI resolves to `drum.lib.umd.edu/handle/1903/29748`, and the item's
  `dc.identifier` is the same DOI), so there is no second record.
- Licence: **CC0 1.0** (`dc.rights`).
- Paper: Karunathilake IMD, Dunlap JL, Perera J, Presacco A, Decruy L, Anderson S, Kuchinsky SE, Simon JZ (2023).
  Effects of aging on cortical representations of continuous speech. J Neurophysiol 129:1359-1377,
  doi:10.1152/jn.00356.2022. (`tmp/papers/karunathilake2023-aging.pdf`; `karunathilake2023.pdf` in the same
  folder is a different paper.)
- Files (ORIGINAL bundle, all downloaded, MD5s match DRUM): `Data.zip` (820,057,273 B), `MEG Analysis.zip`
  (MATLAB: `TRF.m`, `reconstruction.m`, `boosting.m`, `dss0.m`, `megtopoplot.m`, helpers,
  `predictors/Aging_TRF_250.mat`, `predictors/Aging_env_100_110_log.mat`), `Statistical Analysis.zip` (R
  notebooks + xlsx of behaviour, TRF peaks), supplemental PDF (LMM tables).
- **No raw or sensor-level MEG is shared** (bundle listing checked through the DRUM REST API; a DRUM search for the
  author finds only dissertations and a related connectivity article, no other dataset).

## 2. Layout
- `Data/MEG/{Younger,Older}/R####_todss.mat` (100 Hz) and `R####_todss_250hz.mat` (250 Hz), MATLAB v5, one pair
  per subject. Variables: `dss_solo` (trials x time x 6), `dss_mix` (12 x time x 6), `dss_babble` (3 x time x 6),
  float64. time = 6000 (100 Hz) or 15000 (250 Hz): 60 s arrays.
- `Data/stimuli/*.wav`: 15 mono int16 wavs at 22,050 Hz (section 3).
- `Data/TRFs/R####_{Q,0,6}.mat`: authors' TRFs (`TRF_FG` 10 folds x 125 lags, `cor`); `Data/Rec/`: 2507
  reconstruction results (decoders per integration window). Results only, not needed by the adaptor.
- `MEG Analysis/predictors/`: authors' envelopes (`env_mix_fg`, `env_mix_bg` 12 rows; `env_bab_FG`, `env_bab_BG`
  3 rows), 6000 samples (100 Hz) / 15000 (250 Hz). Rows repeat per presentation (rows 1-3 identical, etc.).
- The 100 Hz and 250 Hz files hold the same signal: the 250 Hz data resampled to 100 Hz correlate r = 1.0000 with
  the 100 Hz data in every trial of every subject (`survey.py`). **Use the 250 Hz files**; the 100 Hz files are
  redundant.

## 3. Stimulus <-> trial mapping (verified)
Design (paper, Methods "Stimuli and Experimental Design"): Legend of Sleepy Hollow, male and female LibriVox
narrators, 60 s passages, diotic, insert earphones. Four competing-talker blocks (attend M / F x SNR 0 / "6" dB,
order counterbalanced), each mixture presented 3 times, followed by the block's two talkers alone once each;
babble block (always 3rd): F08 + three-talker babble, 3 presentations, then F08 alone.

Mapping in the shared arrays (same for every subject; arrays are ordered by condition, **not** in presentation
order; presentation order per subject is unknown). Verified two ways: (a) the comments and indexing in
`reconstruction.m`/`TRF.m`, (b) independently, by cross-correlating each trial's DSS components with the envelope of
every wav and averaging over all 34 subjects (`map_trials.py`): every row's best match is the listed wav.

| array row | condition | played wav | attended | unattended |
|---|---|---|---|---|
| mix 1-3 | 0 dB, attend male | pass_mix_M0_M08_F10 | pass_single_M08 | pass_single_F10 |
| mix 4-6 | -6 dB, attend male | pass_mix_M6_M02_F04 | pass_single_M02 | pass_single_F04 |
| mix 7-9 | 0 dB, attend female | pass_mix_F0_F03_M01 | pass_single_F03 | pass_single_M01 |
| mix 10-12 | -6 dB, attend female | pass_mix_F6_F07_M05 | pass_single_F07 | pass_single_M05 |
| babble 1-3 | babble 0 dB, attend female | babb_mix_F08_BF08 | ~pass_single_F08 (see below) | babb_singleQ_BF08 (babble) |
| solo 1 | quiet | pass_single_M08 | | |
| solo 2 | quiet | pass_single_M02 | | |
| solo 3 | quiet | pass_single_F10 | | |
| solo 4 | quiet | pass_single_F04 | | |
| solo 5 | quiet | pass_single_F03 | | |
| solo 6 | quiet | pass_single_F07 | | |
| solo 7 | quiet | pass_single_M01 | | |
| solo 8 | quiet | pass_single_M05 | | |

- **The "6 dB" condition is -6 dB SNR (attended 6 dB softer)**: least-squares decomposition of each mixture into
  its two single-talker wavs is exact (residual 0.02 % rms) and gives fg/bg rms ratios of -0.08, +0.74 (0 dB) and
  -6.07, -6.01 dB ("6" dB) (`mix_snr.py`). The supplement's tables also say "-6 dB". In the female mixes the
  attended talker has gain 0.5 relative to its single wav (whole file scaled), so wav levels are not presentation
  levels (calibrated to 70 dBA, paper).
- **Babble**: `babb_singleQ_BF08` is the three-talker babble alone (gain 0.714 in the mix, constant in every 5 s
  window). The babble mix's foreground is **not sample-identical** to `pass_single_F08`: after subtracting the
  babble, corr with F08 = 0.956, envelope corr 0.91, windowed gains 0.72-1.10 (`babble_check.py`,
  `babble_fg.py`). It is the same passage at lag 0, probably rendered differently. The exact played foreground can
  be recovered as `babb_mix - 0.714 * babb_singleQ_BF08` (human decision, section 8).
- **The quiet F08 trial (end of the babble block) is not shared**: `dss_solo` has 8 rows (4 blocks x 2 talkers).
- **Six younger subjects (R2509, R2629, R2654, R2660, R2665, R2666) have a 9th `dss_solo` row that is junk**: it
  is byte-identical across all six subjects in both files (`solo9_identical.py`), ~2000x larger in scale than every
  other trial, and does not correlate with any of the subject's other trials. The authors' code uses rows 1-8 only.
  Drop it.
- Trials per subject: 8 quiet + 12 two-talker + 3 babble = 23. Same stimuli for every subject.
- Wav durations: 60.55-68.98 s (pass_*), 60.00 s (babb_*), `wavinfo.py`. The MEG covers only the first 58.5 s of
  each (section 6).

## 4. Speech features available
- Raw audio for every played stimulus and every stream (attended, unattended, babble), 22,050 Hz. No transcripts or
  word/phoneme annotations. Authors' log envelopes (1-10 Hz FIR-filtered, with the same 1.5 s delay as the MEG)
  in `predictors/` (not needed: compute our own from the wavs).

## 5. Neural data
- Modality: MEG, KIT 157 axial gradiometers, 3 reference magnetometers, 2 kHz, online 500 Hz low-pass and 60 Hz
  notch (paper, Data Recording). **Shared: only the first 6 DSS components per subject** (no sensors, no reference
  channels, no topographies, no head-shape digitisation, no trigger channels, no stimtrack). The 6 components are
  ranked by trial-to-trial reproducibility; component 1 is the auditory component (component 2 for R2594, paper and
  `TRF.m` line `if strcmp(subject,'R2594') ii=2`).
- Processing before sharing (paper, Data Processing; confirmed by the data): bad/saturated channels removed, TSPCA
  with the reference channels, SNS, **1-10 Hz FIR (fir1 order 6000, Hamming, at 2 kHz)**, DSS over trials,
  downsampled to 250 / 100 Hz. PSD of the shared 250 Hz data relative to its maximum (`psd.py`): 0-0.5 Hz -24 dB,
  0.5-1 Hz -12 dB, 1-10 Hz 0 to -5 dB, 10-12 Hz -18 dB, 12-15 Hz -71 dB, >20 Hz < -90 dB. So the files are
  already band-passed 1-10 Hz.
- Units: arbitrary (DSS projections, scale ~1e-3 per sample). Not physical; no conversion possible. Per-subject
  scale is comparable across trials (sd 0.0007-0.0015), except the junk 9th row.
- Polarity: the paper says the auditory component's sign was aligned across subjects; in the shared files the sign
  of component 1's 40-120 ms cross-correlation with the envelope varies across subjects (`polarity.py`), so either
  the flip was applied later in the pipeline or not stored. Irrelevant for envelope models but noted.
- Reference: not applicable (MEG; gradiometer data then DSS).
- MNE: there is no MEG file to open; the adaptor can wrap the components as a `RawArray` with 6 `misc` channels
  (`dss1`..`dss6`) at 250 Hz.
- Subjects: 18 younger (R2509, R2533-R2538 without R2537, R2552-R2556 without R2555, R2565, R2620, R2625,
  R2629, R2654, R2660, R2665, R2666) and 16 older (R2549, R2550, R2591, R2594, R2595, R2603, R2607, R2618, R2619,
  R2624, R2630, R2632, R2661-R2663, R2672), = the paper's 34 (two further subjects excluded by the authors for
  saturation, not shared). Every subject has both file types, and TRF results for Q/0/6. Ages are not in the MEG
  files; group only (paper: younger 18-26, older 65-78 yr).

## 6. Alignment
- Triggers: not shared, and the paper does not describe triggering or the stimulus delivery chain beyond the
  E-A-RTONE 3A tubes. Hardware vs software: **unknown**. Tube/acoustic delay: **unknown**, not mentioned as
  compensated.
- **Epoch timing (inferred from the data and the code)**: each array is 60 s long and starts **at stimulus onset
  before filtering**, but the 1-10 Hz FIR was applied causally, so every array is delayed by the filter's group
  delay: 3000 samples at 2 kHz = **1.5 s** = 375 samples at 250 Hz (150 at 100 Hz). Evidence:
  - the authors' envelopes match envelopes computed from the wavs only after a +1.50 s shift (100 Hz search,
    `env_match.py`); with a causal FIR applied to our own envelope the residual lag is -0.5 to -2.4 ms
    (`env_lag250.py`, recipe differences);
  - the MEG rms is ~0 at the array start and ramps up exactly like the predictor rms (same 100 ms bins),
    reaching full level at ~1.5 s; the end of the arrays has no ramp (`rms_course.py`). A zero-phase filter would
    give a ramp at both ends; an epoch starting before stimulus onset would show brain noise before the ramp;
  - the authors drop the first 1.5 s in both analyses (`beg = 376` at 250 Hz in `TRF.m`, `beg = 151` at 100 Hz in
    `reconstruction.m`, MATLAB 1-based);
  - with the stimulus placed at +1.5 s, component 1 tracks the envelope at plausible latencies: subject-averaged
    peaks at 50-70 ms (quiet, 0 dB) and 140-160 ms (-6 dB, babble) (`map_trials.py`); no subject peaks at a
    negative lag (`polarity.py`).
- Consequence: array sample 375 (250 Hz) = stimulus time 0; the array ends at stimulus time 58.5 s, so the last
  2.0-10.5 s of each wav were not shared (the trial was epoched to 60 s from onset). The first ~1.5 s after onset
  still carry the filter transient (input before onset was zero).
- Proposed alignment: drop the first 375 samples of each 250 Hz trial; onset = 0 s; neural trial = 14,625 samples
  (58.5 s). Stimuli are not cut (convention); the longer signal is cut at use. Onset uncertainty: the decimation
  phase of the authors' downsampling and any trigger/tube delay are unknown (expected < 1 sample at 250 Hz for the
  former; the latter unknown). The validator's lag sweep is the only check of the absolute onset.
- Drift correction: none possible and none needed in practice (no triggers or stimtrack; 58.5 s trials, typical
  10-35 ppm drift = 0.6-2 ms per trial, < 1 sample at 250 Hz).

## 7. Cross-subject duration check
- Not possible: every trial was cut to exactly 60 s by the authors; there are no trigger-derived durations, so
  drift and jitter cannot be estimated. Record `drift_ppm = null`, `jitter_ms = null`.

## Data size (recorded, not stimulus-length)
Stimulus-length counting would overestimate (wavs 60-69 s, only 58.5 s of MEG per trial after the delay), so the
recorded figure is used: 23 trials x 58.5 s per participant.
- 34 participants (18 younger, 16 older), **22.4 min each (all identical)**, **12.7 h total**.
- Per condition (per participant / total): quiet 8 trials 7.8 min / 4.4 h; 0 dB 6 trials 5.9 min / 3.3 h;
  -6 dB 6 trials 5.9 min / 3.3 h; babble 3 trials 2.9 min / 1.7 h. Each 0 dB / -6 dB / babble mixture is a
  repetition (3x the same audio), so unique audio is 4 mixtures + babble + 8 singles.
- Not added to `tmp/review/data_size.csv` yet (shared file; add with the adaptor run).

## Validation tiers possible
- Only `low` (backward model 0.5-8 Hz). The shared data contain nothing above ~12 Hz (-70 dB) and little below
  1 Hz, so `mlr` (30-60 Hz) and `brainstem` (30-250 Hz) tiers cannot be run. Inside `low`, the effective band is
  1-8 Hz. Six DSS components instead of sensors: the decoder has 6 inputs (as in the paper).
- Per condition: quiet, 0 dB, -6 dB, babble (attended and unattended envelopes). Leave-one-trial-out within
  subject works (8 quiet trials; 6 trials per SNR; only 3 babble trials, all the same audio, so cross-validation
  there is across repetitions of one stimulus, and the "mismatched-stimulus" null for babble must use other
  conditions' envelopes).

## Upstream issues
- Junk 9th `dss_solo` row in R2509, R2629, R2654, R2660, R2665, R2666 (identical across subjects, ~2000x scale).
- Paper calls the harder condition "6 dB SNR"; the stimuli are -6 dB (the supplement says -6 dB).
- `TRF.m` quiet branch uses `env1`..`env8`, which are not in `Aging_TRF_250.mat` (would not run as shipped).
- Shared files are the causally filtered (1.5 s delayed) epochs, which the paper describes as "compensated for
  group delay"; the compensation is only the later removal of the first 1.5 s.

## 8. Open questions (human checkpoint; recommended default in brackets)
1. Include the dataset at all, given it is component-level (6 DSS comps, 1-10 Hz, 250 Hz) rather than sensor MEG?
   [yes, flagged clearly as "DSS components, pre-filtered 1-10 Hz, `low` tier only"; ask the authors for sensor
   data separately]
2. Sample rate: the adaptor defaults target 1000/1024 Hz, but the data are 250 Hz and band-limited to 10 Hz.
   [keep 250 Hz; upsampling adds nothing]
3. Onset: drop the first 375 samples (1.5 s FIR delay) so t = 0 is stimulus onset? [yes; keep the 58.5 s that
   remain, including the first 1.5 s filter transient, and note it in the sidecar]
4. Babble foreground: use `pass_single_F08` (not sample-identical to what was played) or derive
   `babb_mix - 0.714 * babb_singleQ_BF08` as a new stimulus? [store the played mix and the babble track as
   shipped; for the attended stream use the derived foreground under a new name, documented; needs approval since
   it is a derived signal]
5. Drop the junk 9th solo row in the six younger subjects. [yes]
6. Condition labels: name the harder SNR "-6 dB" (stimuli) rather than the paper's "6 dB". [yes, with a note]
7. Component polarity / R2594: ship all 6 components as stored, without sign flips and without reordering for
   R2594. [yes; note that comp 2 is R2594's auditory component]
8. The quiet F08 trial and the presentation order are not shared; nothing to do. [note only]

## User decisions (2026-11-22)
- Include the dataset as DSS components (6 per subject, 1–10 Hz pre-filtered), **low tier only**, clearly flagged in the README.
- Keep the native 250 Hz files (no upsampling); drop the first 375 samples (1.5 s causal-FIR delay) so t = 0 is
  stimulus onset; keep 58.5 s per trial; drop the junk 9th `dss_solo` row (R2509, R2629, R2654, R2660, R2665, R2666);
  label the harder SNR condition "-6 dB".
- Babble trials: attended stimulus = derived signal `babb_mix - 0.714 * babb_singleQ_BF08`, documented as derived.
- Open questions 7 (components as stored, no sign flips/reordering) follows the recommended default.

## 9. Adaptor (implemented with the user decisions above)
- Reads only `Data/MEG/{Younger,Older}/R####_todss_250hz.mat` (100 Hz files ignored, section 2) and
  `Data/stimuli/*.wav`. Array shapes are checked per subject (8 or, for the six junk-row subjects, 9 solo rows;
  12 mix; 3 babble; 15000 x 6); anything else raises.
- Neural data: `RawArray` with 6 channels `dss1`..`dss6`, type **`misc`**, unit set to **`FIFF_UNIT_NONE`** (DSS
  projections are not physical: no conversion to T is possible, and `mag`/`grad` would imply units and sensor
  geometry that do not exist). 250 Hz, no upsampling. The first 375 samples (1.5 s FIR delay, section 6) are
  dropped: 14,625 samples = 58.5 s per trial, t = 0 = stimulus onset. Components as stored (no sign flips, no
  reordering).
- Subject = full R-number (user, 2026-11-23); earlier outputs used R-number - 2000 (R2509 -> 2509, was 509);
  checked unique. `validation.json` subject fields relabelled to the full R-number (results unchanged). Session 1.
- Trials 1-23 per subject in shipped array order (presentation order unknown): 1-8 = `dss_solo` rows 1-8
  (`quiet`; M08, M02, F10, F04, F03, F07, M01, M05); 9-20 = `dss_mix` rows 1-12 (`snr0dB` / `snr-6dB`, mapping
  table in section 3); 21-23 = `dss_babble` rows 1-3 (`babble`). The junk 9th solo row is never read.
- Condition tokens: `quiet`, `snr0dB`, `snr-6dB`, `babble`.
- Stimuli (`audio`, 22,050 Hz, int16 / 32768 as float32, uncut): quiet = the single talker (attended); two-talker
  = [attended single talker (attended), played mixture, unattended single talker], in that order; babble =
  [`babb_F08_foreground_derived` (attended), `babb_mix_F08_BF08`, `babb_singleQ_BF08`]. The derived stimulus is
  computed on load as `babb_mix_F08_BF08 - 0.714 * babb_singleQ_BF08` (section 3).
- Sidecar (`raw.info["description"]`, JSON via `provenance`): alignment_method `onset_only`, trigger_type
  "unknown (not documented; epochs cut at stimulus onset by the authors)", notes (components, units, onset shift,
  filter transient, unknown order), plus `participant` (R-number), `age_group`, `array`, `array_row_1based`
  (row in the shipped array, MATLAB numbering), `played`, `attended`, `unattended`, `snr_db` (null / 0 / -6 / 0
  for babble), `attended_talker` (female/male), `derived_stimulus` (babble only: the formula),
  `auditory_component` (`dss2` for R2594, else `dss1`), `onset_shift_samples` (375), `presentation_order`
  ("unknown"), `units_as_shipped`, `reference` (not applicable), `preprocessing`.
- No drift correction (not estimable, section 7).

## 10. Validation (2026-11-22; `/data_storage/gu08wuvu/datasets/tmp/review/karunathilake2023_aging/validation/`)
- Tier **`low`** in all four conditions (782 trials); `mlr`/`brainstem` impossible (nothing above ~12 Hz, 250 Hz).
  Sanity: 0 errors, no flat/NaN channels; every trial is 1.5-9.7 s shorter than its stimulus by design (uncut wavs).
- Backward decoder (review script, results in `validation.json` and `backward/`; 6 components x 0-250 ms, 0.5-8 Hz,
  64 Hz, **first 1.5 s of each trial dropped after filtering**, LOTO within condition, circular-shift and
  mismatched-story nulls): median r quiet 0.184, snr0dB 0.127, snr-6dB 0.154, babble 0.078, pooled decoder 0.144.
  34/34 subjects above both nulls except babble (26/34 circular, 28/34 mismatch; failing in at least one: R2534,
  R2535, R2538, R2553, R2565, R2595, R2654, R2660, R2661). Attended > unattended 33/34 (snr0dB, snr-6dB), 32/34
  (babble). Lag-sweep peak +0.7 ms (quiet), +1.2 ms (snr0dB, snr-6dB), -0.3 ms (babble); the ~+1 ms is a method
  artefact (habersetzer2025 gives the same with this script). Older > younger in every condition (Mann-Whitney
  quiet p = 0.0004, snr0dB 0.03, snr-6dB 0.02, babble 0.009), as in the paper.
- Forward TRF (attended, 1-10 Hz, 128 Hz): grand GFP peak quiet 65 ms (also ~125 and ~200 ms), snr0dB 148 ms,
  snr-6dB 152 ms, babble 150 ms.
- Repo validator (`repo/`, forward model; it cannot skip the first 1.5 s transient): median r 0.044, 34/34
  significant; babble 0.028, 21/34.
- Figures: `figs/backward_r.png`, `lag_sweep.png`, `latency_trf.png`, `age_groups.png`.

## 11. Coherence (2026-11-22; `/data_storage/gu08wuvu/datasets/tmp/review/karunathilake2023_aging/coherence/{128,native}/`)
Script `tmp/review/scripts/coherence_batch2.py` (5 s windows, 4 s overlap, 1 surrogate). Pooling is the **mean of
per-subject |coherency|**, not the usual complex mean over subjects: DSS component signs and order differ across
subjects and would cancel. Ratio to surrogate (128 Hz; native 250 Hz identical to 3 decimals):

| condition (trials) | 0.2-1 Hz | 1-4 Hz | 4-8 Hz | 8-15 Hz | 15-30 Hz |
|---|---|---|---|---|---|
| quiet (272) | 1.71 | 1.49 | 1.35 | 1.07 | 1.01 |
| snr0dB (204) | 1.44 | 1.42 | 1.36 | 1.06 | 1.01 |
| snr-6dB (204) | 1.42 | 1.51 | 1.37 | 1.08 | 1.00 |
| babble (102) | 1.27 | 1.21 | 1.10 | 1.03 | 1.00 |
| ignored talker, snr0dB + snr-6dB (408) | 1.44 | 1.57 | 1.34 | 1.09 | 1.02 |

Flat above ~10 Hz; dip at 10.5 Hz = the authors' filter edge. The noise floor of |coherency| pooling depends on the
trial count, so conditions with different trial counts are not directly comparable: the ignored-stream curve (408
trials) being as high as the attended ones is not evidence against attention effects; the backward model
(attended > unattended, section 10) is.
