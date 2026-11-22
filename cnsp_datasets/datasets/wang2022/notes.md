# wang2022: notes

Explorer notes (2026-11-22), pilot download sub-01..sub-06 (MEG only). Scripts and results (tmp, will be deleted):
`/data_storage/gu08wuvu/datasets/tmp/review/wang2022/` (`scripts/events_table.py` -> `events_table.csv`,
`scripts/headers.py` -> `headers.csv`, `scripts/cache_runs.py` -> `cache/` (MEG 1-20 Hz at 100 Hz per run),
`scripts/drift_scan.py` -> `drift_scan_sub*.csv`, `scripts/scan_summary.py`, `scripts/drift_fine.py` ->
`drift_fine.csv` (sub-01), `scripts/story_lag.py` -> `story_lag_*.npz`, `scripts/story_lag_summary.py`,
`scripts/lag_by_time.py` -> `lag_by_time.{png,csv}`, `scripts/annots.py`, `scripts/bio_line.py`,
`openneuro_meg_listing.json` (keys and sizes of all 720 MEG files on OpenNeuro)). Port the drift evidence (numbers
below) rather than the scripts: the adaptor needs only the constants.

## 1. Source
- OpenNeuro ds004078 v1.2.1, doi:10.18112/openneuro.ds004078.v1.2.1, "A synchronized multimodal neuroimaging dataset
  to study brain language processing" (SMN4Lang). Licence **CC0** (dataset_description.json; the paper itself is
  CC BY 4.0).
- Paper: Wang, Zhang, Zhang & Zong 2022, Sci Data 9:590, doi:10.1038/s41597-022-01708-5.
- Same 12 participants in fMRI (first) and MEG (>= 1 month later); only the MEG part is in scope. Registry entry
  `wang2022` excludes func/anat/dwi, `derivatives/preprocessed_data`, FieldMap, head_motion, embeddings, code/fmri.
- Shared code (`code/meg/`): Psychtoolbox presentation scripts (`Stimuli_presentation/section1-3/run_story*.m`),
  MNE preprocessing (`Preprocessing/preproc_step1_anotation.py`, `preproc_step2_ica.py`, `transfer_bids.py`,
  source-space scripts), technical-validation inputs (`.mat` only). No alignment code beyond `find_events`.

## 2. Layout
- `sub-XX/meg/sub-XX_task-RDR_run-N_meg.fif` (N = 1..60, not zero-padded) + `_events.tsv`, `_channels.tsv`,
  `_meg.json`; `sub-XX_coordsystem.json`. One FIF per story, 6 visits per subject (10 runs per visit). 12 subjects x
  60 runs = 720 FIFs, 325.2 GB on OpenNeuro (pilot 6 subjects: 360 FIFs, 154 GiB; 0.35-0.91 GB per run).
  `task-RDR` is the BIDS task label; the task is listening (paper; meg.json `TaskName` "Chinese-RDR").
- `stimuli/audio/story_N.wav` (60 files), `stimuli/images/` (screen images).
- `derivatives/annotations/`: `time_align/{char,word}-level/story_N_{char,word}_time.mat`, `frequency/`,
  `syntactic_annotations/{part_of_speech,constituency_parsing,dependency_parsing}/`, `scripts/story_N.txt`
  (transcripts, UTF-8), `quiz/{meg,fmri}_quiz.txt` (2 four-choice questions per story, with keys).
  `derivatives/preprocessed_data/` (authors' tSSS + ICA + 0.1-40 Hz MEG, fMRI) not downloaded.
- **Upstream file misplacement (OpenNeuro listing, v1.2.1)**: in every annotation folder the 22 files of stories
  1, 2, 10-29 (the names that sort before `story_3`) sit in the *neighbouring* folder, e.g.
  `time_align/char-level/` holds `story_{1,2,10..29}_word_time.mat`, the char-level files of those stories are in
  `syntactic_annotations/part_of_speech/`, `frequency/word-level/` holds 22 `*_constituency.txt`, and
  `time_align/word-level/` holds 22 fMRI files `sub-01_task-RDR_run-*_bold.dtseries.nii` (3.8 GB, copies of
  `preprocessed_data/sub-01/CIFTI/`). Likewise `code/meg/Stimuli_presentation/section4-6` and
  `Technical_Validation/*` hold `.mat`/`.png` files that belong to the annotations/embeddings, and sections 4-6 have no
  `run_story*.m`. Checked: the OpenNeuro API lists the files at these paths, and each URL points to an object with the
  same git-annex key at the "right" path (download_log.tsv `file` vs `url`), so this is the upstream tree, not our
  downloader. **The adaptor must find annotation files by file name (`story_N_word_time.mat`) anywhere under
  `derivatives/annotations/`, not by folder.** All 60 x 2 time_align files are present that way.
  Registry: add `derivatives/annotations/time_align/word-level/*.nii` to `exclude` (3.8 GB of fMRI).
- **Upstream duplicate: sub-05 run-58/59/60 and sub-06 run-58/59/60 are the same files** (same annex key
  `MD5E-s428802032--64b7...`, etc.; byte-identical after download; events.tsv identical too). No other duplicate among
  the 720 FIFs (`openneuro_meg_listing.json`). The recordings are **sub-05's**: their `meas_date`s (2021-03-17/18/19
  01:43-01:53 UTC) fall inside sub-05's visits (01:10-02:10 UTC on those days) at the position run 58/59/60 has in the
  fixed presentation order, while sub-06's other runs on those days are at 05:14-07:27 UTC; the head position
  (`dev_head_t` y 2.7 / 7.7 / 9.0 mm) matches sub-05's other runs of the same visit (3 / 7-8 / 9 mm), not sub-06's
  (9-12 / 12-13 / 7 mm, the last visit is not decisive). **sub-06's own runs 58-60 are not on OpenNeuro: skip
  sub-06 runs 58-60.** Upstream issue to report.

## 3. Stimulus <-> trial mapping
- One run = one story; **run N = story N** (paper, Data Records: "The story IDs are consistent with the run IDs").
  Same 60 wavs for every subject; same presentation order for all subjects (paper), different from the fMRI order.
- Presentation order (from `meas_date`, identical for sub-01..06): visit 1: 1, 11, 31, 41, 56, 46, 36, 26, 16, 6;
  visit 2: 21, 51, 2, 12, 32, 42, 47, 37, 7, 17; visit 3: 22, 52, 53, 33, 57, 27, 48, 38, 18, 8; visit 4: 13, 23, 43, 3,
  4, 34, 58, 28, 39, 9; visit 5: 14, 24, 44, 54, 59, 49, 29, 19, 40, 10; visit 6: 15, 5, 25, 35, 45, 55, 60, 50, 30, 20.
  (Dates 2021-03-10..19, the same six days for all six pilot subjects, one ~1 h visit per subject and day.)
  The code's `section1-3/run_story1..10.m` play `sounds/1..10.wav` with local numbering (and the code folder is
  itself affected by the misplacement above), so the code does not give the story ids.
- **Verification by duration**: Beg-End trigger interval vs wav duration agrees to -71..+28 ms in all 360 pilot runs
  (section 7), with a per-story pattern identical across subjects (sd 0.5 ms). That separates every pair of stories
  except the two with identical lengths (7/17: 280.000 s; 8/59: 273.440 s); 3/43 and 4/14 differ by 192 ms and match.
- **Verification by the MEG response** (`drift_scan.py`, at 500 ppm): full-run envelope-MEG cross-covariance score
  (GFP^2 peak at 0-400 ms minus floor) with the run's own story vs the equal/near-equal-length partner and 3 random
  other stories. Own story wins against all 4-5 others in 60/60 runs of sub-01, -02, -03, -05, 51/60 of sub-04 and
  28/57 of sub-06; median other/own ratio 0.08 (sub-01..03, 05). The 7/17 and 8/59 pairs: ratio 0.01-0.64 in all
  of sub-01..04 (sub-04 run 43 vs 3: 1.11, but durations separate those). sub-04 and especially sub-06 have weak
  envelope tracking (own score median 3.3e-4 and 1.9e-4 vs 7.9-12e-4 in the others, in every visit), so their
  losses are SNR, not mapping (their trigger durations follow the per-story pattern of the others to < 1 ms).
  **Mapping run N = story N confirmed.**

## 4. Speech features
- Raw audio as shipped: `story_N.wav`, int16 mono 16 kHz, 240.0-406.4 s, 5.059 h in total (the paper's "6 hours"
  is rounded up). Normalised in Adobe Audition, "played at 16 kHz" (paper); the script opens PsychPortAudio at
  16 kHz and plays the mono file on both channels (diotic). Leading silence 0.36-1.07 s, trailing 0.06-1.13 s.
- Transcripts: `derivatives/annotations/scripts/story_N.txt` (UTF-8, Chinese, line per paragraph).
- Time alignment: `story_N_char_time.mat` / `story_N_word_time.mat` (`start`, `end` (1 x n, s), `char`/`word`
  (strings, padded with spaces)); Kaldi GMM-HMM forced alignment (AISHELL-2), 10 ms resolution, punctuation included
  as zero-length or short tokens. **Times are wav time + 10.65 s** (fMRI offset; README, paper): after subtracting
  10.65 s the first onset is 0.00-1.02 s and the last offset 0.20-1.11 s before the wav end, for all 120 files, so
  the time base is the wav. Char-level starts are not monotonic in stories 23 and 32 (one or two tokens). No phone
  tier (pinyin/tones are mentioned in the paper but not in these files). TextGrid tiers: `words` from the word-level
  file, `phones`: none (characters could go in a `characters` tier; see Open questions).
- Word frequency, POS, constituency and dependency parses: available, out of scope (model features off).

## 5. Neural data
- Elekta-Neuromag TRIUX (PKU, "TRIUX system at PKU Meg Lab"), 306 channels: 102 magnetometers (`mag`, T) and
  204 planar gradiometers (`grad`, T/m); no reference sensors. 1000 Hz, online 0.1-330 Hz (paper, FIF header).
  Units as shipped SI (FIF).
- **The shipped "raw" files are MaxFiltered (tSSS)**: `proc_history` in every FIF: MaxFilter 2.2.15, SSS (in 8 /
  out 3, origin (0, 10, 40) mm, head frame), **tSSS buffer 30 s, correlation 0.98**, fine-cal and cross-talk applied,
  run about 1 h after acquisition. Bad channels: none marked (FIF, channels.tsv), i.e. reconstructed by SSS (the paper
  says MaxFilter found 3-11 bad channels per participant, then interpolated). No movement compensation recorded; head
  position per run in `dev_head_t`. No ICA, no offline filter in these files (that is in the
  not-downloaded derivatives). The truly raw recordings are not shared. MEG rank ~71 after SSS (nfree).
- Other channels (identical list in all 360 pilot files): BIO001 (`bio`, V; ~0.13 mV sd, power mostly < 2 Hz,
  no cardiac periodicity (5-30 Hz autocorrelation 0.05 at 0.4-1.6 s); not audio: no correlation with the story
  waveform or envelope (r < 0.04)); probably one EOG lead (the paper mentions two EOG electrodes; only one channel
  exists; unverified), IAS* (11, internal active shielding), STI001-008 + STI101 (triggers), SYS201.
  **No audio copy (MISC/stimtrack) in any file.**
- `meas_date` real (2021-03-10..19); `first_samp` 6000-24000. Digitisation in every FIF: 3 fiducials, 4 HPI coils,
  111-170 head-shape points (118-177 dig points). Continuous HPI on (293, 307, 314, 321 Hz; meg.json); no CHPI
  channels in the files; the lines are probably reduced by tSSS (unverified).
- Line frequency **50 Hz** (peaks at 50/100/150 Hz in the magnetometers, none at 60/120/180 Hz; sub-02 run-5);
  meg.json `PowerLineFrequency: 60` (set by `transfer_bids.py`, `line_freq = 60`) is wrong.
- Recording margins: Beg trigger 4.6-365.7 s after the first stored sample (median 7.6 s; sub-03 run-46 365.7 s and
  sub-06 run-30 170.1 s, STI101 clean in both); the recording continues >= 11.7 s (median 25 s) after the
  drift-corrected wav end (quiz period), so no trial runs past the end of its recording. No annotations
  (no acquisition skips) in any of the 360 FIFs (`annots.py`).

## 6. Alignment
- **Triggers** (STI101 = STI001 + 2*STI002 + 4*STI003; 10 ms TTL pulses via the stimulus PC's parallel port,
  `io64(ioObj, 0xCFF8, code)` in `run_story*.m`): **1 = Beg** (audio start), **2 = End** (audio end), **3** = quiz
  question shown (twice), **4** = answer key press (twice). Every pilot run has exactly 1, 2, 3, 4, 3, 4 in STI101.
  events.tsv holds only the first two events (Beg, End; `transfer_bids.py` keeps `events[0:2]`); `sample` = FIF
  sample - `first_samp`, onset = sample / 1000 s. README: sub-08 run-16 and sub-09 run-7 (not in the pilot) have no
  Beg trigger; their first trigger is End, so their events.tsv probably lists End/question as Beg/End - **read STI101
  in the adaptor**, take the first code 1 and the next code 2, and for those two runs Beg = End - expected interval
  (section 7 fit; ~10 ms uncertainty).
- **Software triggers, documented** (code): PsychPortAudio opened at 16 kHz, stereo, `reqlatencyclass` 0 (no low-
  latency mode), buffer filled, `PsychPortAudio('Start', h, 1, 0, 1)` (start now, wait for the start), then TTL 1.
  End: a busy loop polls `PsychPortAudio('GetStatus')` and `KbCheck` until `Active == 0`, then TTL 2. So Beg follows
  the (estimated) audio start, End follows the engine stop by an unknown polling latency.
- **Sound delivery and delay**: "Elekta matching insert earphones" (tube earphones; paper). "The delay between the
  event timing and the actual timing of the auditory presentation to the participant was a stable 39.5 ms detected
  with a sound sensor" (paper, Preprocessing/MEG). The authors' code has `# delay = 39.5 #ms` commented out
  (`preproc_step1/2`), i.e. their epochs/derivatives do not apply it. Whether 39.5 ms includes the tube is not stated
  (a sound sensor at the ear would; "to the participant" suggests so).
- **No audio copy** is recorded, so onsets and drift cannot be measured directly; both come from the triggers and
  are checked with the MEG response.
- **Clock drift ~ +490 ppm (MEG clock fast relative to the audio clock)**, from two independent signals:
  1. Triggers: Beg-End interval vs wav duration, fit over 360 runs: **486.4 ppm**, intercept -177 ms, residual sd
     8.6 ms (section 7); per subject 480.7-491.6 ppm. But the residual is per story (shared by all subjects) and
     End-side (below), so the effective n is 60 stories: fit on the per-story medians 482.1 ppm, **95% CI 420-535 ppm**
     (bootstrap over stories). The triggers prove the drift but do not pin it down better than +-30 ppm.
  2. MEG response (`drift_scan.py`, `scan_summary.py`): story time tau mapped to MEG time Beg + 39.5 ms +
     tau (1 + d), d = -400..1400 ppm in 100 ppm steps, full-run envelope (1-20 Hz, 100 Hz) vs all 306 z-scored
     channels; score normalised per run, averaged over runs, quadratic peak (200-800 ppm), bootstrap over runs:
     sub-01 498 (95% CI 488-508), sub-02 498 (489-506), sub-03 510 (496-526), sub-04 464 (426-510), sub-05 507
     (500-515), sub-06 391 (287-455; weak responses, flat curve). Per-run best d (100 ppm grid): median 500 ppm in
     sub-01..05 (IQR 500-500 in sub-01, -02, -05). At d = 0 the score drops to 0.35-0.45 of the peak (sub-01..03,
     05), and the GFP peak lag moves from 110-130 ms (d = 500) to 185-240 ms (d = 0): the uncorrected drift smears
     the response by ~0.2 s at the end of a 400 s story.
     Pooled (normalised curves averaged over runs, bootstrap over stories with all subjects of a story together):
     **503.0 ppm (95% CI 495-510) for sub-01, -02, -03, -05**; 492.3 ppm (484-501) with all six (the two weak
     subjects pull it down; their curves are flat). A 20 ppm grid (400-600 ppm, `drift_fine.py`, sub-01 only):
     497 ppm (485-510), the same as the coarse grid.
  3. Per-subject plot (`lag_by_time.py` -> `lag_by_time.png`, `lag_by_time.csv`): envelope GFP^2(lag) averaged
     over runs in story-time blocks, peak lag (ms) per block 0-100 / 100-200 / 200-300 / 300-410 s:

     | | d = 0 | d = 486 ppm |
     |---|---|---|
     | sub-01 | 136 / 187 / 237 / 275 | 110 / 113 / 116 / 113 |
     | sub-02 | 144 / 196 / 244 / 291 | 121 / 122 / 124 / 127 |
     | sub-03 | 153 / 199 / 250 / 283 | 128 / 126 / 130 / 126 |
     | sub-05 | 159 / 211 / 257 / 303 | 130 / 136 / 138 / 140 |
     | sub-04, sub-06 | no clear peak (noise) | no clear peak (sub-06: ~65 ms in 3 blocks) |

     Uncorrected, the response latency grows by ~150 ms over the story (486 ppm x 305 s = 148 ms); corrected, it is
     flat to within 3-10 ms (the small remaining rise in sub-02/-05 points to slightly more than 486 ppm, as the
     scan). sub-04 and sub-06 show no stable response in this measure at all.
  Trigger and MEG estimates agree (482 [420-535] vs 492-503); the MEG one is the precise one. The size matches the
  other TRIUX datasets (habersetzer2025 +485.07 ppm, yang2026 English +537.9 ppm, both measured on an audio copy).
  Cause unknown (MEG or sound-card sample clock off nominal); not corrected by the authors.
- **Intercept of the trigger fit (-177 ms)**: End comes ~177 ms "early" relative to Beg + wav length on the MEG
  clock (i.e. ~217 ms before the acoustic end if Beg + 39.5 ms is the acoustic start). Plausibly the
  `GetStatus.Active` flag drops when the last buffer is handed to the driver, before it has played out (non-low-
  latency mode). This affects only the End trigger, which the alignment does not use; inferred, not verified.
- **Story-specific trigger residual**: after the fit, the interval error has a per-story pattern (sd 8.6 ms,
  -20..+20 ms) that is identical across subjects (sd within story 0.5 ms), plus occasional ~10 ms steps in single
  subject-runs (e.g. story 3: sub-01 -30 ms vs -20 ms in the others; story 9: two modes 10 ms apart). Deterministic
  per story = playback-side (buffering of each file), not random jitter. **It sits in the End trigger, not in
  Beg**: `story_lag.py` (envelope GFP^2 per run at 486 ppm, cross-covariance interpolated to 1 ms lags, peak in
  40-250 ms) and `story_lag_summary.py`: the response peak lag pooled per story over the six subjects has median
  124 ms and sd 4.7 ms across the 60 stories (less than the 8.6 ms residual sd, and that includes content
  differences), and does not follow the residual (slope 0.03 ms/ms, r 0.06, n 60; a Beg-side residual would give
  slope 1, SE of the slope ~0.07). Per run: r -0.07 (329 runs with GFP^2 peak/floor > 2); the 23 runs with the
  10 ms steps show no lag shift (mean -1.7 ms vs -1.2 ms step). So the Beg trigger is consistent across stories to
  within ~5 ms (bound from the per-story lag sd), and between subjects to < 1 ms.
- **Proposed alignment** (`alignment_method = sw_trigger`, `trigger_type = software (code: run_story*.m; delay:
  paper)`): onset = STI101 code-1 sample (from the first stored sample) + 39.5 ms; drift **+500 ppm** (dataset
  value, MEG-response estimate rounded; see Open question 1) applied with `standardise/clock.py:crop_on_audio_clock(
  raw, onset, n_out, drift=500e-6, sfreq_out=1000)` (as habersetzer2025/yang2026; the native rate is 1000 Hz, no
  resampling otherwise); trial = whole wav. Provenance: `drift_ppm` 500, `jitter_ms` 1 (see Open question 3),
  `validation_tier` from the validator. Residual drift uncertainty +-10 ppm = +-4 ms at the end of the longest story.

## 7. Cross-subject duration check
`events_table.py` -> `events_table.csv` (360 runs; run N = story N; error = (End - Beg) - wav duration, ms; End/Beg
from events.tsv = STI101, 1 ms resolution). Fit error = drift x length + c:

| | drift (ppm) | c (ms) | residual sd (ms) | error mean / min / max (ms) |
|---|---|---|---|---|
| pooled (360 runs) | 486.4 | -177.4 | 8.57 | -29.8 / -71 / +28 |
| sub-01 | 487.1 | -177.7 | 9.10 | -29.8 / -69 / +28 |
| sub-02 | 487.4 | -177.4 | 8.50 | -29.4 / -71 / +28 |
| sub-03 | 488.7 | -178.2 | 8.13 | -29.8 / -71 / +27 |
| sub-04 | 480.7 | -175.6 | 8.77 | -29.7 / -71 / +28 |
| sub-05 | 482.7 | -176.7 | 8.22 | -30.2 / -70 / +27 |
| sub-06 | 491.6 | -179.0 | 8.62 | -29.8 / -71 / +28 |

(sub-06 includes the 3 duplicated runs.) Examples (error in ms, sub-01..06): story 1 (406.4 s) 26 25 26 25 25 25;
story 10 (240.0 s) -69 -71 -71 -71 -70 -71; story 21 (393.5 s) 28 28 27 28 27 28; story 3 (320.0 s) -30 -21 -20
-20 -21 -20; story 9 (258.8 s) -49 -49 -58 -48 -48 -58. The across-subject sd within a story is 0.5 ms (median),
i.e. the 1 ms trigger sampling; the scatter about the line (8.6 ms) is per story, not per subject. So the jitter
between subjects is < 1 ms except for ~10 ms steps: 24 of 360 runs differ from their story's median by > 4 ms,
mostly stories with two modes ~10 ms apart that split the subjects (23, 26, 45: 3 vs 3; 9, 58: 2 vs 4) plus single
runs (sub-01 stories 3, 12, 37; sub-02 story 12).
No condition split (one condition).

## 8. Data size
- Per participant: 60 stories, 18211.8 s = **5.059 h** (240.0-406.4 s per story; mean 303.5 s).
- Pilot (sub-01..06): sub-06 without runs 58-60 (-806.8 s): **30.13 h**, 5.02 h per participant (4.83-5.06).
- Full dataset (12 subjects; only sub-06 runs 58-60 missing as far as known; sub-08 run-16 and sub-09 run-7 usable
  with a reconstructed Beg): **60.48 h**, 5.04 h per participant (4.83-5.06). The recordings cover the whole wav
  in every pilot run (section 5), so the stimulus-based estimate is the recorded figure.
- Storage: FIFs float32, 1.33 MB per recorded second (330 channels), 0.35-0.91 GB per run (recordings 266-687 s,
  34.0 h recorded in the pilot), 325 GB for all 720 runs. Standardised trials (wav length, 306 MEG + BIO001,
  float32) ~1.2 MB/s: ~0.37 GB per trial, ~37 GB per participant set of 60, ~265 GB for the full set (estimate).

## 9. Open questions (recommended defaults so the standardiser can proceed)
1. **Drift correction**: no audio copy. Triggers: 486 ppm (all runs) / 482 ppm (per story, 95% CI 420-535);
   MEG response: 503 ppm (495-510) pooled over the four strong subjects, 492 (484-501) over all six; per subject
   498 / 498 / 510 / 464 / 507 / 391 (sub-01..06; sub-04 and -06 weak and wide). Options: (a) one dataset value for
   every run; (b) per-subject neural values (unreliable for sub-04/-06); (c) none (loses ~60% of the envelope
   tracking score, response smeared by ~0.2 s at the end of a story). **Default: (a) +500 ppm** (MEG-response estimate,
   rounded; within the trigger CI), `drift_ppm = 500`. The choice between 486 and 503 changes the end of a 400 s
   story by 7 ms. Per-subject evidence: `drift_scan_sub*.csv` (score vs drift per run), `lag_by_time.png` (latency
   vs story time with/without correction; table in section 6). The same value for sub-04/-06 (no usable estimate).
   Decided (coordinator, 2026-11-22): (a) +500 ppm for every run (`DRIFT`, adaptor option `drift_correction=500e-6`,
   None to disable), applied with `clock.crop_on_audio_clock(..., drift, sfreq_out=1000)`; provenance `drift_ppm` 500.
2. **Onset delay**: Beg + 39.5 ms (paper, "stable", sound sensor) vs Beg + 0. **Default: + 39.5 ms**, documented as
   the authors' measurement. The MEG response peaks at 110-130 ms after Beg + 39.5 ms (envelope GFP, 1-20 Hz), a
   normal M100 latency; it cannot distinguish 39.5 ms from, say, 30 or 50 ms.
   Decided (coordinator, 2026-11-22): onset = first STI101 code-1 sample (from the first stored sample) + 39.5 ms;
   `alignment_method` `sw_trigger`, `trigger_type` software (code + paper).
3. **Story-specific trigger residual** (+-20 ms, identical across subjects, section 6/7): if it sits in the Beg
   trigger, every subject's onset for that story is off by the same amount. **Default: ignore** (use Beg + 39.5 ms
   for all stories). The MEG response says it is End-side (section 6: per-story response lags do not follow it,
   slope 0.03 +- 0.07). `jitter_ms`: no direct onset-jitter measurement exists; default report 1 (between-subject
   sd of the trigger intervals within a story, 0.5 ms, rounded up) with the note "software trigger; Beg trigger
   consistent across stories to within ~5 ms (MEG response); absolute onset from the authors' 39.5 ms".
   Decided (coordinator, 2026-11-22): ignore (End trigger only recorded in the metadata as `end_sample`); `jitter_ms` 1.
4. **sub-06 runs 58-60** are sub-05's recordings (upstream duplicate). **Default: skip them** (sub-06 has 57 trials)
   and report upstream. Do not use them as sub-05 data twice.
   Decided (coordinator, 2026-11-22): skipped in the adaptor (`SKIP`); upstream report in section 10.
5. **tSSS already applied** by the authors (MaxFilter 2.2.15, tSSS 30 s / 0.98) in the files shipped as raw; truly
   raw data are not shared; the further-processed derivatives (ICA, 0.1-40 Hz) are not wanted. **Default:
   standardise the shipped files as they are** (no further SSS in the adaptor); record "tSSS (MaxFilter 2.2.15,
   by the authors)" and the SSS rank (~71) in the metadata. Validation without extra Maxwell filtering.
   Decided (coordinator, 2026-11-22): as shipped; per-trial metadata `sss` (MaxFilter version, orders, origin, buffer,
   correlation, read from `proc_history`) and `sss_rank` (`nfree`, 67-72 in the pilot trials, mostly 69). The FIF
   `proc_history` is kept.
6. **Channels**: keep 306 MEG (`mag`, `grad`) and BIO001 as `misc` (described "BIO001, bio channel, probably EOG,
   unverified"); drop IAS*, STI*, SYS201. Keep `dev_head_t`, dig. Set `line_freq` = 50 (meg.json says 60).
   Decided (coordinator, 2026-11-22): as proposed (306 MEG + BIO001 as `misc`, `line_freq` 50). In addition the shipped
   `subject_info` holds participant names, birthday, weight and height (FIF header): the adaptor keeps only `his_id`
   (`sub-XX`), sex and hand.
7. **Rate**: native 1000 Hz; the only resampling is the drift correction (`crop_on_audio_clock`, sfreq_out 1000).
   Decided (coordinator, 2026-11-22): as proposed.
8. **Annotations**: TextGrid tier `words` from `story_N_word_time.mat` and an extra tier `characters` from
   `story_N_char_time.mat`, both minus 10.65 s (wav time), punctuation tokens dropped (zero-length) or kept as
   they are (default: drop zero-length intervals, keep the rest); no `phones` tier (none shared). Find the files by
   name anywhere under `derivatives/annotations/` (upstream misplacement). Transcripts from `scripts/story_N.txt`.
   Decided (coordinator, 2026-11-22): tiers `words` and `characters` (times - 10.65 s, rounded to 1 ms), zero-length
   tokens dropped (1790 word / 1167 char tokens over 60 stories, all punctuation), the rest kept (punctuation with a
   duration, i.e. labelling a pause: 7146 word / 7819 char intervals). Char level: 669 pairs of consecutive tokens share
   an identical interval (several punctuation marks on one pause); they are merged into one interval with the labels
   concatenated (e.g. `。”`). After that no interval overlaps, none is < 0 or past the wav end (all 120 files checked).
   No `phones` tier. Transcripts not exported (the TextGrid holds the text).
9. **sub-08 run-16 and sub-09 run-7** (no Beg trigger, README): **default Beg = End - median(End - Beg) of the same
   story over the other subjects** (per-story interval known to ~1 ms, section 7), `alignment_method = sw_trigger`
   with a note "onset reconstructed from the End trigger". Check their events.tsv/STI101 when the full set is
   downloaded.
   Decided (coordinator, 2026-11-22): implemented (`NO_BEG`; median over the other subjects' events.tsv End - Beg;
   `beg_reconstructed` true in the metadata). The loader raises if these runs do have a Beg trigger, or another run
   lacks one.
10. **Weak subjects** (sub-04, sub-06: envelope tracking 3-4x weaker than the others in every visit, no stable
    GFP peak in `lag_by_time.png`): keep; let the validator decide (look at their TRFs separately). Not a trigger
    problem (their trigger intervals match the others to < 1 ms); whether their MEG is noisier or their response
    weaker is unknown.
    Decided (coordinator, 2026-11-22): kept (sub-04 in the pilot as a check).
11. **Full download**: 12 subjects, 720 FIFs, 325 GB (OpenNeuro, no Zenodo limit). Add
    `derivatives/annotations/time_align/word-level/*.nii` to the registry `exclude` (3.8 GB of fMRI CIFTI copies).
    Default: download the remaining six subjects after the human checkpoint.

## 10. Upstream issues (to report to the authors / OpenNeuro)
- sub-05 and sub-06 runs 58-60 are identical files (sub-05's recordings by `meas_date`); sub-06's runs 58-60 missing.
- Annotation (and `code/meg`) files of stories 1, 2, 10-29 are in the neighbouring folders (e.g. word-level
  time_align in `time_align/char-level/`, char-level in `syntactic_annotations/part_of_speech/`), and
  `time_align/word-level/` contains 22 fMRI `sub-01_*_bold.dtseries.nii` files.
- meg.json `PowerLineFrequency` 60 Hz; the recordings show 50 Hz (Beijing).
- The MEG files described as raw have tSSS applied (FIF `proc_history`); the paper/README call them raw.
- events.tsv keeps only the first two STI101 events; for sub-08 run-16 and sub-09 run-7 (no Beg trigger) this
  presumably mislabels End as Beg (not checked: not downloaded).
- The 39.5 ms audio delay is in the paper but not applied in the shared code (commented out) or events.
- participants.tsv ages differ from the paper's Table 1 for sub-01 (25 vs 26) and sub-07 (27 vs 26).
- The FIF headers (`subject_info`) contain participant names, birthdays, weight and height (not de-identified);
  the adaptor drops them.

## 11. Adaptor (2026-11-22)
- `adaptor.py`: condition `story`, trial = run = story id, session = MEG visit (`VISITS`, the fixed order of
  section 3; check it against `meas_date` when sub-07..12 are downloaded). Stimulus names `story_N`. Beg/End read
  from STI101 (`mne.find_events`, first code 1, next code 2); in all pilot trials they equal events.tsv (section
  12). Trial = `ceil(wav samples / 16)` samples at 1000 Hz from Beg + 39.5 ms, drift 500 ppm, via
  `crop_on_audio_clock` (quintic spline on the 1000 Hz data; ~4 GB peak per trial, ~20 s per trial).
- Latency check after standardisation (adaptor output, sub-01 and sub-02, all 60 trials each): envelope (Hilbert,
  1-20 Hz, 100 Hz) vs the 306 z-scored MEG channels (1-20 Hz, 100 Hz), GFP^2 of the cross-covariance per 100 s
  story-time block, averaged over trials, parabolic peak in 0-400 ms (port of `lag_by_time.py` working on the
  standardised trials: tmp `std_scripts/latency_check.py` -> `latency_check.csv`). Peak lag (ms) per block
  0-100 / 100-200 / 200-300 / 300-410 s (n trials 60 / 60 / 57 / 8):
  sub-01 105.3 / 106.4 / 108.4 / 102.5 (peak/floor 2.6-3.8); sub-02 116.0 / 115.9 / 117.2 / 117.0 (3.3-4.2).
  Flat to within 6 ms (sub-01) and 1.3 ms (sub-02) over the story (uncorrected the explorer saw +140-150 ms over
  the same blocks). The values are ~5 ms below the explorer's 486 ppm figures (110-116, 121-127 ms); that check
  ran on a separately filtered 100 Hz cache with nearest-sample indexing, so the small offset is plausibly the
  processing, not the alignment (not investigated).

## 12. Pilot standardisation (2026-11-22)
sub-01..05, all 60 runs each: **300 trials, 0 failures, 25.29 h** (5.059 h per participant; trials 240.0-406.4 s,
each exactly the wav length). All at 1000 Hz, 306 MEG + 1 misc (BIO001), `line_freq` 50. STI101 Beg/End equal
the events.tsv samples in all 300 trials; no Beg reconstructed (no fallback). `sss_rank` 67-72 (69 in 183
trials). 107 GB on disk (float32), peak RSS 4.3 GB, ~17 s per trial. The 60 stimuli (wav + TextGrid) written
once.
