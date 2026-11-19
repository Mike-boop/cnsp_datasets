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

## Open
- Drift correction from the aux channels (per subject or per trial) is proposed, not applied.
