# zhang2025: NJU cEEGrid dataset (three talkers, dynamic attention switching, ear-EEG 125 Hz)

## What it is
- Zhang, Song, Lu, Chen, Lin (2025), "Auditory Attention Decoding from Ear-EEG Signals: A Dataset with Dynamic
  Attention Switching and Rigorous Cross-Validation" (Nanjing University; IEEE preprint). Data: Zenodo
  [10.5281/zenodo.17393865](https://doi.org/10.5281/zenodo.17393865), **CC BY 4.0**.
- Participants heard three competing Mandarin news talkers (CCTV; 6 talkers in total) from loudspeakers at
  +-60/+-120/0 deg (sub-001: +-30/+-90/0), 30-s trials, and followed an on-screen arrow. Seven tasks, 9 trials each:
  1 sustained attention, 2 cued switch to a named talker, 3 free switch, 4 stop attending, 5 switch to a talker that
  appears, 6 switch when the attended talker falls silent (two talkers), 7 ignore a talker that appears. The cue or
  event falls between 13 and 17 s.
- **Included here: 66 participants, 3287 trials, 27.4 h** (0.415 h per participant on average, 0.067-0.525 h;
  8-63 trials each). The release ships 4976 preprocessed trials of 79 participants, but only 3287 of them have
  their raw recording in the release (see Known issues); only those are standardised.

## What is provided
- **EEG:** two cEEGrids (8 electrodes per ear: R1 R2 R3 R4 R7 R8 R9 R10 L10 L9 L8 L7 L4 L3 L2 L1), OpenBCI
  Cyton + Daisy, **raw** data at the native **125 Hz** (not resampled), volts. Original reference: an unused
  left-ear cEEGrid electrode. No EOG, ECG or audio channels. Bad (mostly dead) channels per participant in
  `info['bads']` (18 channels in 15 participants; `bads.json`); exclude them yourself, `raw.pick("eeg")` keeps them.
  sub-002 and sub-003 carry strong 50-Hz noise on all channels.
- **Trials:** subject and trial numbers are the authors' shipped ids (`dataset-001-subject-SSS-trial-TTT`); gaps
  are trials without raw data. Condition `task<k>-<name>` (e.g. `task2-cued-switch`). Each trial is the 30-s segment
  (3750 samples) the authors cut for their preprocessed trial.
- **Stimuli:** the dry talker wavs (48 kHz, 30 s), attended talker at trial start first (`audio01`), then the
  others. Task 6 has two talkers.
- **Events** (annotations, s from trial start): `switch_cue` (tasks 2-4), `interferer_onset` (tasks 5, 7: the third
  talker appears), `attended_silent` (task 6). The wavs are **not** shifted or muted at these times.
- **Provenance per trial** (`raw.info['description']`, JSON): task, speaker directions in stimulus order, attended
  direction, `switch_to` (task 2), event times, `label_per_second` (the authors' attended direction per second;
  -999 = no defined target, e.g. after the cue in tasks 3 and 4), raw source file and start sample, match r.
  Combine `label_per_second` with `speaker_directions_deg` to get the attended stream per second.

## How it was aligned
- A photodiode on the presentation screen was recorded on a separate LSL stream; the authors cut each trial at a
  fixed **1.02 s** after the trial's first photodiode rise (IQR 1.01-1.03 s; the spread is LSL inter-stream jitter).
  The raw trial here is located at exactly the authors' cut, by cross-correlating the shipped preprocessed trial
  with the raw recording, so the authors' timing is kept (`alignment_method` `onset_only`).
- The sound itself was not recorded, so the loudspeaker latency relative to the flash, and so to t=0, is unknown.
  Clock drift could not be measured (LSL timestamps too jittery); for 30-s trials it should be <= ~3 ms. No
  correction is applied.
- **Alignment grade: medium** (under review: the forward TRF is weak and stays inside the null band): onset from the authors' photodiode-based cut, not verified against audio; confirmed by
  validation (forward-TRF peak 156 ms, nothing at negative lags, backward lag sweep peaking at 0, attended >
  ignored).

## How to get it
Registry entry `zhang2025` (Zenodo, four zips, 4.5 GB; extract them into one folder with `eeg/`, `meta/`,
`stimuli/` and `trialinfo/`). Then `python -m cnsp_datasets.standardise.format_dataset zhang2025 <download dir>
<out dir>` (~5 min, 1.5 GB). `mapping.csv` (which raw recording and start sample each trial uses) and `bads.json`
are committed; rebuild them with `python -m cnsp_datasets.datasets.zhang2025.make_mapping <download dir>` (~40 min)
and `python -m cnsp_datasets.datasets.zhang2025.bads <download dir>`.

## Validation
- Low tier (0.5-8 Hz forward model, average reference, all 66 participants, attended talker at trial start):
  **pass**, weak: mean r 0.0069, p_circ 0.020, p_mismatch 0.048, 14/66 participants significant. Per task (about
  7 trials per participant) only tasks 4 and 7 pass on their own. Higher tiers are not possible at 125 Hz.
- Attention (tasks 1-2, attended stream per second): forward-model r attended 0.0063 vs ignored 0.0009 (40/62
  participants, Wilcoxon p 0.008); backward decoder 3-way accuracy 0.37 (task 1), 0.41 (task 2 before the cue,
  p 2e-4), chance 0.33; the authors report 0.415.
- Suitable for low-frequency attention and switching analyses with ear-EEG; weak per participant. Not for
  millisecond timing or high-frequency work.

## Known issues
- **Raw recordings are scrambled and incomplete upstream.** The `trialinfo/` file names do not follow the shipped
  subject/trial ids; the mapping was rebuilt from the EEG (`mapping.csv`; recording order matches the shipped
  trial order in every participant). 1689 shipped trials have no raw recording (participants 15, 26-30 and 64-70
  entirely), and 1689 raw recordings belong to no shipped trial (possibly the participants the authors withhold);
  these are not used.
- When the appearing talker (tasks 5, 7) starts within its wav is undocumented; only the event time is given.
