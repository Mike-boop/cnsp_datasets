# peng2026: SoundBubble-EEG, 128-ch EGI, two competing Mandarin conversations in three scenes

Explored 2026-11-24 (worker session). Scratch: `R/peng2026/` (`R=/data_storage/gu08wuvu/datasets/tmp/review`);
one-off scripts in `R/scripts/peng2026_*.py`.

## 1. Source
- Zenodo 19610628 (concept 19610627), "SoundBubble-EEG: A Multi-Scenario Dataset for Naturalistic Multi-Talker
  Auditory Attention Decoding", Peng, Liu, Zhang, You, Chen, Xi, Sun, Liu, Tan, Wu (Hong Kong PolyU). CC0 1.0.
- One file: `Sound_Bubble_BIDS.zip` (21,579,121,604 B, md5 90017a8ee961afba4627f4dbe8389a75, checked on woody and
  locally; `unzip -t` clean). Copied from woody (`/home/woody/iwpm/iwpm104h/zenodo/peng2026/19610628/`), not from
  Zenodo. No vault backup yet (woody holds the copy).
- Paper: `data_campaign/papers/peng2026.pdf` (preprint; "paper in preparation" per the README).
- Code: github.com/Mashirops/sound-bubble-eeg-code (read, not run). `preprocessing/run_full_pipeline.py` builds the
  events.tsv (and the sub-01..09 re-alignment); `technical_validation/aad_baseline/material_complete.csv` lists the
  attended/ignored source per scene (not in the data release).

## 2. Layout (BIDS, extracted in place)
- `sub-XX/eeg/sub-XX_task-auditory_run-0{1,2,3}_eeg.mff`: raw Net Station MFF (one epoch each; 1 per run), with the
  Net Station log `log_*.txt` inside. `_events.tsv` per run: onset, direction_str (cue), SoundOut1.OnsetTime
  (E-Prime ms), condition (Restaurant/TV/Office), run_id (1-25, the authors' trial number).
- `sourcedata/sub-XX/beh/*_beh.txt`: E-Prime logs (UTF-8): wavfile, direction, SoundOut1.OnsetTime, answers.
- `stimuli/{restaurant,tv,meeting}/Sxxxxx_mix_CH0.wav`: 25 binaural mixtures, 16 kHz stereo PCM16, 126.0058 s.
- `derivatives/preprocessed/`: authors' 0.1-40 Hz, interpolated, CAR, ICA-cleaned epochs (not used, not extracted).

## 3. Stimulus <-> trial mapping
- 30 participants (sub-01..30), one visit, 3 runs: run-01 restaurant (10 scenes), run-02 TV (10), run-03 meeting
  (5). Recorded in the order run-03 -> run-01 -> run-02 for everyone (MFF meas_date; paper: Meeting, Restaurant,
  TV). Same 25 scenes in the same order and with the same cue for all participants.
- Mapping: the E-Prime log gives the wav file for each SoundOut1.OnsetTime, which matches events.tsv exactly (750
  trials). It also matches the authors' material table (run_id order). Practice trials (sub-01..03 run-03: 5
  `kul_ch0` scenes, not shipped) are in the E-Prime log but not in events.tsv; excluded.
- All 750 trials lie inside their recordings. No missing data.
- Cue: left (14 scenes), right (7), front (4, TV: the TV programme in front). Restaurant/meeting: two
  conversations at opposite lateral azimuths plus noise; TV: TV in front, family conversation lateral.
- **Only the binaural mixture is released.** The per-source wavs the authors used for the AAD analysis
  (`cafe_R00358_R8005_M8007_MS806_48951.wav`, ...) are not in the release (their README: "data rather than code").
  So no attended/ignored envelopes; see section 8.

## 4. Speech features
- Audio: the binaural mixture as played (stereo, 16 kHz). Speech from AISHELL4/AliMeeting-style meeting
  recordings (names like `R8005_M8007_MS806`), TV clips (YouTube ids), DEMAND/WHAM noise; CIPIC/KEMAR HRIRs.
  Scene metadata (source names, positions, SNR 15 dB) in the authors' `material/scenes.*.json`.
- No transcripts, no TextGrids, no separate streams.

## 5. Neural data
- EGI NA-400, HydroCel GSN 128, Net Station 5.2, 250 Hz, online reference Cz (VREF), ground COM. MNE
  `read_raw_egi`: 133 channels = E1-E128 + VREF (eeg; VREF all zeros) + SESS/CELL/TBEG/TEND (stim). Units: MFF
  stores µV; MNE reads V. 1-40 Hz SD median ~15-60 µV per run (sub-04 run-03 and sub-22 have large DC/drift).
- Kept: E1-E128 + VREF (Cz, zeros: the reference), native 250 Hz (no resampling). Dropped: the 4 event channels.
  No PNS/peripheral channels, no EOG (periocular E-channels instead). Positions: MFF `coordinates.xml` (same file
  in every recording: the HydroCel template, not digitised).
- Bad channels (`bads.py` -> `bads.json`, per participant, as the validator needs one channel set per subject):
  1-40 Hz SD per trial window, > 5x or < 1/5 of the median over channels in >= 20% of the participant's 25
  trials; the periocular channels (E1, E8, E14, E17, E21, E25, E32, E125-E128) are only tested for low SD (their
  high SD is blinks; testing them flagged 4-11 of them in most participants). 0-10 bads per participant (mean
  2.4; sub-08 10, sub-17 9); flat E43/E126 in sub-18 caught.

## 6. Alignment
### 6a. Triggers
- E-Prime 2.0 sends ECI events to Net Station over TCP (`ECI TCP-IP 55513`): SESS, CELL, TBEG (trial begin), TEND.
  Software triggers. NTP clock sync (`eci_NTPClockSynch`) once at the start of each run; Net Station maps an
  event's E-Prime timestamp to amplifier time with that single clockDiff.
- **sub-10..30:** the TBEG payload is exactly E-Prime's SoundOut1.OnsetTime (e.g. sub-10 run-01: `eventData:
  24495000 + 3982666349` and OnsetTime 24495 ms). So the markers are E-Prime's logged sound onset on the E-Prime
  clock, offset once. Shipped onset vs OnsetTime: slope 0 ppm, residual SD 1 ms (sample rounding) in all 63 runs.
- **sub-01..08 (and sub-09 partly): the E-Prime bug.** E-Prime sent every TBEG with timestamp 0, so every marker
  lands at the same time (e.g. -19.715 s in sub-01; Net Station then drops the duplicates). sub-09 run-01/03
  markers are valid; run-02 has 6/10 valid (the 4 "front" trials of sub-01..09 send no TBEG at all).
- The authors' fix (README, `run_full_pipeline.py`): match the TBEG *arrival* lines of the Net Station log
  (Mac wall clock) to OnsetTime by a difference histogram, fit a line, predict each trial's arrival time, take
  it relative to "EEG START RECORDING" as the onset, minus a run constant (25.1/16.7/-6.0 ms) from sub-10..30.

### 6b. Clocks (R/scripts/peng2026_clocks.py, R/peng2026/timing/clocks.csv)
- **Mac log clock vs amplifier samples:** the log's START->STOP span exceeds the sample count / 250 Hz by
  ~+79 ppm in every run (46-96 ppm per run; Net Station drops/pads samples to keep the file on the amplifier
  clock). So log times are not EEG times.
- **Mac log clock vs E-Prime (marker) clock:** TBEG arrival minus marker (sub-10..30) has slope +65 ppm (runs
  01/02, SD 3) and +32 ppm (run-03, SD 10); arrival jitter ~9 ms SD per trial.
- Hence E-Prime ~ amplifier clock within ~15 ppm (79 - 65; not measurable better without hardware), and
  **the authors' sub-01..09 onsets inherit the Mac clock rate: they drift by ~+65 ppm within each run**
  (shipped onset vs OnsetTime slope +78 ppm, SD 9, in all 27 runs of sub-01..09 vs 0 ppm in sub-10..30).
- Ground truth from sub-09 (valid markers): authors' onset - marker goes -8 -> +76 ms over run-01 (1230 s),
  -48 -> +24 ms over run-02, -12 -> +12 ms over run-03. Figure `R/peng2026/timing/onset_reconstruction_sub01-09.png`.

### 6c. Onsets used (onsets.py; option `onset`)
- `onset="corrected"` (default): onset = OnsetTime + c, c one constant per run (slope 1, like sub-10..30):
  - runs with >= 3 valid (distinct, consistent within 5 ms) ECI TBEG markers: c = median(marker - OnsetTime):
    sub-09..30 (identical to the shipped onsets for sub-10..30 within sample rounding, |d| <= 3 ms);
  - other runs (sub-01..08): c from the log arrivals: arrival = (1 + eps)(OnsetTime + c) + L, with eps and L
    per run from sub-10..30 (CALIBRATION: run-01 64.8 ppm / -18.3 ms, run-02 65.8 / -26.6, run-03 32.2 / -4.7).
  - Accuracy (leave-one-subject-out on sub-10..30, `python -m cnsp_datasets.datasets.peng2026.onsets <dir>`):
    run-offset error mean -4.4 ms, SD 17.6 ms, max 87 ms (sub-24 run-03; others |e| > 30 ms: sub-16 run-03,
    sub-18 runs 1-3); no within-run drift. sub-09 check: reconstruction - marker = +11, -31, +1 ms per run,
    constant within a run (±2 ms).
  - Effect vs shipped (sub-01..08): +20..+37 ms on the first trial of a run to -54..-90 ms on the last.
- `onset="authors"`: the shipped events.tsv onsets.
- This correction is derived from the acquisition logs (clocks, event arrival), not from the EEG; applied by
  default as the better trigger reconstruction (worker default; listed for the user's decision).
- The absolute sound onset relative to OnsetTime (audio output latency, Windows/E-Prime) is unknown; no stimtrack.
- In-ear tubes: none (Sony MDR-EX15LP earbuds).

### 6d. Drift
- Within a trial (126 s), the E-Prime/amplifier mismatch (<= ~15 ppm) is < 2 ms; the sound card's clock is
  unknown. No drift correction (nothing hardware-derived to apply). drift_ppm = null.

### 6e. DNN offset (accou2023 match-mismatch, every trial; R/scripts/peng2026_dnn.py, _dnn_plot.py)
Mixture envelope (mean of the ear envelopes), +-500 ms, 5-s windows, 1-s hop, 750 trials. Figure
`R/peng2026/dnn/dnn_offsets.png`, numbers `R/peng2026/dnn/summary.json`.
- All trials, corrected onsets: **-26 ms** (95% CI -33..-24; negative = EEG late), i.e. speech-in-noise latency
  (~-15 ms expected) plus perhaps ~10 ms audio output latency. Per scene: restaurant -38, TV -23, meeting -29 ms.
- sub-09..30 (markers): -25 ms (-28..-22); early trials of a run (onset < 500 s) -32, late (> 900 s) -23 ms.
- sub-01..08, corrected (log) onsets: -32 ms (-37..-29); early -42, late -31 ms: same pattern as the marker group.
- sub-01..08, **shipped onsets**: early -60 ms, late **+24 ms** (84-ms ramp within the runs, as the clock analysis
  predicts; the pooled +2 ms is the average of the ramp). This independently confirms the correction (brain-based
  check only; nothing applied from it).
- The ~9-ms early/late difference in both groups would fit an E-Prime vs amplifier drift of ~+10 ppm (6b
  estimates <= ~15 ppm); within the CIs, not applied.

## 7. Cross-subject duration check
- No end-of-sound marker usable (TEND is sent ~123 s after onset with a separate payload; not the sound end).
  Onset spacing vs OnsetTime: see 6b.

## 8. Attention contrast without separate streams
- The cue direction is in the provenance (`cue_direction`), with the scene id. Because the two conversations are
  lateralised (restaurant/meeting at opposite sides; TV front vs side) and the mixture is binaural, the left- and
  right-ear channels of the mixture are a proxy for the left/right talker (ILD). The validation uses the ear on
  the cued side as "attended proxy" and the other ear as "ignored proxy" (left/right trials only). Both ear
  channels also carry the scene noise and the other talker, so the contrast is weaker than with clean streams.

## 9. Validation (2026-11-24, all 30 participants, 750 trials, average reference, bads excluded)
Native 250 Hz, so only the low tier (mlr/brainstem need >= 500 Hz).
- **Low tier, pooled** (`validation.json`; figure `R/peng2026/validation/validation.png`): mean r 0.0083
  (median 0.0077), p_circ 0.020, p_mismatch 0.048, 12/30 subjects significant; pass. The forward-TRF GFP stays
  inside the null band (peaks at ~110 ms and ~300 ms, nothing at negative lags): weak, as expected for a
  binaural mixture with 15-dB background noise as the regressor (the authors' backward r_attend ~0.026).
- **Per scene** (`R/peng2026/validation_subsets/<scene>/`): restaurant mean r 0.0063, p_circ 0.020, p_mismatch
  0.048, 5/30 significant; TV 0.0043, p_circ 0.020, **p_mismatch 0.19** (fails the mismatch null: the TV
  scenes' envelopes are alike); meeting 0.0058, p_circ 0.020, p_mismatch 0.048, 2/30.
- **Per onset group**: sub-01..08 (log onsets) mean r 0.0089, p_circ 0.020, p_mismatch 0.095, 4/8 significant;
  sub-09..30 (markers) mean r 0.0080, p_circ 0.020, p_mismatch 0.048, 8/22 significant (same level).
- **Backward model / attention contrast** (R/scripts/peng2026_aad.py, _aad_plot.py; figure
  `R/peng2026/aad/r-attended-vs-r-ignored.png`): ear-channel proxies (section 8), 21 left/right-cued trials per
  subject, LOTO ridge decoders 0-250 ms at 64 Hz. Held-out r: attended-ear 0.034, other-ear 0.033 (own decoders;
  Wilcoxon p 0.67). AAD accuracy (attended decoder, cued ear > other ear): pooled 0.55 (630 trials, binomial
  p 0.008); restaurant **0.61** (p 8e-5), TV 0.52 (p 0.35), meeting 0.47 (p 0.82). sub-01..08 0.57 vs sub-09..30
  0.54. The proxy is weak (each ear carries both talkers and the noise; TV left/right cues leave the frontal TV
  in both ears); the authors' clean-stream decoders reached 0.77/0.72/0.61.
  **Lag sweep of the backward decoder: peak at 0 s** (+-1 s sweep, 31 ms steps), sharp, in nearly every subject.
- Alignment grade (proposed): **medium**. Software triggers (E-Prime's logged sound onset via ECI; sub-01..08
  rebuilt from the Net Station log), the shipped marker timing kept for sub-09..30, validation consistent (low
  tier at population level, backward lag sweep peaking at 0, DNN -26 ms with no negative-lag artefact, sub-01..08
  matching sub-09..30 after the log correction). No brain-based correction applied. Caveat: sub-01..08 run
  offsets carry ~18 ms SD (max ~90 ms) reconstruction error.

## 10. Data size
30 participants x 25 trials x 126.0 s = 52.5 min per participant (all equal; range 52.5-52.5): restaurant 21.0,
TV 21.0, meeting 10.5 min. Total 26.25 h. Standardised: 750 fif (~16.3 MB each) + 25 stereo audio npz, 15 GB.

## Upstream issues
1. sub-01..09 events.tsv onsets drift ~+65 ppm within each run (up to ~0.1 s late by the end of a run; sub-09
   markers show it): the regression maps E-Prime onsets onto the Net Station (Mac) log clock, which runs ~79 ppm
   fast against the amplifier sample clock. Fix: keep slope 1 on the E-Prime clock (as for sub-10..30).
2. sub-09 had valid ECI markers in runs 01 and 03 (and 6/10 in run-02) but was re-aligned with the log method.
3. Only the binaural mixtures are released, not the per-talker wavs used for the AAD baseline (and the
   `stimuli/metadata/` JSONs the paper mentions are not in the zip).
4. events.json says `run_id` is "1 = Restaurant, 2 = TV, 3 = Office"; it is the trial number 1-25.

## Open questions (worker defaults)
0. Alignment grade: proposed medium (section 9).
1. Apply the log-based onset correction for sub-01..08 (and markers for sub-09) by default? Default: yes
   (`onset="corrected"`); `onset="authors"` restores the shipped onsets.
2. Attention contrast: ear-channel proxy only (no separate streams). Default: as in section 8.
3. The separate talker streams could be requested from the authors (user's call; never contact them from here).
4. Per-run bads would be more precise (nets were re-wetted between runs) but the validator needs one channel set
   per subject. Default: per participant.

## Reproduction (scratch scripts, R/scripts/)
peng2026_events_fit.py (onset vs OnsetTime slopes), peng2026_clocks.py (log vs sample clock), peng2026_recon.py
(first reconstruction + sub-09 check, figure R/peng2026/timing/onset_reconstruction_sub01-09.png),
peng2026_pipeline.sh (bads, standardise, validate, AAD), peng2026_validate_subsets.py, peng2026_aad.py /
_aad_plot.py, peng2026_dnn.py / _dnn_plot.py. Logs and outputs next to the results in R/peng2026/.
