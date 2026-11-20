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
- events.tsv `sample` equals the raw S 1 marker in every trial: the README says onsets are corrected for the tube
  delay, but the events are not (or the markers were shifted too: checked from the EEG, section 6).
- S 2 at 63.98 s (`drift_ref_times = stim_dur - 0.02`). **Drift: two clusters**: 24.1-25.2 ppm for sub-diotic01
  to 16 and 10.8-12.1 ppm for sub-diotic17 to 29 (hardware/sound-card change partway through the study).
  **sub-diotic06 has no S 2 markers**: drift from its cluster's median.
- No recording pauses; all 3360 trials lie inside their recordings.

## 5. Polarity of exp1 (flip_signs truncated upstream)
- `stimuli/exp1Diotic/flip_signs` is truncated on OpenNeuro (1,213,647,918 of 2,949,128,196 bytes; h5py cannot
  open it). It holds a per-chapter polarity per talker (`alc_flip_sign`, `wri_flip_sign`); the notebook's
  fine-structure regressor is `aud_all[chapter] * flip_sign[chapter] * -1`, so the stored audio is not always the
  played polarity. Recovered from the EEG instead: section 6 (in progress).

## 6. Polarity recovery (in progress)
Script `tmp/review/scripts/stoll2025_polarity.py`.

## 7. Upstream issues (to report; collected in `tmp/review/upstream_issues.md`)
1. `stimuli/exp1Diotic/flip_signs` and `stimuli/exp3Passive/EMDdict_padded_48k` truncated on OpenNeuro.
2. README: onsets "already corrected for the tubing delay", but events.tsv samples equal the raw markers (to
   confirm from the EEG, section 6).
3. README: exp2 cortex said to be 1 kHz; the files are 500 Hz.
