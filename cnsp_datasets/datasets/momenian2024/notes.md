# momenian2024: Le Petit Prince Hong Kong, older Cantonese listeners, EEG part (OpenNeuro ds004718)

Explorer notes, 2026-11-22. Scratch scripts, tables and figures: `/data_storage/gu08wuvu/datasets/tmp/review/momenian2024/`
(`scripts/*.py`, `*.png`, `sentence_table.csv`, `v112/`). That folder is temporary; every number that explains a
choice is copied here.

**Headline.** The story was played **sentence by sentence** (535 separate wav files, one trigger per sentence), not
as the continuous run wavs shipped in v1.1.1. Inter-sentence gaps (median 8.5 ms, plus software jitter) add up to
0.8-1.9 s per ~5-min Part, so a continuous wav started at the first trigger is ~1 s late by the end of each Part
(EEG-verified, section 7). Align per sentence: splice the EEG at the sentence triggers (section 6).

## 1. Source
- OpenNeuro ds004718, "Le Petit Prince Hong Kong: Naturalistic fMRI and EEG dataset from older Cantonese
  speakers". Downloaded: v1.1.1 (doi:10.18112/openneuro.ds004718.v1.1.1), registry entry `momenian2024`
  (func/anat/derivatives excluded). Licence **CC0** (dataset_description.json).
- **A newer snapshot v1.1.2 (2025-10-14) exists** ("update annotation and stimuli files"). Its README update note
  says: "Since the auditory stimuli were presented sentence by sentence, we decided to include the original audio
  files instead of a continuous file." It adds `sourcedata/stimuli/audio_files_segmented_by_sentence/Part {1..4}/
  <section>.<sentence>.wav` (535 files, 206 MB), `sourcedata/annotation/EEG_trigger_and_sentence_number.xlsx`,
  `sourcedata/annotation/lppHK_timing_word_information.xlsx`, E-Prime fMRI timing logs, and **drops the continuous
  run wavs**. All 153 EEG files (`.set/.fdt/.json`) have identical sizes in v1.1.1 and v1.1.2. The sentence wavs
  and the two xlsx were fetched to `tmp/review/momenian2024/v112/` for this exploration (OpenNeuro, not Zenodo).
- Paper: Momenian M, Ma Z, Wu S, Wang C, Brennan J, Hale J, Meyer L, Li J (2024). Le Petit Prince Hong Kong
  (LPPHK): Naturalistic fMRI and EEG data from older Cantonese speakers. *Scientific Data* 11:992,
  doi:10.1038/s41597-024-03745-8 (preprint doi:10.1101/2024.04.24.590842).
- Code: https://github.com/jixing-li/lpp_data (fMRI quality scripts, f0/RMS extraction for `wav_acoustic.csv`);
  **no EEG code**.

## 2. Layout (v1.1.1 as downloaded)
- `sub-HK<ID>/eeg/sub-HK<ID>_task-lppHK_eeg.{set,fdt,json}`: one continuous EEGLAB file per participant, **51
  participants** (HK001-HK052 without HK031). HK031 is in `participants.tsv` and the behavioural CSV but has no EEG
  in v1.1.1 or v1.1.2 (only anat/func). No `events.tsv`, `channels.tsv` or `electrodes.tsv`; events only in
  `EEG.event`.
- `.set` provenance (`EEG.comments`/`history`): converted from Curry `.dap` files with
  `loadcurry(..., 'KeepTriggerChannel', 'True', 'CurryLocations', 'False')`, EEGLAB 2022.0. Comments hold the
  original lab ID and date (e.g. `#001_20210712/Parti-001.dap`); the BIDS IDs are not the lab IDs.
- `stimuli/task-lppHK_run-{1..4}.wav` (44.1 kHz mono int16; 300.405, 296.871, 301.218, 271.508 s) and
  `task-lppHK.wav` (= the four concatenated, sample-exact; 1170.002 s).
- `annotation/lppHK_word_information.csv` (4473 words: `word, token_id, snt_id, onset, offset, pos, log_freq`;
  times in the concatenated 1170-s timeline), `annotation/snts.txt` (535 sentences, text),
  `annotation/wav_acoustic.csv` (f0 and RMS every 10 ms).
- `quiz/` (20 yes/no questions; behavioural results incl. EEG accuracy), `participants.tsv/json` (age, sex, quiz
  scores, appointment dates, LHQ3/LEQ items).

## 3. Stimulus <-> trial mapping (verified)
- Paradigm: four story sections ("Parts") of ~5 min, each followed by 5 yes/no questions (button press); EEG
  recorded continuously through all four (paper; README). Same stimuli, same order for every participant.
- **Parts are defined by the presentation, not by the annotation's section prefix.** Part folders (v1.1.2), the run
  wavs and the EEG trigger blocks agree: Part 1 = sentences 1.003-1.116 (114), Part 2 = 1.117-1.144 + 2.003-2.117
  (143), Part 3 = 2.118-2.127 + 3.001-3.124 (134), Part 4 = 4.001-4.144 (144). The number before the dot in
  `snt_id`/`sentence_id` is a story section that does *not* match the Parts for 1.117-1.144 and 2.118-2.127 (the
  v1.1.2 xlsx note says it is "the sections of the story presented": upstream inconsistency).
- Sentence wavs vs run wavs (`scripts/sent_vs_run.py`): each run wav is exactly the concatenation of its Part's
  sentence wavs (zero offset at every boundary, r = 1.0000, gain 1.0000-1.0001: the run wav is the (L+R)/2 mono mix
  of the stereo sentence files). The last sentence ends exactly at the run wav's last sample in all four Parts.
- Trigger code = number after the dot (`EEG_trigger_and_sentence_number.xlsx`, all 535 rows), so codes repeat across
  Parts (e.g. code 14 is sentence 1.014, 2.014, ... and also a button response). Matching must use order and
  timing (section 6).
- Independent checks: (a) all 51 recordings contain the full ordered sentence-code sequence (535/535 matched; HK005
  534 minus 4, section 6); (b) trigger intervals equal the sentence wav durations + 8.5 ms (section 7); (c) EEG
  envelope tracking peaks at a constant lag through every Part only with per-sentence alignment (section 7).

## 4. Speech features available
- **Audio as presented**: 535 sentence wavs, 44.1 kHz, **stereo** int16 (L and R not identical, r >= 0.9946),
  0.35-7.38 s (median 1.98 s), v1.1.2 only. Mono run wavs (v1.1.1) = (L+R)/2 of their concatenation.
- Transcript: `snts.txt` (535 sentences, traditional Chinese characters, Cantonese).
- Word timings: `onset/offset` (v1.1.1 CSV) = `onset_all/offset_all` (v1.1.2 xlsx), concatenated timeline, which
  matches the concatenated sentence files (scale ~0 ppm against the wav onsets, `scripts/onset_scale.py`; first word
  starts median 6 ms after its sentence file start, last word ends 1-8 ms after the file end). Quality limits:
  - **Word boundaries are largely interpolated, not aligned**: in 432 of 508 sentences with >= 4 words all word
    durations (except the last) are equal to 1-2 ms; words tile each sentence with no pauses (4391 of 4472 word
    gaps are exactly 0).
  - Errors: offset < onset in 5 rows (CSV lines 661 `1.068`, 1464 and 1481 `2.023`, 3420 `4.002`, 3611 `4.025`);
    sentence ids 2.023/2.024 appear inside 2.020 (lines 1464-1465); 7 sentences have their first word outside their
    own sentence file. `snt_id` is stored as a float (`1.1` means 1.100, `1.01` means 1.010).
  - The v1.1.2 `onset_in_sentence` column (documented as "after the trigger") is inconsistent with the sentence
    files: 1452 words lie outside their sentence wav; `onset_all - (sentence-file start)` is the usable in-sentence
    time.
- No phoneme annotation. POS tags and log frequency (PyCantonese) per word; f0/RMS (10 ms) in `wav_acoustic.csv`.

## 5. Neural data
- System: "gel-based 64-channel Neuroscan system on a 10-20 electrode template, 1000 Hz" (paper); Curry `.dap`
  recordings, so Curry acquisition software; amplifier model, online filters and ground not documented.
- 1000 Hz in all 51 files (`EEG.srate`), one continuous segment each, **no boundary events**, durations
  1308-2509 s (header).
- Units: `.fdt` float32 in µV (memmap matches MNE x 1e6); MNE `read_raw_eeglab` scales to V correctly. 1-40 Hz SD
  ~6-10 µV median over channels (CZ/CPZ 0.4-3 µV), plausible. Large DC offsets (median |mean| 1.7-9 mV): DC or
  very low high-pass recording, not documented.
- Channels (MNE reads all 67-69 as `eeg`):
  - 62 scalp: FP1 FPZ FP2 AF3 AF4 F11 F7 F5 F3 F1 FZ F2 F4 F6 F8 F12 FT11 FC5 FC3 FC1 FCZ FC2 FC4 FC6 FT12 T7 C5 C3
    C1 CZ C2 C4 C6 T8 TP7 CP5 CP3 CP1 CPZ CP2 CP4 CP6 TP8 P7 P5 P3 P1 PZ P2 P4 P6 P8 PO7 PO3 POZ PO4 PO8 O1 OZ O2
    CB1 CB2 (CB1/CB2 cerebellar, keep as `eeg`)
  - M1, M2: mastoids -> `misc` (external)
  - VEO, HEO -> `eog` (bipolar in the usual Neuroscan montage; not documented)
  - EKG (HK015, HK040, HK041, HK042) -> `ecg`; EMG (HK015 only) -> `emg` or `misc`
  - TRIGGER: event code as a value (MNE shows code x 1e-6 V), 8-sample pulses; identical to `EEG.event`
    (HK001: 584 = 584). Drop after reading events.
  - 47 files 67 ch, HK040-042 68 ch (+EKG), HK015 69 ch (+EKG, EMG). Channel order otherwise identical.
- **No stimtrack/audio/aux channel** in any file.
- Reference: **not documented**. `EEG.ref` = 'Common'; the BIDS `_eeg.json` says `EEGReference: "Average"`, which is
  wrong for these files (the channel mean is not zero). Inferred: online reference near CZ/CPZ (lowest 1-40 Hz
  variance at CZ and CPZ in all checked files, `scripts/refcheck.py`), the Neuroscan Quik-Cap default. Keep as
  recorded; record "online reference near CZ/CPZ (inferred; Neuroscan default)".
- No digitisation: chanlocs are an EEGLAB template (identical in every file; F11, F12, FT11, FT12, CB1, CB2, VEO,
  HEO have no coordinates). `meas_date` unspecified.
- **Six `.fdt` files are truncated upstream** (local size = S3 Content-Length; same in v1.1.2), so MNE cannot read
  them as they are; a memmap of the complete samples works:

  | subject | samples present | of header | complete Parts |
  |---|---|---|---|
  | HK019 | 1188.5 s | 1426.8 s | 1-3 (Part 4 missing) |
  | HK023 | 1401.4 s | 1467.0 s | 1-4 (cut in the final quiz) |
  | HK030 | 864.0 s | 1487.9 s | 1-2 |
  | HK042 | 875.2 s | 1410.4 s | 1-2 |
  | HK044 | 649.5 s | 1726.8 s | 1 |
  | HK045 | 1006.9 s | 1584.4 s | 1-2 |

  The authors' preprocessed derivatives (62 ch, 1-40 Hz, ICA, M1/M2 re-referenced, 250 Hz) are complete for these
  subjects (e.g. HK019 356700 samples = 1426.8 s), but are not raw.
- 1000 Hz is a "nice" rate: no resampling.

## 6. Alignment
- Events (`EEG.event`, also the TRIGGER channel): sentence codes 1-144 (one per sentence, at the start of each
  sentence file), question codes 201-220 (questions 1-20, xlsx), codes 14/15 around the questions (button
  responses, inferred: they precede each 2xx by ~0.1 s and follow the last question; which is yes/no is unknown),
  stray codes 700010, 800000, 800001, 1000001, 1200001, 1200002, 4096 and isolated low codes (e.g. a `4` 8 ms after
  `52`). No Part start/end codes, no audio-end codes.
- Hardware/software: STIM2 (Compumedics Neuroscan) presented the audio and set "triggers at the beginning of each
  sentence" (paper, EEG data). Whether the trigger is locked to sound output is not documented. **Inferred
  software timing**: trigger-to-trigger intervals vary across subjects in steps of 0, +-1, +-8-9 and +-15-17 ms
  (a ~16 ms timer), and in ~4 % of transitions the next trigger comes 1-10 ms *before* the previous sentence file
  has ended (`scripts/gaps.py`).
- Trigger matching (`scripts/match.py`): longest common subsequence between the event codes and the 535 expected
  codes, then a timing check against the cross-subject median trigger timeline (+-1.5 s). Result: 535/535 for 50
  participants. **HK005, Part 1**: sentence 1.065 was cut 191 ms short (1.066 started early, preceded by code
  700010), and sentences **1.067-1.070 were never presented** (8.09 s of audio; 1.066 -> 1.071 trigger interval
  3.226 s); the recording then runs ~11 min past the last question (2130 s).
- Playback pauses (gap > 100 ms, all in Part 1): HK019 after 1.103 (151 ms), HK023 after 1.046 (120 ms) and 1.093
  (430 ms), HK025 after 1.113 (918 ms), HK032 after 1.099 (168 ms). The splice below absorbs them.
- **Proposed alignment (per-sentence splice), one trial per Part:** for Part p with sentences i (start W_i in the
  Part's concatenated wav, from the sentence wav lengths) and trigger times t_i, output EEG sample k at 1000 Hz
  (Part time k/1000 s, sentence j with W_j <= k/1000 < W_j+1) is taken from EEG time t_j + (k/1000 - W_j)
  (nearest sample or linear interpolation; the trigger is only good to a few ms anyway). This drops the ~8.5 ms
  inter-sentence gaps (and the longer pauses) from the EEG and repeats a few ms where the next trigger came early.
  The Part stimulus is then the concatenated sentence wavs (= the v1.1.1 run wav), shared by all participants.
  `alignment_method: sw_trigger` (per sentence), `trigger_type: software (inferred; STIM2, paper)`.
  Constant trigger-to-sound latency is unknown; the validator's lag sweep will estimate it.
- Alternatives considered (EEG evidence in section 7): continuous wav from the first trigger (wrong by up to 1.9 s);
  one linear stretch per Part (+3400 to +5100 ppm; leaves per-subject random-walk errors, median max 29 ms, 90th
  percentile 44 ms, up to 0.9 s with the pauses above); piecewise-linear between triggers (better, but spreads each
  gap over its sentence). Trials per sentence (535 x ~2 s) would also be exact but too short for TRF work.

## 7. Cross-subject duration check, drift and jitter
- Trigger interval vs sentence duration (`scripts/gaps.py`, `sentence_gaps.png`; 51 participants, 531 within-Part
  intervals each): gap = next trigger - trigger - sentence wav duration = **median 8.5 ms**, 1st-99th percentile
  -4.5 to 23.6 ms. Per subject, fit interval = duration x (1 + drift) + gap0 + noise:
  - drift (EEG clock vs sound output, within sentences): median +117 ppm (IQR 18-213, range -208..695; each
    estimate has a standard error of roughly 200 ppm because sentences are short). Over the longest sentence
    (7.4 s) 117 ppm is 0.9 ms: **no drift correction**; record `drift_ppm` as the per-subject value or null.
  - gap0 7.7-9.5 ms; **jitter SD 6.3-8.7 ms (median 7.0 ms)** per sentence onset. Record `jitter_ms` ~7.
- Accumulated over a Part, the gaps make the trigger timeline 0.78 s (Part 1), 1.36 s (Part 2), 1.82 s (Part 3)
  and 1.00 s (Part 4) longer than the wav (median subject; equivalent to +3436, +4438, +3886, +4624 ppm). The same
  ~9 ms per sentence explains the different per-Part "ppm" (sentence density 0.38-0.54 per s). This is not clock
  drift. Per subject, the timeline random-walks around the median by +-50-150 ms over a Part
  (`trigger_steps_per_subject.png`).
- EEG verification (`scripts/lagdrift.py`, `warpcheck.py`, `warpcheck_S.py`; `lagdrift_pooled.png`,
  `warpcheck_models.png`, `alignment_B_vs_S_per_subject.png`): FZ/FCZ/CZ/FC1/FC2/C1/C2/F1/F2 re mastoid mean,
  1-8 Hz, 100 Hz, cross-correlated with the 1-8 Hz broadband envelope in 40-s windows, pooled over 51 subjects.
  - Continuous wav from the first trigger: the response ridge moves from ~0.3-0.5 s to ~1.0 s lag across each Part.
  - Linear stretch per Part and piecewise-linear between triggers: vertical ridge at ~0.2 s.
  - **Per-sentence splice: vertical ridge, grand peak at +0.20 s in all four Parts; grand-mean r 0.034, 0.027,
    0.026, 0.039 (Parts 1-4) vs 0.024, 0.017, 0.023, 0.037 piecewise-linear; higher in 152 of 199
    subject-Parts.** A positive peak at +0.02 s and troughs at ~0.1 and ~0.33 s also appear (band-passed
    xcorr shape; not interpreted).
  - Per subject (splice, mean over Parts): r at the grand peak lag (+0.20 s) is positive in 49 of 51 (median
    0.031). Below 0.01 at +0.20 s: HK008, HK019, HK022, HK023, HK041, HK046, HK048, HK052 (their largest peak lies
    at 0.03-0.27 s instead, i.e. the early peak or a later one) and **HK037 (largest peak 0.64 s) and HK042
    (-0.41 s): no clear tracking**. Not excluded; for the validator to judge.

## 8. Data size
- Per complete participant: 535 sentences, 1170.0 s of audio (0.325 h; ~1174.6 s including the gaps).
- **51 participants, 15.78 h** (mean 0.309 h, range 0.083-0.325 h), after the truncated files (HK019 -271.5 s,
  HK030/HK042/HK045 -572.7 s each, HK044 -869.6 s) and HK005's missing sentences (-8.1 s; -124 s, 15.75 h in
  total, if Part 1 is cut at 1.066 as proposed in open question 5). 16.58 h if all files were complete. One
  condition (clear speech; older adults, 65-77 y in `participants.tsv`).
- Not yet added to `tmp/review/data_size.csv`/`data_size.md` (leave to the standardiser with the final trial list).

## 9. Proposed adaptor
- Registry: move to v1.1.2 and include `sourcedata/stimuli/audio_files_segmented_by_sentence/**` and
  `sourcedata/annotation/{EEG_trigger_and_sentence_number,lppHK_timing_word_information}.xlsx` (exclude
  `sourcedata/annotation/Eprime_output_fMRI_timing/*`, func, anat, derivatives). EEG files are unchanged.
- Trials: one per participant x Part (4; fewer for the truncated files). EEG built by the per-sentence splice
  (section 6) from a memmap of the `.fdt` (needed for the truncated files; channel-fastest float32, µV).
- Stimulus per Part: concatenation of the Part's sentence wavs (shared name `part1`..`part4`). Mono (L+R)/2
  reproduces the v1.1.1 run wav; see open question 3.
- Annotations: TextGrid per Part, tier `words` from `onset_all/offset_all` minus the Part start (flag in metadata as
  interpolated within sentences), plus a `sentences` tier from the sentence-file boundaries (exact). No `phones`.
- Channel types and reference as in section 5; TRIGGER dropped.

## 10. Open questions (recommended default in brackets)
1. **Alignment method**: per-sentence splice of the EEG (drops ~8.5 ms gaps, absorbs pauses) vs a single linear
   stretch per Part. [Splice. It is what the authors describe (one trigger per sentence) and fits the EEG best;
   it does mean the stored EEG is not contiguous in time. Record the splice map (sentence, trigger sample, output
   sample) in the trial metadata.]
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** no splice; the EEG of each Part stays continuous and untouched, cropped from the Part's first
   sentence trigger to the end of its last sentence. The stimulus is built **per participant and Part**
   (`HK<id>_part<p>`) by placing each sentence wav at its own trigger (relative to the Part's first trigger, trigger
   sample x 44.1) on a silent 44.1 kHz track: gaps and pauses are silence; where a trigger comes before the previous
   sentence has ended, the earlier sentence is cut at that trigger. Same per-sentence alignment as the splice,
   neural data unaltered (like bentum2023's block audio from file lists + gaps). Sidecar: `sw_trigger`, software
   (inferred; STIM2), `drift_ppm` null, `jitter_ms` 7. See section 13.
2. **Dataset version**: v1.1.1 (downloaded; has the run wavs, no sentence files) vs v1.1.2 (sentence files and
   xlsx; no run wavs; identical EEG). [Pin v1.1.2 in the registry; build the Part stimuli from the sentence wavs.
   The sentence boundaries are also in `tmp/review/momenian2024/sentence_table.csv` (535 rows: sentence, code,
   Part, start sample, length) if a static table in the repo is preferred.]
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** v1.1.2; the adaptor reads the Part folders and wav lengths itself (no static table), and
   does not use the v1.1.1 run wavs.
3. **Stereo or mono stimulus**: the sentence wavs are stereo with slightly different channels. [Store stereo as
   presented if the stimulus format allows; otherwise mono (L+R)/2, which equals the authors' run wav.]
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** mono (L+R)/2. The channels differ only slightly (r >= 0.9946), the playback hardware
   (headphones/loudspeakers, which channel went where) is not documented, and the validator and features assume
   mono audio; the mix equals the authors' run wavs.
4. **Truncated `.fdt` files** (HK019, HK023, HK030, HK042, HK044, HK045). [Use the complete Parts from the raw data
   (HK023 is complete for all Parts); skip Parts that run past the data. Do not mix in the 250 Hz preprocessed
   derivatives. Report upstream.]
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** as recommended: memmap of the samples present; a Part is kept only if its last sentence
   ends inside the data (HK019 Parts 1-3, HK023 1-4, HK030/HK042/HK045 1-2, HK044 1). Derivatives never used.
5. **HK005 Part 1** (1.065 cut short by 191 ms, 1.067-1.070 never played). The full Part 1 stimulus does not
   match after 1.066. [Trial for sentences 1.003-1.065 only (spliced EEG up to the 1.066 trigger, 176 s of the
   wav; the longer stimulus is cut at use, per convention) and drop 1.066 + 1.071-1.116 (116 s). Alternative: a
   second trial with its own derived stimulus name.]
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** sentences 1.003-1.065; the stimulus ends at the 1.066 trigger (1.065 cut 191 ms short as
   played) and so does the EEG. 1.066 and 1.071-1.116 dropped (`STOP_AT` in the adaptor).
6. **Validation reference**: online reference unknown (inferred CZ/CPZ). [Average reference for validation as
   usual; record "unknown, inferred near CZ/CPZ" in the metadata.]
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** recorded as "unknown (inferred online reference near CZ/CPZ, Neuroscan default)", no
   re-referencing. Channel types: M1/M2 `misc` (external), VEO/HEO `eog`, EKG `ecg`, EMG `emg`, TRIGGER dropped;
   1000 Hz kept; positions `standard_1005` template (none for F11, F12, FT11, FT12, CB1, CB2).
7. **Weak-tracking participants** (section 7). [Keep; flag after validation.]
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** kept; HK037 and HK042 flagged (`weak_tracking` in the sidecar).
8. **Annotation quality**: word timings mostly interpolated, several errors (section 4). [Ship the `words` tier with
   a metadata note; do not correct the errors ourselves; report upstream.]
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** TextGrid per stimulus with tiers `words` (upstream `onset_all/offset_all` minus the start of
   the sentence file containing the word onset, placed at that sentence's trigger) and `sentences` (the placed
   wavs). Minimal handling needed for a valid TextGrid, nothing else corrected: the 5 words with offset < onset
   are dropped; words are clipped at the end of their (possibly cut) sentence and at the previous word's end. No
   `phones` tier (none shipped). Interpolated word boundaries noted in the sidecar (`annotation`).

## 11. Upstream issues (to report)
1. Six raw `.fdt` files are truncated on OpenNeuro (HK019, HK023, HK030, HK042, HK044, HK045; 38-96 % of the
   samples present), unchanged in v1.1.2.
2. HK031 has no EEG although the paper reports 52 EEG participants.
3. `_eeg.json` gives `EEGReference: "Average"` for raw data that are not average-referenced; the online reference
   is not documented.
4. The v1.1.1 continuous run wavs and "time-aligned" word timings omit the inter-sentence gaps of the sentence-by-
   sentence presentation (fixed in v1.1.2 by the sentence files and the README note).
5. Word annotation: interpolated word boundaries; 5 rows with offset < onset; mislabelled sentence ids (2.023,
   2.024 inside 2.020); `onset_in_sentence` (v1.1.2) inconsistent with the sentence files; `snt_id` as float.
6. The section prefix of sentence ids does not match the presented Parts for 1.117-1.144 and 2.118-2.127, although
   the v1.1.2 note says it does.
7. HK005: four sentences (1.067-1.070) were not presented.

## 12. Related datasets
- wang2025 (LPP multi-talker, OpenNeuro ds005345, same lab) is next: check whether it also presents the story
  sentence by sentence with one trigger per sentence, ships sentence wavs, and uses the same `snt_id` float
  convention and interpolated word timings. The splice code here should be reusable.

## 13. Standardisation (adaptor, 2026-11-22)
- Scripts and figures: `tmp/review/momenian2024/std_scripts/` (`check_parse.py`, `check_onsets.py`,
  `lagcheck.py`, `lagsummary.py`, `standardise.py`, `pilot_summary.py`), `std_lagcheck_*.png`.
- **Trigger matching** (`_match`): per Part, the first event with the first sentence's code whose following
  sentence codes appear in order, each within -0.3..+1.5 s of (previous trigger + previous sentence duration).
  Identical to the explorer's LCS + timing match (`match.json`) for all 535 triggers of all 51 participants
  (HK005: identical up to 1.066, where the trial stops). Trigger codes agree with
  `EEG_trigger_and_sentence_number.xlsx` for all 535 sentences.
- **Placement** (`_placement`): sentence audio start = (trigger - first trigger of the Part) x 44.1 samples. A
  sentence is cut where the next one starts: 1852 of 25835 placed sentences (7.2 %; ~36 per participant), by at
  most 16.7 ms (HK032), except HK005 1.065 (191 ms, as played). The 7.2 % is higher than the ~4 % of early
  triggers in section 6 because the trigger is only known to 1 ms: overlaps below 1 ms from the sample grid are
  counted too. Pauses > 100 ms: HK019 151 ms, HK023 120 and 430 ms, HK025 918 ms, HK032 168 ms (all Part 1).
- **Words**: 532 words end 1-8 ms after the end of their sentence file and are clipped there; 4 word pairs overlap
  within a sentence (the later word starts at the earlier one's end).
- **Per-Part lag check** (`lagcheck.py`, `lagsummary.py`; `std_lagcheck_pooled.png`,
  `std_lagcheck_100s_HK001_HK023_HK025.png`, `std_lagcheck_100s_HK005_HK032.png`): FZ/FCZ/CZ/FC1/FC2/C1/C2/F1/F2
  re mean(M1, M2), 1-8 Hz, 100 Hz, vs the 1-8 Hz rectified-audio envelope of the adaptor's stimulus ("placed")
  and of the plain concatenated sentence wavs from the first trigger ("concatenated"); 100-s windows, 50-s step.
  - Pooled over HK001, HK005, HK023, HK025, HK032: placed peaks at **+0.20 s in every window of every Part**
    (Part 1: 0.20 0.20 0.20, then 0.02 in the last window; Part 2: 0.19 0.19 0.18, 0.04; Part 3: 0.19 0.20, then
    the ridge fades (r at 0.20 s 0.058 0.050 0.026 0.015 -0.002) with no tilted ridge; Part 4: 0.20 0.20 0.20
    0.20). The late-window 0.02-0.04 s values are the early peak of the band-passed cross-correlation (section 7),
    not a slide. Concatenated: no stable ridge, window peaks between -0.45 and +1.39 s.
  - r at +0.20 s (mean over windows), placed vs concatenated: HK001 0.052/0.058/0.058/0.056 vs
    -0.009/-0.044/-0.040/+0.026; HK025 0.032/0.066/0.041/0.037 vs -0.024/-0.034/+0.016/+0.023; HK032
    0.074/0.053/0.028/0.046 vs 0.010/-0.011/0.003/-0.026; HK005 0.086/-0.020/0.027/0.092 vs
    -0.003/0.000/0.014/0.012; HK023 (weak tracker, section 7) 0.013/0.034/-0.009/-0.032 vs
    -0.003/0.028/-0.004/-0.035.
  - Single-subject 100-s windows are noisy (side peaks at ~0.02 and ~0.4 s compete), so the per-window argmax
    alone is not a test; the placed construction anchors every sentence at its own trigger, so a cumulative
    slide cannot arise from the stimulus side.
- **Pilot (all 51 participants, `std_scripts/standardise.py`, FlatSinkV1)**: 194 trials (46 participants x 4
  Parts, HK019 3, HK030/HK042/HK045 2, HK044 1), 0 failures, 1000 Hz everywhere (no resampling), 66 channels (67
  with EKG: HK040-042; 68 with EKG + EMG: HK015), trial durations 176.7-302.6 s, **15.81 h**. EEG is longer than
  the stimulus by < 1 ms (rounded up to whole EEG samples). No trial needed a weaker alignment method. Output
  24 GB (EEG 15 GB, audio 9.4 GB).

## 14. Timing check: match-mismatch DNN offset (2026-11-22, note only)
`fs128_1020-64_broadband` classifier (trained on accou2023; `tmp/review/scripts/dnn_offsets.py`, 5 s windows,
+-500 ms lags, 100 random Parts, the 6 channels without template positions dropped before the montage
interpolation): **-21.2 ms** (95% CI -24.2 .. -18.1; 47 subjects; per-subject median -20.7, IQR -26.7 .. -15.7)
relative to accou2023 (self-check +0.6 ms). Negative = neural response later than in accou2023.
Two explanations, not separable without a stimtrack: an unmeasured trigger-to-sound latency of the STIM2 software
triggers (sound-card buffer), and longer cortical latencies of older listeners. Recorded, not corrected (same
handling as harshaiyahav2025); compare the TRF P1/N1 latencies of the validation with herrmann2025/weissbart2019
(same code: P1 ~35 ms, N1 ~89 ms).

## 15. HK050 Part 1: bad T8, not misalignment (2026-11-22)
Validation flagged HK050 Part 1 (backward r 0.003 vs 0.11-0.16 in its other Parts; lag-sweep maximum -437 ms;
forward per-trial offset -0.448 s; median EEG SD 26.7 µV vs 4-6 µV).
- **Triggers**: the event list is clean (codes 3-116 in order, one each, no extra, duplicated or out-of-order
  codes, no pause > 100 ms, no boundary events; 10 sentences cut by <= 3.7 ms). Matching is identical to the
  explorer's LCS + timing check. The first trigger of Part 1 is at sample 32078, like other participants (~20-33 s).
- **Signal** (`std_scripts/hk050.py`, `hk050_check.png`; raw `.fdt` memmap): **T8** has a 1-40 Hz SD of
  3.3-3.7 mV (peaks 14.3 mV) from the start of the recording until ~85 s into Part 1, then abruptly ~1.2-1.5 µV
  (neighbour C6: ~6 µV) for the rest of the recording, at a DC offset of ~211 mV: a faulty (inferred)
  electrode throughout. All other channels are normal (median SD 3.4-5 µV; mastoids 4-6 µV).
- **Alignment is fine**: fronto-central channels re mean(M1, M2), 60-s windows: r at +0.20 s 0.04-0.16 in all
  nine windows of Part 1 (the highest of HK050's Parts). With an **average reference including T8**
  (`std_scripts/hk050_avgref.py`; FZ/CZ/F3/F4/C3/C4 mean, 0.5-8 Hz): first 85 s FC SD 45 µV and the
  cross-correlation peak at -0.41 s (r 0.095, r at +0.20 s -0.007); the rest of the Part peaks at +0.21 s
  (r 0.143). **Without T8**: first 85 s FC SD 2.1 µV, peak +0.09 s (r 0.099; r at +0.20 s 0.087); the rest +0.21 s.
  The validator's -0.44 s is therefore the T8 artefact spread by the average reference over 85 of 301 s.
- **Handling**: `BAD_CHANNELS = {"HK050": ["T8"]}` sets `raw.info["bads"]` in all four HK050 trials (data
  unchanged) and lists it as `bad_channels` in the sidecar; Part 1 has `quality: "suspect: ..."` (all other trials
  `ok`). Re-standardised HK050 only (`std_scripts/restandardise_sub.py 50`). The validator must honour
  `info["bads"]` (exclude from the average reference) for this to help.
  (2026-11-22: `cnsp_datasets.validate.load.load_neural` now excludes `info["bads"]` from the picks and the
  average reference; before, MNE's `pick("eeg")` kept bad channels. The momenian2024 validation predates the fix.)
- Channel scan of all 194 trials (`std_scripts/chan_scan.py`, `std_chan_scan.json`; 1-40 Hz SD per channel in
  30-s windows vs the trial median): HK050 Part 1 T8 (3.4 mV) is an order of magnitude above anything else. Next:
  HK011 T8 (up to 0.50 mV in 1-4 windows per Part), HK003 T8 (up to 0.28 mV, most windows), HK037 FP1/FP2
  (~0.2 mV, eye artefacts). Not marked; frontopolar channels > 10x the median in several participants are eye
  artefacts. CZ/CPZ (and neighbours) < 0.3x the median in almost every participant, consistent with the online
  reference near CZ/CPZ (section 5).

## 16. Validation (validator, 2026-11-22; `validation.json`)
Average reference (62 scalp channels), regressor = the placed-sentence track. **Tier low for all 194 trials**
(pooled and per Part); mlr and brainstem fail.
- Forward, low tier: median r 0.034 (mean 0.035), 37/50 subjects above the circular-shift and mismatch nulls;
  TRF / GFP peak 0.19 s.
- Backward (leave-one-Part-out decoder, 0-250 ms, 64 Hz, 0.5-8 Hz): **median r 0.216** (IQR 0.172-0.250),
  **50/50 subjects** above both nulls (HK044 has one Part, no decoder).
- mlr: mean SNR 1.00 (p 0.08, 4/51 subjects); brainstem: 0.98 (p 0.62, 2/51). Expected with ~7 ms software
  trigger jitter per sentence.
- **TRF latency** (forward, 128 Hz, 1-15 Hz, FC mean, same code as herrmann2025): P1/N1 **57.5/115.3 ms** vs
  herrmann2025 34.7/88.6 ms and weissbart2019 34.8/88.9 ms, i.e. +23/+26 ms. Consistent with the DNN offset
  -21.2 ms (section 14); an unmeasured trigger-to-sound latency and older listeners' longer latencies cannot be
  separated. Not corrected.
- **Coherence** (`tmp/review/coherence_batch/{128,native}/momenian2024.json`; ratio to one global-shift surrogate,
  62 ch, 194 trials): 0.2-1 Hz 5.3, 1-4 Hz 3.8, 4-8 Hz 5.1, 8-15 Hz 2.3, 15-30 Hz 1.28, 30-60 Hz 1.05-1.07,
  60-120 Hz 1.05, 120-250 Hz 1.05, 250-500 Hz 1.01 (single surrogate: ratios near 1 are not significant).
- `validation_tier: "low"` is set in every sidecar by the adaptor. Only HK050 has been re-standardised since;
  the other 190 trials in `tmp/review/momenian2024/standardised` still carry `validation_tier: null` and lack
  `bad_channels`/`quality` until the full run.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**poor**: Software sentence triggers (~7 ms jitter), no stimtrack; DNN -21 ms and TRF +23/+26 ms later documented, not applied; trigger latency vs older listeners 'not separable'; low tier.

## Restructure 2026-11-25 (not yet re-validated on data)
- TextGrid written by `iohelpers.textgrid` (was a hand-rolled writer): same intervals (overlaps trimmed as before),
  times at full precision instead of 6 decimals, quotes escaped.
- Audio through `iohelpers.read_wav` ((L + R) / 2, float32 / 32768: unchanged values); bad channels with
  `iohelpers.mark_bads` (strict); skipped Parts are logged (were printed).
