# karunathilake2023: clear vs noise-vocoded audiobook passages, KIT MEG (Dryad, raw MEG)

Explorer notes (2026-11-23). Review scripts: `tmp/review/scripts/karunathilake2023/` (named per finding); figures
`tmp/review/karunathilake2023/figures/`. Nothing below has been changed in the data; decisions for the human
checkpoint are in section 8.

## 1. Source
- Dryad doi:10.5061/dryad.sbcc2frd6, "Neural tracking measures of speech intelligibility: Manipulating
  intelligibility while keeping acoustics unchanged", version 4 (2023-11-18), **CC0 1.0**.
- Paper: Karunathilake IMD, Kulasingham JP, Simon JZ (2023). PNAS 120(49):e2309166120,
  doi:10.1073/pnas.2309166120 (`data_campaign/papers/karunathilake2023.pdf`). Preprint doi:10.1101/2023.05.18.541269.
- Code (`Codes.zip`): Eelbrain pipeline `exp.py` (trigger codes, epochs, subject groups), `make_gammatone*.py`,
  `results1.ipynb`. Read, not run.
- Download (registry `karunathilake2023`, Dryad API with `DRYAD_TOKEN`; 2026-11-23, 1 h 42 min): 8 files, 83.5 GB,
  every file's sha-256 verified against Dryad by the downloader (`download_log.tsv`); zips kept, and `unzip -t` of
  the three MEG zips reports no errors. Skipped by `exclude`: `mri.zip` (11.0 GB, fsaverage coregistration) and
  `TRFs.zip` (1.2 GB, authors'
  boosting results). The README lists a `predictors.zip` that is **not on Dryad** (no TextGrids, transcripts or word
  predictors are shared).

| file | bytes | content |
|---|---|---|
| meg_main1.zip | 30,482,344,958 | 14 main-study participants |
| meg_main2.zip | 27,747,225,279 | 13 main-study participants |
| meg_control.zip | 25,067,737,589 | 12 control-study participants |
| stimuli.zip | 159,617,918 | 96 wavs |
| behavioral.zip | 228,391 | ratings, demographics, TRF peak tables |
| Codes.zip, statistical.zip, README.md | small | code, R notebooks, readme |

## Relation to other datasets
- **Not the same data as `karunathilake2023_aging`** (J Neurophysiol 2023): different paper, stimuli (Sleepy
  Hollow vs Botany of Desire), design, repository (DRUM vs Dryad) and data level (6 DSS components vs raw sensors).
  No shared participants: aging R2509-R2672; this dataset R2383 and R2684-R3015.
- **Same audiobook as `brodbeck2022`** (The Botany of Desire, M. Pollan, male narrator), which ships no audio. Here
  the excerpts are edited (pauses > 400 ms shortened to 400 ms, 4 kHz elliptic low-pass), so not sample-identical
  to brodbeck2022's clips even where the text overlaps. Overlap with `karunathilake2025`: not checked.

## 2. Layout
- `meg_{main1,main2,control}/R####/`: `R####_voc-raw.fif` (2.1 GB) + `R####_voc-raw-1.fif` (FIF split; MNE joins
  it), `R####_emptyroom-raw.fif` (47-66 MB; empty-room recording), `R####-trans.fif` (head -> MRI for the
  scaled fsaverage). macOS `.DS_Store` / `__MACOSX` junk is skipped on extraction.
- `stimuli/split{k}.wav` (clear) and `stimuli/split{k}_vocoded.wav`, k = 1-48 (only 1-36 used).
- `behavioral/`: `Ratings_main.xlsx` (27 sheets, one per participant: Trial, PRE, Q2, POST), `Ratings_control.xlsx`
  (12 sheets: Trial, PRE1, Q2, PRE2), `Demographic.xlsx` (Main 27 / Control 12 rows: age, handedness, sex), TRF peak
  csvs (authors' results).

## 3. Stimulus <-> trial mapping
- Trigger codes (exp.py `SNR`, `label_events`): **164 = PRE (vocoded), 165 = CLEAN, 166 = POST (vocoded)**. One code
  per passage onset, **no offset codes**. The k-th occurrence of a code is passage k: 164 -> `split{k}_vocoded`,
  165 -> `split{k}`, 166 -> `split{k}_vocoded` again (exp.py builds `split{k}_vocodedp` names for its own
  predictors; there is no separate POST file: the paper says POST is acoustically identical).
- Order in the data: main study 164, 165, 166 per passage; **control study 164, 166, 165** (PRE1, PRE2, CLEAN, as in
  the paper), so in the control study 166 is the second vocoded presentation and CLEAN comes last.
- All 39 participants: 36 x 3 = 108 triggers, no other codes, passages 1-36 in story order (same stimuli for
  everyone). Check: for every trial the time to the next trigger exceeds the passage duration (by >= 0.38 s in the
  main study, where POST follows CLEAN directly, and >= 3.6 s in the control study; `survey.py`, `survey.json`).
  Recordings 54-68 min.
- Ratings: sheet row `Trial` k = passage k (clarity 0-5 after each vocoded presentation; `Q2` 0/1, meaning not
  documented; presumably the comprehension question after POST/PRE2).
- Participants (39 shipped): main 27 = the 25 in exp.py `ALL` + **R2383 and R2806** (in no list in the code;
  ratings and demographics shipped); control 12 = the 11 in `ALL` + **R3015**. exp.py `good_sub2` (23 main
  participants, the paper's analysed N) excludes R2813 and R2891 = the paper's "two excluded for excessive
  artefacts" (inferred). All are standardised; list membership goes into the sidecar.

## 4. Speech features available
- Raw audio for every played stimulus: 44.1 kHz mono int16, 17.5-26.5 s; each vocoded wav has exactly the length of
  its clear wav. **The vocoded wavs are clipped**: every one reaches +-32767, median 3.9e-5 (max 1.8e-4) of samples
  at full scale; the clear wavs are not (one sample in one file). This is what was played; noted, not changed.
- No TextGrids/transcripts (the `predictors.zip` the README describes is not on Dryad).

## 5. Neural data
- KIT 160-channel system ("University of Maryland/Kanazawa Institute of Technology/160-channel MEG System (54)
  V2R004 PQ1160R"), converted to FIF by the authors (MNE): `MEG 001-157` axial gradiometers (MNE type `mag`, coil
  `KIT_GRAD`, T), 3 reference magnetometers (`ref_meg`), `MISC 001-032` (V), `STI 014`. 1000 Hz, online 200 Hz
  low-pass, 60 Hz notch (paper); `info` highpass 0, lowpass 200. Units T (median gradiometer rms ~2e-13 T).
  Head-shape digitisation in `info['dig']` (2238 points in R2963). No projectors, no software compensation, no
  bads marked, no annotations.
- One continuous recording per participant, 54-68 min.
- MISC lines (R2963; `misc_survey.py`, `misc_clip.py`; figures `misc_psd_R2963.png`, `misc_time_R2963.png`):
  MISC 005-007 = TTL trigger lines (5 V idle, pulses to 0; STI 014 is built from them); the other lines are 5 V
  constant (unused), or MISC 018 (broadband noise + mains harmonics), MISC 030-032 (flat noise floor). **No audio
  copy**: cross-correlation of MISC 018/030/031/032 with each played wav (< 190 Hz) and its envelope over -0.5..+2 s
  gives |r| <= 0.13 at random lags in every trial tested (`audio_channel.py`). No peripheral (EOG/ECG) is recorded.
  All MISC lines and STI 014 are dropped.
- Flat channels (rms < median / 20 in 10 x 10 s windows; all 39 participants, `survey.json`): **MEG 086** in every
  participant except R2963; **MEG 056** in every participant except R2865-R2891 (main2, recorded in sequence).
  Marked in `info['bads']` per participant by the adaptor. One noisy channel: **R2851 MEG 062** (~6x the rms of its
  neighbours, but a normal spectrum: no line-noise dominance, 43% of power in 1-20 Hz like MEG 061/063); not
  electrical noise only, so left unmarked (open question 6).
- Reference: not applicable (MEG). Empty-room recordings are shipped but not standardised (not continuous speech).

## 6. Alignment
- Triggers: TTL codes from Presentation (paper) on MISC 005-007. Hardware vs software: the TTLs are sent by the
  stimulus software (**software, inferred**); the latency from trigger to sound and the E-A-RTONE tube delay are
  **unknown** (not in the paper; no audio channel). Same lab, system and software as brodbeck2022.
- Proposed (and implemented) alignment: onset = trigger sample, no shift; trial length = played wav length at
  1 kHz. Constant offsets found later (lag sweep, TRF latency) are documented, not applied.
- Drift: **not measurable** (no offset triggers, no audio channel; the gap to the next trigger includes the rating
  and question time). Not corrected. Trials are <= 26.5 s, so typical sound-card drift (10-50 ppm) is <= 1.3 ms
  per trial.

## 7. Cross-subject duration check
- Not possible (onset triggers only). `drift_ppm = null`, `jitter_ms = null`.

## 8. Adaptor (implemented, 2026-11-23)
- Shared code with the lab's other KIT datasets (R-number subjects, wav loaders, epoch/continuous-raw helpers,
  bad-channel rules) in `datasets/simon_base/common.py` (2026-11-23; output unchanged except subject numbers).
- Reads `**/meg_*/R*/R*_voc-raw.fif`, `**/split1.wav` (stimulus folder) and `**/Ratings_{main,control}.xlsx` under
  the download root (extracted zips).
- Subject = full R-number (user, 2026-11-23); earlier outputs used R-number mod 1000 (R2383 -> 2383, was 383; R3009 ->
  3009, was 9). Checked unique; R-number also in the sidecar (`participant`). Session 1.
- Trials 1-108 in presentation order. Conditions: main `pre`, `clean`, `post`; control `control-pre1`,
  `control-pre2`, `control-clean`.
- Neural data: gradiometers + reference magnetometers (160 channels), T, 1000 Hz native (no resample), cropped
  with `crop_on_audio_clock` at the trigger for the wav duration; MISC and STI 014 dropped; flat channels in
  `info['bads']` (rule above, computed in the adaptor).
- Stimulus: the played wav (44.1 kHz, int16 / 32768 as float32, uncut), attended; vocoded trials use
  `split{k}_vocoded`, clean trials `split{k}`.
- Sidecar: `sw_trigger`, trigger_type as above, `drift_ppm`/`jitter_ms` null, plus `participant`, `study`,
  `passage`, `presentation`, `trigger_code`, `onset_s`, `stimulus_file`, `vocoded`, `clarity_rating` (vocoded
  trials), `q2_as_shipped`, `in_authors_pool` (exp.py `ALL`), `in_authors_main_analysis` (exp.py `good_sub2`, main
  only), `units_as_shipped` ("T"), `reference` ("not applicable (MEG)"); the last two as in the lab's other KIT
  datasets (user decision, 2026-11-23).

## Upstream issues
- README lists `predictors.zip`; it is not in the Dryad record.
- Vocoded wavs clip at full scale (1e-4 of samples).
- Paper reports 25 main + 12 control participants; 27 main participants are shipped (R2383, R2806 extra) and the
  control participant R3015 is not in the code's subject list.

## Open questions (human checkpoint; recommended default in brackets)
1. Onset = trigger with no latency correction (software TTL, tube delay unknown). [yes; document the lag-sweep /
   TRF latency, do not shift]
2. Subject numbering R-number mod 1000 until the reader accepts 4-digit subjects. [yes; better: allow `\d{3,}` in
   `base_sink.py` and use the full R-number. Done 2026-11-23: full R-number]
3. Include R2383, R2806 (not in the authors' lists) and R3015. [yes, flagged in the sidecar]
4. Drop all MISC lines and STI 014 (no peripherals, no audio copy). [yes]
5. Condition names (`pre`/`clean`/`post`, `control-pre1`/`control-pre2`/`control-clean`). [yes]
6. R2851 MEG 062 (noisy, not flat): leave unmarked or add to bads? [leave unmarked; mention in the README]
7. Full standardisation (39 participants, ~59 GB, i.e. ~35 GB more than the 24 GB pilot of 16) once tmp has
   room. [run it after the zips or the extracted copies are deleted]
8. Storage: the zips (78 GB) and the extracted copies (102 GB) duplicate each other. [delete the extracted MEG of
   non-pilot participants now, re-extract per participant for the full run; or delete the zips, since sha-256 and
   `unzip -t` both passed]

## 9. Validation
Repo validator (`validate_cond.py`, standardised data as stored, picks `mag` = good axial gradiometers, no
re-referencing, tiers low/mlr/brainstem; results and four-panel figures in
`tmp/review/karunathilake2023/validation/<set>/`).
- **Control study, pooled (12 participants, 1296 trials; `validation/control_all/`)**: tier **brainstem**. Low:
  median r 0.040 (subjects 0.024-0.056), 12/12 above the circular-shift null, p_circ 0.020, p_mismatch 0.048; TRF
  peaks ~110 ms and ~360 ms, nothing at negative lags. mlr (30-60 Hz, 18-45 ms): mean SNR 1.01, p 0.050, 1/12
  subjects; the 30-60 Hz GFP peaks at ~50 and ~62 ms, later than the window (brodbeck2022, same lab/system/
  software: 58 ms, low-tier TRF peak also 109 ms). Brainstem (30-250 Hz, MEG window 28-45 ms): mean SNR 1.29,
  p 0.010, 9/12 subjects, sharp peak at ~38 ms, flat at negative lags. Per-trial offset estimates are not
  informative for 20 s MEG trials (MAD 60 ms, 52 at the search edge). No sign of a trigger-to-sound latency beyond
  what brodbeck2022 shows.
- **Control study per condition** (36 trials per participant each; `validation/control_{pre1,pre2,clean}/`):

  | condition | low median r | subjects sig | TRF peak | mlr SNR (p, subj) | brainstem SNR (p, subj) | tier |
  |---|---|---|---|---|---|---|
  | control-pre1 | 0.042 | 12/12 | 125 ms | 0.97 (0.24, 1/12) | 1.09 (0.010, 5/12) | low |
  | control-pre2 | 0.051 | 12/12 | 78 ms | 0.99 (0.14, 1/12) | 1.03 (0.10, 2/12) | low |
  | control-clean | 0.040 | 11/12 | 94 ms | 1.03 (0.010, 1/12) | 1.45 (0.010, 10/12) | brainstem |

  The high-frequency response comes from the clean speech; noise-vocoded speech has no F0/harmonic structure for
  the 30-250 Hz response to follow, so its weak HF tiers are acoustic, not a timing problem. Clean 30-250 Hz TRF:
  onset ~18-20 ms, peaks ~33 and ~38 ms, nothing at negative lags. R3009 (sub 9) is at its null in control-clean
  (r 0.007).
- **Main study pilot (4 participants: R2684, R2813, R2851, R2883; R2813 is one of the two the authors excluded;
  432 trials; `validation/main_{all,pre,clean,post}/`)**. Only a pilot was standardised because of the tmp storage
  limit (2026-11-23); the full run (27 main participants, ~40 GB) is pending.

  | set | low median r | subjects sig | TRF peak | mlr SNR (p, subj) | brainstem SNR (p, subj) | tier |
  |---|---|---|---|---|---|---|
  | pooled | 0.032 | 4/4 | 94 ms | 1.08 (0.010, 1/4) | 1.70 (0.010, 4/4) | brainstem |
  | pre | 0.031 | 4/4 | 94 ms | 0.96 (0.32, 0/4) | 1.13 (0.010, 1/4) | low |
  | clean | 0.031 | 4/4 | 94 ms | 1.05 (0.030, 1/4) | 2.11 (0.010, 4/4) | brainstem |
  | post | 0.035 | 3/4 | 109 ms | 0.90 (0.66, 0/4) | 1.11 (0.010, 2/4) | low |

  Same picture as the control study: pooled 30-250 Hz peak at ~40 ms, nothing at negative lags; the HF tiers come
  from the clean speech.
- Sizes: standardised output ~1.5 GB per participant (108 trials, 160 channels, float32); control 12 = 18 GB, main
  pilot 4 = 6 GB. Full dataset would be ~59 GB.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**medium**: Software TTL trigger, no audio copy, no shift; drift not measurable; brainstem tier (clear speech), flat at negative lags.

## Restructure 2026-11-25 (not yet re-validated on data)
- Adaptor on `BaseAdaptor`; bads computed by the adaptor are now added to the recording's own `info['bads']`
  (`iohelpers.mark_bads`, strict) instead of replacing them; the shipped files list none, so no change is expected;
  stimulus wavs read with soundfile through `simon_base.read_wav` (`iohelpers.read_wav`): float32 in [-1, 1), any PCM
  width; the same values as before for the shipped int16 wavs; dataset.json: paper DOI.
