# thornton2025: two competing talkers, dry-contact in-ear EEG

EEG from two dry-contact in-ear electrodes while listeners attended one of two audiobook talkers (one male, one
female) presented diotically over headphones. English. 16 trials of 2.2-4.0 min; the attended talker alternates
every four trials (male in trials 1-4 and 9-12, female in 5-8 and 13-16; the same for every listener).

- **Source:** Zenodo 10260082, "Imperial College Ear-EEG Dataset for Auditory Attention Decoding"
  (`icl_earEEG_dataset.zip`, 0.56 GB), doi:10.5281/zenodo.10260082. **Licence: CC-BY-4.0.**
- **Paper:** Thornton MD, Mandic DP, Reichenbach T (2025). Comparison of linear and nonlinear methods for decoding
  selective attention to speech from ear-EEG recordings. *IEEE Access* 13, doi:10.1109/ACCESS.2025.3590490
  (preprint arXiv:2401.05187).

## Size
**19 participants, 303 trials, 14.9 h in total, 0.79 h per participant** (0.75-0.79; sub-002 has no trial 1).
- `attend-male`: 6.8 h (0.36 h per participant); `attend-female`: 8.1 h (0.43 h).
- The paper reports 18 participants; the release holds 19 (sub-000..sub-018). Which one is extra is not known.
  All 19 are included.

## What is provided
- **EEG:** 2 channels, `left_ear` and `right_ear` (dry in-ear electrodes), each referenced to an electrode at
  **FT7** (lower left forehead), ground on the right earlobe; 256 Hz (stored unchanged). No positions, no EOG.
- **Units:** the release's EEG is **z-scored per trial and channel** (mean 0, SD 1), so physical units are lost.
  It is stored as `eeg` with the z-scores multiplied by 1e-6 (1 SD reads as 1 uV). Do not compare amplitudes with
  other datasets.
- **Stimuli** per trial: `trial_TT_attended` and `trial_TT_ignored` (`audio`, 44.1 kHz float32, as shipped;
  RMS-normalised by the authors). `is_attended` marks the attended stream. No transcripts.
- Conditions `attend-male` / `attend-female`. The provenance sidecar also gives the story (1-4) and the reference.

## Alignment
- The authors recorded the headphone sound with microphones in the ear modules, cross-correlated these
  recordings with the audio and cut the EEG to start with the audio (paper II.B). The microphone recordings are
  not released, so the onsets cannot be re-measured. Timing kept as shipped (`stimtrack_xcorr`, by the authors).
- Clock drift: not estimable from the release (no markers); not corrected.
- **Alignment grade: medium.** The onsets are hardware-derived but cannot be verified here; validation confirms
  them (low tier passes, forward-TRF peak at 172 ms with nothing at negative lags, decoder lag sweep at 0 ms).
- The match-mismatch DNN offset check does not apply (it needs a scalp montage).

## Validation
All 19 participants, original FT7 reference, both channels.
- **Low tier** (forward model, 0.5-8 Hz, attended audio): mean r 0.021, population p 0.02 (circular shift) and
  0.05 (mismatched trials), 10/19 participants individually significant; pass. Middle-latency tier fails (SNR
  1.00), brainstem not testable (256 Hz).
- **Attended vs ignored** (backward decoder, leave-one-trial-out, 0.5-8 Hz): Hilbert envelope r 0.025 vs 0.009,
  attended > ignored in 17/19 (Wilcoxon p 7e-5), 30-s decoding accuracy 0.58; onset envelope r 0.027 vs 0.012,
  16/19, accuracy 0.65.
- Suitable for low-frequency envelope tracking and attention decoding with ear-EEG. Not suitable for
  high-frequency or latency-precise analyses, or for amplitude comparisons (z-scored data).

## Caveats
- EEG is z-scored per trial by the authors (the record calls it "unprocessed").
- sub-002 trial 1 is empty upstream (skipped).
- All listeners attended the same talker in the same trial, so talker identity and attention are confounded
  within a trial; the design balances them across trials.

Details: `notes.md`.
