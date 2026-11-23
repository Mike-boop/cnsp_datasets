# straetmans2021: mobile EEG while attending one of two talkers, sitting or walking

Wireless EEG (24 channels, 250 Hz) while participants attended one of two competing German talkers (a short story
from an audiobook, against snippets of the same book from the opposite side) with occasional environmental
distractor sounds. Three narratives were heard sitting, three while walking a route indoors.

- **Source:** OpenNeuro ds003801 v1.0.0 (https://openneuro.org/datasets/ds003801/versions/1.0.0),
  doi:10.18112/openneuro.ds003801.v1.0.0. **Licence: CC0.**
- **Paper:** Straetmans L, Holtze B, Debener S, Jaeger M, Mirkovic B (2021). Neural tracking to go: auditory
  attention decoding and saliency detection with mobile EEG. *J Neural Eng* 18:066054.
- **Code (authors):** none shared.

## Size
20 participants (sub-001..020; the paper analysed 19 of 21 recruited, without saying which file is excluded),
6 narratives each (270-402 s; 120 trials), **32.5 min per participant, 10.8 h in total**; 16.2 min per
participant in each condition (`sit`, `walk`). Narrative order and the sit/walk assignment vary per participant.

## What is provided
- **EEG only. No stimulus:** the release contains no audio, envelope, transcript, attended side (left/right) or
  distractor-event times. The narratives come from a commercial audiobook (Kling 2009, *Die Känguru-Chroniken*).
  Trials therefore have no stimulus; the narrative number (1-6) is in the sidecar (`narrative`) so the audio can
  be attached if it becomes available. Speech-tracking analyses are not possible with this release.
- 24 scalp channels (SMARTING, EasyCap; Fp1 ... O2 incl. TP9/TP10), **raw**: DC-coupled, unfiltered, original
  common reference (the paper says Fz, but Fz is a recorded channel; the reference is probably FCz). Re-reference
  and high-pass before use. Template electrode positions. No EOG, motion or audio channels.
- Bad channels: sub-018 P4 (broken in 4 of 6 narratives), in `info['bads']`. sub-010 is noisy on all channels;
  walking blocks are noisier than sitting blocks.
- Trial = narrative from its start to its stop marker; condition `sit`/`walk`; rest EEG not included.

## Alignment
- Software markers: audio and markers both came from Presentation on an Android phone, and the markers went
  to the EEG via LSL (`alignment_method` `sw_trigger`). The delay of the sound after the marker is unknown and
  was not corrected.
- Marker durations of the same narrative agree across participants within ~6 ms (median), with occasional
  outliers up to +75 ms (jitter ~15 ms). Amplifier vs phone clock drift (LSL): within ±3 ppm, except sub-001
  (+27 ppm, ~11 ms over a narrative). Not corrected (`drift_ppm` in the sidecar).

## Validation
**None possible** (sidecar `validation_tier` null: untestable): without a stimulus no forward model can be fitted. Sanity checks
pass for all 120 trials (units, no flat/NaN channels, trial lengths). The 250 Hz rate would in any case rule out
the 30-250 Hz (brainstem) tier.

Details: `notes.md`.
