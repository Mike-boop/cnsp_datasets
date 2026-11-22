# wang2022: 60 Mandarin stories (SMN4Lang, MEG part)

MEG of 12 native Mandarin speakers (4 female, 23-30 years, right-handed, normal hearing; paper) listening to 60
news-commentary stories (Renmin Daily Review, one male broadcaster, 4-7 min each, 5.06 h in total) over six
visits. The same participants also did the stories in fMRI (not in scope).

- **Source:** OpenNeuro ds004078 v1.2.1, doi:10.18112/openneuro.ds004078.v1.2.1 ("A synchronized multimodal
  neuroimaging dataset to study brain language processing", SMN4Lang). **Licence CC0.** Registry entry `wang2022`
  (MEG, stimuli, annotations and code only; fMRI, anatomy, diffusion, embeddings and the authors' preprocessed
  data are not downloaded).
- **Paper:** Wang S, Zhang X, Zhang J, Zong C (2022). A synchronized multimodal neuroimaging dataset for studying
  brain language processing. *Sci Data* 9:590. doi:10.1038/s41597-022-01708-5
- **Code (authors):** `code/meg/` in the dataset (Psychtoolbox presentation, MNE preprocessing).

## Size
**12 participants, 717 trials (one per story) of 240.0-406.4 s, 60.48 h in total; 5.04 h per participant (range
4.83-5.06 h).** Every participant has all 60 stories (5.06 h) except sub-06 (57; runs 58-60 are not on OpenNeuro,
see Caveats). Standardised and validated so far: sub-01..06, **357 trials, 30.13 h; 5.02 h per participant
(4.83-5.06 h)** (sub-01..05 as the pilot, sub-06 afterwards with the same adaptor).

## What is provided
- **MEG:** Elekta-Neuromag TRIUX (Peking University), 102 magnetometers (`mag`, T) and 204 planar gradiometers
  (`grad`, T/m), recorded and stored at **1000 Hz** (resampled only for the drift correction), online 0.1-330 Hz.
  **tSSS already applied by the authors** in the files OpenNeuro ships as raw (MaxFilter 2.2.15, in/out order
  8/3, 30 s buffer, correlation 0.98; SSS rank 67-72); the truly raw recordings are not shared. No bad channels
  marked (reconstructed by MaxFilter). No reference sensors.
- **Other channels:** BIO001 (`misc`, V): a bio channel, probably one EOG lead (unverified). Head-shape
  digitisation (111-170 points), fiducials, HPI coils and the device-to-head transform are kept. Dropped: STI*,
  IAS*, SYS201. No audio copy exists in the recordings. `line_freq` set to 50 Hz (the shipped meg.json says 60).
- **Stimuli** (shared by all participants): `story_1` ... `story_60`.
  - `audio`: the wav as shipped (16 kHz mono int16);
  - `textgrid`: tiers `words` and `characters` from the authors' Kaldi forced alignment (10 ms resolution), on
    the wav time base (the shipped times carry a +10.65 s fMRI offset, removed). Zero-length punctuation tokens
    are dropped; punctuation with a duration (labelling a pause) is kept; punctuation marks sharing one interval
    are joined. No phone tier (not shared).
- **Condition:** `story`; trial = run = story id (1-60); session = MEG visit (1-6, 10 stories each, the same
  fixed order for all participants). Each trial starts at the sound onset and is as long as the wav (the
  recordings continue >= 11.7 s after every wav end).
- Trial metadata (`raw.info["description"]`, JSON): story, visit and position, Beg/End trigger samples, onset,
  sound delay, drift applied, MaxFilter settings and SSS rank, `validation_tier` and `validation_note`.

## Alignment
- **Software triggers** (`alignment_method` `sw_trigger`): the presentation script sends TTL 1 (Beg) on the
  parallel port right after `PsychPortAudio('Start')` and TTL 2 (End) when playback stops; read from STI101.
- **Onset = Beg + 39.5 ms**, the delay to the participant measured by the authors with a sound sensor (paper;
  their own code does not apply it). The MEG envelope response then peaks at a normal M100 latency (110-140 ms),
  but this cannot pin the delay to better than ~10-20 ms. Beg is consistent between participants to < 1 ms and
  across stories to ~5 ms (MEG response); `jitter_ms` 1.
- **Clock drift +500 ppm** (MEG clock fast): no audio copy, so the drift is the dataset value from the MEG
  envelope response (503 ppm, 95% CI 495-510, in the four strongly responding pilot subjects; the triggers give
  482 ppm, CI 420-535). Without correction the response slides by ~150 ms over a story. Corrected in the same
  interpolation that cuts the trial (`drift_correction=500e-6` default, `None` disables); residual uncertainty
  ~+-10 ppm (+-4 ms at the end of the longest story). Checked on the standardised trials (sub-01, sub-02, 60
  trials each): the envelope response peak stays at 103-108 ms and 116-117 ms across 100 s blocks of the stories.
- The End trigger has a story-specific +-20 ms scatter (playback side, identical across participants) and is not
  used.
- sub-08 run-16 and sub-09 run-7 have no Beg trigger (README): Beg = End - median End-Beg of the same story in the
  other participants (`beg_reconstructed` true; ~1 ms uncertainty).

## Validation
**mlr tier in all 6 validated participants** (sub-01..06, 357 trials, 30.13 h; `validation_tier: mlr`); the
brainstem tier is not reached. Data as shipped (the authors' tSSS, no further Maxwell filtering), 102 magnetometers,
no re-referencing. Repo `checks.validate_subject` (low / mlr / brainstem) plus a backward model (64 Hz, 0.5-8 Hz,
lags 0-250 ms, leave-one-trial-out ridge, 50 circular-shift and mismatched-stimulus nulls, lag sweep +-1 s). For
MEG the "brainstem" tier tests the 30-250 Hz cortical response at 28-45 ms, not a brainstem response.

| subject | trials | low forward r | backward r (95th pct circular null) | lag-sweep peak | mlr SNR (p) | brainstem SNR (p) |
|---|---|---|---|---|---|---|
| sub-01 | 60 | 0.064 | 0.337 (0.031) | 0 s | 2.94 (0.0099) | 0.61 (1.0) |
| sub-02 | 60 | 0.062 | 0.381 (0.033) | 0 s | 2.59 (0.0099) | 0.51 (1.0) |
| sub-03 | 60 | 0.073 | 0.439 (0.039) | 0 s | 1.77 (0.0099) | 0.53 (1.0) |
| sub-04 | 60 | 0.049 | 0.275 (0.034) | 0 s | 1.46 (0.0099) | 0.37 (1.0) |
| sub-05 | 60 | 0.049 | 0.398 (0.030) | 0 s | 3.40 (0.0099) | 0.88 (0.97) |
| sub-06 | 57 | 0.043 | 0.285 (0.033) | 0 s | 1.82 (0.0099) | 0.70 (1.0) |
| median | | 0.056 | 0.359 | | 2.21 (mean 2.33) | 0.57 (mean 0.60) |

- **Low tier:** every participant at the null floor (circular-shift p 0.0196 = 1/51, mismatched-stimulus p 0.048).
  **mlr** (30-60 Hz, 18-45 ms): significant in 6/6 (p at the floor, 1/101). **Brainstem** (30-250 Hz): SNR < 1 in
  every participant, not significant.
- **Backward decoder** above its circular-shift null by 8-13x in every participant; the lag sweep peaks at 0 s in
  all six (64 Hz, one sample = 15.6 ms), i.e. the onsets (Beg + 39.5 ms) and the +500 ppm drift hold end to end at
  that resolution. It cannot confirm the 39.5 ms delay more finely.
- sub-04 and sub-06 (the weak participants of the exploration, Caveats) have the lowest backward r, but both pass
  the low and mlr tiers.
- **Coherence** (MEG magnetometers vs the envelope, 5 s Hann windows, 4 s overlap, ratio to one global
  circular-shift surrogate; all 6 participants, 357 trials), 128 Hz / native 1000 Hz:

  | band (Hz) | 0.2-1 | 1-4 | 4-8 | 8-15 | 15-30 | 30-60 | 60-120 | 120-250 | 250-500 |
  |---|---|---|---|---|---|---|---|---|---|
  | 128 Hz | 10.93 | 8.31 | 8.02 | 2.76 | 1.43 | 1.23 | - | - | - |
  | 1000 Hz | 10.92 | 8.32 | 8.05 | 2.72 | 1.46 | 1.29 | 1.35 | 1.13 | 1.02 |

- **DNN offset:** not applicable (the match-mismatch classifier is trained on EEG).
- **Not validated:** sub-07..12 (not standardised yet); the gradiometers; BIO001.
- **Suitable for:** low-frequency envelope tracking and decoding (strong: coherence 8-11x the surrogate below
  8 Hz), word- and character-level analyses (forced-aligned TextGrids), middle-latency (30-60 Hz) cortical
  responses, and between-story comparisons (60 stories, the same for every participant). **Not suitable for**
  30-250 Hz / sub-millisecond timing or subcortical (ABR/FFR-type) analyses: software triggers with an onset known
  only from the authors' 39.5 ms measurement, drift from a neural estimate (+-10 ppm, +-4 ms at the end of a story),
  ~10 ms story-specific trigger modes, and the brainstem tier fails. The tSSS cannot be undone (rank 67-72).

## Decisions taken (coordinator, 2026-11-22; to revisit)
- **Files standardised as shipped** (authors' tSSS); no further Maxwell filtering, no use of the ICA/0.1-40 Hz
  derivatives.
- **Drift +500 ppm for every run**, onset Beg + 39.5 ms (see Alignment).
- **sub-06 runs 58-60 skipped** (copies of sub-05's runs, see Caveats).
- **BIO001 kept as `misc`**; participant names, birthday, weight and height removed from the FIF `subject_info`
  (only `sub-XX`, sex and hand kept).

## Caveats
- tSSS (30 s, 0.98) is already in the data and cannot be undone; the data rank is 67-72 (`sss_rank`).
- Continuous HPI (293, 307, 314, 321 Hz) was on during recording; whether tSSS removed the lines is not checked.
- Two participants (sub-04, sub-06) show 3-4x weaker envelope tracking than the others in every visit; not a
  trigger problem. Both still reach the mlr tier (Validation).
- Upstream: sub-05 and sub-06 runs 58-60 are the same files (sub-05's recordings by `meas_date` and head
  position); sub-06's own runs 58-60 are missing. Annotation files of stories 1, 2, 10-29 sit in neighbouring
  folders (the adaptor finds them by name). meg.json says 60 Hz line frequency; the recordings show 50 Hz.

Details: `notes.md`.
