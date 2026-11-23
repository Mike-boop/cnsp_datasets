# brodbeck2018: two-talker cocktail party (attend one), Dickens audiobook, KIT MEG (DRUM, preprocessed epochs)

Explorer notes (2026-11-23). Review scripts: `tmp/review/brodbeck2018/scripts/` (named per finding); outputs in
`tmp/review/brodbeck2018/` (`survey.json`, `trigger_lines.tsv`, `integrity.tsv`, `decoder.tsv`, `figures/`,
`validation/`). Nothing in the data was changed beyond what is listed in section 9.

## 1. Source
- DRUM (University of Maryland) item `6ce1b090-3446-46d8-9582-f689afcd23de`, hdl 1903/21109, DOI
  **10.13016/M2ZC7RZ0F**, "Data from: Rapid Transformation from Auditory to Linguistic Representations of
  Continuous Speech" (2018). Authors Brodbeck C, Hong LE, Simon JZ. ISR technical report TR_2018-03.
- Licence: **none stated** (`dc.rights` absent; checked 2026-11-23). Open question 1.
- Paper: Brodbeck C, Hong LE, Simon JZ (2018). Rapid transformation from auditory to linguistic representations of
  continuous speech. Curr Biol 28:3976-3983, doi:10.1016/j.cub.2018.10.042 (`data_campaign/papers/brodbeck2018.pdf`).
- Same recordings re-analysed in Brodbeck, Jiao, Hong, Simon (2020) PLoS Biol 18:e3000883 ("Neural speech
  restoration at the cocktail party"). Its DRUM deposit `001f33ce-b522-4384-9ccf-5d2c66e8a43c`
  (doi:10.13016/tlmm-vtrd, 0.49 GB: `ICA.zip`, `Gammatone.zip`, three `TRFs*.zip`) is "incremental to" this one:
  ICA solutions, eelbrain gammatone pickles and TRFs, **no neural recordings**. Not downloaded (listing in
  `tmp/review/brodbeck2018/drum_listing_2020_001f33ce.json`); nothing in it is needed (raw audio is in this deposit).
- No code shipped.
- Files (ORIGINAL bundle, 6 files, 2.29 GB): `readme.txt`, `conditions.txt`, `subjects.txt`, `MEG1.zip` (1.12 GB),
  `MEG2.zip` (1.12 GB), `stimuli.zip` (44 MB). Downloaded 2026-11-23 (registry `brodbeck2018`, 1 worker,
  read_timeout 120 s, 8 min, 0 failures). md5 and size of all 6 = DRUM listing, `unzip -t` clean
  (`integrity.tsv`). Backed up to the NHR vault (`backup_verify.txt`: all 11 files present with matching sizes).

## Relation to other datasets (overlap check, 2026-11-23)
**No recording overlap with any dataset in the campaign.**
- `brodbeck2022` (Appleseed, OpenNeuro ds007870): 12 students aged 19-23 recorded 2019-12 to 2020-03 (`scans.tsv`);
  here 26 community participants aged 22-61 recorded **2015-07-13 to 2016-07-15** (`meas_date`). Different
  recordings, stimuli (Botany of Desire vs Dickens) and design. brodbeck2022 ships no R-numbers, so whether a
  person took part in both cannot be checked; the age ranges and four-year gap make it unlikely.
- `karunathilake2023`, `karunathilake2025`: R2383 and later, recorded 2021-2022; `karunathilake2023_aging`:
  R2509-R2672. All R-numbers here are R2262-R2375: no shared participant IDs.
- `presacco2016` (same KIT system, recorded around the same years) ships no R-numbers and uses a different
  paradigm; participant overlap cannot be checked, recordings are different.
- The 2020 PLoS Biol deposit is the same recordings (derived data only, see section 1).

## 2. Layout
- `R####/R####-two_speakers-epo.fif` (16 epochs), `R####-single_speaker-epo.fif` (8 epochs): MNE Epochs, 193
  channels, 100 Hz, 0-60 s (6001 samples), float64; `emptyroom-cov.fif`, `R####-trans.fif` (to scaled fsaverage),
  `MRI scaling parameters.cfg` (fsaverage scale). 26 subject folders split over MEG1.zip/MEG2.zip. macOS
  `__MACOSX/`, `.DS_Store` junk in the zips (skipped when extracting).
- `stimuli/`: 16 wavs (`{male,female}_{1-4}.wav`, `{male,female}_{1-4}_mix.wav`) and 128 predictor `.mat` files
  (100 Hz: `audspec-8`, `audspec-8-onset`, phoneme/word/cohort/surprisal/entropy impulses; model-derived, not used).
- `conditions.txt`: trigger code -> foreground (attended), background (ignored), mix. `subjects.txt`: R-number,
  age, sex, handedness (26 rows).
- Extracted for exploration and the adaptor into `tmp/review/brodbeck2018/x/` (2.8 GB); the zips are kept too
  (md5 checks, vault backup; both together 5 GB).

## 3. Stimulus <-> trial mapping (verified)
- Paper (Methods): 1-min segments of LibriVox "A Child's History of England" (Dickens), ch. 3 (male) and ch. 8
  (female); pauses > 300 ms shortened to 250-300 ms; loudness matched perceptually. Mix-k = male-k + female-k with
  an initial 1 s of only the to-be-attended talker. Each mix 4 times (attend one talker, counterbalanced across
  subjects), next mix 4 times attending the other talker, then the four segments just heard alone once; same for
  segments 3-4. A question after each mix trial.
- Trigger codes (`conditions.txt`; MNE KIT channel coding: code = 159 + MISC line number, e.g. 163 = MISC 004):
  two-talker 163 male_1/female_1, 164 female_2/male_2, 169 female_1/male_1, 170 male_2/female_2, 178 male_3/female_3,
  179 female_4/male_4, 184 female_3/male_3, 185 male_4/female_4 (attended/ignored); single 165 male_1, 166 female_1,
  167 male_2, 168 female_2, 183 male_4, 186 female_3, 187 male_3, 188 female_4.
- Every subject (`survey.py`, `survey.json`): exactly 16 two-talker + 8 single epochs, none dropped (`drop_log`
  empty). Presentation order from the raw onset samples (`events[:, 0]`, 1 kHz sample numbers of the original
  recording, increasing across both files), two counterbalancing groups (12 and 14 subjects):
  - group A, 12 subjects (R2262, R2269, R2287, R2299, R2306, R2310, R2316, R2322, R2332, R2343, R2356, R2373):
    163 x4, 164 x4, 165 166 167 168, 184 x4, 185 x4, 186 187 188 183 (attend male_1, female_2, female_3, male_4);
  - group B, 14 subjects (R2266, R2286, R2289, R2296, R2302, R2304, R2309, R2315, R2318, R2323, R2341, R2346, R2353, R2375):
    169 x4, 170 x4, 166 165 168 167, 178 x4, 179 x4, 187 186 183 188 (attend female_1, male_2, male_3, female_4).
  (`subjects.txt` order is not recording order.)
- **The wavs** (`wav_decomp.py`, `wav_first_second.py`): all 16 are 22,050 Hz mono int16, exactly 60.000 s
  (1,323,000 samples). `{fg}_mix.wav` = `{fg}.wav` + `{bg}.wav` with the background **zeroed for samples < 22050
  (1.000 s)**, exact to +-1 LSB, no clipping, both talkers at lag 0 of their files (no delay: the background's own
  first second is dropped, not shifted). So `male_1_mix` (attend male) and `female_1_mix` (attend female) are
  identical after 1 s and differ only in which talker is heard in the first second. The mix played for a code is
  `{foreground}_mix`, as `conditions.txt` says.
- Same stimuli for every participant; each mixture is heard 4 times by each subject.

## 4. Speech features available
- **Raw audio of everything played** (the sheet's "gammatone spectrograms only" is wrong for this deposit): the 8
  single-talker wavs and the 8 mixtures as played. The ignored talker as played = `{bg}.wav` with its first second
  zeroed (= `mix - fg` to +-1 LSB).
- Predictor `.mat` files (auditory spectrogram, onsets, lexical/phonetic impulses at 100 Hz): model-derived, off
  by default, not carried.
- No transcripts or TextGrids (the paper used Gentle + manual correction; not shipped).

## 5. Neural data
- KIT 157-channel axial-gradiometer system (UMD), 1 kHz online (200 Hz low-pass, 60 Hz notch); **shipped only as
  the authors' preprocessed epochs**: tSSS (`proc_history`: mne-python 0.14, `max_st` buffer 10 s, subspace
  correlation 0.9), zero-phase FIR 1-40 Hz (`info` highpass 1.0, lowpass 40.0), decimated to **100 Hz**; 0..60 s
  from the onset trigger (readme, paper). No raw continuous data in either deposit.
- Channels (all subjects): `MEG 001-157` (`mag`, coil `FIFFV_COIL_KIT_GRAD`, T), `MEG 158-160` (`ref_meg`), `MISC
  001-032` (V), `STI 014`. MEG rms ~1.9e-13 T. No projectors, no compensation.
- MISC lines are **not filtered** (only decimated): TTL steps survive. MISC 003 = common offset line (code 162),
  MISC 004-011, 019-020, 024-029 = the 16 per-condition onset lines (code - 159); MISC 001, 018, 030-032 low-level noise (~4.5 mV
  std); envelope |r| <= 0.054 at any lag (R2262, `misc_scan.py`). **No audio copy / stimtrack.** MISC and STI
  dropped by the adaptor (brodbeck2022/presacco2016 precedent).
- Bads (`info['bads']`, as shipped): MEG 056 in all 26, plus MEG 111 in R2356. MEG 056 is zero-variance only in
  R2286 and R2287 (elsewhere tSSS reconstructed it); no other flat (< median/20) or loud (> 10x median) channel.
- Digitisation: 3751 dig points (fiducials, HPI, head shape) and `dev_head_t` per subject; kept.
- Participants (`subjects.txt`): 26, 18 M / 8 F, age 22-61 (mean 45.2), 3 left-handed (R2309, R2318, R2332).
  Paper: 28 recorded, 2 excluded by the authors (not shared).

## 6. Alignment
- Epoch t = 0 is the onset-trigger sample (event sample in raw 1 kHz units, decimated with t = 0 on the grid).
  In all 624 epochs the condition's own onset line deviates from idle at sample 0, and the offset line MISC 003
  at sample 6000 (60.00 s) and never at 5990 (`trigger_lines.py`, `trigger_lines.tsv`). With 4-5 ms pulses
  sampled every 10 ms, this puts the onset-to-offset trigger interval within ~59.995-60.000 s in every trial
  (cf. presacco2016, same lab and system: 59.997-59.998 s at 1 kHz).
- Hardware vs software: **software (inferred)**: the paper's key-resources table lists Presentation
  (Neurobehavioral Systems); triggers are TTL lines recorded by the KIT system; latency to the sound and the
  insert-earphone tube delay are not documented.
- Implemented: trial = shipped epoch as is (t = 0 = onset trigger, 6001 samples at 100 Hz). No offset correction.
- Drift: not measurable beyond the bound above (an interval within 5 ms of 60 s: |drift| <~ 80 ppm, i.e. < 5 ms at
  the trial end, half a sample at 100 Hz). Not corrected; `drift_ppm` null.
- Decoder check (section 10) for timing: see the lag sweep.

## 7. Cross-subject duration check
- Onset and offset trigger both inside every epoch (section 6): 624/624 trials with an interval of
  59.995-60.000 s, all subjects alike. Finer resolution is impossible (100 Hz, no raw data). Jitter between onset
  and offset trigger < ~5 ms; `jitter_ms` left null (not estimable beyond that).

## 8. Data size
26 participants x 24 trials x 60 s = **24.0 min each (all identical), 10.4 h in total**: two_speakers 16 min /
6.93 h, single_speaker 8 min / 3.47 h. (The sheet's 8.7 h is too low.) Unique audio: 8 single talkers, 4 mixtures
(x 2 attention versions, identical after 1 s).

## 9. Adaptor (implemented 2026-11-23)
- Shared code with the lab's other KIT datasets (R-number subjects, wav loaders, epoch/continuous-raw helpers,
  bad-channel rules) in `datasets/simon_base/common.py` (2026-11-23; output unchanged except subject numbers).
- Reads `R####/` folders and `stimuli/` under the root (the extracted zips, `tmp/review/brodbeck2018/x/`).
- Subject = full R-number (user, 2026-11-23); earlier outputs used R-number mod 1000 (R2262 -> 2262, was 262). Checked
  unique, as in karunathilake2023/2025; R-number also in the sidecar (`participant`). `validation.json` subject fields
  relabelled to the full R-number (results unchanged). Session 1. Trials 1-24 in presentation order (raw onset sample).
  Conditions `two_speakers`, `single_speaker` (the authors' file names); attended talker, trigger code, epoch
  file/index, raw onset sample in the sidecar.
- Neural data: the shipped epoch as Raw, 157 gradiometers (`mag`) + 3 reference magnetometers (`ref_meg`), T,
  **100 Hz as shipped (native; no resampling)**, 6001 samples, `info` (dig, dev_head_t, highpass/lowpass) kept;
  bads = shipped `info['bads']` + any zero-variance channel. The loader checks the onset line at sample 0 and the
  offset line at the last sample.
- Stimuli (22.05 kHz float32): single = the talker (attended); two-talker = attended talker (`is_attended`),
  the played mixture `{fg}_mix`, and the ignored talker as played `{bg}_from1s` (the shipped wav with samples
  < 22050 set to 0).
- Run 2026-11-23 (again after the review fixes, same trial list): all 26 subjects, 624 trials, 24 audio files,
  **2.5 GB**, 74 s, no errors. The loader requires the onset line to be active only at t = 0 and the offset line only
  at the last sample (passes in all 624). Round trip:
  standardised data = shipped epoch data exactly (max abs diff 0).

## 10. Validation (2026-11-23; `tmp/review/brodbeck2018/`)
Basis: the standardised data as stored (all 26 subjects, 624 trials), gradiometers (`--picks mag`, bads
excluded), no re-referencing (MEG), attended talker as the stimulus (`--first-attended`). Only the low tier can run:
the data are 100 Hz and 1-40 Hz filtered, so mlr (30-60 Hz) and brainstem (30-250 Hz) are not attempted.
- **Sanity:** 624/624 trials neural 60.01 s vs stimulus 60.00 s; 0 flat, 0 NaN channels after bads; no flags.
- **low (0.5-8 Hz forward): pass.** Mean r 0.037 (median 0.036), **26/26 subjects** above the circular-shift
  null, p_circ 0.020, p_mismatch 0.048. TRF GFP peaks ~50, **109** and ~200 ms; at null level at negative lags.
  Forward-model per-trial offsets: median +0.6 ms (IQR -16..+19), subject medians -12..+10 ms (1-min trials are
  too short for useful per-trial drift: validator drift estimate 78 +- 322 ppm).
  `validation.json`, `validation.png`.
- Per condition (`validate_subset.py`, `validation/cond_*/`):

  | condition (trials/subject) | low r | sig | TRF peak |
  |---|---|---|---|
  | two_speakers (16) | 0.032 | 26/26 | 109 ms |
  | single_speaker (8) | 0.043 | 26/26 | 188 ms |

- **Attention contrast and timing** (`decoder_attention.py`, `decoder.tsv`, `decoder_lag.npz`): backward model per
  subject (good gradiometers, 1-8 Hz, 100 Hz, 40 PCs, ridge on lags 0-250 ms, leave-one-trial-out over the 24
  trials, trained on the attended envelope). Two-talker trials: r attended **0.183** vs ignored-as-played 0.076
  (from 1 s on), attended > ignored in **26/26** subjects (Wilcoxon p = 3e-8). Stimulus-shift sweep (+-500 ms, 10 ms
  steps): subject-mean peak at **0 ms in 25/26 subjects, +10 ms in R2304**; per-trial peaks median 0 ms (IQR
  -10..+10), 93% within +-30 ms. No evidence of an onset error larger than one 100 Hz sample.
- Validation tier: **low** (highest possible with the shipped 100 Hz data).
- Figures: `validation.png`, `validation/cond_two_speakers/validation.png`,
  `validation/cond_single_speaker/validation.png`, `figures/r-attended-vs-r-ignored.png`,
  `figures/decoder_lag_per_subject.png`, `figures/decoder_lag_per_trial.png`,
  `figures/trigger_lines_per_subject.png`.
- Not run: coherence batch and DNN offset check (WORKFLOW 5-6); the DNN check is EEG-specific and the data are
  1-40 Hz at 100 Hz.

## Upstream issues
- No licence on the DRUM item.
- Only preprocessed (tSSS, 1-40 Hz, 100 Hz) epochs are shared; the raw recordings are in neither deposit.
- `readme.txt` "weas" typo; the zips carry macOS `__MACOSX/` and `.DS_Store` files.

## 11. Open questions (human checkpoint; recommended default in brackets)
1. Licence: none stated. [include; note "no licence stated"; ask the authors via the user]
2. Neural rate: the shipped data are 100 Hz (authors' decimation). PLAN keeps native rates <= 1024 Hz and never
   upsamples. [keep 100 Hz; only the low tier can be validated]
3. Ignored-talker stimulus: store the ignored talker as played (`{bg}_from1s`, first second zeroed; implemented)
   or the shipped `{bg}.wav` unchanged? [as played; the mixture is stored too]
4. Conditions: `two_speakers` / `single_speaker` with the attended talker in the sidecar, or split two-talker
   conditions by attended sex (`attend_male` / `attend_female`)? [two labels; sex in the sidecar]
5. MISC trigger lines dropped (facts in the sidecar/notes). [yes]
6. Onset: shipped epoch start (onset trigger), no shift; no drift correction (not measurable). [yes]
7. Delete `x/` (extracted, 2.8 GB) or the zips after the work? The zips are on the vault. [user decides at clean-up]
