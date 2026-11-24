# zhang2025: NJU cEEGrid three-talker attention-switching dataset (ear-EEG, OpenBCI 125 Hz)

Scratch: `R/zhang2025/` (R = `/data_storage/gu08wuvu/datasets/tmp/review`), scripts in `R/scripts/zhang2025/`,
progress log `R/zhang2025/agent_log.md`.

## 1. Source
- Data: Zenodo [10.5281/zenodo.17393865](https://doi.org/10.5281/zenodo.17393865) (2025-10-20), **CC BY 4.0**:
  "16 channel Three speaker dynamic switch cEEGrid Auditory Attention Decoding Dataset, Nanjing University".
  Registry entry `zhang2025` (version pinned, fe3393d). Copied from the vault copy on woody and md5-verified
  (Zenodo blocks this server; the zips are kept in `R/zhang2025/download/`).
- Paper: Y. Zhang, Z. Song, J. Lu, F. Chen, Z. Lin, "Auditory Attention Decoding from Ear-EEG Signals: A Dataset
  with Dynamic Attention Switching and Rigorous Cross-Validation" (IEEE preprint; `data_campaign/papers/zhang2025.pdf`).
- No analysis code released with the data (the record points to the authors' SuperHugeAAD / SuperPrepare
  packages).

## 2. Layout (4 zips, 4.5 GB)
- `eeg/dataset-001-subject-SSS-trial-TTT.npy`: the authors' **preprocessed** 30-s trials (3750 x 16, 125 Hz;
  re-referenced, 0.5-62 Hz, notch, ASR, ICA): 4976 trials = subjects 1-40 and 51-89 (79 subjects) x 63 (sub-069: 62).
  Not used as data (preprocessed), only to locate the raw trials (section 3).
- `meta/publish_metadata.pkl`: one dict per shipped trial: task, attended speaker id, `label` (attended direction
  per second, -999 = no defined target), channel names, paths of derived stimuli that are not released. Read with
  a restricted unpickler (numpy arrays only). `scaling_factor.pkl` / `channelwise_scaling_factor.pkl`: unused.
- `trialinfo/S<ss>_T<tt>.mat` (4976 files): **raw** OpenBCI recordings per trial (~60 s: `eeg` 16 ch uV + LSL
  timestamps `eegts`; `aux` (3 ch, ~46 Hz, its own LSL stream; channel 2 = photodiode) + `auxts`; `bp` (unused))
  and a MATLAB class object `this_trial_info` (`task<k>info`: subject_id, trial_id, speaker directions, attended
  speaker, audio paths, switch/interferer time, quiz). scipy cannot read MCOS objects; `trialinfo.py` parses the
  MAT-file function workspace.
- `stimuli/speaker_<k>_segment_<n>.wav`: 126 dry 30.0-s mono wavs, 48 kHz int16 (6 talkers; CCTV news) + 2 Adobe
  `.pkf` peak files (ignored).

## 3. Stimulus <-> trial mapping (mapping.csv, make_mapping.py)
- **The trialinfo file names do not follow the shipped subject/trial ids.** The trials of one recording session
  (one MCOS `subject_id`, consecutive LSL timestamps) are scattered over several `S<ss>` names (e.g. S01_T05..T63
  are mostly MCOS id 74). By name, only ~5% of shipped trials match their raw file.
- The mapping was rebuilt from the EEG: each shipped (preprocessed) trial is slid over every raw recording with the
  same task, attended talker and initial attended direction (1-8 Hz, mean-over-channels Pearson r). A trial is kept
  when the best r > 0.3, beats the runner-up by >= 0.15 and no other trial claims the same recording.
  Scores are bimodal (true matches ~0.45, the rest ~0.07). `make_mapping.py` (committed, ~40 min on 2 threads)
  reproduces `mapping.csv` exactly: **3287 trials of 66 subjects**.
  - History: a first scratch mapping (`R/scripts/zhang2025/match3.py`) had 3279 trials; its scores for one raw
    file (S77_T15, 56 s) were spurious (r 0.57 against 15 different trials; recomputed 0.05-0.08), which blocked 8
    trials by the margin rule and wrongly suggested a 15-fold match. The committed script gives the 3287.
- **Independent checks of the mapping:** every mapped subject's trials come from a single MCOS subject_id, and in
  66/66 subjects the LSL start times increase with the shipped trial number (recording order = trial order;
  sub-040 has a 2.6-h gap = a break). The task class of the raw object matches the shipped task for every trial
  (checked in the adaptor).
- **1689 shipped trials have no raw counterpart** (best r <= 0.3 against every raw file of the same task,
  `R/scripts/zhang2025/match4.py`, max 0.30): subjects 15, 26-30 and 64-70 entirely, and part of most others
  (8-62 of 63 trials mapped; mean 49.8). Conversely 1689 raw recordings match no shipped trial; they come from 65
  MCOS ids, including complete 63-trial sessions for ids 52-61 and 86-94. The Zenodo text says some subjects'
  EEG is "reserved for other purpose", so these may be the withheld participants. They are **not used** (open
  question 2). Upstream issue 1.
- Subjects keep the shipped ids (sub-001..089, gaps); session 1; trials keep the shipped trial numbers (1-63, with
  gaps where no raw trial exists). The MCOS subject_id differs from the shipped id and is not used.
- Conditions: `task<k>-<name>`: 1 sustained, 2 cued-switch, 3 free-switch, 4 stop-attending, 5 switch-to-new
  (a third talker appears), 6 switch-on-silence (two talkers; the attended one stops), 7 ignore-new (a third
  talker appears and is to be ignored). Mapped trials per task: 466, 469, 442, 519, 466, 464, 461.
- Per-trial provenance (`raw.info['description']`): task, speaker directions (stimulus order), attended direction,
  `switch_to` (task 2), event times, `label_per_second` (the authors' per-second attended direction; -999 = no
  target), source file and start sample, match r.

## 4. Speech features
Raw audio: the dry talker wavs as played, attended first (`audio01` = attended at trial start). Same wav sets are
reused across trials and subjects (126 wavs). No transcripts or word alignments. Envelopes/mel features used by
the authors are not released (~200 GB, on request).

## 5. Neural data
- OpenBCI Cyton + Daisy, 16 channels at 125 Hz: two cEEGrids, 8 electrodes per ear: R1 R2 R3 R4 R7 R8 R9 R10
  L10 L9 L8 L7 L4 L3 L2 L1 (same order in every trial's metadata; checked). Raw uV -> V. **Original reference**:
  an unused electrode of the left cEEGrid (OpenBCI SRB); ground on the cEEGrid too (paper Fig. 1a). No EOG/ECG,
  no audio channel. Amplitudes plausible (1-40 Hz robust SD median 6.6 uV, 5-95% 3.6-10.8 uV).
- Trials: 30 s = 3750 samples from the authors' cut (section 6), native 125 Hz, not resampled.
- **Bad channels** (`bads.py` -> `bads.json`, the chen2026 rule: 1-40 Hz SD > 5x or < 1/5 of the channel median in
  >= 20% of the participant's trials): 18 channels in 15/66 subjects (max 3, sub-022 R2 R3 R4). Several are fully
  flat for the whole session (sub-004/010 R1, 011 L1, 016 R2, 022 R2+R4, 075 L4; sub-001 L4 nearly flat). Kept in
  the data, listed in `info['bads']`. sub-002 and sub-003 have strong 50-Hz noise on all channels (65-90% of the
  1-60 Hz power), not marked (whole-montage; use a notch).

## 6. Alignment
### 6a. Triggers
- A photodiode at the corner of the presentation screen (paper II.A) is recorded as `aux` channel 2 on a separate
  LSL stream; the EEG and aux streams are joined only by LSL timestamps. Most recordings show 2 rises (4222), some
  1 (703), 7 none: the first at trial start, the second at the switch cue / interferer event.
- The paper says the EEG was "aligned with audio stimuli using the rising edge of trigger signals" and that no
  further alignment was done (II.C). Measured: the authors' cut (start of the shipped trial, located in section 3)
  lies **1.023 s after the first photodiode rise** (median; IQR 1.012-1.032 s; 3280 trials with a rise), and the
  second rise lies at cut + event time (median -8 ms, IQR -20..+6 ms). So the authors' t=0 is a fixed ~1.02 s after
  the trial-start flash, consistent with their own event timeline; the ~20-ms spread is the LSL inter-stream
  jitter.
- **The sound itself is not recorded** (no stimtrack, no audio copy; loudspeakers driven by the presentation PC).
  The audio output latency relative to the flash, and so relative to the authors' t=0, is unknown.
### 6b. Onset used
The authors' cut, as located by EEG cross-correlation (sample-exact: the shipped trial is the raw segment after
preprocessing). This keeps the authors' timing (`alignment_method` `onset_only`), and avoids the ~20-ms LSL jitter
that a photodiode-based cut would add. No correction applied.
### 6c. Drift
Not measurable: there is no audio copy, and the LSL timestamps are too jittery (eegts vs sample index over 200 raw
files: slope median +79 ppm, IQR -19..+225 ppm, 6.7-ms residual SD; `R/scripts/zhang2025/clockfit.py`), the spread
being timestamp jitter rather than a crystal error. For 30-s trials a typical crystal error (<= 100 ppm) gives
<= 3 ms. None applied.
### 6d. Events
Annotations (s from trial start): `switch_cue` (tasks 2-4), `interferer_onset` (tasks 5, 7), `attended_silent`
(task 6). **When the third talker (tasks 5, 7) actually starts relative to its wav is undocumented** (the wav is
30 s and the trial 30 s: either the wav plays from the event, cut at trial end, or it plays muted until the event).
The adaptor does not shift it; open question 3.

## 7. Cross-subject duration check
Not applicable: trials are fixed 30-s cuts of one stream (no end trigger). Raw recordings are 43-60 s, every mapped
cut fits (the loader checks for 3750 samples).

## 8. Attention design
Three talkers at +-60/+-120/0 deg (sub-001: +-30/+-90/0; task 6: two talkers), loudspeakers. `label_per_second`
gives the attended direction per second; with `speaker_directions_deg` it gives the attended stream per second.
Task 1 (sustained) and task 2 (cued switch, `switch_to`) are fully labelled with all talkers present; task 3
(free switch) and task 4 (stop attending) have no defined target after the cue (-999).

## 9. Validation
Run 2026-11-24 on all 66 participants / 3287 trials (`R/zhang2025/standardised_v3`; the final adaptor's output
`standardised_v4` has the same data and audio, only the provenance text differs), average reference over the
good channels (16 ear channels, no mastoids; bads excluded), attended (trial-start) stimulus. Native 125 Hz, so only
the low tier (mlr/brainstem need >= 500 Hz).
- **Low tier, pooled** (`validation.json`; figure `R/zhang2025/validation/validation.png`): mean r 0.0069 (median
  0.0052), p_circ 0.020, p_mismatch 0.048, 14/66 subjects significant: **pass**, weak (16 ear channels, 30-s
  trials, three talkers from loudspeakers; the authors' 3-way WF accuracy is only 41.5%). Forward-TRF GFP peaks at
  156 ms and is lowest at negative lags, but stays inside the null band. The validator's per-trial offset/drift
  estimates are noise at this SNR (599 offsets at the scan edge; "drift" 1110 +- 670 ppm) and are not used.
- **Per task** (`R/zhang2025/validation_tasks/<task>/`; ~7 trials per subject each, underpowered): task 4 (stop
  attending) mean r 0.0079, p_circ 0.020, p_mismatch 0.048, pass; task 7 (ignore new) 0.0067, 0.039, 0.048, pass;
  tasks 1, 2, 3, 5, 6 not significant alone (mean r 0.0021, 0.0023, 0.0015, -0.0009, 0.0026). Task 5's attended
  stream changes to the new talker at ~13 s (the "attended first" stimulus is only the initial target), and tasks
  2/3/6 switch too, so pooled stimulus 1 is a mixed regressor.
- **Attention contrast** (`R/scripts/zhang2025/attention.py`; figure `R/zhang2025/attention/r-attended-vs-r-ignored.png`,
  numbers `attention.json`): tasks 1-2, attended stream per second from `label_per_second`, 62 subjects with
  >= 5 such trials. Forward model: attended r 0.0063 vs ignored (mean of two) 0.0009, attended higher in 40/62,
  Wilcoxon p 0.008. Backward decoder (0-250 ms, leave-one-trial-out) 3-way accuracy (chance 1/3): task 1 0.37
  (464 trials, p 0.07), task 2 before the cue 0.41 (462, p 2e-4), task 2 after the switch 0.35 (p 0.17); the
  authors report 0.415 (WF, 30 s). Lag sweep of the backward decoder (task 1, +-1 s): peak at 0 ms (relative
  check: held-out trials line up with the training trials).
- Data-sanity: 3287/3287 trials 3750 samples (30.0 s) = wav length; amplitudes plausible (section 5).

## 10. Data size
3287 trials x 30 s = **27.4 h**, 66 participants, mean 0.415 h per participant (range 0.067-0.525 h; 8-63 trials).
Per task 3.9 h (task 3: 3.7 h; task 4: 4.3 h). Standardised: 3287 fif (~245 kB) + 126 audio npz, 1.5 GB.

## Alignment grade
**medium** (not confirmed by the user, 2026-11-24: the forward TRF looks poor; it peaks at 156 ms but stays
inside the null band, and only 14/66 subjects track individually, so the low-tier pass rests on the pooled
statistic; revisit the grade, e.g. with a DNN check if a 16-channel ear model becomes available). The onset is the authors' cut, fixed 1.02 s after a screen photodiode (hardware, but a
visual trigger on a separate LSL stream; the sound itself is not recorded, so the onset is not verified against
audio); validation confirms it at the low tier (pooled pass, forward-TRF peak 156 ms, nothing at negative lags,
attended > ignored p 0.008, backward lag sweep peaking at 0); no correction applied. Not `good`: no audio copy, and
~20-ms LSL jitter between the photodiode and EEG streams.

## Upstream issues
1. The `trialinfo/` file names do not follow the shipped subject/trial ids (sessions scattered over several
   `S<ss>`), and only 3287 of 4976 shipped trials have a raw recording in `trialinfo/` (13 subjects none at all).
   The other 1689 raw recordings belong to participants/trials that are not among the shipped trials (possibly
   the withheld subjects). A file -> shipped-trial table, and the missing raw trials, would fix it.
2. The paper says the EEG was cut at the photodiode's rising edge; the shipped trials start 1.02 s after it
   (consistently), which is undocumented. The audio latency relative to the flash is not given.
3. When the third talker starts in tasks 5 and 7 (relative to its wav) is undocumented.

## Open questions (worker defaults)
1. Alignment grade: proposed above.
2. Standardise the 1689 unclaimed raw recordings as extra participants (MCOS ids as subjects; cut = first
   photodiode rise + 1.023 s, ~20 ms jitter; ~14 h)? Default: **no**, the authors appear to withhold them.
3. Shift the third talker's wav to `interferer_onset` in tasks 5/7? Default: no (unknown), annotation only.

## Reproduction
- `python -m cnsp_datasets.datasets.zhang2025.make_mapping <download dir> [out.csv]` (mapping.csv),
  `python -m cnsp_datasets.datasets.zhang2025.bads <download dir>` (bads.json), then
  `python -m cnsp_datasets.standardise.format_dataset zhang2025 <download dir> <out dir>`.
- Scratch (R/scripts/zhang2025/): inventory.py (keys, lengths, photodiode edges, MCOS fields -> inventory.jsonl),
  match*.py (mapping history), sigcmp.py, chanqc.py, clockfit.py, attention.py, validate_tasks.py, pipeline.sh,
  run_dev.py (runs a dev-worktree module under `python -I`).
