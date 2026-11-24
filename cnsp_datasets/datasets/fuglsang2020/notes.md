# fuglsang2020: selective attention in hearing-impaired and normal-hearing listeners (DTU, ds-eeg-snhl)

Notes from exploration, standardisation and validation (worker agents, 2026-11-24). Scripts:
`/data_storage/gu08wuvu/datasets/tmp/review/scripts/fuglsang2020/`; logs, json and figures:
`/data_storage/gu08wuvu/datasets/tmp/review/fuglsang2020/` (`agent_log.md`). That folder is temporary.

## 1. Source
- Zenodo record 3618205, doi:10.5281/zenodo.3618205, "Selective auditory attention in normal-hearing and
  hearing-impaired listeners". One file, `ds-eeg-snhl.tar` (34.9 GB, md5 41d02a9f0289110a847eee99ccff7612 =
  `MD5SUMS`). **Licence:** the Zenodo record says CC BY 4.0; `dataset_description.json` says ODbL. Both require
  attribution; the record's licence is the one granted.
- Paper: Fuglsang SA, Märcher-Rørsted J, Dau T, Hjortkjær J (2020). Effects of sensorineural hearing loss on cortical
  synchronization to competing speech during selective attention. J Neurosci 40(12):2562-2572
  (`data_campaign/papers/fuglsang2020.pdf`). Cite the paper (README "Citing this dataset").
- Code: gitlab.com/sfugl/snhl (MATLAB, not shipped; not used).
- Obtained from the user's archive copy on woody (`zenodo/fuglsang2020/3618205/`, rsync over ssh -4); md5 checked.
  This server never contacted Zenodo. Extracted with `tar -xf --skip-old-files` into `extracted/ds-eeg-snhl/`
  (all 5997 files of the listing present).
- Same lab as fuglsang2018 (Zenodo 1199011, incorporated); different participants (older listeners) and different
  audiobooks (section 4).

## 2. Layout (BIDS 1.3.0)
- `sub-XXX/eeg/sub-XXX_task-{selectiveattention,tonestimuli,rest}_{eeg.bdf,channels.tsv,eeg.json,events.tsv}`;
  sub-024 has a second selective-attention file (`_run-2`, the last 9 trials). Only `selectiveattention` is
  standardised (tones: no continuous stimulus; rest: no stimulus).
- `participants.tsv`/`.json`: age, `hearing_status` (hi/nh), `ear_eeg`, handedness, gender, SRT (DaHINT), digit
  span, FT test, SSQ, audiograms (125-8000 Hz, both ears).
- `derivatives/stimuli/subXXX/{target,masker}/{t,m}NNN[woa].mat`: envelopes (struct `dat`: `feat`, `fs` = 512, `t`
  = time re trial onset). `woa` = without CamEQ (hearing-impaired listeners only). `derivatives/README`.
- **No audio.** README: raw audio "on request" (jensh@drcmr.dk); not requested (the user: envelopes are fine).

## 3. Stimulus <-> trial mapping (verified)
- 44 participants: 22 hearing-impaired (hi), 22 normal-hearing (nh); ear-EEG in 19 (9 hi, 10 nh). 48 trials each
  (2112), all present: per participant 2 blocks x 12 trials attending the male talker and 2 x 12 attending the
  female (24/24 in every participant), each block 4 single-talker + 8 two-talker trials (16 single, 32 two-talker).
- `events.tsv` (`STATUS` rows): `targetonset` (codes 224/240/248/252/254/255/135/133 = single/two-talker x
  male/female x left/right), `maskeronset` (137), `trialend` (131), dummy 128. `stim_file` (as presented, CamEQ for
  hi) and `stim_file_without_cambridge_eq` name the stimulus; `.wav` -> `derivatives/stimuli/<same>.mat`. Trial
  number = the `tNNN` number (target `tNNN` and masker `mNNN` share it). Difficulty rating and questionnaire score
  sit on the `trialend` row.
- Every events.tsv `STATUS` row equals a Status-channel transition in the BDF at `sample - 1` (BIDS samples are
  1-based); the BDF additionally has the returns to the idle code 128 (triggers last ~10 ms). Checked for all 45
  files (`bdf_check/`).
- Envelopes: 3520 used (2112 target, 1408 masker); 1800 distinct contents (hi CamEQ versions are per listener).
  Target `t[0]` = 0; masker `t[0]` = masker trigger - target trigger exactly (3.0-5.0 s, the cue period), so it
  was derived from the triggers.
- Lengths 50.0-56.9 s (target). Maskers end a median 4.3 s (range -3.8 to +11.7 s) after the target: the masker
  file is longer than the trial. Whether its tail was played after the trial-end trigger is not documented.

## 4. Speech features available
Only envelopes (derivatives/README, paper p. 2566): mono (L/R average) of the presented (HRTF-spatialised,
loudness-matched, 12 kHz low-passed) audio, 6 kHz low-pass, 12 kHz, 24 gammatone bands (ERB, 100-4000 Hz, AMT),
full-wave rectified, `|.|^0.3`, averaged, 256 Hz low-pass, 512 Hz. CamEQ vs no-CamEQ envelope of one stimulus:
r = 0.985, level x1.52 (sub001 t001).

**Audio recovery from fuglsang2018 failed (2026-11-24).** Both studies used Danish audiobooks read by a male and a
female talker, so the fuglsang2018 wavs (Zenodo 1199011 `AUDIO.zip`, 128 trial wavs from 11 stories) were tested:
- 8-s windows (512 Hz, the README recipe on the 2018 wavs) of sub001's 80 envelopes: 99th percentile r 0.86;
  10-Hz/64-Hz 10-s windows (sub001, sub030): max r 0.80; 4-s windows with a position-consistency score
  (sub001/012/022/035/042): p99 0.86-0.88, consistency ~0 (`match/*.json`, `match/short_more.log`).
- Positive control of the method: a 2018 wav re-enveloped differently (Hilbert) finds itself at r 0.92-0.98 in every
  4-s window. Pause truncation (450 ms in 2020) breaks fixed windows, so a pause-robust test was added: speech chunks
  >= 2.5 s between silences (`match_chunks.py`). Control (2018 wavs with pauses cut to 450 ms): median r 0.993, 19
  chunks. Shipped envelopes (sub001, sub030): 982 chunks, median 0.57, max 0.81, **none > 0.95**
  (`figures/audio_recovery_chunks.png`).
- Conclusion: the 2020 audiobooks are not in the 2018 release; no other DTU release in the repository has them.
  The shipped envelopes are the stimulus (user, 2026-11-24).

**Representation** (PLAN.md section 2: "envelopes only when audio is unavailable (`feature_name` says which)";
precedent brodbeck2022): `StimulusRecord("audio", name, ..., feature_name="envelope")`, `{"fs": 512, "data": (1,
n)}`, as presented (CamEQ for hi). Hi listeners also get `feature_name="envelope-no-cameq"` (the paper's analysis
used these; results were similar). Names `subXXX-target-tNNN` / `subXXX-masker-mNNN` (envelopes are per listener).
Masker envelopes are zero-padded before their `t[0]` so that sample 0 = target onset for every stream (the masker
was silent then). No shared code was needed.

## 5. Neural data
- BioSemi ActiveTwo, 64 scalp channels (10-20, biosemi64 names) + EXG1-8 + Status, 512 Hz (kept; no resampling).
  ER-3 insert earphones (tube delay not documented, not corrected).
- Units: BDF in µV, read by MNE into V. Scalp 1-40 Hz SD within trials: median per file 6.8-13.6 µV (section 5b);
  EOG 27-31 µV (sub-001): plausible, no scaling issue.
- Reference: CMS/DRL (`EEGReference`), reference-free recording, kept.
- EXG channels per `channels.tsv` `description`, two montages:
  - 24 files (23 participants without ear-EEG + ...): EXG1/2 = left/right mastoid -> `M1`/`M2` (misc); EXG3-5 =
    left eye below/mid/above -> `VEOG_L_low`, `HEOG_L`, `VEOG_L_high`; EXG6-8 = right eye -> `VEOG_R_low`,
    `HEOG_R`, `VEOG_R_high` (eog).
  - 20 files (19 ear-EEG participants; sub-024 has no ear-EEG? see 5b): EXG1/2 = left eye below/mid ->
    `VEOG_L_low`, `HEOG_L` (eog); EXG3-5 = right ear-EEG 1-3 -> `ER1-3`, EXG6-8 = left -> `EL1-3`.
  - The paper says "two bipolar EOG electrodes above and below the left eye"; channels.tsv is more detailed and is
    followed. Labels checked against the data (section 5b).
- **Montage rule:** scalp + EOG + mastoids -> ns_type `eeg` (biosemi64 template positions); in-ear EEG ->
  ns_type `ear-eeg` (6 channels, no positions), same trial, onset and stimuli.
- CMS/DRL dropouts: README lists sub015, 033, 037, 038, 039 (selective attention, during breaks); see 5b.

## 5b. Per-file checks (`scripts/fuglsang2020/bdf_check.py`, `bads_cms.py`, `bads_hf.py`; `bdf_check/*.json`)
- All 45 files: 512 Hz, Status present, every events.tsv `STATUS` row matches a Status transition (section 3).
  Scalp 1-40 Hz SD within trials, median per file 3.8 (sub-042) to 15.3 µV (sub-030).
- CMS/DRL dropouts (sub-015, 033, 037, 038, 039; `bads_cms.log`): every out-of-range span lies outside the trials
  (breaks), as the README says. Nothing to drop.
- Flat: right EOG (EXG6-8) in sub-010 and sub-034 -> `HEOG_R`, `VEOG_R_low/high` bad; EXG6 in sub-022 is ear-EEG
  `EL1` (bad).
- High-frequency (45-200 Hz SD > 5x the montage median): a recurring fault on P2 / PO4 / POz (24 participants),
  sub-033 a parietal cluster (C2, P2, P4, P6, P8, PO4, Pz), sub-014 right fronto-temporal (C6, F8, FC6, FT8);
  sub-039 CP6 at 5.8x in 1-40 Hz without a blink correlation. Ear-EEG: near-dead channels (45-200 Hz < 0.2x) in
  sub-005, 008, 021, 022, 024, 030. All in `BADS` (adaptor) -> `info['bads']`.
- Frontal channels with 3-9x the 1-40 Hz SD correlate with VEOG (|r| 0.6-0.99): blinks, not bad channels (kept).

## 6. Alignment
- Onset = target-onset trigger (Status, events.tsv `sample - 1`); trial length = the target envelope length (EEG
  and target envelope have the same 512 Hz grid). The masker starts at its shipped `t[0]` (= its trigger).
- Trigger generation (sound card vs software port) is **not documented** (paper, README): `trigger_type`
  `unknown`, `alignment_method` `sw_trigger` (as gao2024).
- **Trial end vs envelope length** (`timing_table.py`, `timing_table.csv`, 2112 trials): the trial-end trigger
  comes 6 samples (11.7 ms) before the end of the target envelope in 65 % of trials, 7 (27 %) or 5 (7 %) in most of
  the rest (range 5-13 samples; SD 1.2 ms). Theil-Sen of the error vs trial length (50-57 s): **0 ppm**, constant
  -11.7 ms; per participant also 0. So no drift between the trigger clock and the EEG; the constant ~12 ms is either
  an onset-trigger latency (sound later than the trigger by 12 ms) or an early end trigger. fuglsang2018 shows the
  same pattern (end trigger 3-4 samples early). Not corrected; documented. `drift_ppm` 0.0, `jitter_ms` 1.2 (SD of
  the end-trigger error, quantisation-limited).
- No audio copy, no stimtrack (EXG all electrodes).
- Brain-based checks: section 9 (lag sweep).

## 6b. Masker (distractor) delay and shared segments
- **Delay:** in two-talker trials the masker starts 3.0-5.0 s after the target (uniform, drawn per listener and
  trial; 1408 trials; `figures/masker_delay_per_subject.png`, top). Source: the masker trigger (137) minus the
  target trigger, which equals the shipped masker `t[0]` to the sample in every trial. Hardware timeline, not
  brain-based.
- **Same content, different delay:** the same masker segment is heard by many listeners at different delays
  (figure, middle); aligned on their own first sample the envelopes agree to +-1 sample (bottom). So each
  listener needs their own masker timeline.
- **Storage (user decision 2026-11-24):** every masker is stored per listener and trial (`subXXX-masker-mNNN`,
  `audio02` in the trial file name) with the delay built in: zero-padded from trial onset to `t[0]`, so sample 0
  of every stream is the target onset. The delay is in each trial's sidecar (`masker_delay_s`, from the triggers).
  Maskers run past the trial end and are not cut (cut at the point of use).
- **Shared segments** (`shared_segments.csv`, from `scripts/fuglsang2020/canonical.py` -> `canonical.csv`): the
  no-CamEQ envelopes are grouped by content (normalised cross-correlation over the first 20 s, +-6 s, r > 0.95
  against the first member of a group; 589 groups, all members r >= 0.95, content lag 0 or +-1 sample).
  Groups heard by more than one listener are named `<talker>-NN`, numbered per talker in order of first
  appearance (sub-001 first); they are in the sidecar as `target_segment`/`masker_segment`. Groups heard by one
  listener only (510 of 589) get none (`None`). The csv is committed; `canonical.py` is in the temporary scripts
  folder; the rule above reproduces it.

## 7. Data size
Per participant 48 trials, 41.1 min of EEG (sum of target lengths; mean 51.3 s per trial), 32 two-talker
(27.5 min) and 16 single-talker (13.5 min); identical for every participant (same material, permuted).
Total 44 participants, 30.1 h; ear-EEG 19 participants (13.0 h).
Output (measured on the 20-participant pilot): 6.5 GB scalp + 0.29 GB ear-EEG + 0.26 GB envelopes = 7.1 GB, i.e.
~6.8 MB per 51-s scalp trial (float32 fif); full run 16 GB
(measured: 2112 scalp + 912 ear-EEG trials, 5280 envelope files).
**Extra storage for the per-listener envelopes:** each participant has its own envelope files (target `t` and
masker `m`, 80 per participant; hi listeners also the no-CamEQ copies, 160): 5280 files of ~0.1 MB, ~0.56 GB for
all 44. Storing each of the 589 distinct contents once (section 6b) would take ~0.06 GB, but the CamEQ versions are
individual anyway and the per-listener masker delay would then have to be applied at use. Accepted by the user
(2026-11-24): every stream starts at trial onset with its own delay, at ~3 % of the dataset's size.

## 8. Adaptor
`adaptor.py` (`Fuglsang2020Adaptor`, option `subjects=[...]` for pilots). Download dir = the folder holding the
extracted `ds-eeg-snhl/` (or the BIDS root itself). Condition `single-talker` / `two-talker`; attended talker
(male/female), side, masker onset, CamEQ, ratings and hearing status in the provenance. Subject = participant number
(sub-001 -> 1), session 1 (sub-024's run-2 is the same session; `run` in the provenance). The loader crops the
MNE BDF raw (header kept: `lowpass` 104 Hz = BioSemi's hardware filter at 512 Hz, `meas_date`) rather than
rebuilding it (reviewer, 2026-11-24).

## 9. Validation
Repository validator (`cnsp_datasets.validate`, forward model, average reference over good `eeg`-typed channels, bads
excluded; `scripts/fuglsang2020/validate_fug.py`, `summarise.py`). Results in `validation_full/` (all 44; the
20-participant pilot in `validation/` gave the same picture). The low tier runs at 64 Hz, the HF tiers at the
native 512 Hz; the validator's low-rate fix (`checks.py`, diliberto2023 agent) does not apply here (512 Hz > 64 Hz).

| run (stimulus) | n | low mean r | subj. sig | TRF peak | subject-median offset (median, range) |
|---|---|---|---|---|---|
| scalp, all trials, target | 44 | 0.058 | 44/44 | 172 ms | +0.7 ms (-7..+26) |
| scalp, single-talker, target | 44 | 0.070 | 40/44 | 172 ms | +0.5 ms (-28..+25) |
| scalp, two-talker, target | 44 | 0.052 | 44/44 | 172 ms | -0.1 ms (-10..+23) |
| scalp, two-talker, masker (ignored) | 44 | 0.023 | 30/44 | 141 ms | -1.7 ms (-100..+88; IQR -16..+17) |
| ear-EEG, all trials, target | 19 | 0.015 | 7/19 | 109 ms | -15 ms (-128..+90) |

Population p (circular shift) 0.02 (the floor with 50 shifts) in every run; all pass the low tier.
- **mlr (30-60 Hz, 18-45 ms):** scalp mean SNR 1.89, p = 0.0099, 34/44 subjects; clear peaks at ~27 and ~40 ms
  (`validation_full/scalp_attended/validation.png`). Ear-EEG fails (SNR 1.00, p = 0.57).
- **brainstem (30-250 Hz, 4-9 ms):** nominal pass (SNR 1.16, p = 0.0099, 8/44), but the 30-250 Hz TRF has no
  wave V; it rises at ~15 ms into the MLR peak at ~30 ms, which leaks into the window. The feature is a 512 Hz
  envelope low-passed at 256 Hz, not the rectified waveform PLAN.md requires. **Tier recorded: `mlr`** (scalp),
  **`low`** (ear-EEG), `VALIDATION_TIER` in the adaptor.
- **Attention (two-talker trials):** attended r 0.052 vs ignored 0.023; attended > ignored in **39/44** (Wilcoxon
  p = 1.4e-10); hi 19/22 (0.055 vs 0.021), nh 20/22 (0.048 vs 0.025). The paper reports stronger tracking of the
  target in hi listeners; the same direction here.
- **Ignored-stream lag sweep (user's check of the masker delay):** the per-subject best shift of the per-listener
  masker is centred on 0 (median -1.7 ms, IQR -16..+17 ms), with a cortical TRF (peak 141 ms, nothing at negative
  lags). Had the delay been wrong by the 3-5 s jitter, no peak would be found within +-0.5 s. So the delays from the
  triggers (= shipped `t[0]`) are right. Figure: `figures/attended_vs_ignored_lag.png`.
- Ear-EEG: weak but above chance (7/19 subjects), as expected for 3 electrodes per ear canal; peak 109
  ms. Useful for group-level or pooled analyses only.

## 10. Alignment grade
**`medium`**: trigger generation unknown (no audio copy or stimtrack); shipped trigger timing kept with no
correction; validation confirms it (low tier 44/44, TRF peak 172 ms, MLR at 18-45 ms in 34/44, lag-sweep peak at
+0.7 ms for the target and -1.7 ms for the per-listener masker, nothing at negative lags). The masker delay is
hardware (trigger-derived), not brain-based.
