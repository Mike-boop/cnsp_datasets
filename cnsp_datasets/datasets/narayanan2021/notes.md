# narayanan2021 notes

Mundanad Narayanan, Zink & Bertrand 2021, "EEG miniaturization limits for stimulus decoding with EEG sensor
networks", J. Neural Eng. 18, doi:10.1088/1741-2552/ac2629. Data: Zenodo 4518754 (CC BY-NC 4.0). 30 normal-hearing
male participants, 255-channel EEG (SynAmps RT, 1 kHz, Curry `.dat/.dap/.rs3/.ceo`), auditory attention to one of
two Dutch stories (two male speakers, HRTF-filtered to +-90 degrees, insert phones, 60 dBA). Four recordings per
participant `S<n>/S<n>_AAD_<P>`, P = story part (1, 2) + attended side (L, R); ~6.5 min each.

## Conditions and stimulus mapping
- Zenodo table (corrected 2026-08-11; before, it encoded the unattended speaker): part 1 left ear
  `part1_track2_dry`, right ear `part1_track1_dry`; part 2 left `part2_track1_dry`, right `part2_track2_dry`. The
  letter in P is the attended side. Conditions `competing-fL-hrtf` / `competing-fR-hrtf` (as das2019).
- The previous adaptor had the right attended tracks but the attended side inverted (1L labelled R).
- Checked against the EEG: leave-one-trial-out backward decoders (1-8 Hz, 0-250 ms) trained on the labelled-attended
  and, separately, the labelled-ignored track: attended r 0.060 vs ignored 0.019; attended higher in 104/120 trials
  and 27/30 participants (Wilcoxon p = 1e-7), equally for L and R. S4, S12, S26 track weakly (r < 0.06 for both)
  without a consistent swap; not conclusive with four trials.
- Recording order (meas_date) is 1L-2R-1R-2L (16 participants) or 1R-2L-1L-2R (14); trials are numbered in that
  order.
- Only the dry (non-HRTF) wavs are shipped (44.1 kHz; part 1 394.000 s, part 2 395.326 s).

## Alignment
- `Trigger` channel: one pulse per second while the story plays, 390 pulses for part 1 and 392 for part 2 (the
  authors' `sample_script.m` takes the first to the last pulse as the experiment). The last pulse comes 5.004 s
  (part 1) / 4.330 s (part 2) before the story ends in 116 of 120 recordings, so the pulses most likely start with
  the sound; whether the first pulse coincides with the sound onset is not documented and there is no stimtrack.
  The EEG is cut from the first pulse for the wav duration.
- S8_AAD_1R has a stray pulse 16.18 s before the train (taking the first pulse, as the authors' script and the old
  adaptor did, puts that trial 16 s early); S26_AAD_2L, S28_AAD_1L and S28_AAD_2L have a stray pulse after the
  train (harmless). The adaptor takes the first pulse followed by a 1-s spacing.
- Pulse period against the EEG clock: -10.0 ppm (S0-S23, 34-ms pulses) and -16.8 ppm (S24-S29, 171-ms pulses: a
  different setup), residual 0.29 ms (sampling): 4-7 ms over a trial if the pulses follow the audio clock. The
  adaptor corrects it by default (`drift_correction=True`): each trial is resampled onto the pulse clock, period fitted
  per recording, first pulse as the anchor (S25: 7 samples at the end of a trial, 6.7 predicted)
  (`tmp/review/narayanan2021/triggers/triggers.csv`).
- XtraL/XtraR carry no audio (envelope correlation <= 0.09 at random lags; slow drift only); dropped with Trigger.

## Neural data
- 253 EEG channels in uV in the files (V after MNE). Positions from the authors' `misc/eeg255ch_locs.csv` (spherical,
  BESA convention: theta signed by hemisphere, phi azimuth). Curry's own embedded positions look mirrored (T8 at
  x = -84 mm) and are not used. Recording labels FP*/AFP*/PPO8h are renamed to the csv's Fp*/AFp*/PPO8 (PPO8h sits
  at 90/-45, the mirror of PPO7: a labelling typo).
- Reference not documented. No bad-channel lists; some channels have very large variance (up to 6.8 mV std).

## Validation (2026-11-20, average reference, `tmp/review/narayanan2021/`)
- Tier **low**. Envelope decoding mean r 0.025, 83% of participants significant, TRF peak 78 ms; MLR p = 0.10, no
  brainstem response. Without drift correction: the same r, 80% significant.
- Coherence (attended envelope, ratio to null): 0.2-1 Hz 3.1, 1-4 Hz 2.2 (fL) / 1.9 (fR), 4-8 Hz 2.2 / 2.1; the same
  with and without drift correction.
- Latency against accou2023 (DNN offsets): fL -5.1 ms (CI -8.9..-1.8), fR -8.8 ms (-13.2..-3.8) with drift
  correction; -2.9 / -6.6 ms without. Plausible for a two-talker mixture; no sign of a misalignment.
- Size: 30 participants x 0.44 h (0.22 h per attended side), 13.2 h.
- No MLR / brainstem response is expected: only the dry wavs are shipped while the participants heard HRTF-filtered
  versions, so the half-wave-rectified dry wav is a poor regressor above ~30 Hz (the envelope is barely affected).
- The previous adaptor took the first Trigger edge as the onset (the same sample except S8_AAD_1R, 16.18 s early),
  ran ~5 s past the audio and had no drift correction.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**medium**: Onset = first pulse of the 1 s trigger train (coincidence with sound onset undocumented, no stimtrack); pulse-clock drift (-10/-16.8 ppm) corrected; DNN -5/-9 ms plausible for two talkers; low tier.

## Restructure 2026-11-25 (not yet re-validated on data)
- dataset.json: participants 30, listening_hours 13.2 (were 24 / 12.0; size line in this file).
- Trials are `ceil(wav samples * 1000 / 44100)` EEG samples long, the span of the wav (part 1: 394000), one sample
  fewer than before: `round(duration * sfreq) + 1` was an off-by-one (nothing in the alignment needs the extra
  sample; the onset and drift are unchanged).
- A recording without a 1-s pulse train on `Trigger` raises (`np.argmax` used to return the first pulse silently).
- Stimulus audio through `iohelpers.read_wav` (first channel, float32 / 32768: unchanged values).
- `to_audio_clock` imported from `standardise.clock` (was via bentum2023.drift).
