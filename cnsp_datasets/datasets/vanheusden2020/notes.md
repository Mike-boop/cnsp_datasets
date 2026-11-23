# vanheusden2020: hearing-impaired listeners, audiobook aided vs unaided (Southampton ePrints D1140)

Explorer notes, 2026-11-22. Scratch scripts and outputs: `tmp/review/vanheusden2020/` (data storage;
`scripts/*.py`, `*.json`, `*.log`). Everything below that explains a choice is recorded here because tmp is deleted.

## 1. Source
- Dataset: Vanheusden FJ et al. (2019). *Dataset for: Hearing aids do not alter cortical entrainment to speech at
  audible levels in mild-to-moderately hearing-impaired subjects.* University of Southampton, doi:10.5258/SOTON/D1140
  (ePrints 438737). Licence: CC BY 4.0 (ePrints record; the readme says "CC-BY").
- Paper: Vanheusden FJ, Kegler M, Ireland K, Georga C, Simpson DM, Reichenbach T, Bell SL (2020). Hearing aids do
  not alter cortical entrainment to speech at audible levels in mild-to-moderately hearing-impaired subjects.
  *Front. Hum. Neurosci.* 14:109. doi:10.3389/fnhum.2020.00109.
- No analysis code shared. Paper pipeline (Methods): 1-4, 4-8, 1-20 Hz FIR (MNE), 64 Hz, envelope = |analytic
  signal| of the stimulus filtered/downsampled like the EEG, backward model -100..400 ms, ridge, 5-fold CV.
- Recorded at the Audiology Department, Royal Berkshire Hospital, Reading (readme), 2018-02-09 .. 2018-08-10.

## 2. Layout
Download (`/data_storage/gu08wuvu/datasets/vanheusden2020/download/`, read-only):
- `Readme_Vanheusden_D1140.txt`, `Questionnaire.docx` (4 multiple-choice questions x 4 options per segment, see 3),
  `Behavioural_Results.xlsx` (one sheet: 20 subjects, age, gender, `Subject #` = S_xxx, history questionnaire,
  hearing-aid RESP50 / OSPL90 curves, attack/release times, audiometry). **No per-segment answer scores and no
  BKB scores** in the shipped xlsx (the paper's Figure 2 data are not shipped).
- `Dataset_odin.zip`: 8 wavs `odin_1_1..1_4`, `odin_4_1..4_4` (section 4).
- `Dataset_S_001_006.zip`, `..._007_011`, `..._012_017`, `..._018_027`: 40 BDFs, one per subject x condition,
  `S_<id>_<Aided|Unaided>_Speech-Deci.bdf` (case varies: `speech`, `unaided`, `UnAided`; S_002 is
  `..._Speech_Rep.bdf` / `..._Speech_rep.bdf`). No `__MACOSX` entries.
- `S_001_Unaided_Speech_Deci.bdf` (loose, underscore instead of hyphen): a duplicate, see section 3.

Subjects: **20 with data** (S_001, 002, 004-014, 016-020, 024, 027), both conditions each, 40 files. The paper has
17 (Table 1, IDs 01-17; subject 13 then removed from the EEG analysis for a "technical issue"; two subjects did not
complete the BKB test). Which 3 of the 20 recorded subjects are not in the paper, and how the paper's IDs 01-17 map
to S_xxx, is not documented (inferred mapping in section 3). The xlsx lists all 20 (its row numbers 1-20 are not the paper's IDs: e.g. row 5 is
S_001, F, 65; paper ID 01 is F, 65).

## 3. Stimulus <-> trial mapping
- Each BDF is one condition block: the 8 audiobook segments in a row, one Status pulse at each segment onset
  (section 6), breaks with 2 multiple-choice questions in between (readme; the questionnaire has 4 questions per
  segment, "one out of four will be asked per fragment per experiment"). Same 8 wavs for every subject and both
  conditions. Answers per segment are not shipped.
- **Order: fixed, `odin_1_1, 1_2, 1_3, 1_4, 4_1, 4_2, 4_3, 4_4`, in both conditions** (not documented; established
  from the data):
  - Trigger gaps: in every 8-trigger file the gap to the next trigger exceeds the fixed-order wav by 0.8-242 s
    (median 48 s). The gap constraint (gap >= wav) alone leaves 576-8640 of the 40320 orders per file; in most files
    exactly the 576 = 4! x 4! orders with the chapter-1 segments in slots 1-4 and chapter 4 in slots 5-8.
  - EEG check (`scripts/ident2.py`, `perm_test.py`; `ident2.json`): leave-one-subject-out forward TRF (envelope ->
    32 ch, average reference, 1-8 Hz, 128 Hz, lags 0-400 ms, trained on the fixed order of the other subjects),
    every trigger scored against all 8 wavs. The fixed order is the best feasible order in **31 of 35** 8-trigger
    files; the 4 exceptions (S_004 aided rank 220/576, S_008 aided 12/1152, S_011 aided 5/2304, S_017 unaided
    24/2304) are 4 of the 6 files with the weakest tracking (r 0.016-0.023; median file 0.040, range 0.016-0.086),
    and their best orders differ from each other: noise, not another order. Use the fixed order for them.
- Files with fewer triggers (all others have exactly 8):
  - **S_002** (`*_Speech_Rep.bdf`/`_rep.bdf`, 944 / 905 s): 4 triggers per condition, **chapter 1 only**. Aided order
    `1_1, 1_2, 1_3, 1_4`; **unaided order `1_3, 1_4, 1_1, 1_2`** (score matrix diagonal 0.115 / 0.073 / 0.085 / 0.073
    vs <= 0.036 off-diagonal; a whole-recording scan finds each wav's peak at its trigger, z 4.3-6.7). "Rep" is not
    explained (repeat session?). S_002 is not in the paper (see 2).
  - **S_020 aided** (7 triggers) and **S_004 unaided** (7): fixed order `1_1 .. 4_3`; **odin_4_4 missing**. The
    recordings end 354 / 387 s after the `4_3` trigger; a scan of the first 60 s of `4_4` over the remaining 135 /
    168 s finds nothing above the other wavs (control) (`scripts/partial_scan.py`). S_020 aided is clear (r 0.081 at
    4_3); S_004 unaided has too little tracking to confirm anything; its gaps (break 26-39 s after each fixed-order
    wav) fit the fixed order like its aided file.
  - **S_019 unaided** (6 triggers): fixed order `1_1 .. 4_2` most likely (diagonal best in rows 1, 3, 4, 6:
    r 0.025, 0.031, 0.048, 0.043; rows 2 and 5 ambiguous); `4_3`, `4_4` missing (file ends 235 s after the `4_2`
    trigger, `4_2` is 229.4 s). Breaks are long here (81-156 s per gap).
- S_027 aided: after the 8th segment (ends at 1944.9 s) there are **120 extra pulses at exactly 1-s spacing**
  (1969.46-2088.46 s), not mentioned anywhere (another stimulus? a test?). Ignore them for the audiobook; see 6.
- Recording order (BDF `meas_date`): unaided first for S_001, 007, 013, 014, 016, 018, 024; aided first for the
  other 13 (paper: "conditions were randomized"). S_017, S_020 and S_024 recorded the two conditions on **different
  days** (aided 06-29 / 07-13 / 08-10, unaided 07-03 / 08-10 / 07-17), against the readme's "on the same day".
- Trials: 35 x 8 + 2 x 4 + 7 + 7 + 6 = **308** segment trials, 20 subjects, 40 recordings. All 40 files open with
  MNE; no truncation inside a triggered segment (smallest tail after the last segment: S_007 aided 0.8 s).
- Loose `S_001_Unaided_Speech_Deci.bdf`: MD5 68616991958557ccffe660443a63136a, **identical** to
  `S_001_Unaided_Speech-Deci.bdf` in `Dataset_S_001_006.zip` (same size as S_020 unaided, but different content).
  Ignore it.
- Paper IDs (Table 1, 17 subjects): matching age and gender in S-number order gives an exact match for
  01-17 = S_001, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 016, 017, 018, 024, 027 (all 17 age/gender
  pairs agree, 11 M / 6 F as in the readme; inferred, not documented). Not in the paper: **S_002** (4-segment
  "Rep" files), **S_019** (F53), **S_020** (F55). Paper subject 13 (removed for a "technical issue" seen in the power spectrum) would then be
  **S_016**; its tracking here is normal (z 12.2 aided / 8.6 unaided), so the issue is unknown.

## 4. Speech features available
- Audio: 8 wavs, 44.1 kHz mono int16 (scipy warns about a non-data chunk: the `odin_4_*` files have ~2.8 kB
  trailing after the `data` chunk; harmless). Exact durations (samples / 44100):

  | wav | samples | s |
  |---|---|---|
  | odin_1_1 | 6804072 | 154.2873 |
  | odin_1_2 | 7057943 | 160.0441 |
  | odin_1_3 | 6237143 | 141.4318 |
  | odin_1_4 | 6790359 | 153.9764 |
  | odin_4_1 | 9858742 | 223.5542 |
  | odin_4_2 | 10118343 | 229.4409 |
  | odin_4_3 | 9648243 | 218.7810 |
  | odin_4_4 | 10583564 | 239.9901 |

  Sum 1521.506 s = 25.36 min (the paper's "about 25 min", "eight segments of about 3 min").
- Content: LibriVox *The Children of Odin* (Padraic Colum), female reader; paper footnote: chapters 2 and 5. The
  file names `odin_1_*` / `odin_4_*` are the questionnaire's "Odin 1_x" / "Odin 4_x"; the questions confirm the
  stories (1_x: the giant builder of Asgard's wall and the horse; 4_x: Brock, Loki and the dwarfs' gifts). The
  numbering "1"/"4" vs "chapters 2 and 5" is the LibriVox track index vs chapter number (inferred, not documented).
- **Bandwidth: the wavs are brick-wall low-passed at ~4.05 kHz** (Welch PSD flat to 4.02 kHz, -60 dB by 4.1 kHz,
  then a flat quantisation floor), not at the paper's 3 kHz ("low-pass filtered at 3,000 Hz using 120th order FIR
  before presentation"). Either the shipped wavs are before that filter, or the description is inaccurate; unknown.
  For cortical envelope work this does not matter; it means the wavs may not be sample-exact what was played.
- Levels: `odin_1_*` RMS 0.070-0.099 FS with 1-2 full-scale samples each; `odin_4_*` RMS 0.027-0.029, peak 0.41-0.46
  (~10 dB lower). All were presented at 70 dBA LeqA (paper), so the playback gain differed per chapter
  (calibration not shipped). Speech starts at wav sample ~0 in all files (|x| > 1e-3 within 0-26 ms).
- What the stimulus represents: the loudspeaker signal (1.2 m in front, free field). In the **aided** condition the
  listener heard it through their own hearing aids (GN ReSound, paper Table 2): the ear signal is hearing-aid
  processed (gain, compression, extra delay of a few ms), and none of that is shipped or measurable from the data.
- No transcript, no word/phoneme timings. Questionnaire (comprehension questions) only.
- BKB sentences (paper: randomised BKB lists at 65 dBA, aided and unaided): **not in the dataset** (no audio, no
  EEG; the BDFs hold the audiobook blocks only, plus an unexplained pulse train in S_027 aided, see 3). Nothing
  to skip.

## 5. Neural data
- BioSemi ActiveTwo, `.bdf`, 2048 Hz, 48 channels, 1-s data records. Header: EEG/EXG "Active Electrode", unit `uV`,
  physical range -262144..262143 (MNE scales to V correctly), prefilter "HP: DC; LP: 417 Hz" (BioSemi decimation
  filter). Patient and recording fields blank (anonymised); `meas_date` present (matches the readme's collection
  dates except S_017, S_020, S_024 unaided, see 3). File names say `Deci` (BioSemi Decimator output? original rate
  unknown).
- Channels: `A1..A32` (32 scalp), `EXG1..EXG8`, `GSR1 GSR2 Erg1 Erg2 Resp Plet Temp`, `Status`.
  - `A1..A32`: BioSemi 32-channel cap, 10-20 positions (paper). The ABC labels are the BioSemi default; the standard
    BioSemi-32 mapping (A1 Fp1, A2 AF3, A3 F7, A4 F3, A5 FC1, A6 FC5, A7 T7, A8 C3, A9 CP1, A10 CP5, A11 P7, A12 P3,
    A13 Pz, A14 PO3, A15 O1, A16 Oz, A17 O2, A18 PO4, A19 P4, A20 P8, A21 CP6, A22 CP2, A23 C4, A24 T8, A25 FC6,
    A26 FC2, A27 F4, A28 F8, A29 AF4, A30 Fp2, A31 Fz, A32 Cz) is **inferred**: on S_001 aided (1-20 Hz, average
    reference) A1's best neighbour is A30 (r 0.96), A15-A16-A17 chain, A13 ~ A22/A9, A7 and A24 correlate with the
    EXGs (temporal). Consistent, not proof.
  - `EXG1`, `EXG2`: mastoids (paper: "two additional electrodes positioned at either mastoid"). On S_001 aided EXG1
    pairs with A24 (T8, r 0.70) and EXG2 with A7 (T7, r 0.68); the same holds (EXG1 closer to A24, EXG2 closer to
    A7) in 35 of 40 files (`scripts/exg_side.py`, 128 Hz cache; the others are dominated by large common artifacts:
    S_007 unaided, S_014 unaided, S_016 aided r >= 0.95 everywhere; S_014 aided, S_027 aided EXG2 near 0):
    **EXG1 = right, EXG2 = left mastoid (inferred)**, the reverse of the usual BioSemi convention.
  - `EXG3`: active, 7.7 µV MAD (1-20 Hz), weakly correlated with everything (r <= 0.28). Not mentioned in the paper;
    unknown (EOG? nose?). `EXG4..EXG8`: unconnected (constant ~-0.259 V, saturated).
  - `GSR1/2, Erg1/2, Resp, Plet, Temp`: constant (S_001 aided). **No stimtrack/audio channel.**
- Reference: BioSemi CMS/DRL (reference-free recording); paper re-referenced to the average of all electrodes.
- Amplitudes plausible: 1-20 Hz median |x| per file 1.6-5.3 µV (median over scalp channels, average reference),
  no flat scalp channel and no channel > 5x the file median in any of the 40 files. Large transient artifacts
  in S_007 unaided, S_014 unaided, S_016 aided (dominate the channel correlations).
- No digitisation.

## 6. Alignment
- Status channel (MNE masks to 17 bits): idle value 65533 (0xFFFD) in every file; a trigger sets **bit 1 (value 2)**
  for 21-24 samples (10.3-11.7 ms). No other codes. One pulse per segment, **at the onset only** (no offset
  marker): the first pulse comes 22.6-345.7 s into the recording and each segment fits between its pulse and the
  next; an offset reading is impossible (the first gap would have to hold a 154-s wav before the first pulse).
  The code does not identify the segment; the order is fixed (section 3).
- Hardware vs software triggering: **unknown** (paper and readme say nothing about triggers). The pulse width
  varies by 3 samples, so the pulse length is not sample-locked; the 1-s pulse train in S_027 aided (section 3) is very
  regular (residual 0.14 ms SD around a line), so pulses can be timed precisely by the presentation system.
- No stimtrack: Erg1/Erg2/Resp/Plet/Temp/GSR1/GSR2 are constant (checked on S_001 aided, `scripts/aux_check.py`;
  the other files have the same 48-channel header but their aux content was not read); nothing records the audio.
- **Onset plausibility** (`ident2.py`): the pooled prediction correlation of each file peaks at a stimulus shift of
  -20 .. +24 ms (aided mean 0.0 ms, SD 12.0, n 16; unaided -1.4 ms, SD 8.1, n 14; files with z >= 7). This is the
  resolution of a 1-8 Hz cortical check (the peak also absorbs per-subject latency vs the LOSO TRF), so the triggers
  are at the sound onset to within ~10-20 ms; a constant offset of a few ms (sound card latency, 1.2 m loudspeaker
  distance = 3.5 ms) cannot be seen. Paired aided-unaided peak difference: -0.4 ms (SEM 1.6, n 13): no hearing-aid
  delay visible at this resolution (expected a few ms).
- Drift: **not measurable from the triggers** (onset pulses only, breaks of variable length between them). The EEG
  half-split estimate (shift in the 2nd vs 1st half of each segment) is 35 +- 25 ppm (n 231 trials): uninformative.
  The S_027 aided 1-s pulse train has a period of 2047.951 EEG samples (-24.1 ppm vs 2048) over 119 s: if that
  train was timed by the same clock that plays the audio, the audio runs 24 ppm fast in EEG time (-5.8 ms over a
  240-s segment). Whether the same clock drives the audio is unknown.
- Proposed alignment: stimulus onset = rising edge of Status bit 1 (first transition 65533 -> 65535), per segment,
  in the fixed order (exceptions in section 3). No drift correction (cannot be measured; <= ~6 ms per segment if the
  -24 ppm figure applies, negligible for cortical analyses). Hearing-aid processing delay in the aided condition is
  not shipped and not corrected; document it.

## 7. Cross-subject duration check
- Only onset triggers: trigger-derived durations do not exist. Gap to the next trigger minus the fixed-order wav
  duration (= break incl. questions) over the 35 8-trigger files: min 0.8 s (last segment to file end, S_007
  aided), median 47.9 s, max 241.6 s (S_014 aided after `1_4`); never negative, so no segment is cut by a later
  trigger or by the end of the file. Per-file table: `tmp/review/vanheusden2020/` (trigger summary in
  `triggers_all.json`, script `trig_summary.py`).
- Drift/jitter fit (duration error = drift x length + noise) not possible (see 6).

## 7b. Data size
- From the stimuli (each segment counts its wav length): full block 1521.506 s (25.36 min); S_002 609.74 s per
  condition; one wav fewer for S_004 unaided and S_020 aided (1281.5 s), two fewer for S_019 unaided (1062.7 s).
- **20 participants, 0.807 h per participant (0.339-0.845), 16.14 h total** (aided 8.13 h, unaided 8.01 h),
  308 trials. Paper's 17 (all full blocks): 17 x 0.845 = 14.37 h. Total recording length of the 40 BDFs: 21.4 h.
- Confirmed on the standardised output (`tmp/review/scripts/data_size.py`, 2026-11-22; rows written to
  `tmp/review/data_size.csv`): 20 participants, 308 trials, 16.14 h; 0.807 h per participant (0.339-0.845).
  `aided` 155 trials, 8.13 h, 0.407 h per participant (0.169-0.423); `unaided` 153 trials, 8.01 h, 0.400 h
  (0.169-0.423).

## 7c. Validation tiers
- Native 2048 Hz, DC-coupled, 417 Hz hardware low-pass: low (cortical) tier clearly possible (tracking in all 40
  files, LOSO r 0.016-0.086). MLR tier possibly (2048 Hz, onset triggers precise to unknown ms; no stimtrack).
  Brainstem tier unlikely: free-field loudspeaker, wavs band-limited at ~4 kHz (3 kHz per the paper), trigger-to-sound
  latency and jitter unknown, and in the aided condition an unknown hearing-aid delay; worth one try on unaided only.
- Reference for validation: average (standard); paper also used the average.

## 8. Open questions (recommended defaults in brackets)
1. Subjects: keep all 20 recorded (S_002, S_019, S_020 are not in the paper) or only the paper's 17? Drop the paper's
   subject 13 (= S_016 by the inferred ID mapping)? [Keep all 20 incl. S_016; note the paper's exclusions in the
   README; tracking is normal in all of them.]
2. S_002 "Rep" files: 4 segments (chapter 1) per condition, unaided order `1_3, 1_4, 1_1, 1_2` (from the EEG).
   Use them? [Yes, with the EEG-derived order; mark as not in the paper.]
3. Order: fixed order assumed for all files incl. the 4 weak files where the EEG prefers another order (S_004 aided,
   S_008 aided, S_011 aided, S_017 unaided), S_004 unaided (no usable tracking) and S_019 unaided (2 of 6 triggers
   ambiguous). [Fixed order everywhere except S_002 unaided.]
4. Missing last segment(s): S_004 unaided and S_020 aided without `4_4`, S_019 unaided without `4_3`, `4_4`. [Skip
   them; no trigger, no evidence they were played/recorded.]
5. Stimulus as played: the wavs are band-limited at ~4.05 kHz, not at 3 kHz as the paper says; levels differ by
   ~10 dB between chapters but all were presented at 70 dBA. Use the wavs as shipped? [Yes; note it. Do not refilter
   to 3 kHz without the authors' filter.]
6. Aided condition: the ear signal went through the participant's own hearing aid (gain/compression/delay unknown).
   [Same stimulus for both conditions; condition labels `aided` / `unaided`.]
7. Drift: unmeasurable; -24 ppm from the S_027 1-s pulse train is the only hint. [No correction.]
8. EXG1/EXG2 = right/left mastoid (inferred from correlation with T8/T7 in nearly all files; reversed vs BioSemi
   convention); EXG3 unknown. [Ship EXG1-3 as `misc`/`eeg` with names `EXG1..3`, note the inferred sides; drop
   EXG4-8 and the constant aux channels.] Channel positions: BioSemi-32 default ABC layout (inferred).
9. S_027 aided: 120 pulses at 1-s spacing after the audiobook. Unknown purpose. [Ignore.]
10. BKB sentences: not in the dataset. [Nothing to do.]

## Upstream issues
- Readme: "17 subjects" but 20 subjects' data shipped; "same day" not true for S_017, S_020, S_024; segment order and
  trigger scheme undocumented; S_002 files hold 4 segments only (unaided in a different order); 3 files lack the
  last 1-2 segments; loose S_001 unaided BDF duplicates the zipped file.
- Paper says 3 kHz low-pass; the shipped wavs are band-limited at ~4.05 kHz.

## Decisions (user, 2026-11-22)
Implemented in `adaptor.py`.
1. Subjects: all 20 kept. The README notes the paper's 17 (S_002, S_019, S_020 not in it) and its exclusion of
   paper subject 13 (= S_016, inferred); provenance has `paper_id_inferred` and `excluded_in_paper`.
2. Order: fixed `1_1..1_4, 4_1..4_4` everywhere, including the weak files; S_002 unaided `1_3, 1_4, 1_1, 1_2`
   (`order_source='eeg'`), S_002 aided `1_1..1_4`. Missing segments left out (S_004 unaided and S_020 aided
   `4_4`; S_019 unaided `4_3`, `4_4`; listed in `missing_segments`). `order_ambiguous=True` for S_004 (both files),
   S_008 aided, S_011 aided, S_017 unaided and S_019 unaided slots 2 and 5.
3. Channels: the 32 scalp channels, renamed to the biosemi32 template (A1-A32 mapping inferred, section 5), plus
   the mastoids EXG1 (right) / EXG2 (left; sides inferred) as `misc` under their own names. EXG3 (role unknown;
   user's choice), EXG4-8 and the aux channels are dropped. Reference: CMS/DRL as recorded, not re-referenced
   (repo convention; the paper used the average). Units V (MNE scales the BDF's µV).
4. Stimulus: the wavs as shipped (44.1 kHz), the same wav for both conditions; condition `aided` / `unaided`.
   The ~4.05 kHz band limit and the missing hearing-aid processing go in the per-trial notes.
5. Alignment: onset = rising edge of Status bit 1; `onset_only`, trigger type unknown (not documented); no drift
   correction. S_027 aided: only the first 8 pulses are used (1-s train ignored).
6. Rate: 2048 Hz decimated to 1024 Hz (repo default 1000/1024 Hz; integer factor, `clock.crop_on_audio_clock`).
   Each trial is cut to the wav length (ceil(n_wav * 1024 / 44100) samples); if the recording ended earlier the
   trial is kept shorter and flagged (`eeg_shorter_than_stimulus`; not expected, section 3). Trials are numbered
   over both files in recording order (`meas_date`). Session = recording day (user, 2026-11-22): S_017, S_020 and
   S_024 recorded the conditions on different days, so their second recording is session 2; all other subjects
   have session 1 only. `meas_date` is in the provenance.

## 9. Validation (2026-11-22)
Repo validator (forward model), 32 scalp channels, average reference, run pooled and per condition (records
filtered before `validate()`); scripts and raw outputs in `tmp/review/vanheusden2020/validation/`, summary in
`validation.json`. **Tier `mlr`, pooled and in both conditions; brainstem fails.**
- low (0.5-8 Hz, 64 Hz): mean r 0.058 (median 0.054, subjects 0.033-0.092); 20/20 subjects pooled, `aided` 18/20
  (r 0.057), `unaided` 19/20 (r 0.057). Misses: S_004 aided (r 0.025, p_circ 0.059) and S_014 in each condition
  (aided p_mismatch 0.095; unaided r 0.023, p_circ 0.098); S_014 passes pooled. S_004 unaided (order ambiguous,
  "no usable tracking" in section 3) scores r 0.069 at the p floors.
- mlr (30-60 Hz, 18-45 ms): SNR 1.46 pooled (12/20 subjects), 1.25 aided (6/20), 1.33 unaided (9/20); p 0.0099
  (permutation floor) in all three. GFP peak 43 / 40 / 42 ms (pooled / aided / unaided), near the window edge.
- brainstem (30-250 Hz, 4-9 ms): SNR 0.99 pooled (p 0.45), 0.94 aided (p 0.86), 0.97 unaided (p 0.77); 1/20
  unaided subjects at p < 0.05 (chance). As expected from 7c.
- Forward TRF GFP: one dominant peak at 172 ms (pooled GFP/null 8.8), local maxima near 0 ms (4.6) and 78 ms
  (3.9); the "N1" at 141 ms is the window edge on the flank of the 172 ms peak. Same in both conditions.
- 0 ms bump (`zero_lag_bump.py`): GFP(0)/GFP(172) median 0.51 (0.20-1.10), > 0.3 in 18/20 subjects; a synthetic
  EEG from the 100-300 ms TRF only, refitted with the same ridge, gives 0.03 (max 0.06), so it is not envelope
  autocorrelation (0.83 at 31 ms, -0.10 at 172 ms) or ridge smearing. Topography = the 172 ms map (subject median
  r 0.89, grand map r 0.98), no frontal-polar/ocular dominance (3% of power on Fp1/Fp2/AF3/AF4). The hand-aligned
  reference datasets show the same ratio (weissbart2019 0.69, fuglsang2018 0.62, bentum2023 read-aloud 0.49), and
  no subset of trials is shifted by ~170 ms (275/308 offsets within +-50 ms). Not a timing problem.
- Per-trial offsets: subject medians +0.76 ms pooled (bootstrap 95% -1.40..+1.70), all within +-12.5 ms. MAD
  12.7 ms pooled (aided 13.1, unaided 15.0). Drift not estimable (validator drift 54 +- 278 ppm: uninformative).
- S_014 aided trial 9 (first trial of S_014's second recording) has offset -19.47 s: `models.peak_shift` artefact
  (argmax at the -0.5 s edge, the clipped parabola is not around a maximum and the near-zero curvature makes the
  vertex step unbounded). A +-30 s LOO sweep (`s014_sweep.py`) finds no peak at any lag (z at 0 = 0.56, far max
  2.66, as in the other trials' far lags): no tracking, not misalignment. It drives the aided jitter SD to 1562 ms;
  use the MAD. Fixed in the repo afterwards (2026-11-22): `peak_shift` returns NaN for an edge argmax, and the
  summary leaves such trials out and counts them (`n_offsets_at_edge`). Aided re-run (low tier) with the fix:
  jitter SD 72 ms (was 1562), MAD 12.4 ms, 3 offsets at the edge, mean r unchanged. Figures:
  `validation/extra_s014_sweep.png` (S_014 vs S_009 sweeps) and `validation/extra_zero_lag_bump.png`.
- Order provenance: `order_ambiguous` trials median r 0.034 (n 41) vs 0.058 (n 267), Mann-Whitney p 3e-7; expected,
  these files were flagged for weak tracking. 38/41 have r > 0. S_002 unaided (EEG-derived order) r 0.102, the
  highest subject-condition (trials 0.067-0.125); partly circular.
- Aided vs unaided (paired, 20 subjects): r -0.0007 (p 0.70), N1/P2 GFP latency 0 ms median, per-trial offset
  -1.4 ms (SEM 1.4, p 0.65), MLR SNR -0.08 (p 0.78). No measurable hearing-aid delay at the 64 Hz resolution; the
  pooled-model estimate without S_004 (-4.5 ms, SEM 2.6, p 0.08) has the opposite sign of an aid delay.
- Sanity: 308 trials, no errors, no flat or NaN channels, EEG 0-12 ms shorter than the stimulus after 64 Hz
  rounding.

## 10. Coherence (2026-11-22)
EEG-envelope coherence, complex mean over subjects, average reference, 5 s Hann windows with 4 s overlap, ratio to
1 surrogate; `tmp/review/vanheusden2020/coherence/{128,native}/`.

| band | aided 128 Hz | unaided 128 Hz | aided 1024 Hz | unaided 1024 Hz |
|---|---|---|---|---|
| 0.2-1 Hz | 6.3 | 6.1 | 6.3 | 6.1 |
| 1-4 Hz | 6.9 | 6.5 | 6.9 | 6.4 |
| 4-8 Hz | 6.3 | 5.4 | 6.4 | 5.4 |
| 8-15 Hz | 1.87 | 1.77 | 1.86 | 1.77 |
| 15-30 Hz | 1.19 | 1.14 | 1.19 | 1.14 |
| 30-60 Hz | 1.06 | 1.18 | 1.12 | 1.19 |
| 60-120 Hz | | | 0.99 | 1.01 |
| 120-250 Hz | | | 1.03 | 1.03 |
| 250-500 Hz | | | 1.02 | 1.02 |

Native rate agrees with 128 Hz; nothing above 60 Hz.

## 11. DNN offset vs accou2023 (2026-11-22)
Match-mismatch classifier trained on accou2023 (`fs128_1020-64` broadband, 128 Hz), lag scan +-500 ms, 5 s windows,
1 s hop, 100 trials per condition, CI by bootstrapping subjects (`tmp/review/scripts/dnn_offsets_batch2.py`;
results `tmp/review/vanheusden2020/dnn_offsets/offsets.json`):
- `aided` **+4.4 ms** (95% CI +0.7..+7.2), `unaided` **+5.1 ms** (+1.5..+8.3); subject offsets -23..+20 ms.
- Sign (checked in the script docstring and `cnsp_datasets.align.scan.lag_scores`): EEG window [t, t+L) is paired
  with stimulus [t+lag, t+lag+L); a positive best lag means the stimulus must be moved earlier, i.e. the neural
  data are EARLY relative to accou2023 (negative = late). So the EEG here is ~5 ms early: the trigger probably fires
  a few ms after the actual sound onset (unverified). The 1.2 m loudspeaker path (3.5 ms) would make the EEG late,
  so it does not explain this.
- Documented, not applied (project rule for constant DNN offsets). No aided-unaided difference beyond the CIs.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**medium**: Status-bit trigger (type unknown), no stimtrack; shift peaks within ~10-20 ms; DNN +4.4/+5.1 ms documented (within band); drift not measurable; segment order partly EEG-inferred; mlr tier.
