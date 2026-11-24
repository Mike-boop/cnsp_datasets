# peng2026: SoundBubble-EEG (selective attention to one of two Mandarin conversations, 128-ch EGI)

## What it is
- Peng, Liu, Zhang, You, Chen, Xi, Sun, Liu, Tan, Wu (2026), "SoundBubble-EEG: A Multi-Scenario Dataset for
  Naturalistic Multi-Talker Auditory Attention Decoding" (Hong Kong Polytechnic University; paper in
  preparation). Data: Zenodo [10.5281/zenodo.19610628](https://doi.org/10.5281/zenodo.19610628), **CC0 1.0**.
  Code: github.com/Mashirops/sound-bubble-eeg-code.
- 30 participants (sub-01..30), one session each. Each heard 25 binaural "sound bubble" scenes (126 s) over
  in-ear headphones: two competing Mandarin conversations (AISHELL4-style meeting speech, TV clips) spatialised
  with HRIRs, plus scene noise (SNR 15 dB). Scenes: restaurant (10), TV (10; a TV programme in front, a family
  conversation to one side), meeting (5). A visual cue (left/right; front for the TV programme in 4 TV scenes)
  told the listener which conversation to attend. Comprehension questions after each scene (not included).
- Size: **30 participants x 52.5 min** (every participant the same; restaurant 21.0, TV 21.0, meeting 10.5 min),
  26.25 h in total.

## What is provided
- **EEG:** EGI NA-400, HydroCel GSN 128, raw Net Station recordings at the native **250 Hz** (not resampled),
  volts. Channels E1-E128 plus **VREF** (Cz, the recording reference, all zeros; kept so that an average
  reference includes Cz). Original reference (Cz). No EOG/ECG/peripheral channels; the event channels are
  dropped. Positions: the HydroCel 128 template from the recordings (not digitised). Bad channels per participant
  in `info['bads']` (0-10 channels, mean 2.4; `bads.json`; exclude them yourself, `raw.pick("eeg")` keeps them).
- **Trials:** one per scene, numbered 1-25 in presentation order (meeting, then restaurant, then TV); condition
  = scene (`restaurant`, `tv`, `meeting`). The EEG starts at the sound onset and lasts the wav's 126.0 s.
- **Stimulus:** the binaural mixture as played (`Sxxxxx_mix_CH0`, 16 kHz stereo: left, right ear). **The
  separate talker streams are not in the release**, so there is no attended/ignored envelope pair; the cued
  side is in each trial's provenance (`cue_direction`: left/right/front). No transcripts or word alignments.
- Provenance per trial (`raw.info['description']`): onset source and value, the authors' onset, the E-Prime onset,
  scene, stimulus, cue, BIDS run.

## How it was aligned
- Triggers are **software**: E-Prime 2.0 sends a TBEG event to Net Station over TCP carrying E-Prime's logged
  sound onset (`SoundOut1.OnsetTime`), mapped to the amplifier clock with one NTP sync per run. No stimtrack, so
  the audio output latency is unknown and sound-card drift cannot be measured (none applied).
- **sub-09..30:** onset = OnsetTime + the run offset given by the TBEG markers (same as the shipped events.tsv
  within sample rounding).
- **sub-01..08:** an E-Prime bug sent every marker with timestamp 0. The authors rebuilt these onsets from the
  Net Station log, but on the log computer's clock, which runs ~+79 ppm against the EEG samples, so their onsets
  drift by up to ~0.1 s within a run. This adaptor keeps OnsetTime with slope 1 (as for sub-09..30) and takes
  only each run's offset from the log arrival times, calibrated on sub-10..30 (leave-one-subject-out error SD
  18 ms, max 87 ms per run; provenance `onset_error_sd_ms`). Checked against sub-09's valid markers and, by the
  DNN timing check, against the EEG (shipped onsets: -60 ms early in a run to +24 ms late; corrected: -42 / -31 ms,
  like the marker group's -32 / -23 ms).
- Option: `onset="corrected"` (default) or `onset="authors"` (the shipped events.tsv onsets).
- **Alignment grade: medium**: software triggers, confirmed by validation (backward-decoder lag sweep peaks at
  0 s; DNN offset -26 ms, as expected for speech in noise; nothing at negative lags). sub-01..08 have the extra
  per-run uncertainty above.

## How to get it
Registry entry `peng2026` (Zenodo, one 21.6 GB zip, extracted in place; the preprocessed derivatives in the zip
are not used). Then `python -m cnsp_datasets.standardise.format_dataset peng2026 <download dir> <out dir>`
(`--adaptor-opt onset=authors` for the shipped onsets). Bad channels: `python -m
cnsp_datasets.datasets.peng2026.bads <download dir>`; onset calibration: `python -m
cnsp_datasets.datasets.peng2026.onsets <download dir>`.

## Validation
- Low tier (0.5-8 Hz forward model, average reference, all 30 participants): **pass**, but weak: mean r 0.008,
  12/30 participants significant (the regressor is a noisy binaural mixture). Per scene: restaurant and meeting
  pass; TV fails the mismatched-stimulus null (p 0.19). Higher tiers are not possible at 250 Hz.
- Attention contrast (backward decoder; ear channels of the mixture as a proxy for the left/right talkers):
  accuracy 0.61 in the restaurant (p 8e-5), chance in TV and meeting, 0.55 pooled. Clean-stream decoding (as in
  the paper) needs the talker wavs, which are not released.
- Suitable for low-frequency tracking of the mixture and coarse attention analyses; not for millisecond timing
  (software triggers, unknown audio latency) or brainstem/MLR work.

## Known issues
- No separate talker streams (see above); the per-talker file names are in the authors' code repository
  (`technical_validation/aad_baseline/material_complete.csv`).
- The shipped sub-01..09 onsets drift within runs (fixed here by default); sub-09 had valid markers.
- `events.json` describes `run_id` as the run; it is the trial number 1-25.
