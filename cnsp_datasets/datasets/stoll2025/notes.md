# stoll2025: selective attention, subcortical + cortical EEG (OpenNeuro ds006434) — in progress

## 1. Source
- OpenNeuro ds006434 v1.2.0 (`10.18112/openneuro.ds006434.v1.2.0`), EEG-BIDS.
- Stoll TJ et al. (2025). The auditory brainstem response to natural speech is not affected by selective
  attention. Code: dataset `code/` (`diotic_analysis.ipynb`, `dichotic_analysis.ipynb`, `passive_analysis.ipynb`)
  and https://github.com/maddoxlab/stoll_et_al_selective_attention. Shared code: `datasets/maddox_base/common.py`.

## 2. Layout and experiments
- exp1Diotic: 28 subjects (`sub-diotic01..29`, no 15), `task-exp1DioticCortex` (32 ch, 1 kHz) and
  `task-exp1DioticSubcortex` (A1, A2 = FCz minus each earlobe, plus TM (eardrum) for subjects 1, 3, 4, 7-13, 16,
  18; 10 kHz). Recorded simultaneously at 25 kHz, split and downsampled by the authors.
- exp2Dichotic: 24 subjects, Cortex (32 ch, **500 Hz**; README says 1 kHz) and Subcortex (FCz, 10 kHz).
- exp3Passive: 14 subjects, A1, A2 at **25 kHz**.

## 3. exp1 trial mapping (verified)
- 120 x 64 s trials: chapter pairs of two audiobooks summed diotically (A Wrinkle in Time, female, `wri`; The
  Alchemyst, male, `alc`), attend one per trial. Order (same for every subject, notebook): trial t plays chapter
  `chapt_ind[t]` = 0,1,0,1,2,3,2,3,... and attends female if `((t + 2) // 4) % 2 == 0`. Each attention group hears
  chapters 0..59 in order, so every chapter pair is heard twice (once attending each talker).
- **Verified twice**: events.tsv `attend`/`chapter` match the formula in all 28 subjects, and the 7-bit trial ID
  after each start trigger decodes (MSB first) to [attended talker (1 bit: 0 female), chapter (6 bits)] =
  0, 1, 64, 65, 66, 67, 2, 3, ... as the formula predicts.
- Stimuli: `stimuli/exp1Diotic/stim+pulses+silences.hdf5`: `alc_aud_all`, `wri_aud_all` (60 x 1 x 3,072,000:
  64 s at 48 kHz), pulse indices per chapter, silent intervals (`*_silent`, samples; the authors zero the EEG there
  when deconvolving), fs 48000. `anm_regressors.hdf5`: (2 polarities, 60, 3,072,000) per talker.

## 4. exp1 timing
- events.tsv `sample` equals the S 1 marker in every trial, and **the markers already include the tube delay**
  (README: "corrected for the tubing delay"): the ER-2 electrical artefact sits at -0.8 ms relative to the
  marker in the EEG (section 6), i.e. the marker is the sound at the eardrum. The adaptor must not add 0.81 ms.
- S 2 at 63.98 s (`drift_ref_times = stim_dur - 0.02`). **Drift: two clusters**: 24.1-25.2 ppm for sub-diotic01
  to 16 and 10.8-12.1 ppm for sub-diotic17 to 29 (hardware/sound-card change partway through the study).
  **sub-diotic06 has no S 2 markers**: drift from its cluster's median.
- No recording pauses; all 3360 trials lie inside their recordings.

## 5. Polarity of exp1: the stored audio is the played waveform
- `stimuli/exp1Diotic/flip_signs` is truncated on OpenNeuro (1,213,647,918 of 2,949,128,196 bytes; h5py cannot
  open it). Its expected size is exactly 2 talkers x 60 chapters x 3,072,000 float64 (+ 8 kB header): it holds a
  **±1 envelope per chapter and talker** (`alc_flip_sign`, `wri_flip_sign`), not one sign per chapter. The data
  start at byte 8192; what arrived covers `alc` chapters 0-48 completely (and 49 partly), no `wri`.
- Recovered envelopes: the sign strictly alternates, ~22-35 times per 64 s chapter (segments 0.2-6.9 s), with
  ~38-sample ramps, always where the audio is silent (rms 0.0000 within ±10 ms of a flip); flips also occur in
  short pauses that are not in `*_silent`, so the envelope cannot be regenerated from the silences.
- **Which waveform was played? The stored one** (EEG, `tmp/review/scripts/stoll2025_flipcheck.py`, alc chapters
  0-48, ER-2 artefact at -0.8 ms in the TRF):

  | subject | stored audio: spike (SNR) | stored x flip: spike (SNR) |
  |---|---|---|
  | diotic23 | +11.6 µV (93) | -1.5 µV (18) |
  | diotic18 | +3.5 µV (81) | -0.25 µV (9) |
  | diotic05 | +2.4 µV (47) | +0.22 µV (11) |
  | diotic27 | +3.5 µV (43) | -0.22 µV (4.5) |
  | diotic02 | +0.79 µV (23) | -0.09 µV (3.3) |
  | diotic11 | +0.28 µV (5.5) | -0.05 µV (2.6) |

  The stored audio gives a large artefact of the same sign in every subject; applying the flips destroys it. So
  the flips were applied when the stimuli were made (stored = original x flip, polarity alternating across
  segments within each trial), and the notebook's `aud * flip * -1` undoes them for its fine-structure regressor.
  **The adaptor uses the stored audio as played**; flip_signs is only needed to recover the unflipped original.
- Earlier per-trial/per-chapter sign scoring (`tmp/review/scripts/stoll2025_polarity.py`) showed no chapter
  structure, as expected for within-trial flips; its single-trial scores in weak subjects are noise.

## 6. Evidence files
`tmp/review/stoll2025/polarity/` (per-trial TRFs, plot), `tmp/review/stoll2025/flipcheck/`.

## 8. exp2 (dichotic) findings
- 60 x 64 s trials (sub-dichotic02: 47, the recording stops inside the 47th; sub-dichotic12: 61 starts, the 14th
  was restarted after 26.6 s). The adaptor skips trials that run past the end and trials whose next start comes
  less than 64 s later (the authors drop the same two).
- **8 ID bits come before S 1** (`events[si-8:si]`): 6 chapter bits, attended story (0 = female/Wrinkle), attended
  side; they match events.tsv `chapter_ind`, `att_story`, `att_side` in all 1428 trials. Chapters 0-29, each
  twice.
- Stimuli `stimuli/exp2Dichotic/wrinkle_alchemyst%03i.wav` (by chapter): **24414.0625 Hz (TDT)**, int16,
  1,562,500 samples (64 s), **channel 0 = Wrinkle, channel 1 = Alchemyst** (by story, not by ear; the notebook's
  regressors). Which ear heard which story follows from `att_side` and `att_story`, but **side 0/1 -> left/right
  is not documented** (participants.tsv has no electrode side; the notebook only uses relative sides): kept as
  `side0`/`side1`, a question for the authors.
- **No S 2 markers**, so no marker drift. From the ER-2 artefact (first vs second half of each trial;
  `tmp/review/scripts/stoll2025_artefact_timing.py`): about **-5 ppm** in every subject with a strong artefact
  (03, 08, 11, 21, 22, 23, 25: -4.6..-5.6 ppm, tight IQR); weaker subjects scatter around it. Applied as one value.
  (Control: exp1 sub-diotic18 gives 12.5 / 10.4 ppm vs 11 ppm from its markers; weak subjects are noisy.)
- Artefact at about -0.8 ms relative to S 1 in all subjects: markers = sound at the eardrum, as in exp1.
- Single subcortical channel `FCz` (FCz minus one earlobe, side counterbalanced across subjects, not documented
  per subject).

## 9. exp3 (passive) findings
- 32 trials: 8 story/distractor pairs (`stim/{fM,fW}/{story,distractor}[trial_order - 1]`, 48 kHz, padded to
  8,214,463 samples = 171.13 s), each played 4 times in a row; story + distractor summed diotically. 4 ID bits
  (3 trial order, 1 focus) between S 1 and S 2; events.tsv `trial_order` (1-4), `focus_order` (0 fM, 1 fW).
- **Polarity alternates across the 4 repetitions** (notebook: "trial polarity alternated"; not in events.tsv).
  From the ER-2 artefact (template projection, 40 s windows agree within every trial, so no within-trial flips):
  sub-passive18 plays the stored waveform in repetitions 1 and 3, sub-passive17 in 2 and 4: the starting
  polarity differs between subjects. Per-trial result for all subjects: section 10.
- Marker drift (S 2 at 171.1146 s): 11.5 ppm (sub-passive17, 18). The 25 kHz EEG is resampled to 1 kHz.
- The authors analyse 10-130 s of each trial (padding); the adaptor keeps the full trial.

## 10. Per-trial polarity (in progress)
`tmp/review/scripts/stoll2025_trial_polarity.py` (template = exp1 sub-diotic23 artefact with stored audio).

## 7. Upstream issues (to report; collected in `tmp/review/upstream_issues.md`)
1. `stimuli/exp1Diotic/flip_signs` and `stimuli/exp3Passive/EMDdict_padded_48k` truncated on OpenNeuro.
   flip_signs is only needed to undo the within-trial polarity alternation (the stored audio is as played);
   the README should also say that the stored exp1 audio alternates polarity across segments.
2. (Not an issue: the markers do include the tube delay, as the README says; section 4.)
3. README: exp2 cortex said to be 1 kHz; the files are 500 Hz.
4. exp2: which side `att_side` 0/1 means, and which earlobe each subject's electrode was on, are undocumented.
5. exp3: the per-trial polarity (alternating across repetitions, starting polarity differs between subjects) is
   not in events.tsv.
6. exp2 has no end (S 2) markers; drift (-5 ppm, from the EEG) cannot be checked from triggers.
