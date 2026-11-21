# stoll2025: selective attention, subcortical + cortical EEG (OpenNeuro ds006434)

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

## 7. exp2 (dichotic) findings
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

## 8. exp3 (passive) findings
- 32 trials: 8 story/distractor pairs (`stim/{fM,fW}/{story,distractor}[trial_order - 1]`, 48 kHz, padded to
  8,214,463 samples = 171.13 s), each played 4 times in a row; story + distractor summed diotically. 4 ID bits
  (3 trial order, 1 focus) between S 1 and S 2; events.tsv `trial_order` (1-4), `focus_order` (0 fM, 1 fW).
- **Polarity alternates across the 4 repetitions** (notebook: "trial polarity alternated"; not in events.tsv).
  From the ER-2 artefact (template projection, 40 s windows agree within every trial, so no within-trial flips):
  sub-passive18 plays the stored waveform in repetitions 1 and 3, sub-passive17 in 2 and 4: the starting
  polarity differs between subjects. Per-trial result for all subjects: section 9.
- Marker drift (S 2 at 171.1146 s): 11.5 ppm (sub-passive17, 18). The 25 kHz EEG is resampled to 1 kHz.
- The authors analyse 10-130 s of each trial (padding); the adaptor keeps the full trial.

## 9. Per-trial polarity (all subjects)
`tmp/review/scripts/stoll2025_trial_polarity.py` -> `tmp/review/stoll2025/trial_polarity/`: per trial (and story),
deconvolution on the stored audio, projected onto the ER-2 artefact template (exp1 sub-diotic23, stored audio;
the artefact is biphasic, so the sign of the largest peak alone is unreliable).
- exp1 controls (02, 05, 18, 23): strong trials (|z| > 3) 76-100 % positive: stored = played.
- exp3: polarity alternates by repetition. 12 subjects play the stored waveform in repetitions 1 and 3 (every
  strong trial consistent); **sub-passive17 is reversed** (16/16 strong trials); **sub-passive20 has no measurable
  artefact** (0 strong trials): the majority pattern is assumed (unverified).
- exp2: no alternation: strong subjects are uniformly negative for both stories (single FCz-earlobe channel and TDT
  hardware, so the absolute sign is not comparable with exp1; the notebook averages both ANM polarities). The
  stored wavs are taken as played. In sub-dichotic03 the artefact sign follows the ear the story was played to
  (median z -5.8 vs +3.0 by ear), other strong subjects differ in size by ear: independent confirmation that the
  ear routing follows `att_side`/`att_story`.

## 10. Adaptor (stoll2025 = subcortex; stoll2025_cortex = 32-channel cortical files of exp1 and exp2)
- Subjects: label number + 100 x experiment (exp1 101-129, exp2 202-225, exp3 317-331). Conditions
  `diotic-attend-{female,male}`, `dichotic-attend-{female,male}-side{0,1}` (side of the attended talker),
  `passive-{fM,fW}`. Trials numbered by start marker within the recording.
- Onset = S 1 (markers include the tube delay). Cortex trials use the subcortical marker time (same recording,
  split by the authors; cortex markers are the subcortical ones floored to 1 kHz / 500 Hz).
- Drift: exp1 per recording from S 2 (sub-diotic06: 24.8 ppm), exp2 -5 ppm, exp3 per recording from S 2.
- 1000 Hz by default; cortex keeps 1 kHz (exp1) and 500 Hz (exp2) (never upsampled); exp3 25 kHz -> 1 kHz.
- Stimuli: exp1 `wrinkle_chNN`, `alchemyst_chNN` (audio 48 kHz, pulses; `anm` with save_anm=True), attended one
  marked; exp2 `<talker>_dichotic_chNN` (24414.0625 Hz as shipped; the wav header says 24414); exp3
  `exp3_<fM|fW>_<story|distractor>K[_inv]` (none attended; `_inv` = negated, from section 9).
- Not included: exp1 silences (`*_silent`: in the stimulus file, the authors zero the EEG there), exp2 ANM
  regressors (36 x 640,000 at 10 kHz: 36 entries for 30 chapters, unclear), exp3 EMD features (truncated file).

## 11. Data size (from the adaptor's trials; stimulus durations)
66 participants, 5234 trials (subcortex). exp1 28 x 2.13 h (120 x 64 s; 59.7 h); exp2 24 x 1.06 h (sub-dichotic02
0.82; 25.4 h); exp3 14 x 1.52 h (32 x 171.1 s padded; README: ~117 s of audio each, i.e. ~1.04 h; 21.3 h padded).
Total ~106 h (padded exp3) or ~99 h. Per condition: diotic attend female / male 28 x 1.07; dichotic each of 4
(attended talker x side) 24 x 0.26; passive fM / fW 14 x 0.76 (padded).

## 12. Upstream issues (to report; collected in `tmp/review/upstream_issues.md`)
1. `stimuli/exp1Diotic/flip_signs` and `stimuli/exp3Passive/EMDdict_padded_48k` truncated on OpenNeuro.
   flip_signs is only needed to undo the within-trial polarity alternation (the stored audio is as played);
   the README should also say that the stored exp1 audio alternates polarity across segments.
2. (Not an issue: the markers do include the tube delay, as the README says; section 4.)
3. README: exp2 cortex said to be 1 kHz; the files are 500 Hz.
4. exp2: which side `att_side` 0/1 means, and which earlobe each subject's electrode was on, are undocumented.
5. exp3: the per-trial polarity (alternating across repetitions, starting polarity differs between subjects) is
   not in events.tsv.
6. exp2 has no end (S 2) markers; drift (-5 ppm, from the EEG) cannot be checked from triggers.

## 13. Validation (2026-11-20; subcortex, 1000 Hz, no re-reference; first run failed on a resampler bug, re-run)
`tmp/review/stoll2025/validation.{json,png}`; per condition `tmp/review/stoll2025/by_condition/`. The validator
scores the attended talker (diotic/dichotic) or the first stimulus by name (passive: the distractor).

| condition | low r (sig) | low peak | mlr SNR (sig) | brainstem SNR (sig) | tier |
|---|---|---|---|---|---|
| all (66 subjects) | 0.040 (0.91) | 78 ms | 1.99 (0.55) | 2.55 (0.77) | brainstem |
| diotic-attend-female | 0.030 (0.82) | 94 ms | 2.05 (0.61) | 1.90 (0.71) | brainstem |
| diotic-attend-male | 0.040 (0.93) | 94 ms | 1.28 (0.25) | 2.44 (0.71) | brainstem |
| dichotic-attend-female-side0 | 0.046 (0.67) | 266 ms | 1.43 (0.21) | 1.85 (0.42) | brainstem |
| dichotic-attend-female-side1 | 0.050 (0.62) | 250 ms | 1.57 (0.29) | 1.46 (0.21) | brainstem |
| dichotic-attend-male-side0 | 0.048 (0.58) | 62 ms | 1.43 (0.21) | 2.04 (0.67) | brainstem |
| dichotic-attend-male-side1 | 0.051 (0.62) | 234 ms | 1.21 (0.12) | 1.71 (0.38) | brainstem |
| passive-fM | 0.030 (0.79) | 16 ms | 1.28 (0.29) | 1.51 (0.43) | brainstem |
| passive-fW | 0.030 (0.71) | 0 ms | 1.11 (0.14) | 1.19 (0.21) | low |

Low-tier peaks at 230-270 ms in three dichotic conditions (single FCz-earlobe channel; 0.5-8 Hz TRF of one
channel peaks late), not an offset: the brainstem tier passes with the same onsets. To compare with the
coherence results (`tmp/review/coherence_peaky/`).

## 14. Coherence: attended vs ignored (2026-11-21; open observation)
`tmp/review/coherence_peaky/stoll2025*` (coherence of the 5 s-window envelope with the EEG / median of a
mismatched-trial null), plot `tmp/review/coherence_peaky/stoll2025_attention.png`, same talker attended vs ignored:
- dichotic: attended > ignored at nearly all frequencies, both montages (as expected);
- **diotic: ignored > attended at ~1-3 Hz** (up to 2x: subcortical female talker 14x vs 7x the null at 1 Hz;
  cortical: smaller, male talker about equal), while attended > ignored at 4-10 Hz.
A swapped attention label would flip both bands, so a labelling error is unlikely; the lowest bins are the weakest
estimates (5 cycles per window at 1 Hz, small noisy null), and attended/ignored come from different trials and
blocks. Not investigated further (per-subject ratios or 10 s windows would tell).
