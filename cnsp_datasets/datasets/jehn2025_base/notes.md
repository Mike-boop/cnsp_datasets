# jehn2025 notes (jehn2025_th / _ha / _ci share this adaptor)

Selective attention to one of two German audiobooks (Elbenwald, Polarnacht) played from left and right
loudspeakers, in normal-hearing (nh, 28), hearing-aid (hi, 29) and cochlear-implant (ci, 24) listeners. 20 trials
per subject: single speaker (codes 1xx, 8 trials) and competing speakers (2xx, 12 trials). One HDF5 file per group
with 31 EEG channels + 2 aux channels per trial at 1 kHz, already cut at stimulus onset, and the stimuli (48 kHz,
plus 1 kHz envelopes). See `hdf5_dataset_info.txt` (its table mislabels codes 225-220 as SS; they are CS).

## Checks with the aux channels (rows 32-33)
The aux channels are low-quality recordings of the left (row 32) and right (row 33) loudspeaker signals.
Cross-correlating them with the shipped stimuli (2-200 Hz, first and last 30 s of every trial):
- **Attended side:** odd trials right, even trials left (the parity rule; confirmed by the one PsychoPy csv per
  hi/ci group), except **ci 103, nh 305 and nh 306, who attended the left speaker on odd trials** (all 20 trials).
  ci 121 and nh 308 carry both streams on one aux channel, so their side is unverified (parity assumed).
  ci 127's aux channels do not contain the stimulus (r ~0.02), so nothing can be checked for it.
- **Onset:** the stimulus on the aux channels sits within ~2 ms of the shipped stimulus at trial start; the offset
  depends on the stimulus file and side (-5 .. +3 ms), not on subject or trial.
- **Drift (not corrected in the shipped EEG):** 26.7 ppm median, very consistent across subjects (IQR 25-28 ppm per
  trial); ci 118-122 and hi 201 drift ~18 ppm. That is 3-5 ms over a 100-200 s trial.
  Evidence: `tmp/review/jehn2025/aux_drift.png`, `aux_check.csv`.

## Standardised format
- Conditions `<natural|competing>_<fR|fL>_<group>`; subjects numbered within group.
- Stimuli: target (attended) and, in competing trials, the distractor stream (`<story>_<part>_target` /
  `_distractor`; distractor parts are different recordings from the same story's targets).
- CI: channels removed at the magnet position (`taken_out_indices`) are dropped.

## Drift correction (optional, off by default)
`drift.py` writes the per-trial aux-channel estimates to `drift.csv`; `drift_correction="subject"` resamples each
trial's EEG to the audio clock with the subject's median drift (trials with >= 10 valid windows; `to_audio_clock`,
anchored at the trial onset). Default `None` leaves the EEG as shipped.

Effect, all subjects, with vs without correction (2026-11-19; `tmp/review/jehn2025/drift_compare/`):
- 0.5-8 Hz: unchanged (encoding scores, envelope TRF, coherence within +-0.05 of the null ratio in every condition).
- 30-60 Hz TRF: slightly sharper; fraction of subjects significant nh 0.04 -> 0.14, hi 0.10 -> 0.21, ci 0.79 -> 0.79.
- 30-250 Hz: no brainstem response in nh/hi either way. In ci the implant artefact (stimulus-locked, no latency)
  lines up better (SNR 5.3 -> 6.7) and 30-60 Hz coherence rises; that is artefact, not neural response.
- Nothing gets worse. Use the correction for high-frequency or precise-latency analyses.
