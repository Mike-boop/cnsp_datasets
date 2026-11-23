# karunathilake2025: noise, nonwords, scrambled words and narrative (gTTS passages), KIT MEG (Dryad, raw MEG)

Explorer notes (2026-11-23). Review scripts: `tmp/review/scripts/karunathilake2025/` (named per finding); results
and figures `tmp/review/karunathilake2025/` (`survey/*.json`, `figures/`, `validation/`). Nothing below has been
changed in the data; decisions for the human checkpoint are in "Open questions".

## 1. Source
- Dryad doi:10.5061/dryad.ht76hdrpf, "Data from: Neural dynamics of the processing of speech features: Evidence
  for a progression of features from acoustic to sentential processing", version 5 (2025-01-31), **CC0 1.0**.
- Paper: Karunathilake IMD, Brodbeck C, Bhattasali S, Resnik P, Simon JZ (2025). J Neurosci 45(11):e1143242025,
  doi:10.1523/JNEUROSCI.1143-24.2025 (`data_campaign/papers/karunathilake2025.pdf`). Preprint
  doi:10.1101/2024.02.02.578603.
- Code (`Codes.zip`): Eelbrain pipeline `exp.py` (trigger codes, subject list, epochs, tSSS + 1-10 Hz settings),
  notebooks, R analysis, TRF peak tables. Read, not run.
- Download (registry `karunathilake2025`, Dryad API with `DRYAD_TOKEN`; 2026-11-23, meg.zip 1 h 04 min at
  ~13-19 MB/s, 1 worker): 6 files, 52.1 GB, every file's sha-256 verified by the downloader (`download_log.tsv`),
  zips kept, `unzip -t` clean for all. Skipped by `exclude`: `trfs.zip` (333 MB, authors' boosting results).

| file | bytes | content |
|---|---|---|
| meg.zip | 51,977,401,590 | 30 participants: recording + empty-room FIF |
| predictors.zip | 100,551,115 | authors' predictors, eelbrain pickles (section 4) |
| Stimuli.zip | 36,053,314 | 16 wavs, transcripts, acoustic-comparison scripts |
| Codes.zip | 11,108,404 | exp.py, notebooks, R, figures |
| behavioral_responses.zip, README.md | small | probe answers + age/sex/handedness; readme |

## Relation to other datasets (overlap check, 2026-11-23)
**Not the same data as any dataset in the campaign.**
- `karunathilake2023` (PNAS, Dryad sbcc2frd6): different stimuli (human-narrated, noise-vocoded Botany of Desire
  passages vs gTTS synthesis here), design and triggers (164-166 there, 164-180 here). Two participant IDs occur in
  both, **R2383 and R2684**, but in separate sessions: here 2021-06-22 and 2021-06-04, there 2022-03-06 and
  2022-03-11 (`meas_date`). Same people, different recordings.
- `karunathilake2023_aging` (DRUM): participants R2509-R2672 (DSS components only); none of them here (R2548 is
  not in the aging list).
- `brodbeck2022` (Appleseed audiobook): recorded 2019-12 to 2020-03; here 2021-06 to 2021-12. Same source text
  (The Botany of Desire, M. Pollan) but here it is re-synthesised with gTTS, so the audio is not shared.

## 2. Layout
- `meg/R####/R####_fif-raw.fif` (2.0-2.15 GB; 18 participants also have a FIF split `R####_fif-raw-1.fif`, which
  MNE joins), `R####_emptyroom-raw.fif` (the first 9 participants, R2383-R2690, share a byte-identical empty-room
  file), `meg/meg_info.rtf` (one line). No trans files, no MRI.
- `Stimuli/wav files/{AS,ASM,ASN,PH}_M0{1-4}.wav`, `Stimuli/transcripts/*.txt`, `Stimuli/acoustic comparisons/`
  (MATLAB scripts and eps).
- `predictors/<stim>|<feature>.pickle` (section 4); `behavioral responses/behavioral data.xlsx` (one sheet).

## 3. Stimulus <-> trial mapping
- Passage types (README): **ASN** speech-envelope-modulated noise, **PH** nonwords, **ASM** scrambled words,
  **AS** narrative ("story"). Four 1-min passages per type, numbered M01-M04.
- Trigger codes (exp.py `ACOUSTICS`, `PHONEMES`, `LEXICAL`, `SEMANTIC`): 164-167 = ASN_M01-04, 168-171 = PH_M01-04,
  172-175 = ASM_M01-04, **176, 178, 179, 180 = AS_M01-04 (177 unused)**. One code per passage onset, no offset codes.
- Every participant (`survey.py`, `survey/*.json`, figure `figures/trigger_timeline.png`): exactly 32 triggers,
  each of the 16 codes twice **in a row** (each passage is played twice back to back), no other codes. The gap to
  the next trigger exceeds the played wav's duration by >= 8.6 s in every trial (questions between passages).
- **Presentation order is identical for all 30 participants**: PH1 ASM1 ASN1 AS1 | ASN2 AS2 ASM2 PH2 | ASM3 PH3
  AS3 ASN3 | AS4 ASN4 PH4 ASM4 (blocks of 8 trials). The type order rotates across blocks (Latin square), it is not
  counterbalanced across subjects as the paper says (upstream issue). The behavioural sheet's block headers have
  the same order (PH1, LE1, SE1 | SE2, LE2, PH2 | LE3, PH3, SE3 | SE4, PH4, LE4; noise passages had no scored
  question). Narrative passages AS1-4 are in story order.
- Participants: 30 = exp.py `good_sub` = the behavioural sheet = the paper's 30 analysed (34 recruited; 4 excluded
  by the authors and not shared). R2383, R2548, R2682-R2796 (see `survey/`). Recorded 2021-06-02 to 2021-12-06,
  43.4-55.7 min each.
- Recording boundaries: R2693 (1371.0 s, 2038.0 s), R2740 (1851.0 s), R2778 (1426.0 s) have `BAD boundary` /
  `EDGE boundary` annotations: the authors concatenated separate recordings (MNE joins them with no gap). **No trial
  spans a boundary** (nearest trial onset 13-44 s away; `boundaries.py`, `boundaries.json`). Kept as is.
- Same stimuli for every participant.

## 4. Speech features available
- Raw audio for every played stimulus: 16 wavs, 22,050 Hz mono int16, 60.0-62.5 s (ASN 61.3-62.5 s). gTTS (en-US
  male), 4 kHz low-pass, silences trimmed to 400 ms, resampled (paper says 22.5 kHz; the files are 22.05 kHz).
  Peak-normalised to full scale: 1-13 samples per file at +-32767 (negligible clipping), rms -15.5 to -18.9 dBFS.
- Transcripts (`*.txt`) for all 16, including the noise passages (text of the speech that modulated the noise).
- `predictors.zip`: authors' eelbrain objects at 1 kHz (the paper bins them to 100 Hz for the TRFs), 60 s long (60,000 samples; the wavs are
  longer): `gammatonelog-8`, `gammatonelog-on-8` (NDVar, 8 bands x time) and `pho`, `wor`, `psr1`, `pen`, `wfr`,
  `hug` (eelbrain `Dataset` of onset times + values). Read with a whitelist unpickler (`peek_words.py`; never
  unpickle untrusted data unrestricted). **The word and phoneme tables carry onset times only, no labels** (the
  label column is all `True`). Word-onset counts equal the transcript's token count in 9 of 16 passages and differ
  by 1-5 in the rest, so labelled word TextGrids cannot be built by zipping the two. Not carried (model-derived;
  open question 4).
- No TextGrids.

## 5. Neural data
- KIT 160-channel system ("University of Maryland/Kanazawa Institute of Technology/160-channel MEG System (54)
  V2R004 PQ1160R"), converted to FIF by the authors: `MEG 001-157` axial gradiometers (MNE type `mag`, coil
  `KIT_GRAD`, T), `MEG 158-160` reference magnetometers (`ref_meg`), `MISC 001-032` (V), `STI 014`. 1000 Hz, online
  200 Hz low-pass and 60 Hz notch (paper); `info` highpass 0, lowpass 200. Median gradiometer rms 1.4-2.6e-13 T.
  Head-shape digitisation in `info['dig']` (1799-3037 points). No projectors, no compensation, no bads marked.
- MISC lines (R2682 checked in detail, all participants by xcorr; `survey.py`): MISC 009 carries the trigger
  pulses; MISC 001-002 and 030-032 are noise floor; the rest are constant 5 V. **No audio copy**: max |normalised
  xcorr| of every MISC line with the first trial's wav (resampled to 1 kHz) and its envelope, lags -0.5..+2 s, is
  <= 0.024 in all 30 participants. No EOG/ECG. All MISC lines and STI 014 are dropped.
- Bad channels (rms < median / 20 in 10 x 10 s windows; `survey.json` `flat`): **MEG 056 flat in all 30; MEG 086
  flat in 29**. In R2682, MEG 086 is instead >10x the median rms (`noisy`), as is MEG 062 in R2693. Their PSDs and
  traces (`noisy_psd.py`, figure `figures/noisy_channels.png`, pilot trials 1-4): **R2682 MEG 086 is broken** (it
  jumps between the +-15,000 fT rails, rms 88x the median, flat broadband PSD 2-3 decades above the other
  channels); **MEG 062 is a working channel** with large physiological transients (eye/heart-like, 2-3x the median
  in R2693 and R2383; the PSD follows the other channels). Rule in the adaptor (CLAUDE.md: flat or noise-only
  channels go in `info['bads']`): median rms over 10 x 10 s windows < median / 20 (flat) or > 30 x median
  (saturated). Pilot result: MEG 056 + MEG 086 in R2383, R2682, R2693; MEG 062 not marked.
- Reference: not applicable (MEG). Empty-room recordings are shipped but not standardised (not continuous speech).

## 6. Alignment
- Triggers: TTL codes from the stimulus PC on MISC 009 / STI 014. Hardware vs software: **software (inferred)**,
  as in karunathilake2023 and brodbeck2022 (same lab, system and software). Latency from trigger to sound, and the
  E-A-RTONE 3A tube delay: **unknown** (not in the paper; no audio channel).
- Alignment (implemented): onset = trigger sample, no shift; trial length = played wav length at 1 kHz.
  Constant offsets found later (lag sweep, TRF latency) are documented, not applied.
- Drift: **not measurable** (no offset triggers, no audio channel; the gap to the next trigger includes question
  time). Not corrected. Trials are <= 62.5 s, so typical sound-card drift (10-50 ppm) is <= 3 ms per trial.

## 7. Cross-subject duration check
- Not possible (onset triggers only). `drift_ppm = null`, `jitter_ms = null`.

## 8. Adaptor (implemented, 2026-11-23)
- Shared code with the lab's other KIT datasets (R-number subjects, wav loaders, epoch/continuous-raw helpers,
  bad-channel rules) in `datasets/simon_base/common.py` (2026-11-23; output unchanged except subject numbers).
- Reads `**/R*/R*_fif-raw.fif` and `**/AS_M01.wav` (stimulus folder) under the root (extracted zips).
- Subject = full R-number (user, 2026-11-23); earlier outputs used R-number mod 1000 (R2383 -> 2383, was 383). Checked
  unique, as in karunathilake2023; R-number also in the sidecar (`participant`). `validation.json` subject fields
  relabelled to the full R-number (results unchanged). Session 1.
- Trials 1-32 in presentation order. Conditions (exp.py epoch names): `noise` (ASN), `nonwords` (PH), `scrambled`
  (ASM), `narrative` (AS).
- Neural data: gradiometers + reference magnetometers (160 channels), T, 1000 Hz native (no resample), cropped
  with `crop_on_audio_clock` at the trigger for the wav duration; MISC and STI 014 dropped; flat and saturated
  channels in `info['bads']` (section 5). The adaptor checks 32 triggers = each code twice in a row.
- Stimulus: the played wav (22,050 Hz, int16 / 32768 as float32, uncut), attended.
- Sidecar: `sw_trigger`, trigger_type as above, `drift_ppm`/`jitter_ms` null, plus `participant`, `passage_type`,
  `passage` (1-4), `repetition` (1-2), `block` (1-4), `trigger_code`, `onset_s`, `stimulus_file`,
  `units_as_shipped` ("T"), `reference` ("not applicable (MEG)"); the last two as in the lab's other KIT datasets
  (user decision, 2026-11-23).
- Output size: ~1.17 GB per participant (32 trials, float32), ~35 GB for all 30.

## Data size
Same 16 passages, each twice, for every participant: **30 participants, 32.3 min each (all identical), 16.2 h in
total**; per condition 8.0-8.2 min per participant, 4.0-4.1 h total (noise 4.11, nonwords 4.03, scrambled 4.00,
narrative 4.03 h). Unique audio 16.2 min (the spreadsheet's 0.53 h assumed 32 distinct passages).

## Upstream issues
- The paper says the order of passage types was counterbalanced across subjects; in the data all 30 participants
  have the same order (rotation across blocks only).
- The paper says stimuli were resampled to 22.5 kHz; the wavs are 22.05 kHz.
- The predictor word/phoneme tables have no labels, and their word counts differ from the transcripts in 7 of 16
  passages.
- The first 9 participants share one empty-room recording.

## Open questions (human checkpoint; recommended default in brackets)
1. Onset = trigger with no latency correction (software TTL, tube delay unknown). [yes; document the lag-sweep /
   TRF latency, do not shift]
2. Subject numbering R-number mod 1000 (as karunathilake2023). [yes; better: allow `\d{3,}` in `base_sink.py` and
   use the full R-number, for both datasets. Done 2026-11-23: full R-number]
3. Bad-channel rule flat (< median / 20) or saturated (> 30 x median): marks R2682 MEG 086 (rails), not MEG 062
   (physiological transients). [yes; implemented, evidence `figures/noisy_channels.png`]
4. Word/phoneme onsets from `predictors.zip` (no labels): not carried. [not carried; transcripts are in the
   download, and a forced alignment of the wavs would give proper TextGrids]
5. Keep the three participants with concatenated recordings (no trial spans a boundary). [yes]

## 9. Validation (pilot, 2026-11-23)
Pilot: 3 participants (R2383, R2682, R2693; chosen for the overlap with karunathilake2023, the FIF split + broken
MEG 086, and the concatenated recording), 96 trials, standardised from `extracted/` (`scripts/pilot.sh`; 3.5 GB).
No full run (storage). Repo validator through `validate_cond.py` (picks `mag` = good axial gradiometers, no
re-referencing, tiers low/mlr/brainstem); results and four-panel figures in
`tmp/review/karunathilake2025/validation/<set>/` (`all` copied to `validation.json` here). With 3 participants the
smallest attainable p is 0.020 (circular shift) / 0.048 (mismatch).

| set | low median r | subjects sig | TRF peak | mlr SNR (p, subj) | brainstem SNR (p, subj) | tier |
|---|---|---|---|---|---|---|
| all (pooled) | 0.054 | 3/3 | 47 ms | 1.16 (0.010, 1/3) | 1.28 (0.010, 3/3) | brainstem |
| noise | 0.029 | 3/3 | 172 ms | 0.91 (0.69, 0/3) | 0.99 (0.64, 0/3) | low |
| nonwords | 0.064 | 3/3 | 63 ms | 1.06 (0.069, 1/3) | 1.18 (0.010, 1/3) | low |
| scrambled | 0.070 | 3/3 | 47 ms | 0.99 (0.28, 0/3) | 1.12 (0.010, 1/3) | low |
| narrative | 0.049 | 3/3 | 31 ms | 1.08 (0.020, 1/3) | 1.14 (0.010, 1/3) | brainstem |

- Pooled 30-250 Hz TRF: sharp peak at ~38 ms (within the MEG 28-45 ms window), second at ~52 ms, nothing above
  the null at negative lags; 30-60 Hz peaks at ~38, 50 and 62 ms (as karunathilake2023 and brodbeck2022, same
  lab/system). No sign of a trigger-to-sound latency problem.
- Speech-modulated noise has no harmonic structure, so its HF tiers fail by construction (as the vocoded trials in
  karunathilake2023). Its 0.5-8 Hz TRF is broad (envelope low-passed at 5 Hz) with a bump at -20 ms barely above
  the null (8 trials x 3 participants); not read as a timing error, to recheck on more participants.
- Validator per-trial offsets/drift are not informative for 1-min MEG trials (jitter MAD 21-42 ms, drift SE
  700-2200 ppm).
- **Trial -> stimulus check** (`map_check.py`, figure `figures/map_check.png`, `map_check.json`): backward model per
  participant (good gradiometers, 1-8 Hz, 100 Hz, 40 PCA components, lags 0-500 ms, ridge), trained without both
  presentations of the test passage; the test trial's reconstruction correlates best with its labelled passage among
  all 16 in **96/96 trials** (rank 1 each). The mean matched-r lag scan (+-1 s) peaks at 0 ms in all three; this is
  relative (training trials share the trigger alignment) and only shows that no trial is off on its own.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**medium**: Software trigger, no audio copy, no shift; drift not measurable; brainstem (pilot 3), nothing at negative lags (noise condition bump at -20 ms to recheck).
