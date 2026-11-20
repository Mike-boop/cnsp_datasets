# polonenko2025: peaky speech with 1-5 simultaneous talkers (OpenNeuro ds005408)

## 1. Source
- OpenNeuro ds005408 v1.0.1 (`10.18112/openneuro.ds005408.v1.0.1`), EEG-BIDS, licence CC0.
- Polonenko MJ & Maddox RK (2025). The effect of speech masking on the human subcortical response to continuous
  speech. *eNeuro* 12(4) ENEURO.0561-24.2025. doi:10.1523/ENEURO.0561-24.2025
- Code: https://github.com/polonenkolab/peaky_snr. Read for this review: `exp_code/exp_peaky_snr.py` (v1, sub-01
  to 06), `exp_code/exp_peaky_snr_v2.py` (v2, sub-07 on), `analysis_code/analysis_peaky_snr_eeg_regressors.py`.
- Same lab setup as polonenko2024; shared code in `datasets/maddox_base/common.py`.

## 2. Layout
- `sub-01`..`sub-25/eeg/sub-XX_task-peakysnr_run-0N_eeg.{vhdr,vmrk,eeg}`, `_events.tsv`; two runs for sub-04,
  08, 19, 23 (one run otherwise).
- `stimuli/speech/<story>/<story>_NNN_peaky_diotic_regress.hdf5` (5 stories x 396 files): `audio` (48 kHz,
  480000 samples = 10 s; no `fs` entry), `pinds`, `anm` (2 x 480000), `f0`. `stimuli/clicks/` (ABR only).
- 41 GB (16 GB EEG, 24 GB stimuli).

## 3. Stimulus <-> trial mapping
- 780 trials per subject: 60 x 10 s click trials (**left out**) and 720 x 10 s speech trials, 180 per condition,
  randomised: clean (1 talker), 0 dB (2), -3 dB (3), -6 dB (5 talkers), all male narrators, each story at 65 dB
  (rms 0.01). The trial audio is the sum of the talkers, diotic. Story tokens were randomised, so the stories cannot
  be followed (passive listening, silent captioned videos).
- `events.tsv` gives `snr`, `n_simultaneous_stimuli` and one file per story (`file_story1..5`, `n/a` if absent).
  **Verified independently**: the 48/49 bits stamped after each start trigger (1 stim, 2 SNR, 5 x 9 token bits
  (511 = story absent), + 1 polarity bit from sub-07) decode to the same type, SNR, tokens and sample (+8) for every
  trial of all 29 recordings, 0 mismatches.
- **Polarity (not in events.tsv):** v2 (sub-07 to 25) inverts half the speech trials (`trial_audio *=
  flipping[flip_idx]`, `flipping = [-1, 1]`, so bit 0 = inverted): 360 of 720 per subject. v1 (sub-01 to 06) has a
  "flip phase" comment but no code: no inversion, no bit. The authors' analysis (pulse trains, ANM averaged over
  both polarities) does not depend on polarity, so they did not need it; an audio-based regressor does.

## 4. Speech features
- Raw audio per story (`audio`, 48 kHz, float64, as played; mixtures = sum of the stories). Glottal pulse indices
  (`pinds`) and auditory-nerve-model regressors (`anm`). No transcripts or word alignments.

## 5. Neural data
- As polonenko2024: BrainVision actiCHamp + EP-PreAmp, **10 kHz**, float32, µV; channels `A1`, `A2` = FCz minus
  left / right earlobe; no stimtrack.
- 25 participants (all in the paper), 19-37 years.

## 6. Alignment
- Sound-card triggers (expyfun), S 1 = start, S 2 = 20 ms before the end, S 4 / S 8 = ID bits. ER-2 tube delay
  0.81 ms (`events.tsv` samples include 8 samples for it).
- **Drift:** 24.0-25.9 ppm per run (per-trial durations quantised to 2-3 samples; mean over the run's trials).
- Recording pauses: sub-23 run-01 (two, inside click trials) and run-02 (one, inside a click trial). Trials
  crossing a pause or the end of a run are skipped: only sub-19 run-01's last speech trial (the recording stops
  4.5 s into it; it was not repeated in run-02, so sub-19 has 718 speech trials).

### Adaptor
- One TrialRecord per speech trial; every story in the trial is its own stimulus `<story>_NNN` (inverted trials:
  `<story>_NNN_inv`, audio negated, `anm` rows swapped), none attended. Conditions `talkers1-clean`,
  `talkers2-snr0dB`, `talkers3-snr-3dB`, `talkers5-snr-6dB`. Trials numbered across runs in recording order.
- Onset = S 1 + tube delay; drift correction per run (default on); 1000 Hz by default (`sfreq=None`: 10 kHz);
  features `audio`, `pulses`, optional `anm` (`save_anm=True`).
- Provenance: `alignment_method=hw_trigger` (sound-card), `drift_ppm` per run, `jitter_ms` ~0.

## 7. Cross-subject duration check
- All 1980 speech files are 480000 samples (10.000 s); S 2 - S 1 = 99802-99803 samples in every complete trial.

## 8. Data size
25 participants, 17,998 speech trials x 10 s = **50.0 h in total, 2.00 h per participant** (1.99 for sub-19).
Per condition: 4500 (clean, 0 dB) / 4499 (-3, -6 dB) trials = 12.5 h, 0.50 h per participant.

## 9. Polarity check (done, sub-07, 09, 10)
`tmp/review/scripts/polonenko2025_polarity.py` -> `tmp/review/polonenko2025/polarity/`: frequency-domain
deconvolution (30-2000 Hz, 10 kHz, drift-corrected EEG, mean of A1/A2) per subject and polarity group.
- Signed audio with the decoded flips **ignored**: the TRFs of normal and inverted trials are anti-correlated
  (r = -0.97, -0.71, -0.69); with the flips **applied** (the adaptor's `_inv` stimuli): r = +0.97, +0.71, +0.69.
  The polarity bit and its sign (bit 0 = inverted) are right.
- The polarity-following component is a sharp spike exactly at **-0.81 ms**, when the sound leaves the ER-2
  transducer: the earphone's electrical artefact (plus fine-structure FFR). Its position also confirms the onset
  (marker + tube delay) to within a 10 kHz sample.
- Adding the two groups' TRFs (file audio) cancels the artefact; subtracting keeps only it. Users who want
  artefact-free audio TRFs can average over polarities (sub-07 on). polonenko2024 alternates no polarity, so the
  artefact cannot be cancelled there; it shows in its brainstem-tier TRF at about -3..+1 ms.
- Half-wave-rectified audio as played: wave V at ~7.5 ms identical in both groups (r = 0.94-0.99); with flips
  ignored the inverted group is misaligned (r = -0.25..-0.94).

## 10. To check in validation
- Validate without re-referencing (`--reference ""`; both channels are FCz minus an earlobe).
- The validator scores the first stimulus by name (one of the talkers in mixtures): per-condition scores will drop
  with the number of talkers.
