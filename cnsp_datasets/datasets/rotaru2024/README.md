# rotaru2024: AV-GC-AAD, audiovisual gaze-controlled auditory attention decoding

Flemish listeners attended one of two competing male talkers (popular-science podcasts, rendered at -90/+90 deg
over insert phones) for 10 min per trial. Halfway, at 300 s, the two talkers swap ears; the attended talker stays
the same. The visual conditions were built to separate attention decoding from gaze: a video moving with the
attended talker (MovingVideo), the same with babble noise added at -1 dB SNR and a fixation cross
(MovingTargetNoise), a static video on the attended side (FixedVideo, "StaticVideo" in the paper) and no visuals
(NoVisuals).

- **Source:** Zenodo 11058711 (AV-GC-AAD, v1), doi:10.5281/zenodo.11058711. **Licence: CC BY-SA 4.0.**
- **Paper:** Rotaru I, Geirnaert S, Heintz N, Van de Ryck I, Bertrand A, Francart T (2024). What are we really
  decoding? Unveiling biases in EEG-based decoding of the spatial focus of auditory attention. J Neural Eng 21,
  016017. Cite the record and the paper. The podcasts are Universiteit van Vlaanderen videos.

## Size
13 of the 16 participants are shared: sub-01, 03, 04, 07-16. Two 10-min trials per condition (MovingTargetNoise not
for sub-01, 03; sub-14 has one FixedVideo trial). 99 trials, **16.5 h in total, 1.27 h per participant (1.0-1.33)**.
Per condition: MovingVideo 26 trials, NoVisuals 26, FixedVideo 25, MovingTargetNoise 22.

## What is provided
- **EEG:** the authors' preprocessed data (only these are released): BioSemi 64 channels (biosemi64 template
  positions; sub-16 has 63, no P9) plus 4 EOG (`VEOG_high`, `VEOG_low`, `HEOG_right`, `HEOG_left`; the
  horizontal side is inferred from the data), **128 Hz, band-passed 1-40 Hz by the authors**, in volts, original
  CMS/DRL reference (re-reference before use). Near-flat channels are listed in `info['bads']` (sub-03 P1, PO3;
  sub-16 P1) and kept in the data. Each trial is the authors' 600-s epoch.
- **Stimuli:** two talkers per trial, `audio01` = attended, `audio02` = ignored (also `attended_stimulus` /
  `unattended_stimulus` in the sidecar). Named by the podcast title.
  - `envelope` for all 30 podcasts: the authors' 128 Hz envelope of the dry speech (gammatone filterbank,
    |.|^0.6, 1-40 Hz), 600.02 s, starting at the trial onset.
  - `audio` for the 10 podcasts that are also in SparrKULee (accou2023): the matching 600-s excerpt of the
    SparrKULee podcast audio (48 kHz), written only when the standardiser is given a SparrKULee download
    (`--adaptor-opt sparrkulee_dir=<accou2023 download>`). The release itself contains no audio (copyright).
  - The sound actually heard is not shipped: each talker was convolved with an HRIR (+-90 deg) and in
    MovingTargetNoise babble noise was added.
- **Attention:** annotations `attend/left` (or right) for 0-300 s and the other side for 300-600 s. The sidecar
  holds the condition ID with its block, the visual stimulus file (video, the moving-crosshair image in
  MovingTargetNoise, none in NoVisuals), the initial attended side, the recording start
  time, the trigger-pulse summary and a `timing_flag` (see Alignment).

## Audio recovery
The release has envelopes only. The podcasts were matched by envelope against two candidate sources (figure
`audio_match.png` in the review folder; details in `notes.md`, section 4):
- **SparrKULee:** 10 of the 30 podcasts match with one constant offset (start 17.964 or 18.000 s into the
  SparrKULee file), 0 ppm, within 1 ms over the whole 600 s. Stored as `audio`.
- **rotaru2026 wavs** (same 30 titles): their silences are trimmed to 0.2 s, so they match only piecewise; not the
  audio that was played, not used.
- The other 20 podcasts: shipped envelope only.

## Alignment
- The shipped epochs are kept as they are (no onset or drift correction). The authors cut each 600-s epoch from a
  1-s square-pulse train sent by the playback system and recorded by the EEG; the cut sample is not shipped.
- In 11 trials (sub-04 and sub-07) playback stalled at the first audio buffer (+46-116 ms). A backward decoder
  shows that in these trials the EEG lags the envelope by ~20-130 ms, most at the start, so the pulse train does
  not track the audio there. In sub-04 MovingTargetNoise2 the epoch starts ~1 s into the audio. These 12 trials
  carry a `timing_flag` in the sidecar; filter on it for timing-sensitive work. The offsets are estimated from the
  EEG and are documented, not corrected (per-trial estimates in `alignment/decoder_lags.csv`).
- In the other 87 trials the decoder's EEG lag is +3.8 ms (95% CI 0.8-7.0).
- **Alignment grade: poor.** The onsets come from the authors' epochs, with no audio copy to verify them, and 12 of
  99 trials have a known misalignment that is only estimated from the EEG. The unflagged trials alone would rate
  medium.

## Validation (all 13 participants, average reference)
| tier | result |
|---|---|
| low (0.5-8 Hz) | pass: mean r 0.014, 11/13 subjects significant (p 0.02 circular, 0.048 mismatch), TRF peak 172 ms |
| 30-60 Hz, 30-250 Hz | not testable: shipped data low-passed at 40 Hz, 128 Hz (nominal runs: `notes.md`) |

- Attended vs ignored talker: a backward decoder (stimulus reconstruction, leave-one-trial-out) prefers the
  attended talker in 97/99 trials and all 13 participants (60-s window accuracy 0.77; 0.70-0.81 per condition).
  Forward models (channel-mean r) separate the talkers less well: attended > ignored in 9/13 participants
  (p 0.13), clearly only in MovingTargetNoise (10/11, p 0.010).
- Suitable for cortical envelope tracking and attention decoding (report per condition). Not usable for
  middle-latency or brainstem responses.

## Known issues
- The release's `randomization` table is not in trial order for 9 participants; the adaptor matches it by
  condition ID (reading it by row gives the wrong podcast for 30 of 99 trials).
- The shipped trial order is not the recording order; trials here are numbered by recording time (the shipped
  index is in the sidecar).
- The authors report that MovingVideo and FixedVideo still allow gaze-based shortcuts for spatial (left/right)
  decoders; report results per condition.

Details: `notes.md`.
