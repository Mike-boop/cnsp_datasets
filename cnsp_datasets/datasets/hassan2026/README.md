# hassan2026: MAESTRO, attention to one of four loudspeaker talkers in noise (EEG)

EEG of 16 listeners (S01-S16) in a room with six loudspeakers. Four play different English audiobook talkers
(LibriSpeech) and two rear ones play domestic noise (CHiME-Home). In each 30-s trial the listener attends one
talker. There are 105 trials per listener: 5 training and 100 evaluation trials, presented in the same order to
everyone.

- **Source:** Hugging Face `aspire-osu/maestro-eeg-dataset`, pinned to commit `534710be3a11...` (registry entry
  `hassan2026`). The release also contains Tobii gaze, pupil and head IMU, which are downloaded but not
  standardised, and a 36.7 GB egocentric scene video, which is not downloaded. The download without the video is
  5.15 GB.
- **Access is gated.** Accept the terms on the dataset page while logged in (approval is automatic). Then put a
  Hugging Face token of that account into `secrets.json` under `"hf"` and export it as `HF_TOKEN`; the downloader
  sends it as a bearer header.
- **Licence: CC BY-NC-SA 4.0** (dataset card and `LICENSE`). **Derived data (including this standardised version)
  may be redistributed only for non-commercial use and only under the same licence.** The stimuli come from
  LibriSpeech (CC BY 4.0) and CHiME-Home; the CHiME-Home licence was checked and accepted by the project owner.
- **Paper:** Hassan KMN, Alavi A, Williamson DS (2026). MAESTRO: a Multimodal Auditory-attention Egocentric
  Speech-TRacking Open corpus. arXiv:2609.31898 (eess.AS). The sources list no DOI for the paper or the data.
- **Code (authors):** `maestro-loader` 0.1.2 (PyPI, Apache-2.0). It was read but not used, and it gets the timing
  wrong (see Caveats). Its GitHub repository returns 404.

## Size
**16 participants x 0.875 h = 14.0 h in total** (every participant has all 105 trials, so the range is 0.875-0.875
h). Durations are counted from the 30-s stimuli (`data_campaign/scripts/data_size.py`):
- `main` (evaluation): 100 trials, 0.833 h per participant, 13.3 h in total;
- `training`: 5 trials, 0.042 h per participant, 0.67 h in total.

The standardised output is about 4.5 GB.

## What is provided
- **EEG:** ANT Neuro eego mylab, 32 channels at **500 Hz** (native, not resampled), in V. Every trial is cut from
  one continuous recording per subject (session 1).
  - **Channels:** 30 scalp channels (`eeg`) and the mastoids **M1/M2 as `misc`**. There is no EOG, ECG or
    stimulus channel.
  - **Reference:** the original amplifier reference, **CPz (inferred)**. CPz and the ground AFz are not shipped, and
    the data are not re-referenced. The paper's linked-mastoid reference belongs to the authors' preprocessing.
  - **Positions:** template positions (`standard_1020`).
  - The recording is DC-coupled (offsets of about 1-40 mV), and some subjects carry strong 60/120 Hz line noise.
- **Bad channels:** kept in the data and listed in `info['bads']`. They are the authors' list plus channels that sit
  at the ADC clip in more than 10% of samples or are flat (rule in `bads.py`, values in `bads.json`). The rule adds
  S02 M1 (clipped) and S14 Pz (flat, possibly bridged to the reference). S08 has no bad channels. The mastoids are
  bad in 8 of 16 subjects, so an average reference over the good scalp channels is the safer choice.
  `raw.pick("eeg")` keeps bads; exclude them yourself.
- **Stimuli:** six 16 kHz mono FLACs per trial, exactly 30.000 s each, named `<trial_id>_speaker<k>`. They are the
  same for all subjects, and no excerpt is repeated.
  - Speakers 1-4 are LibriSpeech talkers (attendable). Speakers 5-6 are CHiME-Home noise.
  - The attended talker is flagged `is_attended`.
  - Loudspeaker azimuths come from `metadata/audio_layout.json`: speakers 1/2 at -67.5/-22.5 deg, 3/4 at
    +22.5/+67.5 deg, 5/6 at -135/+135 deg. The dataset card's table differs (see Caveats).
  - Attended SNR is 3-18 dB (mean 11.6).
  - There are no transcripts, word or phone alignments, or TextGrids. The `spkid` in the file name is the
    LibriSpeech or CHiME speaker id, but the excerpt boundaries within LibriSpeech are not given.
- **Trials and conditions:** trial = presentation position (1-105). Condition `training` (positions 1-5) or `main`
  (eval_001-100).
- **Trial metadata** (`raw.info["description"]`, JSON):
  - the authors' trial id, `block` (1 = training + eval_001-049, 2 = eval_050-100; nominal, see Caveats), attended
    speaker, its hemisphere, inner/outer position and azimuth, SNR and `comprehension_correct`;
  - `onset_sample`, `onset_correction_s` and its method, and the raw per-device playback offsets
    (`playback_offsets_ms_by_raw_device`);
  - the units as shipped, the reference and the external sensors.

## Alignment
- **Software timestamps only.** Every trial has unix timestamps for the first EEG sample (LSL) and for each audio
  device's playback start, all on one host clock (paper). There is no hardware trigger and no recorded copy of the
  sound in the EEG. Trigger type: software (from the paper and the timing files).
- **Onset:** earliest playback timestamp minus the EEG first-sample timestamp, **plus a constant +0.718 s, applied
  by default** (`onset="dnn"`; `alignment_method = dnn`). The EEG is cropped at this onset and runs to the end of
  the shipped trial, about 29.6 s, so the **last ~0.4 s of each stimulus has no EEG** (the stimuli are not cut).
  - `onset="none"` drops the correction (`alignment_method = sw_trigger`, about 30.3 s of EEG). To use it,
    instantiate `Hassan2026Adaptor(download_dir, onset="none")` directly: `format_dataset` uses the default.
- **Where the 0.718 s comes from (brain-based, circular).** It is the accou2023 match-mismatch DNN offset of the
  attended talker, measured on this EEG at the uncorrected onset:
  - pooled over 16 subjects and 1,600 trials: -718.2 ms (95% CI -719.2..-717.1);
  - trials attended on device 1 and on device 2 give -718.4 and -717.9 ms;
  - per-subject values (-703..-723 ms) are not reliably different, so one constant is used;
  - a backward-model lag sweep agrees (grand peak +797 ms; per-subject peaks 562-1031 ms, broader);
  - after the correction the DNN offset is +0.2 ms (95% CI -1.0..+1.4).

  The value may include about 15 ms of extra response latency from listening in noise. It cannot tell a late sound
  from a late LSL timestamp. Because it was estimated from the same EEG, `alignment_quality = poor`.
- **The per-device playback timestamps are not applied.** Devices 2 and 3 are stamped about +80 and +160 ms after
  device 1, but the evidence says devices 1 and 2 sound together:
  - the scene-video microphone: dev2 - dev1 = -20..+26 ms in 12 trials, precision about +-15 ms;
  - the DNN: device 1 and device 2 differ by 0.5 ms.

  All six streams therefore share one onset. The rear noise device (3) cannot be detected in the microphone, so its
  timing is assumed rather than checked.
- **Drift:** the amplifier clock runs +6.8..+9.8 ppm against the host clock (median 8.9 ppm, stored as
  `drift_ppm = 9.0`). That is 0.27 ms over a 30-s trial, so it is **not corrected**. There is no hardware estimate of
  the sound cards' clocks.
- **Jitter:** the trial-to-trial jitter of the actual sound onset is **unknown** (`jitter_ms = null`).
  - The LSL first-sample stamps are consistent to about 2 ms (residual SD 1.6-1.8 ms; S10 2.3 ms; S11 5.8 ms with
    one outlier of 56 ms).
  - The playback stamps scatter by about 20 ms SD around their device offsets, and how they relate to the sound is
    unknown.
  - The validator's per-trial offset spread (about 250 ms SD at 0.5-8 Hz) only shows that per-trial offsets cannot
    be resolved from 30-s trials.

## Validation
**Low tier** (all 16 subjects, 1,680 trials, average reference over the 30 scalp channels without bads, attended
talker; `validation.json`, 2026-11-23).

| onset | backward r (mean) | subjects sig. | p circular / mismatch | TRF peak | MLR SNR (p) | brainstem SNR (p) |
|---|---|---|---|---|---|---|
| default (`dnn`, +0.718 s) | 0.0193 | 11/16 | 0.020 / 0.048 | 62.5 ms | 0.94 (0.92) | 0.95 (0.93) |
| shipped timestamps (`none`) | 0.0097 | 5/16 | 0.020 / 0.048 | 469 ms (at the window edge) | 1.01 (0.27) | 1.00 (0.46) |

- Both p-values are at the resolution of the tests (50 circular shifts, 20 mismatches).
- With the correction the TRF has a P1 at about 60 ms and a second peak at about 230 ms.
- Envelope tracking is weak (mean r about 0.02, with 4 talkers and noise on loudspeakers).

**Suitable for** low-frequency (about 0.5-8 Hz) attention decoding and envelope TRFs at the corrected onset. Use
many trials: the effect is small.
**Not suitable for** MLR or brainstem analyses: the timing is software only, corrected by a constant estimated from
the brain, and the jitter is unknown. Absolute latencies are not reliable either, because the onset is circular by
construction (the 0.718 s was fitted to make responses line up with the accou2023 model).

## Caveats and upstream issues
- **The authors' loader (0.1.2) ignores the timing files.** It aligns EEG sample 0 with audio sample 0, which is
  about 4.4 s off (1.7-5.7 s depending on the trial). The paper's per-device shift adds a further 80-160 ms error.
  How the raw device ids map to devices 1/2/3 of the FLAC names is not documented.
- The 0.718 s between the playback timestamp and the sound in the EEG is not mentioned in the paper.
- **Units:** the card says "raw ADC units", but the values are volts. They clip at +-0.08388608 (2^23 x 10 nV),
  and their RMS (5-19 uV at 1-40 Hz) and alpha peak are plausible as volts. The values are stored unscaled.
- **Clipping:** values at +-0.0839 V are ADC saturation; see the bad-channel rule.
- `comprehension_correct` is **False for all 1,600 evaluation trials** as shipped, although the paper reports
  behavioural accuracy. It is stored as shipped; do not use it.
- `subjects.csv` has no demographics.
- The "naturally mixed audio recording" announced in the paper is not in the release.
- `tobii.recording_start_unix` equals the audio anchor in every trial, so it is not an independent time.
- **Azimuths:** the dataset card's table (1 = -22.5, 2 = +22.5, 3 = -67.5, 4 = +67.5 deg) disagrees with
  `metadata/audio_layout.json`. The JSON, which is self-consistent with the hemisphere and inner/outer columns, is
  used.
- The SNR scaling clipped the peaks of the attended stream (16-bit PCM; paper). This can bias envelope statistics
  of attended versus ignored talkers. That the FLACs are exactly what was played is the paper's claim and was not
  verified sample by sample; the scene microphone matches them (envelope r up to 0.6 for the attended talker).
- **Blocks:** `block` 1/2 follows the paper's two sessions, split at eval_050, which is where the longest break
  falls in 12 subjects. In S05, S10, S14 and S15 the longest break is elsewhere. It is one EEG recording with the
  same cap.
- **Missing data:** gaze, IMU and video are missing for S02 eval_077/078 (not used here). No EEG trials are missing
  or excluded. The 24 scene videos used for the timing check are not part of the standardised data.

Details: `notes.md`.
