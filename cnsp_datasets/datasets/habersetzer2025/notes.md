# habersetzer2025: notes

Explorer notes (2026-11-22). Scripts and results: `/data_storage/gu08wuvu/datasets/tmp/review/habersetzer2025/`
(`scripts/align_run.py`, `audio_lag/audiobook.csv`, `audio_lag/drift_onset_per_subject.png`, `scripts/olsa_check.py`,
`scripts/extra_ev.py`); the authors' code is cloned in `code/`, one authors' tSSS derivative in `deriv_probe/`.

## 1. Source
- OpenNeuro ds006468 v1.1.2, doi:10.18112/openneuro.ds006468.v1.1.2, "MEG-SCANS: Stories, Chirps And Noisy
  Sentences". Licence CC0 (dataset_description.json). Downloaded without `anat/` and the per-subject derivatives
  (1254 files, 102 GB).
- Paper: Habersetzer, Steuer, Radeloff & Meyer 2025, Sci Data 12:1938, doi:10.1038/s41597-025-06397-4 (cite as asked
  in `HowToAcknowledge`).
- Code: github.com/tillhabersetzer/MEG-SCANS (BSD-3; Zenodo doi:10.5281/zenodo.17397581). FieldTrip/mTRF pipelines,
  trial functions (`helper_functions/my_trialfun_audiobook.m`, `my_trialfun_olsa.m`), MNE MaxFilter script
  (`maxfilter/apply_maxfilter_parallel.py`). Presentation and BIDS-conversion scripts are "available upon request".
- CHANGES 1.1.0 says "Removed sub-02, audiobook2-run-01 because audiofiles can't be shared", but sub-02 has
  audiobook2_run-01 (and its audio copy matches the shipped wav, r 0.99); the run missing is sub-01's audiobook2
  (both runs, pilot audio withheld, paper "Subject Data Integrity"). The CHANGES line probably means sub-01.

## 2. Layout
- `sub-XX/meg/sub-XX_task-<task>[_run-0N]_meg.fif` (+ `_events.tsv`, `_channels.tsv`, `_meg.json`), tasks
  `audiobook1` run-01/02, `audiobook2` run-01/02, `olsa`, `noise` run-01/02 (empty room before/after; sub-11 has no
  noise run-02). One file per run, one session. `sub-XX_acq-calibration_meg.dat` and `sub-XX_acq-crosstalk_meg.fif`
  (fine calibration and cross-talk, for SSS) per subject. `sub-XX/beh/`: audiogram, OLSA SRT, intelligibility (SNR
  per list), audiobook comprehension questions.
- `stimuli/audiobooks/task-audiobook{1,2}_run-0{1,2}_stim.{wav,txt,TextGrid}`; `stimuli/audiobooks/pilot/` (sub-01's
  preliminary audiobook1 versions); `stimuli/transient/upchirp_stim.wav` (10.3 ms chirp, int16 44.1 kHz);
  `stimuli/olsa/sentences/<id>.{wav,txt,TextGrid}` (70 unique sentences); `derivatives/stimuli/
  preprocessed_olsa_envelopes_decoding.mat`.
- Not downloaded (on OpenNeuro): `derivatives/sub-XX/maxfilter/*_proc-tsss-mc_meg.fif` (authors' tSSS + movement
  compensation + transformation to the head position of audiobook1_run-01; ~3.5 GB per subject for the four
  audiobook runs, ~85 GB in total), `*_raw.pos` (head positions), maxfilter report/log, `coregistration/*_trans.fif`.
- Acquisition order (scans.tsv, constant across subjects): noise run-01, olsa, audiobook1 run-01, run-02, audiobook2
  run-01, run-02, noise run-02. `meas_date`s are shifted to 1909-1910 (anonymised; relative times kept).

## 3. Stimulus <-> trial mapping
- **Audiobooks (in scope)**: two German Poe stories read by two male lab members ("Das schwatzende Herz" =
  audiobook1, "Die Maske des roten Todes" = audiobook2), each split in two runs; one recording per run and one wav
  per run (`stim_file` column of events.tsv). Same wavs for sub-02..sub-24; sub-01 heard the pilot versions of
  audiobook1 (`stimuli/audiobooks/pilot/`, 0.8-2.0 s shorter; events.tsv points to them) and no audiobook2.
  Wavs: float32 mono 44.1 kHz, 561.597 / 524.537 / 494.291 / 535.788 s (pilot 560.780 / 522.503 s).
- Each audiobook run starts with 60 up-chirps (code 2, ISI >= 1.1 s + 200 ms jitter; sub-02: 150; sub-01: none),
  then the story. The story carries a trigger (code 1, 200 ms pulse) at every full second of the audio, the first at
  the audio onset ("continuously triggered every second, aligned with the audio stream", paper; events.tsv
  `trial_type` "audiobook 1s"). Trial = one run, starting at the first code-1 event.
- **Verified with the audio copy** (section 6): in all 94 audiobook runs MISC001 correlates with the listed wav at
  r 0.91-0.999 (median over 10 s windows; every window >= 0.88, 9805/9805 windows used), at a constant lag of
  2.6 ms after the first trigger. Number of code-1 events = floor(wav duration) in every run (pilot runs: +1).
- **OLSA (out of scope by default, see 8)**: 120 sentences (6 lists x 20, one target intelligibility per list:
  20-95 %, SNR set per subject from the SRT), in randomised order, in a continuous speech-shaped noise stream at
  65 dB SPL. Trigger per sentence (code = 20 * list position + sentence; sub-01 has other codes, e.g. 4609), with
  `duration`, `SNR`, `intelligibility`, `stim_file`, `sentence` in events.tsv. The 120 sentences (70 unique files)
  are the same for all subjects (261.5 s of speech); the SNRs differ.
- **Chirps (out)**: transient stimuli, code 2; not continuous speech.
- **Empty room (out)**: no stimulus; useful only as noise reference.

## 4. Speech features
- Audiobooks: raw audio (as shipped), transcripts (`.txt`, UTF-8, CRLF), TextGrids with tiers `words` and `phones`
  (Montreal Forced Aligner, v1.1.0), xmax = wav duration, i.e. relative to the start of the wav.
- OLSA: the clean sentences and the noise are commercial and **not shared** (paper, Data Records). The files in
  `stimuli/olsa/sentences/*.wav` are **not audio**: 64 Hz int16 envelopes (Biesmans gammatone envelope, the authors'
  decoding feature), length = sentence duration + 0.5 s. TextGrids (words, phones) and `.txt` are shared. The
  presented mixture is recorded in MISC001/002 (1 kHz, 330 Hz low-pass) for the whole OLSA block.

## 5. Neural data
- Elekta/MEGIN TRIUX (serial 3127, software 4.11.5), upright 68 deg, 306 channels: 102 magnetometers (`mag`, T) and
  204 planar gradiometers (`grad`, T/m). No reference sensors (`ref_meg`): noise suppression is by SSS.
  1000 Hz, online 0.1-330 Hz (paper, FIF header). Units as shipped are SI (FIF), cal applied by MNE.
- **Shipped files are raw: no SSS/MaxFilter** (`proc_history` empty; readable with `allow_maxshield=False`, so IAS
  was off; the 8 `magn8_iasoff_68deg` SSP projectors are inactive). No bad channels marked in any channels.tsv or
  FIF. The authors mark MEG2143 and MEG1112 bad for every subject ("marked in scanprotocols") plus
  `find_bad_channels_maxwell` (e.g. sub-05: MEG1023), then tSSS (st_duration 10 s, int 8 / ext 3, head frame, fine-cal
  + cross-talk), movement compensation from cHPI, destination = head position of audiobook1_run-01.
- Their derivative (checked for sub-05 audiobook1 run-01) has the same `first_samp` (44000), length and sample
  times as the raw file, identical MISC/STI channels, bads interpolated (`bads` empty) and 9 extra `chpi` channels.
  So onsets measured on the raw file apply to it unchanged.
- Other channels: EOG001/EOG002 (VEOG/HEOG, bipolar, V), ECG003 (V), MISC001/MISC002 (left/right audio copy, V,
  ~8 mV rms; identical, r 0.9998: diotic), MISC007 (experimenter's microphone; absent in sub-01), STI001-016 +
  STI101 (triggers), 11 IAS channels and SYS201 (system). sub-01 additionally has 32 EEG channels (EEG001-032,
  pilot with simultaneous EEG; reference not documented).
- Continuous HPI (5 coils at 261, 278, 295, 311, 328 Hz) in every run; head shape digitised (Polhemus, ~220 points
  plus fiducials and HPI) and `dev_head_t` in every FIF.
- Annotations: none in the FIFs. events.tsv `sample` = FIF sample - `first_samp` (onset = sample / 1000), i.e. time
  from the first stored sample, as MNE `raw.times`.
- STI101 glitches: sub-03 audiobook1 run-01 has ~200 spurious codes between 378 and 398 s and lacks two code-1
  triggers there; 6 other runs have one extra 1 ms code-1 blip; sub-01 audiobook1 run-01's first trigger is not a
  code 1 in STI101. events.tsv is clean (one code-1 event per second in every run), and the audio copy is continuous
  through the sub-03 glitch (lag constant to 0.01 ms). **Use events.tsv, not STI101.**

## 6. Alignment
- Triggers: **hardware, documented** (paper, Procedure): the trigger signals are an extra channel of the sound card
  (RME Fireface UCX, 44.1 kHz) sent as S/PDIF to a custom FPGA trigger box clocked by the Fireface, which drives a
  5 V TTL input of the MEG. So triggers and audio share the sound-card clock.
- Sound delivery: Tip-300 insert earphones with foam tips, driven by a TDT HB7, diotic. The authors shift all
  trials by `audio_latency = 3 ms` after the trigger ("see measurements 28.06.24", `speech/settings_speech.m`,
  `chirps/settings_chirps.m`); the paper does not mention it. Tube length/acoustic delay are not reported.
- **Audio copy**: MISC001/MISC002 are the presented waveform (not an envelope), sampled with the MEG (same 330 Hz
  anti-alias filter as the sensors, so its delay applies to both). Where it is tapped (sound-card output or HB7
  output) is unknown.
- Measurement (`scripts/align_run.py`, all 94 audiobook runs): the wav (1 kHz, 2-200 Hz) is put on the trigger
  clock (one trigger per audio second), then cross-correlated with MISC001 and MISC002 in 10 s windows every 5 s
  (sub-sample peak, Theil-Sen through the window lags).
  - **MISC onset = first trigger + 2.61 +- 0.32 ms** (1.75-3.13 ms; relative to the trigger line fitted through all
    triggers: 2.61 +- 0.22 ms; the spread is mainly the 1 ms sampling of the TTL edge). Per-run window lags scatter
    by 0.004 ms (sd).
  - MISC vs triggers: residual drift -0.01 +- 0.03 ppm, i.e. the audio and the triggers are on one clock (as
    documented).
  - **Audio clock vs MEG clock: +485.07 ppm** (MEG counts 1000.485 samples per audio second; per run
    484.99-485.15 ppm, subject medians 485.01-485.14, a slow trend over recording dates; plot
    `audio_lag/drift_onset_per_subject.png`). At this rate the end of a 9 min run is **272 ms late** if not
    corrected. The cause (sound-card or MEG sample rate off nominal) is unknown; the authors' trial function allows
    "1/2 ms delay per sec trigger" (`my_trialfun_audiobook.m`), so they knew of it, and they re-anchor at the 1 s
    triggers (10 s or 120 s epochs) instead of correcting it.
- **Proposed alignment** (`alignment_method = stimtrack_xcorr`, `trigger_type = hardware (paper)`): per run, onset
  = first audiobook trigger (events.tsv `sample`) + the MISC001 onset of that run (fractional samples), plus an
  acoustic delay (default 0.4 ms: see Open questions); drift +485.07 ppm (dataset value; or the run's own value,
  the difference is < 0.05 ms over a run) applied with `standardise/clock.py:crop_on_audio_clock(raw, onset,
  n_out, drift=485.07e-6, sfreq_out=1000)`. Trial length = wav length at 1000 Hz (the recording extends >= 0.28 s
  past the end of every wav after drift). The standardiser should port `scripts/align_run.py` into the repo
  (`datasets/habersetzer2025/drift.py` + CSV, as schueller2024), since tmp is deleted.
  Fallback without MISC: first trigger + 2.6 ms and 485.07 ppm (error < 0.5 ms).
- OLSA (if ever included): sentence onsets from events.tsv (hardware triggers, same box); check on sub-05 with the
  shipped envelopes against the MISC001 envelope: lag about -10 ms (envelope method, low precision), r rising with
  SNR (0.19 at -9.8 dB to 0.61 at -2.6 dB), so the mapping is right; onsets not measured precisely.

## 7. Cross-subject duration check (audiobooks)
- Trigger span (first to last code-1 event, L = n - 1 audio seconds) vs L: error 239-240 ms (L 493, 23 runs),
  253-254 (522/523), 259 (534), 271-272 (560). Fit error = drift x L + c over 94 runs: **484.1 ppm, c 0.5 ms,
  residual sd 0.36 ms** (= 1 ms sampling of the triggers; no jitter beyond that). Through the origin: 485.0 ppm.
  The MISC estimate (485.07 +- 0.03 ppm) is the more precise one.
- Onset jitter of the audio relative to the triggers: sd 0.22 ms (relative to the trigger line); 0.32 ms relative
  to the first trigger sample. With the per-run MISC onset, the onset error is set by the MISC measurement
  (~0.01 ms), not the triggers.

## 8. Data size
- Audiobooks: 24 participants; sub-02..24: 4 runs, 2116.2 s = 0.588 h each; sub-01: 2 pilot runs, 1083.3 s =
  0.301 h. **13.82 h in total, 0.576 h per participant (0.301-0.588).** Per story: audiobook1 7.24 h (24 subj.),
  audiobook2 6.58 h (23 subj.).
- OLSA (if included): 261.5 s of sentences per participant in a ~393 s block of noise (1.74 h of sentences or
  2.62 h of block for 24 participants).
- Recording size: ~0.85 GB per audiobook run (306 + 37 channels, 1000 Hz, float). One run at a time in memory
  (~1.7 GB as float64).

## 9. Open questions (recommended defaults so the standardiser can proceed)
1. **SSS**: the shipped data are raw (no SSS); raw MEGIN data failed the high-frequency tiers before (libribrain100).
   Options: (a) download the authors' `derivatives/sub-XX/maxfilter/*_task-audiobook*_proc-tsss-mc_meg.fif`
   (~85 GB, OpenNeuro S3, same time base as raw, verified on one file) and standardise those; (b) run
   `mne.preprocessing.maxwell_filter` in the adaptor with the shipped fine-cal/cross-talk files and the authors'
   settings (bads MEG2143, MEG1112 + `find_bad_channels_maxwell`, tSSS 10 s), slow (minutes per run, plus cHPI
   fitting for movement compensation). **Default: (a)**, keep a `sss=False` option reading the raw files; record
   "tSSS-mc by the authors (MNE 1.9.0)" in the metadata. Needs the human's go for another ~85 GB download (and the
   raw audiobook files must stay for MISC unless MISC is read from the derivative, which carries it identically).
   Decided (coordinator, 2026-11-22, user asleep; revisit): standardise the raw files as shipped (least processed); the
   authors' tSSS derivatives are not
   downloaded (README points to them). Validation applies Maxwell filtering in the validation only (as
   libribrain100, `tmp/review/scripts/meg/validate_sss.py`). MEG2143 and MEG1112 are set in `info["bads"]`.
2. **Drift correction: +485.07 ppm** (MEG fast relative to the audio clock), measured on every run (plot
   `audio_lag/drift_onset_per_subject.png`). It is large but consistent (484.99-485.15 ppm in all 94 runs) and
   confirmed independently by the triggers. **Default: correct with the dataset value** (or the per-run value
   from the CSV).
   Decided (coordinator, 2026-11-22, user asleep; revisit): correct per run from `drift.csv` (`drift.py`, a port of the
   explorer's `align_run.py`; values
   identical to the explorer's CSV); adaptor option `drift_correction="run"|"dataset"|None`, default "run".
3. **Acoustic delay**: MISC sits 2.6 ms after the trigger; the authors use 3 ms after the trigger ("measurements
   28.06.24", not described). If their 3 ms is the acoustic onset at the ear, the earphone/tube adds ~0.4 ms to MISC.
   **Default: onset = MISC onset + 0.4 ms** (= the authors' 3 ms on average), documented as an assumption; the
   alternative is MISC onset + 0 (electrical). Either way < 1 sample.
   Decided (coordinator, 2026-11-22, user asleep; revisit): onset = first audiobook trigger (events.tsv) + the run's
   MISC001 onset (drift.csv, fractional
   samples) + 0.4 ms (`ACOUSTIC_DELAY_MS`); trial = whole wav. Provenance: `stimtrack_xcorr`, hardware trigger,
   drift_ppm per run, jitter_ms 0.01 (MISC window-lag sd ~0.004 ms; the 0.36 ms trigger residual is the 1 ms
   TTL sampling and does not enter the onset).
4. **OLSA**: short sentences (~2.2 s, ISI >= 1 s) in continuous noise; neither the sentences nor the noise are
   shared (only 64 Hz clean-speech envelopes, `stimuli/olsa/sentences/*.wav`). **Default: skip** (not continuous;
   no audio). Possible later: the whole block as one trial with the MISC001 recording (presented mixture, 1 kHz,
   330 Hz bandwidth) as the stimulus, if the licence of the OLSA material allows redistributing that recording
   (it is in the CC0 MEG files already).
   Decided (coordinator, 2026-11-22, user asleep; revisit): skip.
5. **Chirps and empty room**: skip (not continuous speech; no stimulus). The audiobook trial starts at the first
   code-1 event, so the chirp block before it is excluded.
   Decided (coordinator, 2026-11-22, user asleep; revisit): skip (chirps, empty room).
6. **sub-01 (pilot)**: include its two audiobook1 runs with the pilot wavs (`stimuli/audiobooks/pilot/`; MISC
   confirms them, r 0.98 / 0.998). Stimulus names must differ from the final versions (e.g. `pilot_audiobook1_run-01`)
   because a stimulus name maps to one file. Its 32 EEG channels: **default drop** (pilot only, reference
   undocumented; the dataset is MEG).
   Decided (coordinator, 2026-11-22, user asleep; revisit): include with the pilot wavs as stimuli
   `pilot_audiobook1_run-0N`; EEG dropped.
7. **Channels kept**: MEG (mag + grad), EOG001/002 (`eog`), ECG003 (`ecg`), MISC001 and MISC002 (`misc`, audio copy
   left/right, described in the metadata). **Default drop** MISC007 (experimenter's microphone), STI*, IAS*,
   SYS201 and the derivative's CHPI* channels.
   Decided (coordinator, 2026-11-22, user asleep; revisit): as the default (the raw files have no CHPI channels;
   head-position info and dig are kept).
8. **cHPI** lines at 261-328 Hz remain in the data (inside the 330 Hz band; above the 250 Hz edge of the
   brainstem tier). Default: leave them (do not filter during standardisation); note in the metadata.
   Decided (coordinator, 2026-11-22, user asleep; revisit): left in; noted in the provenance (`chpi`) and README.
9. Conditions: `audiobook1` and `audiobook2` (two narrators, two stories) as conditions, run number as trial;
   validate per condition (PLAN section 3).
   Decided (coordinator, 2026-11-22, user asleep; revisit): conditions `audiobook1`, `audiobook2`; trial = presentation
   order (1-2 audiobook1 run 1-2,
   3-4 audiobook2 run 1-2; sub-01: 1-2), run number in the provenance. Stimuli: wav as shipped (float32,
   44.1 kHz) + the shipped TextGrid (words, phones; xmax = wav duration).

## 10. Standardisation (2026-11-22)
- `adaptor.py`, `drift.py` -> `drift.csv` (94 runs; onset 2.614 +- 0.320 ms after the first trigger, drift
  485.070 +- 0.026 ppm, residual vs triggers -0.011 +- 0.028 ppm: identical to the explorer's `audiobook.csv`).
- **Audio-copy check on the standardised data** (`tmp/review/habersetzer2025/scripts/misc_check.py`): MISC001 of the
  trial vs the wav (both 2-200 Hz, 1 kHz), 10 s windows, sub-sample lag (> 0: MISC later). Drift corrected per run:
  - sub-05 trial 1: start -0.379/-0.381/-0.379 ms, end (540-550 s) -0.385/-0.374/-0.374 ms (r 0.95);
  - sub-05 trial 4: start -0.374/-0.380/-0.383, end (515-525 s) -0.386/-0.378/-0.376 ms (r 0.94);
  - sub-12 trial 1: start -0.385/-0.385/-0.382, end -0.392/-0.381/-0.383 ms (r 0.95);
  - sub-12 trial 4: start -0.394/-0.399/-0.402, end -0.403/-0.397/-0.395 ms (r 0.94).
  So the audio copy sits at lag 0 minus the 0.4 ms assumed acoustic delay, constant from start to end (< 0.03 ms
  change over 9 min). Without drift correction the lag grows from ~2 ms in the first windows to beyond the +-30 ms
  search range by the end (r falls from 0.95 to 0.04-0.08), as expected for +485 ppm (272 ms at 560 s).
- Pilot (all 24 subjects, audiobook runs): 94 trials, 0 failures, 1000 Hz, 311 channels (306 MEG, 2 EOG, 1 ECG,
  MISC001/002), 2 bads, dig kept (159-306 points). audiobook1 48 trials / 24 subjects / 7.24 h, audiobook2 46 / 23 /
  6.58 h; 13.82 h total; trial length 494.3-561.6 s (= the wav). No trial used a weaker alignment method (all
  `stimtrack_xcorr` from the per-run MISC001 fit). 59 GB on disk; peak RSS 5.8 GB (one process), 50 min.

## 11. Validation and coherence (2026-11-22)
Results: `validation.json` (this folder). Scripts (tmp, will be deleted):
`tmp/review/scripts/meg/habersetzer2025_validate.py`, `habersetzer2025_summary.py`; logs and figures in
`tmp/review/habersetzer2025/validation/` (`run.log`, `summary.log`, `figs/validation_habersetzer2025_{tsss,raw}_*.png`,
`figs/backward_sweep_latency.png`). Coherence: `tmp/review/coherence_batch/{128,native}/habersetzer2025_audiobook{1,2}`
`.{json,npz,png}`.
- Two variants, 102 magnetometers, no re-referencing, 24 subjects / 94 trials: **raw** (as stored) and **tSSS**
  (validation only): bads MEG2143, MEG1112 + `find_bad_channels_maxwell` on the first 120 s of each trial (extra
  bads e.g. MEG1023 in many subjects, MEG0113, MEG1413, MEG1533, MEG1713, MEG2522, MEG2533, MEG2633 in single
  runs; `tsss_bads` in validation.json), `maxwell_filter` with the subject's shipped fine-cal + cross-talk, tSSS
  st_duration 10 s, origin fitted to the head shape, head frame, no movement compensation.
- **tSSS:** low median r 0.060 (24/24 vs circular and mismatch nulls; TRF peak 125 ms); backward (LOTO decoder,
  0.5-8 Hz, 0-250 ms) median r 0.346 (24/24); mlr (30-60 Hz, 18-45 ms) median SNR 1.35, mean 1.40, p 0.01,
  18/24 (not sig.: 9, 11, 12, 16, 18, 22); brainstem (30-250 Hz, 28-45 ms) median 1.24, mean 1.25, p 0.01, 14/24
  (not sig.: 9, 10, 11, 13, 14, 16, 18, 20, 22, 23). Per condition: audiobook1 low 0.053, mlr 1.20 (8/24),
  brainstem 1.21 (12/24); audiobook2 low 0.056, mlr 1.21 (9/23), brainstem 1.10 (8/23); all pass. The 30-250 Hz
  GFP peaks at ~20 ms and ~25 ms (just before the window) with a lag-0 spike (GFP rel 1.41); 30-60 Hz peaks at
  ~27 and 38 ms (figure). **Tier brainstem (weakly)**, all 94 trials.
- **Raw:** low 0.030 (23/24; sub-19 not sig.), backward 0.260 (24/24), mlr median 1.21 / mean 1.26 (7/24, p 0.01),
  brainstem median 0.99 / mean 1.01, p 0.0495, 1/24, GFP peak at **0 ms** (stimulus artefact), nothing in the
  window above the noise: not counted. Per condition the brainstem tier fails (p 0.22) and mlr passes
  (audiobook1 1.08, p 0.03, 1/24; audiobook2 1.20, p 0.01, 7/23). **Raw reaches mlr.** validation.json keeps the
  formal `raw all` tier ("brainstem"); `validation_tier_basis` is "tsss".
- **Backward lag sweep** (tSSS, 64 Hz, +-1 s, 15.6 ms steps, parabolic peak): +0.7 ms (95% CI -0.0..+1.3);
  audiobook1 -0.1 ms, audiobook2 +1.4 ms; subject peaks -1.9..+4.5 ms, 24/24 within one sample. Raw: +0.9 ms
  (0.3..1.6). End-to-end confirmation of the per-run +485 ppm drift correction and the MISC onsets (uncorrected
  drift would shift the end of a run by 272 ms). Validator residual drift -8.2 +- 13.9 ppm (tSSS), jitter SD
  9.3 ms (noise-dominated, says nothing about timing).
- **Latencies** (forward TRF, Hilbert envelope, 1-15 Hz, 128 Hz, GFP; tSSS): audiobook1 M50 subject median 53 ms
  (local max in 15/24; none in the grand average), M100 grand 94 ms, subject median 108 ms; audiobook2 M50 grand
  46 ms (subject median 46.5 ms, 20/23), M100 grand 109 ms, subject median 112 ms. Raw: M50 grand 42 / 41 ms, M100
  115 / 108 ms.
- **Reference MEG datasets** (same code, magnetometers, mean SNR): gwilliams2023 (20) low 0.046, mlr 2.09 (20/20),
  brainstem 1.55 (19/20); armeni2022 (3) 0.061, 2.57, 3.03; schueller2024 (19) 0.020, 1.05 (4/19), 1.68 (18/19);
  libribrain100 sub-0 tSSS (all MEG) 0.030, 0.95 (n.s.), 1.10 (tier low). habersetzer2025 has the weakest
  high-frequency response of the brainstem-tier MEG datasets.
- **Coherence** (raw, 102 magnetometers, no re-reference, 5 s Hann windows, 4 s overlap, one global-shift
  surrogate; ratio to the surrogate), 128 Hz / native 1000 Hz:
  - audiobook1 (24 subj., 48 trials): 0.2-1 Hz 3.84 / 3.84, 1-4 2.86 / 2.84, 4-8 1.74 / 1.73, 8-15 1.17 / 1.14,
    15-30 1.06 / 1.07, 30-60 1.09 / 1.18; native 60-120 1.71, 120-250 1.75, 250-500 1.20.
  - audiobook2 (23 subj., 46 trials): 4.13 / 4.13, 2.56 / 2.57, 1.70 / 1.73, 1.15 / 1.18, 1.12 / 1.11,
    1.15 / 1.15; native 60-120 1.42, 120-250 1.69, 250-500 1.22.
  The 60-250 Hz ratios on raw data most likely reflect the lag-0 stimulus artefact (raw 30-250 Hz TRF), not a
  neural response (not verified; coherence was not run on tSSS data).
- DNN offset: not applicable (EEG-trained match-mismatch classifier).
- Provenance: `validation_tier="brainstem"` and `validation_note` ("brainstem tier with tSSS ...; raw data reach
  mlr") in `adaptor.py`; checked that the adaptor parses (94 records).

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**good**: Hardware trigger box on the sound card's S/PDIF + MISC001 audio copy per run (+2.61 ms); drift +485 ppm from the audio copy corrected; +0.4 ms acoustic delay assumed; brainstem (tSSS).
