# diliberto2023: nursery rhymes, infants at 4, 7 and 11 months and adults, EEG (OSF mdnwg, CND)

A longitudinal cohort of 47 infants recorded at 4, 7 and 11 months, plus 17 adults, watching 18 audio-visual
nursery-rhyme videos (a woman singing or chanting, infant-directed), each played 3 times. EGI GES 300 at 1 kHz.
**The release holds only heavily preprocessed EEG**: 0.1-8 Hz, 50 Hz, ASR-cleaned, bad channels interpolated,
re-referenced to linked mastoids, and **averaged over the repetitions of each rhyme** (one trial per rhyme, not
single trials; section 3). No audio: the stimuli ship as 50 Hz features only (8-band spectrogram, envelope
derivative, 19 phonetic features, visual motion). The user approved incorporating the data as shipped
(2026-11-24).

## 1. Source
- OSF project mdnwg (https://osf.io/mdnwg/), files from 2023-09-10. 689 files: `eegCND/` (4.84 GB), `code/` (4 .m
  scripts, `phDict.mat`, two `.asv` autosaves, `results/` 0.37 GB of TRF results), `libs/libs.zip` (77 MB:
  mTRF-Toolbox, EEGLAB, NoiseTools, CNSP utils). The registry entry downloads `eegCND/` and `code/` without
  `results/`, `.asv` and `libs/` (638 files, 4.84 GB). All 638 matched OSF's md5 and size (2026-11-24). Six files
  first failed with HTTP 429 (OSF rate limit, 2 workers); a 1-worker resume 5 min later fetched them.
- **Licence:** OSF says "copyright 2021" with no holder and no named licence (no CC licence). Raw EEG is "available
  upon request" from the corresponding author (paper, Data availability); the videos are not shared.
- Paper: Di Liberto GM, Attaheri A, Cantisani G, Reilly RB, Ní Choisdealbha Á, Rocha S, Brusini P, Goswami U
  (2023). Emergence of the cortical encoding of phonetic features in the first year of life. *Nat Commun* 14:7789,
  https://doi.org/10.1038/s41467-023-43490-x (`data_campaign/papers/diliberto2023.pdf`). The infants are the first
  50 of the 122-infant BabyRhythm cohort of Attaheri et al. (2022, NeuroImage 247:118698), whose data are not
  public. No overlap with another campaign dataset.
- Shared code: `code/mainTRFanalysis.m` (TRF fits), `mainFiguresAndStats.m`, `plotFigure1C.m`, `plotFigureViolin.m`
  (read, not run).

## 2. Layout
- `eegCND/dataStim.mat`, struct `stim` (CND): `names` = 'Sgram', 'Envelope derivative', 'Phonetic Features (step)',
  'Visual Motion'; `data` {4 x 18}; `stimIdxs` = 1..18, `condIdxs` = 1 ('Listening'), `fs` = 50;
  `additionalDetails`: the 8 Sgram band edges (250-8000 Hz, Greenwood-spaced), 44 phoneme labels, the 19 phonetic
  feature labels, phoneme counts and the 44 x 19 phoneme-to-feature matrix.
- `eegCND/{4mo,7mo,11mo,adults}/dataSub<k>_pre<band>Hz.mat` (k = 1..47 for each infant age, 1..17 for adults;
  no zero padding), struct `eeg` (CND): `data` {1 x 18} of (n x 58) arrays, `fs` 50, `chanlocs` (58 labels and
  EEGLAB coordinates), `extChan` (`description` 'Mastoids', `data` {1 x 18} of (n x 2), labels E29 and E47),
  `nonemptyTrials` (18 logicals), `processingPipeline` = {'LPF_8Hz', 'HPF_0.1Hz', 'Downsample to 50Hz',
  'removeBadChannels', 'None'}, `reRef` 'Mastoids', `deviceName` 'EGI, GES 300 amplifier, Geodesic Sensor Net'.
  The same fields in all 158 files.
- **Four band copies per subject and age:** `01_8` (0.1-8 Hz), `01_1` (0.1-1 Hz), `1_4` (1-4 Hz), `4_8` (4-8 Hz).
  They are separately filtered copies, not a decomposition: the three narrow bands sum to the 0.1-8 Hz copy with
  r = 0.95-0.98 (relative error 0.36-0.41; `bands.py`, adults Sub1 and 4mo Sub10). Welch spectra confirm the pass
  bands. **The adaptor uses only `01_8`**: it is the broadest, and it is the copy the authors fit their TRFs on
  (`mainTRFanalysis.m`: `freqBand = '01_8'`); the narrow copies only build their group-average "ground-truth" test
  EEG. The narrow copies can be recomputed approximately by filtering. The registry still downloads them (3.6 GB).

## 3. Stimulus <-> trial mapping (all 158 files: `tmp/review/scripts/diliberto2023/survey.py` -> `R/diliberto2023/survey.json`)
- **Trials are averages over repetitions, not single presentations.** Each rhyme was played 3 times (54 videos,
  20'33"); infants heard at least 2 repetitions. Each file holds 18 trials, one per rhyme (`stimIdxs` 1..18), and
  the paper says "Data from repeated trials was then averaged" (Methods, Data preprocessing). So each trial is
  the mean of the 2-3 presentations of that rhyme, in the 0.1-8 Hz, 50 Hz, mastoid-referenced space. How many
  repetitions went into each average is not shipped. The presentation order is not shipped either.
- Trial k of every subject is rhyme k (`stimIdxs`); the authors' code pairs them by index and cuts both to the
  shorter length. In every non-empty trial of every file, the EEG length equals the stimulus length exactly (0
  samples difference).
- **Empty trials** (`nonemptyTrials` = 0, data `[]`): adults none. 4mo: Sub8 and Sub13 have **no trial at all**
  (18 empty). The others miss 0-9 trials, mostly in pairs (rhymes 11+12 in 35 files, 1+2 in 12, 10 and 17 in 4,
  ...), which suggests rhymes were presented in blocks of two. 7mo: 22 of 47 infants miss trials (11+12 in 20).
  11mo: 11 miss rhymes 11+12. Empty trials are skipped by the adaptor.
- Rhyme durations from the features: 4.7-79.0 s, 6.20 min for all 18 (the paper's 54 videos at 20'33" make 6.85 min
  per set; the difference is probably video lead-in/out without sound features, unknown).
- **Longitudinal mapping:** `dataSub<k>` is the same infant at 4mo, 7mo and 11mo. The authors' repeated-measures
  ANOVA (`anova_rm`) and paired `signrank` (`mainFiguresAndStats.m`) index subjects by k across the three groups.
  Adults `dataSub<k>` are different people.
- Standardised ids: infants subject k (sub-001..047), session 1/2/3 = 4/7/11 months; adults subject 100 + k
  (sub-101..117), session 1. Condition = age group (`4mo`, `7mo`, `11mo`, `adults`). Trial = rhyme number. The
  sidecar keeps the original file (`age_group`, `original_subject`). Stimulus name `rhyme01`..`rhyme18` (titles
  not shipped).

## 4. Speech features available
- **No audio** (the videos are confidential: infants' recordings). 50 Hz features of the 18 rhymes in
  `dataStim.mat`, same length as the EEG trials:
  - `Sgram`: 8-band spectrogram (n x 8), bands 250-8000 Hz logarithmically spaced (Greenwood). Values mostly
    positive; 1-3% slightly negative (filter ringing). Band means 0.27-1.26, not z-scored.
  - `Envelope derivative` (n): zero mean per trial, std 0.5-0.7. The paper's D is the half-wave-rectified
    derivative of the broadband envelope; the shipped one is not rectified (the authors' code clips it at 0 when
    loading) and correlates only 0.64-0.76 with the derivative of the band sum, so it was computed at another rate
    or normalised.
  - `Phonetic Features (step)` (n x 19, binary): voiced, unvoiced, sonorant, syllabic, consonantal, approximant,
    plosive, fricative, nasal, strident, labial, coronal, dorsal, anterior, front, back, high, low, obstruent. 1
    from the start to the end of each phoneme carrying the feature. They come from transcripts and an automatic
    syllable-based alignment that was then corrected by hand in Praat (paper, Methods). They are
    annotation-derived, not model-derived. The paper's 14 features are these 19 minus columns 3-6 and 19
    (sonorant, syllabic, consonantal, approximant, obstruent; `mainTRFanalysis.m`). Phoneme identity cannot be
    recovered (several phonemes share a feature vector), so no TextGrid can be rebuilt.
  - `Visual Motion` (n): frame-to-frame luminance change of the video. A visual feature, not standardised (visual
    stimuli are out of scope).
- **The adaptor's stimuli** (all at 50 Hz, `modality="audio"`, stimulus `rhymeNN`):
  - `envelope` = the sum of the 8 Sgram bands, as shipped. This is the paper's definition of the broadband
    envelope ("the sum across the eight frequency bands of S"). No envelope is shipped as such; this is the
    validator's input.
  - `spectrogram` = Sgram (8 x n), with `band_edges_hz`.
  - `envelope_derivative` = the shipped D, unrectified.
  - `phonetic_features` = the 19 x n step matrix, with `labels`. **On by default**: they are annotation-derived
    phoneme timings (hand-corrected), the only phoneme-level annotation in the release and the study's main
    feature. The rule "model-derived regressors are off by default" does not apply, and PLAN.md section 8 asks to
    carry phoneme alignments whenever they exist. An adaptor option `phonetic_features=False` drops them.
  - Visual motion is left out.

## 5. Neural data
- EEG, EGI Geodesic Sensor Net, GES 300, recorded at 1 kHz: 64 channels for infants, 128 for adults. Facial
  channels 61-64 removed. The adults' 128 channels were spline-interpolated to the infants' 64-channel layout, so
  **the adult channels are virtual electrodes** at infant positions. 0.1-8 Hz zero-phase Butterworth (order 2),
  downsampled to 50 Hz, ASR, kurtosis/probability-based bad channels spherically interpolated, re-referenced to
  linked mastoids (E29, E47), mastoids removed: 58 channels (E1..E60 without E29 and E47). Native rate 50 Hz, kept
  (never upsample).
- **Units as shipped: µV (assumed; not verifiable).** Per-channel std: medians 0.3-2.0 (infants) and 0.14-1.1
  (adults); 4mo Sub10 Welch PSD 0.9 at 1 Hz, adults Sub1 0.07 (units²/Hz). That is roughly 3-30x below typical raw
  EEG power in 0.1-8 Hz, which repetition averaging (≤ 3x in power for noise) and ASR only partly explain. The CND
  and EEGLAB convention is µV, and no other unit fits better. Scaled by 1e-6 to V. **Absolute amplitudes should
  not be trusted.**
- No NaN and no flat channel in any file. Interpolated channels are not listed in the release (which channels were
  interpolated is unknown), so `info['bads']` stays empty.
- **Channel positions:** `chanlocs` X/Y/Z, identical in all 158 files (a template; radius 6.4-7.5, so cm on an
  infant head). EEGLAB axes (X nose, Y left, Z up) are converted to MNE head coordinates (x right = -Y, y nose = X,
  z = Z, metres). Labels and positions agree: the most-correlated channel (average reference) is one of the 4
  nearest in 1099/1160 channel checks (every 8th file; `positions.py`).
- **Mastoids** (`extChan`, E29 left with Y > 0, E47 right): the shipped values are in the reference before the
  mastoid re-reference, not in the mastoid reference. The mean of the 58 channels regresses on (E29 + E47) with
  slope -0.514 and r = -0.999 for 4mo Sub10, close to the -30/58 = -0.517 expected from a 60-channel average
  reference. The slope spans -0.6 to 0.0 across files (91/156 within -0.55..-0.50), so later steps (ASR,
  interpolation) touched them differently. The adaptor stores them as `M1` = (E29 - E47)/2 and `M2` = -M1 (`misc`).
  This is the mastoids in the shipped linked-mastoid reference, which is exact whatever common reference E29 and
  E47 shared. It keeps the file in one reference: re-referencing to M1/M2 is a no-op, and an average over all 60
  channels recovers the 60-channel average reference.
- No EOG, no peripherals, no digitisation, no stimtrack.

## 6. Alignment
- Trials are cut by the authors at the stimulus onset and averaged over repetitions; the EEG and feature lengths
  are identical. The paper mentions "synchronisation triggers" (5 adults were excluded "due to inconsistencies with
  the synchronisation triggers"). The trigger route (hardware or software, video or audio onset) is not
  documented: `trigger_type` "unknown". The videos are audio-visual, so the audio onset relative to the trigger also
  depends on video playback (unknown).
- `alignment_method` "onset_only" (the authors' epochs), shift 0 (the authors' code uses `circshift(..., 0)`).
- **Drift: not measurable** (no raw recordings, no trigger times, trials cut to the stimulus length). At 50 Hz and
  ≤ 79 s per trial, even 100 ppm is 8 ms over the longest rhyme, under half a sample.
- Averaging 2-3 presentations smears any per-presentation jitter. This is harmless at 0.1-8 Hz, but it rules out
  higher-frequency work, and 50 Hz rules it out anyway.

## 7. Cross-subject duration check
Not possible: the EEG trials were cut to the stimulus length by the authors (EEG length = feature length in every
trial), and no trigger times are shipped.

## 8. Data size
Durations of the averaged trials (each rhyme counted once; the infants actually listened 2-3 times as long):
- 4mo: 45 infants with data (Sub8 and Sub13 empty), 247.5 min, 5.5 min per infant (range in `survey.json`).
- 7mo: 47 infants, 277.3 min, 5.9 min each.
- 11mo: 47 infants, 286.7 min, 6.1 min each.
- adults: 17, 105.4 min, 6.2 min each (all 18 rhymes).
- Total 917 min (15.3 h) in 156 sessions; per infant (3 sessions) about 17.4 min.

## 9. Upstream issues
- 4mo Sub8 and Sub13 ship no trial (all 18 empty), although the paper reports 47 infants at every age, with 3
  excluded for noise in at least one session.
- The mastoids in `extChan` are not in the reference of the EEG they ship with (section 5).
- No licence beyond "copyright 2021".

## 10. Decisions (2026-11-24)
1. Band copy: **0.1-8 Hz only** (`dataSub<k>_pre01_8Hz.mat`), the copy the authors fit their TRFs on; the narrow
   bands are separately filtered copies of the same data (section 2).
2. Phonetic features **on by default** (annotation-derived, hand-corrected); `phonetic_features=False` drops them.
3. Mastoids stored as M1 = (E29 - E47)/2, M2 = -M1 (`misc`), in the shipped linked-mastoid reference.
4. **Repetition-averaged trials incorporated as shipped** (user approved the authors' processed data), flagged in
   the README, the sidecar (`repetition_averaged: true`) and the description.

## 11. Validation (2026-11-24; `R` = `tmp/review/diliberto2023`)
Low tier only (0.5-8 Hz forward model on the envelope = sum of the Sgram bands): the data are 0.1-8 Hz at 50 Hz,
so the 30-60 Hz and 30-250 Hz tiers cannot be run. The validator resamples to 64 Hz but never upsamples, so it
ran at 50 Hz. A validator bug found here (the low tier was told 64 Hz for 50 Hz data, mis-scaling lags, offsets
and drift by 64/50) was fixed on main (commit "validate: low tier uses the native rate when it is below 64 Hz");
the buggy first run is in `R/pooled_buggy64/`.

The infants keep one subject id across sessions, so a default validation pools 4, 7 and 11 months into one model
per infant. Grading uses one run per age group (`tmp/review/scripts/diliberto2023/validate_ages.py`, which
filters the records by `condition`; average reference, bads none) as well as the pooled run:

| group | subjects | mean r | p circular / mismatch | subjects sig. | TRF GFP peak | figure |
|---|---|---|---|---|---|---|
| pooled | 64 | 0.010 | 0.020 / 0.048 | 21/64 | 60 ms | `R/validation.png` |
| 4mo | 45 | 0.008 | 0.020 / 0.048 | 11/45 | 40 ms | `R/validation_4mo/validation.png` |
| 7mo | 47 | 0.007 | 0.020 / 0.048 | 8/47 | (flat; max -60 ms) | `R/validation_7mo/validation.png` |
| 11mo | 47 | 0.008 | 0.020 / 0.048 | 5/47 | 220 ms | `R/validation_11mo/validation.png` |
| adults | 17 | 0.015 | 0.020 / 0.048 | 4/17 | 180 ms | `R/validation_adults/validation.png` |

- Every group passes the low tier: the group mean r beats both nulls at their smallest attainable p (50 circular
  shifts, 20 mismatched pairings). Tracking is weak (mean r 0.007-0.015; repetition-averaged 0.1-8 Hz data).
- The group TRF GFP stays inside the null 95th percentile at every lag in every group, so the peak latencies are
  only indicative. Adults peak at 180 ms with a smaller bump at 60 ms; pooled at 60 ms. The 7mo TRF is flat
  (1.03-1.19 x the null median over the whole lag range); its maximum at -60 ms is not a peak and does not point to
  an offset.
- Per-trial offsets and drift are not informative: the per-trial SNR is too low (offset SD ~260 ms, about the
  spread of a uniform draw over the +-0.5 s search; 393 of 2616 offsets at the search edge; drift estimates
  +-2000-5500 ppm SE). No correction is proposed.

## Alignment grade
**medium**: trigger source unknown and onsets are the authors' epochs (kept, no correction); every age group
passes the low tier (r above circular-shift and mismatch nulls) with a plausible adult TRF peak (180 ms) and no
evidence of an offset, but the TRFs are too weak to verify the latency closely, and drift is not measurable.

## Restructure 2026-11-25 (not yet re-validated on data)
- BaseAdaptor only (no other change).
