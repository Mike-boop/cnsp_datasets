# gwilliams2023 (MEG-MASC): notes

Findings that explain `adaptor.py`. Review scripts and results: `tmp/review/gwilliams2023/`,
`tmp/review/scripts/meg/gwilliams_*.py` (2026-11-21).

## 1. Source
- OSF ag3kj (+ parts hqvm3, u5327, dr4wy), BIDS 1.6.0, 1304 files, 107 GB. Paper: Gwilliams et al. 2023, Sci Data
  10:862, doi:10.1038/s41597-023-02752-5. Code: github.com/kingjr/meg-masc (decoding checks; no alignment code).
- **Download bug fixed (2026-11-21):** the repo's OSF walker read one page (10 items) per folder, so the registry
  entry resolved 535 of 1304 files (only `the_black_willow` audio, missing subject files, no `participants.tsv`).
  It now follows the pages.

## 2. Layout
- `sub-XX/ses-{0,1}/meg/sub-XX_ses-Y_task-Z_meg.con` (KIT), `_events.tsv`, `_channels.tsv`, marker/headshape
  files. 27 subjects; 5 have one session (sub-03, 12, 16, 20, 21: `participants.tsv` n_sessions). Tasks 0-3 =
  stories lw1, cable_spool_fort, easy_money, the_black_willow (README: "The_Black_Widow"), in the per-subject order
  `task_order` of `participants.tsv` (same order in both sessions).
- `stimuli/audio/<story>_<k>.wav` (22.05 kHz int16, ~3 min each; 31 files incl. a whole-story `lw1.wav`),
  `stimuli/text*/`.

## 3. Stimulus <-> trial mapping
- Each recording holds one story; its `sound` events (one per wav) carry the wav path. Event paths are written
  `lw1_0.0.wav` (float sound id) and `The_Black_Willow_0.wav` (capitals); the files are `lw1_0.wav` and
  `the_black_willow_0.wav`. The adaptor normalises the names.
- One trial per wav; trial numbers count the sounds in presentation order within a session; condition = story.
- Word and phoneme events give `start` (time within the wav) and duration; identical for every subject hearing a
  given wav (checked on 12 recordings), so the TextGrid depends on the wav only.

## 4. Speech features
Audio (synthesised speech, Mac OS TTS, 3 voices, varying rate; word lists inserted, <1% pseudo-words) and
word/phoneme TextGrids (gentle forced alignment, from the events).

## 5. Neural data
- KIT/Yokogawa: 208 axial gradiometers (MNE type `mag`), 16 reference magnetometers (`ref_meg`), 1000 Hz,
  0.03-200 Hz online; 32 MISC channels: trigger lines (MISC 001-004, 008, 010, 0-5 V), MISC 009 = audio copy,
  MISC 031 = a regular TTL train, the rest low-level noise. Kept: MEG, reference sensors and MISC 009.

## 6. Alignment
- The `sound` event onsets are the MISC 008 trigger (e.g. sub-01 ses-0 task-0: 23.506 s in both).
- MISC 009 carries the sound: envelope correlation with the wav r = 0.94-0.97 (2-40 Hz Hilbert envelopes; 0.77
  in sub-13 ses-0 task-0).
- All 196 recordings, 1470 sounds (`gwilliams_audio_lag.py`, `gwilliams_lag_plot.py`; table
  `tmp/review/gwilliams2023/audio_lag.csv`, figure `audio_lag_per_subject.png`): **the sound starts 37-51 ms
  (median 44 ms) after the trigger.** The shipped sound, word and phoneme onsets are therefore ~44 ms early.
- The delay varies from sound to sound (within-session SD 2.75 ms, in steps of ~3 ms: audio buffer jitter). It is
  real: two independent estimates (envelope cross-correlation; Theil-Sen intercept through 10 s windows of the
  70-200 Hz waveform) correlate at r = 0.93 across sounds. The waveform estimate is 2.7 ms (SD 1.1) later than the
  envelope one, probably the group delay of the 200 Hz online low-pass, which the MEG channels share; the absolute
  onset is therefore known to ~3 ms.
- The adaptor measures each sound's delay on MISC 009 (envelope cross-correlation within +-0.5 s of the trigger,
  sub-sample peak) and starts the trial there (`onset="audio"`, default); `onset="trigger"` keeps the events.

## 7. Drift
- Theil-Sen through 10 s windows (70-200 Hz waveform of MISC 009 vs the wav): **-46 ppm** (median over 1470 sounds,
  IQR -47 to -45; every subject and session -45 to -48), i.e. the MEG clock runs slow relative to the audio: ~-8 ms
  over a 3 min wav. A few sounds with few usable windows give outliers (-138 to +228 ppm).
  `drift_correction=True` (default) resamples each trial onto the audio clock with the dataset value.

## 8. Validation (2026-11-21, pilot 20 subjects, all trials, magnetometer-type axial gradiometers, no re-referencing)
`python -m cnsp_datasets.validate gwilliams2023 --download-dir ... --picks mag --n-subjects 20` (defaults: audio
onsets, -46 ppm drift). Results and figure: `tmp/review/gwilliams2023/validation/`.
- low (0.5-8 Hz): mean r 0.050 (median 0.046), 20/20 subjects above the circular-shift and mismatch nulls.
- mlr (30-60 Hz, 18-45 ms): SNR 2.09, p = 0.01, 20/20 subjects significant; peaks at ~35 and ~45 ms.
- brainstem tier (30-250 Hz, MEG window 28-45 ms): SNR 1.55, p = 0.01, 19/20 subjects; sharp peak at 35 ms, flat
  baseline at negative lags. **Validation tier: brainstem.**

## 9. Data size
27 participants (22 with two sessions), 1.90 h per participant, 51.4 h in total (sum of the wav durations of each
recording's sounds; `tmp/review/scripts/meg/meg_data_size.py`).
