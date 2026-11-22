# herrmann2025: younger and older adults, stories in clear and 12-talker babble at 16 SNRs (OSF p8nxq)

Explorer notes, 2026-11-21/22. Scratch scripts and figures: `tmp/review/herrmann2025/` (data storage;
`scripts/*.py`, `*.png`). Everything below that explains a choice is recorded here because tmp is deleted.

## 1. Source
- OSF project p8nxq (https://osf.io/p8nxq), created 2025-05-04, last modified 2026-03-16. No DOI registered for the
  node (OSF `identifiers` empty).
- Paper: Herrmann B (2025). Age-related differences in the impact of background noise on neural speech tracking.
  *Neurobiology of Aging* 153:10-20. doi:10.1016/j.neurobiolaging.2025.06.001.
- **Licence: unknown.** OSF API `node_license` is `null`. `read_me.txt` is a generic lab statement ("datasets under a
  Creative Commons license"; asks to cite the paper and consider involving the authors), no licence version.
- No analysis code shared. The paper's pipeline: re-reference to mastoid mean, 60 Hz notch, 0.7-22 Hz, 512 Hz, ICA,
  zeroing of >80 µV segments, 10 Hz LP; onset envelope from a 30-band cochlear model of the *clean* story (no babble);
  mTRF forward model, lambda 10, lags 0-0.4 s.

## 2. Layout
- `rawdata/naNNa{1..5}.bdf`: one BioSemi file per block (5 blocks x 4 stories), 260 files, 52 participants
  (younger `na01`-`na26`, older `na40`-`na65`). Recorded 2024-05-27 .. 2024-08-23.
- `logfiles/naNNa{b}.mat`: per-block MATLAB log (`lists`: story wav, subjID, SNR, storyID, questions; `resp`, `gist`,
  `noise`, `comph`: answers and ratings). **Only 146 of 260 blocks have a log** (34 participants; OSF lists exactly
  146 files, so this is not a download gap). See section 3.
- `stories/<Title>_sil_L<SNR>.wav`: 20 stories x 17 versions = 340 wavs, 44.1 kHz mono int16. `L` = SNR in dB:
  57, 52.8, 48.6, 44.4, 40.2, 36, 31.8, 27.6, 23.4, 19.2, 15, 10.8, 6.6, 2.4, -1.8, -6, and `Inf` (clear).
- `stories_text/<Title>.txt` (transcript) and `<Title>.xlsx` (4 questions x 4 options, first option correct).
- `demographics.xlsx` (ID, age group YA/OA, age, gender, ethnicity, hearing aid, neurological disease),
  `audiometry.xlsx` (pure-tone thresholds per ear, 0.25-8 kHz). Both list 50 participants: **no na17 and na60**.
  Read with `pd.read_excel` (openpyxl, a dependency since 2026-11-22); audiometry headers carry trailing spaces.

## 3. Stimulus <-> trial mapping
- Each block plays 4 stories; one marker per story (section 6). In a logged block, `lists[i]` is the i-th story of
  the block and `lists[i].story` is the exact wav played (`<Title>_sil_L<SNR>.wav`; the SNR field matches the file
  name in all 584 entries; `subjID` matches the file name in all; `storyID` 1-20 = alphabetical title order).
- Per participant: 20 stories, each once; 4 clear + one at each of the 16 SNRs; assignment and order randomised per
  participant (paper 2.4). All 22 fully logged participants have exactly 4 clear + 16 distinct SNRs.
- Verification of the logs (independent signals):
  - Log file creation time (MAT header) vs BDF `meas_date` + duration: -67..+19 s (median -2 s) for all 146 logs:
    each log belongs to its recording. (`meas_date` is local time labelled UTC.)
  - Trigger gaps cannot check the order within a block: each gap exceeds the story by 34-196 s (questions), so every
    permutation fits.
  - **EEG check** (`scripts/trf_id.py`, `id_summary.py`, `lag_sweep2.py`; `mapping_trf.png`,
    `lag_sweep_loso_10s.png`): leave-one-subject-out forward TRF on the onset envelope of the clean story (FC mean
    re mastoids, 1-8 Hz, 64 Hz), each logged trial scored against all 20 stories. The logged story ranks first in
    35 % of trials (chance 5 %, median rank 2); the logged within-block order is the best of 24 permutations in 72 of
    146 blocks (chance ~6). Per participant the prediction peaks at zero stimulus shift (robust z(0) >= 2.5 against
    shifts within +-10 s) for 26 of 34; borderline na02 (2.0) and na47 (2.3, 4 trials); **na10, na21 (4 trials),
    na55, na61, na64, na65 show no clear tracking** (z(0) 1.5, 1.7, 1.2, 0.3, 0.2, -2.2; no consistent alternative
    shift). Their amplitudes are normal (na64 large frontal/eye
    activity); timestamps tie their logs to their recordings. Cause unknown (weak responses vs wrong log content).
- **Unlogged blocks (114: na12-15, na17, na22-26, na40-46, na60 entirely; parts of na06, 11, 16, 18-21, 47, 48, 51,
  62, 64): story and SNR unknown.** The EEG identifies the story only in ~35 % of trials and cannot recover the SNR.
  For participants with 4 of 5 logs the missing block's 4 stories and 4 SNRs are known as sets, but not which story
  had which SNR, nor the order.
- **na17 and na60**: full raw data (5 BDFs each) on OSF, but absent from demographics, audiometry and logs. The paper
  (Data availability) says one younger and one older participant declined public sharing; these two are the likely
  ones (younger na17, older na60; the paper's 26 + 26 = the 52 BDF IDs). See Open questions.

## 4. Speech features available
- Audio as played: `<Title>_sil_L<SNR>.wav` (speech + babble mixture, all normalised to the same RMS, 0.0251).
- Clean speech: `<Title>_sil_LInf.wav` (identical to the speech component of every SNR version: least-squares
  speech gain a = 1.0000 at 57 dB, 0.985 at 15 dB, 0.798 at 2.4 dB, 0.445-0.447 at -6 dB; residual SNR equals the
  nominal SNR within 0.07 dB).
- Babble: not shipped separately. The residual `mix - a*clean` is the babble; it starts at wav sample 0 with an
  abrupt (~10 ms) onset, and is a different babble segment in every file (residual correlation ~0 between SNRs of
  one story; ~0.04 between stories at the same SNR).
- `_sil`: the clean speech is preceded by 0.008-0.343 s of exact digital zeros (speech onset >30 LSB at
  0.326-0.386 s) and followed by 0.11-0.67 s; the meaning of "sil" is not documented (silence padding is the likely
  reading).
- Durations: 91.43-135.51 s (mean 104.0 s; the paper's "1.5-2.5 min" is approximate). All 17 versions of a story
  have identical length.
- Transcripts (plain text) and comprehension questions; no word/phoneme timings.

## 5. Neural data
- BioSemi ActiveTwo, `.bdf`, 1024 Hz (all 260 files), online low-pass 208 Hz (header and paper), DC. 574-1114 s per
  block (median 715.5 s), 52.9 h of recording in total.
- Channels (identical in all 260 files): 16 scalp `Fp1 Fp2 F4 Fz F3 T7 C3 Cz C4 T8 P4 Pz P3 O1 Oz O2`, `EXG1`,
  `EXG2` (left and right mastoid per the paper; which is which is not documented, EXG1 = left is the BioSemi
  convention, unverified), `Status`. No EOG, no ECG, **no stimtrack/Erg/aux channel**. No digitisation.
- Units: header physical range +-262143 µV, MNE scales to V correctly; 1-8 Hz MAD re mastoid mean 2-8 µV on scalp
  channels (median over files), plausible; no flat channels (min 1.9 µV), largest na64a5 (Fp 40 µV, eye activity).
- Reference: BioSemi CMS/DRL (recorded reference-free); the authors re-reference to the mastoid mean. Keep as
  recorded; mastoids as `misc` (external).
- Native 1024 Hz is already a "nice" rate: no resampling needed.

## 6. Alignment
- Status channel: baseline low byte 254 (bits 1-7 high); one rising edge 254 -> 255 per story, 103-104 samples
  (~101 ms) wide. 4 markers in every file, 1040 in total; no other codes, **no end markers**. Bit 16 is set for the
  first 64 samples of every file (BioSemi epoch-start flag); mask the Status channel with `& 0xFF` (or 0xFFFF).
- Meaning: story onset (inferred: 4 per block = 4 stories; the ERP below). Not described in the paper.
- Hardware/software: **unknown**. Psychtoolbox 3.0.14 in MATLAB on a Lenovo T480 laptop (Windows 7), RME Fireface
  400, Sennheiser HD 25-SP II (paper 2.2); the trigger interface and whether the marker is scheduled with the audio
  are not documented. Inferred: software marker from MATLAB.
- Onset check (`scripts/onset_erp.py`, `onset_erp.png`): marker-locked ERP (FC mean re mastoids, 1-30 Hz) on
  logged trials. Babble trials SNR <= 15 dB (babble starts at wav sample 0): P1 62 ms, N1 126 ms; clear trials
  locked to marker + speech onset in the wav: N1 129 ms; TRF (onset envelope): P1 47 ms, N1 109 ms, P2 ~200 ms.
  Consistent with marker ~ sound onset to within a few tens of ms; finer offsets cannot be resolved without a
  stimtrack. Per-subject babble N1 latency 70-159 ms (median 119) mixes biology and timing.
- Proposed: onset = marker rising edge (`alignment_method: sw_trigger`, `trigger_type: unknown (inferred software)`),
  no drift correction, `drift_ppm: null`, `jitter_ms: null`. Clock drift between the Fireface and the BioSemi is
  not measurable here; at a typical 25-35 ppm it amounts to <= 5 ms over the longest story.

## 7. Cross-subject duration check
- Not possible: one marker per story, no end marker, no stimtrack. Gaps between markers include questions and
  ratings (34-196 s after each story). Every story fits inside its recording (>= 32.6 s after the last story ends
  in logged blocks; unlogged blocks: every gap >= 130.4 s, so all but the longest story fit even if unknown).
- Drift and jitter: not estimable from these data.

## 8. Data size
- If every block were usable: 52 participants x 0.578 h (20 stories, 2079.5 s) = 30.0 h (50 without na17/na60:
  28.9 h).
- **Logged blocks only (proposed): 34 participants (16 younger, 18 older), 584 trials, 16.9 h; per participant
  0.50 h (0.12-0.58).** Younger 7.4 h, older 9.5 h. Clear 124 trials (3.6 h); babble 460 trials (13.3 h), 27-33
  trials per SNR (~0.8 h each).
- 22 participants are fully logged (0.578 h each).

## 9. Proposed adaptor
- One TrialRecord per logged story; condition `clear` or `snr<+NN.N>` (or one condition `babble` with the SNR in the
  trial metadata); participant group (YA/OA, age, PTA from `audiometry.xlsx`) in the subject metadata.
- Stimuli per trial: `<Title>_L<SNR>` mixture as played (44.1 kHz); `<Title>` clean speech (the LInf wav, shared by
  all trials of that story); babble `<Title>_L<SNR>_babble` = mixture - a*clean (derived, separate name per file).
  Clear trials: mixture == clean, no babble.
- EEG at 1024 Hz unchanged; EXG1/EXG2 `misc`; original CMS/DRL reference kept.
- Onset = marker; no drift correction.

## 10. Open questions (recommended default in brackets)
1. **na17 and na60** (raw data public, but not in demographics/audiometry/logs; probably the two who declined public
   sharing). [Exclude, and ask the author whether their upload was intended. They have no logs, so the default
   below drops them anyway.]
   Decided by the user (2026-11-22): keep na17 and na60 (no exclusion); they have no logs, so item 2 applies.
2. **Unlogged blocks (114 of 260; 18 participants with no log at all).** [Skip; only the 146 logged blocks. Ask
   the author for the missing logs: they would add ~13 h.]
   Decided by the user (2026-11-22): skip them (not standardised with `stimulus=[]`).
3. Participants with no clear tracking under the logged mapping (na10, na21, na55, na61, na64, na65; na64/na65
   worst). [Keep; flag in the trial notes; revisit after validation. Exclude only if the author confirms a problem.]
   After validation (section 13): they track like the others with a backward model; kept, flag kept.
4. Licence unknown (OSF node licence empty; read_me says "a Creative Commons license"). [Treat as CC-BY-4.0-like
   "cite the paper" for internal use; ask the author before redistributing standardised data.]
5. Babble as a derived stimulus (least-squares residual, not shipped by the authors). [Include, named as derived in
   the metadata; the mixture and the clean speech are the primary stimuli.]
6. Marker vs sound onset unknown to better than a few tens of ms; no drift estimate. [Onset = marker, no shift, no
   drift correction; `drift_ppm`/`jitter_ms` null; expect validation up to the `low` tier at most (16-channel cap,
   ~100 s stories).]
   After validation (section 13): mlr tier at >= 15 dB, marker = sound onset within a few ms; no correction.
7. EXG1/EXG2 left/right assignment. [EXG1 = left, EXG2 = right mastoid, marked as convention, unverified.]

## 11. Upstream issues (to report)
1. Logs missing for 114 of 260 blocks (18 participants entirely): stimulus and SNR cannot be recovered.
2. na17 and na60 raw data on OSF while missing from demographics/audiometry (possible consent issue, section 3).
3. No licence set on the OSF node.
4. Story durations are 91-136 s, not 1.5-2.5 min as in the paper (minor).

## 12. Adaptor (2026-11-22)
Implemented on the explorer's defaults (section 10), as instructed by the coordinating agent. The coordinator
relayed on 2026-11-22 that na17 and na60 are to be kept (not singled out; treated like the other unlogged
participants) and that unlogged blocks stay out. The user confirmed both on 2026-11-22 (10.1, 10.2).
- Nothing in the code singles out na17 and na60: they are skipped only because they have no logs.
- OSF logfiles folder re-checked (coordinator, 2026-11-22): 146 files, all downloaded and identical to a separate
  copy; na12-15, na17, na22-26, na40-46 and na60 have raw data but no logs on OSF.
- Unlogged blocks are skipped. Per participant (blocks without a log): na06 1, na11 3, na12-15 5 each, na16 3,
  na17 5, na18 1, na19 3, na20 1, na21 4, na22-26 5 each, na40-46 5 each, na47 4, na48 1, na51 1, na60 5, na62 1,
  na64 1 (114 in total).
- `weak_tracking: true` in the trial metadata for na10, na21, na55, na61, na64, na65 (kept).
- Stimuli: `<Title>` (LInf wav) is the attended stimulus in every trial, so the validator and
  `assume_first_attended` use the clean speech (as the paper does). Babble trials add `<Title>_L<SNR>` (mixture,
  not marked attended) and `<Title>_L<SNR>_babble` (derived: `mix - (mix.clean / clean.clean) * clean`, float64,
  stored float32). The adaptor checks that mixture and clean wav have the same length (all start at sample 0).
- EEG: Status channel dropped after reading the markers (`& 0xFF`, 254 -> 255 edges; the adaptor requires as many
  edges as logged stories). Trial = marker to marker + clean-wav duration, 1024 Hz unchanged.
- Subject info per trial: age group, age, sex (demographics.xlsx), pure-tone average 0.5/1/2/4 kHz over both ears
  (audiometry.xlsx), read with `pd.read_excel` (`_table` in the adaptor; identical values to the earlier XML reader).

## 13. Validation, DNN offset and coherence (2026-11-22)
Scratch outputs (deleted with tmp): `tmp/review/herrmann2025/validation/` (figs, backward,
reference_weissbart2019_16ch), `tmp/review/herrmann2025/dnn_offsets/offsets.{json,png}`,
`tmp/review/coherence_batch/{128,native}/herrmann2025_*` (native = 1024 Hz);
`tmp/review/scripts/{dnn_offsets,coherence_batch,data_size}.py`. Numbers below are from `validation.json` (this
folder) unless marked otherwise.
- Settings: average reference over the 16 scalp channels (EXG1/2 excluded), clean speech `<Title>` as regressor.
  SNR groups in validation.json: high >= 40.2 dB (5 levels), mid 15-36 dB (6), low <= 10.8 dB (5).
- **Tier: `mlr`** overall, clear, babble, babble high and mid, mixture regressor; **`low`** for babble <= 10.8 dB.
  Brainstem fails everywhere (all: SNR 0.97, p 0.63). Set per trial by the adaptor (`LOW_TIER_MAX_SNR` = 10.8):
  444 trials `mlr`, 140 `low` (`trial_validation_tier_counts`).
- Forward low tier (0.5-8 Hz, 64 Hz): median r 0.036 (all; 27/34 above the circular null, 26/34 above mismatch),
  clear 0.046, babble 0.032; high 0.045, mid 0.030, low 0.015 (7/30). Reference datasets, same code: weissbart2019
  0.035, etard2019 0.027, accou2023 0.029, fuglsang2018 0.032, das2019 0.024. TRF GFP peak 172 ms.
- Backward (LOTO ridge decoder, 0-250 ms, 64 Hz, 0.5-8 Hz; nulls: 50 circular shifts, 20 mismatched envelopes):
  median r 0.123 all, 34/34 above both nulls; clear 0.148 (33/34 circ, 34/34 mismatch), babble 0.113, high 0.147,
  mid 0.128, low 0.071 (28/31 circ, 29/31 mismatch). Babble-only decoders: clean 0.109, mixture 0.112 (no gain
  from the mixture). weissbart2019 on the same 16 channels, same code: 0.145.
- Backward lag sweep (+-1 s, 15.6 ms steps, parabolic peak, subject bootstrap CI): all +0.6 ms [-0.7, 2.0], 33/34
  subjects within one sample; clear +0.3 [-2.3, 3.4]; high -2.7 [-5.0, -0.5]; mid -2.5 [-4.3, -0.8];
  **low +11.8 ms [8.2, 15.3]** (18/31 within one sample). Latency change in noise or timing: not separable.
- MLR (30-60 Hz, 1000 Hz): SNR 1.31 (mean 1.32), p 0.01, 11/34 subjects; GFP peaks ~18, 28, 39 ms (figure
  `validation_all.png`), nothing above the null at negative lags. Clear 1.08 (p 0.04, 2/34); babble 1.20
  (p 0.01, 9/34); high 1.10 (p 0.01); mid 1.17 (p 0.02); low 0.94 (p 0.71, fails); mixture 1.23 (p 0.01).
- Latency TRF (clean envelope, 128 Hz, 1-15 Hz, FC mean Fz Cz F3 F4 C3 C4): grand P1 / N1 clear 34.7 / 88.6 ms,
  high 36.2 / 91.0, mid 34.0 / 88.9, low 40.0 / 98.3. Stimtrack-aligned weissbart2019 on the same 16 channels,
  same code: 34.8 / 88.9 ms. So the marker is the sound onset to ~1 ms in this comparison (to a few ms given
  between-dataset latency differences).
- Validator jitter/drift (all: SD 241 ms, MAD 98 ms; 94 +- 404 ppm) are noise at these r values; not used.
- Weak participants (na10, na21, na55, na61, na64, na65; `weak_vs_other`): forward 5/6 above the circular null,
  median r 0.028 vs 0.040; MLR 1.23 vs 1.32; backward median r 0.116 vs 0.125 (Mann-Whitney p 0.15, one-sided),
  all above both nulls; lower only at <= 10.8 dB (0.058 vs 0.074, p 0.03). The pre-validation finding (section 3)
  came from a leave-one-subject-out forward TRF on mastoid reference; with subject-specific models they track like
  the others. Kept, flag kept (for transparency).
- **DNN offset vs accou2023** (match-mismatch classifier fs128_1020-64 broadband, trained on accou2023; up to 100
  trials per group; +-500 ms lag scan; positive = neural data early relative to accou2023; CI by subject
  bootstrap). Groups by SNR here differ from validation.json: high 23.4-57 dB, mid 2.4-19.2 dB, low -6/-1.8 dB.
  accou2023 itself +0.6 ms [-1.9, 2.9]; clear +4.9 ms [2.1, 7.9] (34 subjects); babble high +5.0 [1.5, 8.6] (32);
  mid +2.8 [-0.4, 5.6] (31); low +128 [-24, 138] (30 subjects, 57 trials): two peaks (near 0 and ~+125 ms),
  unreliable. Conclusion: markers are sound onsets within a few ms; no correction.
- **Coherence** (EEG vs clean-speech envelope, average reference, 5 s Hann windows, 4 s overlap, complex mean over
  subjects, one global-shift surrogate; channel mean). Above the surrogate up to ~10-12 Hz, peaks in delta (~1 Hz)
  and theta (~6 Hz); nothing above the surrogate > 30 Hz. Ratio to the surrogate per band (128 Hz run; the 1024 Hz
  run agrees within 0.08, and 60-500 Hz is 1.02-1.08 everywhere):

  | group (trials)          | 0.2-1 | 1-4  | 4-8  | 8-15 | 15-30 | 30-60 |
  |-------------------------|-------|------|------|------|-------|-------|
  | clear (124)             | 4.56  | 2.33 | 2.73 | 1.47 | 1.14  | 1.04  |
  | babble (460)            | 3.39  | 2.64 | 4.08 | 2.02 | 1.17  | 1.08  |
  | babble 23.4-57 dB (263) | 4.14  | 2.89 | 3.49 | 1.79 | 1.12  | 1.13  |
  | babble 2.4-19.2 dB (140)| 3.03  | 1.75 | 2.82 | 1.61 | 1.10  | 1.07  |
  | babble -6/-1.8 dB (57)  | 1.72  | 1.47 | 1.28 | 1.22 | 1.06  | 1.01  |
- Data size (`data_size.py`, stimulus durations): 34 participants, 16.9 h, 0.50 h each (0.12-0.58); clear 3.6 h,
  6.4 min per participant (1.7-7.8); babble 13.3 h, 23.4 min (1.8-28.2).
- Decisions (user, 2026-11-22): keep na17/na60 (not excluded; they have no logs, so no trials); skip the 114
  unlogged blocks (18 participants).
