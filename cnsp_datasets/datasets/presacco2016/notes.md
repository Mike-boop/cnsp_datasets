# presacco2016: aging, speech in noise with an English or Dutch competing talker, KIT MEG (DRUM, MEG part only)

Explorer notes (2026-11-23). Review scripts: `tmp/review/presacco2016/scripts/` (named per finding); outputs in
`tmp/review/presacco2016/explore/`. **User decision: MEG only; the EEG (BioSemi FFR to /da/ syllables) is not
adapted** (and not downloaded beyond the 7 zips fetched earlier: S01-03, S06, S07, S10, S12 `.zip`, all EEG).

## 1. Source
- DRUM (University of Maryland) item `79afc7aa-560d-442d-b201-ab63e7f1e69f`, hdl 1903/21184, DOI
  **10.13016/M2599Z52H**, title "EEG-MEG", 2018. Authors Presacco A, Simon JZ, Anderson S.
- Licence: **none stated** (no `dc.rights` in the item metadata; checked 2026-11-23). Open question.
- Papers (item `dc.description.uri`): Presacco, Simon, Anderson (2016a) "Evidence of degraded representation of
  speech in noise, in the aging midbrain and cortex", J Neurophysiol, doi:10.1152/jn.00372.2016 (not in
  `papers/`); and
  (2016b) "Effect of informational content of noise on speech representation in the aging midbrain and cortex",
  J Neurophysiol 116:2356, doi:10.1152/jn.00373.2016 (`data_campaign/papers/presacco2016.pdf` = 2016b). The
  hearing-impaired group is not in either paper (probably Presacco et al. 2019, PLoS One; not checked).
- No code shipped.
- Files (ORIGINAL bundle, 93 files, 116.6 GB): 46 EEG zips (`S01.zip`..`S35.zip`, `S01_HL.zip`..`S17_HL.zip`;
  BDF), 46 MEG zips (`S##_Younger_MEG.zip`, `S##_Older_Normal_Hearing_MEG.zip`,
  `S##_Older_Hearing_Impaired_MEG.zip`, 1.60-1.72 GB each, 77 GB in total) and `Stimuli.zip` (47 MB). The registry
  entry has `include: ["*_MEG.zip", "Stimuli.zip"]` (MEG only). Listing with sizes and md5:
  `tmp/review/presacco2016/drum_listing.json`.
- Download (2026-11-22/23): DRUM times out at the default 15 s read timeout (17 of 24 EEG zips failed on
  2026-11-22); with `max_workers=1, read_timeout=120` all 46 MEG zips came through (~4 min each); one (S02 HI)
  was cut by an HTTP 504 and fetched again. All 47 files: md5 = DRUM, `unzip -t` ok, 10 .mat per subject,
  extracted sizes = zip listing (`integrity.tsv`, `scripts/check_zips.sh`, `check_extracted.sh`).

## 2. Layout
- `S##_<group>_MEG/S##_<tag>.mat`, 10 files per subject, MATLAB v7.3 (HDF5; read with h5py). `tag` in Q_H,
  Q_L, P3_H, Zero_H, M3_H, M6_H, P3_L, Zero_L, M3_L, M6_L (P = plus, M = minus, number = SNR in dB; H = English
  background, L = Dutch background; Q = quiet; DRUM abstract).
- **File names differ in the hearing-impaired group**: `S##HL_M3H.mat` (S01, S02, S04-S07, S12),
  `S##HL_M3_H.mat` (S03, S08), `S##_HL_M3H.mat` (S13-S17). **S04 HI has `S04HL_M6L_II.mat` instead of
  `S04HL_M6L.mat`** (presumably a repeated recording; 3 normal epochs, triggers as usual; the only M6_L file of
  that subject, used). The adaptor matches each condition by its tag without underscores (`M3H`), allowing an
  `II` suffix.
- Each file has one struct `data_exported`: `eeg_data_aligned` float64 (3 repetitions, 192 channels, 60000
  samples) as h5py reads it (MATLAB 60000 x 192 x 3), gzip; `labels` = '1'..'192'; `sampling_frequency` 1000;
  `channels` 192; `samples` and `trial_duration` = length of the continuous recording the epochs were cut from
  (244-345 s, one recording per condition block); `chanlocs`, `eeg_data`, `events_trigger`, `events_type` all
  empty; `bad_channels` empty in the younger and older normal-hearing files, filled in the hearing-impaired files
  (section 5). So only the three 60 s epochs are shipped, not the continuous recordings.
- `Stimuli/Stimuli/High Context/` and `Low Context/`: 12 mono int16 wavs, 44.1 kHz, all exactly 60.000 s
  (2,646,000 samples): `Quiet_H, Plus_3_H, Zero_H, Minus_3_H, Minus_6_H, English_F` and the `_L` set with
  `Dutch_F`.

## 3. Stimulus <-> trial mapping (verified)
- Paper (2016b, "MEG: Stimuli and Recording"): attend a male talker (The Legend of Sleepy Hollow) mixed with a
  female talker (English: A Christmas Carol; Dutch: "Aljaska en de Canada-spoorweg") diotically, 1 min mixtures,
  quiet (two different segments), +3, 0, -3, -6 dB SNR; each condition 3 trials; 30 trials. Randomised order.
  ~70 dB SPL, E-A-RTONE 3A tubes with foam plugs, delivery equalised 40-3000 Hz.
- **The shipped "condition" wavs are the foreground alone, not the mixtures** (`mix_decomp.py`): least-squares
  fit of the background wav into each one gives gain ~0.01 (-38 to -40 dB) at any lag; their F0 is 97-120 Hz
  (male), English_F 172 Hz and Dutch_F 195 Hz (female; `wav_ident.py`). All 10 foreground wavs have the same RMS
  (1012.3), English_F 1007.8 and Dutch_F 1006.4: levels are normalised, the SNR is not in the files.
- **`Minus_6_H.wav` is byte-identical to `Quiet_H.wav`, and `Minus_6_L.wav` to `Quiet_L.wav`**
  (`wav_ident.py`, same sample md5). The paper describes 8 different noise segments plus 2 quiet ones; the
  shipped wavs have 6 different foregrounds. The MEG decides it: the -6 dB trials decode the shared wav at r
  0.35 / 0.39 vs <= 0.14 for every other foreground (S01, section 6, `decode_map.py`), so the -6 dB blocks really
  used the quiet segments as foreground. Not an upload error; the paper's "eight different segments" is wrong or
  refers to something else. (Upstream issue.)
- Background placement: the mixtures are not shipped, so where the 60 s background sits in each mixture is not
  given. In every noise condition the MEG tracks the English_F / Dutch_F envelope at lag ~0 (decoder trained on
  the foreground, foreground regressed out of the prediction, lag scan +-10 s; `bg_scan.py`,
  `explore/bg_scan.npz`, `figures/background_lag.png`): S01, S02 younger, S21 older NH, S01 HI x 8 noise
  conditions: peak at -10..+30 ms in 30 of 32 (r 0.12-0.33); S01 HI M6_L peaks at +180 ms (r 0.146 vs 0.120 at 0)
  and S01 HI Zero_L is weak (r 0.037 at 0, best 0.107 at +3.27 s, noise level). So each mixture = foreground +
  background from their starts, the same background file at every SNR (S01 HI Zero_L not confirmed).
  English_F / Dutch_F start with 1.3 s of silence.
- Mapping per file: 3 repetitions of one mixture (DRUM abstract; within-file MEG trial correlations 0.007-0.041
  vs ~0.000 across files, `trial_corr.py`). Onset trigger line per tag (section 6) confirms the file tag in every
  trial checked.
- Trial numbering (adaptor): conditions in the order Q_H, Q_L, P3_H, Zero_H, M3_H, M6_H, P3_L, Zero_L, M3_L,
  M6_L, 3 repetitions each (trials 1-30). Presentation order is unknown (not in the files; the mat-file times are
  export times, in tag order).

## 4. Speech features available
- Raw audio of every stream: foreground (attended) and background talker (unattended), 44.1 kHz. Not the played
  mixture (could be rebuilt as `fg + 10^(-SNR/20) * rms(fg)/rms(bg) * bg` if the authors' RMS convention were
  known; it is not: open question). No transcripts or annotations.
- DRUM: "The stimuli have been pre-processed as described in our publications ... The envelope needs to be
  extracted." (the delivery equalisation, presumably).

## 5. Neural data
- KIT 157-channel axial-gradiometer MEG (UMD), 3 reference magnetometers, 32 MISC lines; 1000 Hz.
- **Raw, not denoised**: every channel is an integer multiple of a per-channel step (ADC counts x calibration;
  `raw_or_not.py`), which any TSPCA/filtering would destroy. PSD (S01 Q_H, median over sensors): 60 Hz -22 dB
  relative to 30-55 Hz (online notch), falls above ~200 Hz (online low-pass, ~200 Hz as in the lab's other KIT
  datasets; not stated in the paper). The paper's TSPCA and 2-8 Hz / 1-8 Hz filtering were analysis steps, not
  applied to the shipped data.
- **Units: fT** (inferred). Steps are ~0.45 per count on every channel; idle 5 V MISC lines read 15006.2 =
  32767 counts x 0.458, i.e. the exporter applied the MEG calibration to every channel, with the KIT full scale
  at ~15 pT (brodbeck2022's dead MEG 056 sits at -1.5e-11 T, the same full scale). MEG noise ~2 fT/sqrt(Hz) at
  65-100 Hz and RMS ~90-180 fT (broadband) are plausible for KIT gradiometers in fT and impossible in any other
  unit. The adaptor multiplies by 1e-15 (T).
- Channels: 1-157 = MEG 001-157 (`mag`, coil `FIFFV_COIL_KIT_GRAD`), 158-160 = reference magnetometers
  (`ref_meg`, `FIFFV_COIL_KIT_REF_MAG`; ch 158 has 10x the variance of the others, environmental field), 161-192
  = MISC 001-032:
  - MISC 004 (ch 164): offset trigger line, MISC 007-016 (ch 167-176): onset trigger lines, one per condition
    (section 6). Active-low TTL (idle 15006 = 5 V, pulse ~0).
  - MISC 001-003, 005-006, 017, 019-029: constant; MISC 018, 030-032 (ch 178, 190-192): low-level noise (~12
    units, 155 distinct values), no audio content (envelope |r| < 0.07 at any lag +-2 s, `misc_audio.py`).
  - **No audio copy / stimtrack in the MEG.** MISC lines are dropped by the adaptor (as in brodbeck2022).
- No sensor positions, head shape, fiducials or device-to-head transform shipped (`chanlocs` empty). The
  standardised files have zero channel positions. (KIT-157 device geometry exists in brodbeck2022's FIF files of
  the same UMD system: open question whether to borrow it.)
- Bad channels: the hearing-impaired files list them in `bad_channels` as **0-based** indices: every HI file
  checked lists 55 and has MEG 056 (1-based) all zero; S04 HI lists [55, 61] and has MEG 056 and MEG 062 all zero
  (MEG 056 is also the dead channel of every brodbeck2022 subject on the same UMD system). So the listed channels
  were zeroed by the authors. The younger / normal-hearing files list none but also have zeroed channels (S03
  MEG 105). The adaptor marks as bad the union of the listed channels (+1) and all zero-variance MEG channels,
  per trial. Full list in section 7 from the survey.
- Subjects: 17 younger (S01-S17), 15 older normal-hearing (S21-S35), 14 older hearing-impaired
  (S01-S08, S12-S17 `_Older_Hearing_Impaired`). Subject numbers in the standardised data: younger 1-17, older
  normal-hearing 21-35, older hearing-impaired 101-117 (S01 HI = 101); original names in the sidecar
  (`participant`). Paper ages: younger 18-27, older 61-73 (normal hearing).

## 6. Alignment
- Triggers in each shipped epoch (`trig_misc.py`, `survey.py`): a 4-5 sample active-low pulse on the
  condition's onset line starting at **epoch index 1** (index 0 is still high), and the offset line (MISC 004)
  going low at index 59998 or 59999 (pulse truncated by the epoch end). Onset lines: Q_H 167, P3_H 168, Zero_H
  169, M3_H 170, M6_H 171, Q_L 172, P3_L 173, Zero_L 174, M3_L 175, M6_L 176. So the authors cut each epoch from
  one sample before the onset trigger, for 60000 samples.
- Hardware vs software: **unknown**. The paper (2016b) does not describe the presentation software for the MEG
  part (Presentation is named for the EEG part). The lines are recorded by the KIT system.
- **Adaptor: t = 0 at the onset-trigger edge** (epoch index 1; index 0 dropped), so each trial is 59,999
  samples. Stimuli are not cut. No offset correction; the tube delay (E-A-RTONE 3A, typically ~1 ms per 30 cm,
  length not given) is not compensated.
- **Check with the MEG, all 46 subjects** (`decode_map.py` via `decode_all.sh`, `figures.py`): backward
  decoder (157 sensors, 1-8 Hz, 100 Hz, 40 PCs, lags 0-500 ms, ridge), trained leave-one-condition-out on the
  other 9 conditions, prediction averaged over the 3 repetitions, correlated with every foreground wav and swept
  +-1 s in 10 ms steps. The assumed wav (or its byte-identical twin) gives the highest r at lag 0 in **459 of 460**
  subject x condition tests (the exception, S11 younger M6_H, decodes weakly overall: 0.13 for Minus_6_L vs 0.11
  for the assumed wav). Lag-sweep peak: **median 0 ms, IQR -10..+10 ms, all 460 within -50..+30 ms**; group means
  +0.5 (younger), +0.5 (older NH), +1.4 ms (older HI), SD ~14 ms; median r at lag 0 0.33. No onset error larger
  than ~10 ms at this resolution; the 30-250 Hz validation (section 9) puts a tighter bound on it.
- Drift: no drift correction applied (section 7).

## 7. Cross-subject duration check (all 46 subjects, 1380 trials; `survey.py`, `explore/survey.tsv`)
- Onset edge at epoch index 1 in **all 1380 trials**, on the onset line that matches the file tag in all 1380;
  pulse width 5 samples (1311), 4 (68), 6 (1).
- Offset-line edge - onset edge = **59,998 samples in 1085 trials, 59,997 in 294**, i.e. 2-3 ms short of the
  60.000 s wavs, in every subject and group alike (`figures/trigger_interval_per_subject.png`). One trial has no
  offset edge inside the epoch: S15 HI `S15_HL_M6H.mat` repetition 2 (offset later or missing; onset normal).
- Every stimulus is 60.000 s, so a constant trigger offset and a clock drift cannot be separated. If the offset
  trigger marks the end of the sound on the same timeline as the onset, the sound clock runs **-37 ppm** relative
  to the MEG (mean -2.21 ms per 60 s; 1 ms quantisation). If the offset trigger is simply sent ~2 ms before the
  end, there is no drift. Either way the effect is <= 2.2 ms at the end of a 60 s trial (< 0.2 cycle at 70 Hz).
  The trigger type is unknown, so the rule "hardware-derived drift correction on by default" does not settle
  it. **Not applied** (open question 5); `drift_ppm` left null in the sidecar.
- Continuous recordings per condition block were 219-373 s (`samples`), 3 x 60 s trials each.
- Zero (all-zero) MEG channels per subject (1-based; marked bad): younger S03 105, S08 62, S09 62, S12 62 157,
  S13 62, S16 56, S17 56; older NH S23 99 111 146, S28 62, S32 56, S33 1 2 56, S34 56, S35 56; older HI 56 in all
  14, plus S04 62, S06 62, S07 13 14 15 31 73 106 111, S15 13, S17 23 24 25 26 148. No other flat channels (< 5 % of
  the median SD). MISC lines carry no pulses other than the onset/offset lines.

## 8. Open questions (human checkpoint; recommended default in brackets)
1. Licence: none stated on DRUM. [include; note "no licence stated"; ask the authors via the user]
2. Stimuli: store foreground (attended) + background (unattended) as shipped, or also a rebuilt mixture?
   [as shipped; SNR in the sidecar; no rebuilt mixture (the RMS convention is unknown)]
3. Minus_6 = Quiet foreground: keep the shipped names (`Minus_6_H` is stored as its own stimulus, identical to
   `Quiet_H`, noted in the sidecar `identical_stimulus`). [yes]
4. Onset: trigger edge at epoch index 1, drop index 0. [yes]
5. Drift: trigger interval 2-3 ms shorter than 60 s. [no correction; document the estimate]
6. Sensor geometry: leave positions empty, or borrow the KIT-157 device geometry from brodbeck2022 (same UMD
   system, later recordings)? [leave empty; note]
7. MISC trigger lines: dropped (brodbeck2022 precedent); trigger facts are in the sidecar. [yes]
8. Condition labels: `quiet`, `english_snr+3dB` ... `dutch_snr-6dB`; both quiet segments are `quiet`
   (file tag in the sidecar). [yes]
9. Full standardisation (46 subjects, ~53 GB) was not run (tmp near its cap). [run when storage allows, after
   deleting the extracted copy or the zips]
10. Storage (171 GB in `tmp/review/presacco2016`): zips 79 GB (incl. 5.5 GB of EEG zips not needed), extracted
    `meg_x/` 73.5 GB, pilot `standardised/` 22 GB. The adaptor reads the extracted folders, so the zips (after
    the md5 check, done) or the 7 EEG zips can go. [user decides]

## 9. Adaptor and pilot (2026-11-23)
- Shared code with the lab's other KIT datasets (R-number subjects, wav loaders, epoch/continuous-raw helpers,
  bad-channel rules) in `datasets/simon_base/common.py` (2026-11-23; output unchanged).
- `adaptor.py` as described in sections 3-7: subjects younger 1-17, older NH 21-35, older HI 101-117; trials
  1-30 = conditions Q_H, Q_L, P3_H, Zero_H, M3_H, M6_H, P3_L, Zero_L, M3_L, M6_L x 3 repetitions; conditions
  `quiet`, `english_snr{+3,0,-3,-6}dB`, `dutch_snr{+3,0,-3,-6}dB`; channels MEG 001-157 (`mag`, KIT_GRAD) and
  MEG 158-160 (`ref_meg`), T, 1000 Hz, 59,999 samples from the onset edge; stimuli foreground (attended) +
  background (unattended) as 44.1 kHz float32. Sidecar: `onset_only`, trigger type unknown, participant,
  group, hearing, file, repetition, foreground, background, snr_db, trigger lines, identical_stimulus.
- Pilot: 20 subjects (younger 1-10, older NH 21-26, older HI 101, 103-105), 600 trials, 22 GB in
  `tmp/review/presacco2016/standardised/`; 0 errors. Round trip: standardised data = shipped values x 1e-15 to
  float32 precision. ~1.15 GB per subject, so all 46 would be ~53 GB (not run: storage, 2026-11-23).

## 10. Validation (pilot, 2026-11-23; `tmp/review/presacco2016/validation.json`, `validation.png`)
Basis: standardised data as stored, axial gradiometers (`--picks mag`, bads excluded), no denoising, no
re-referencing (MEG). Repo validator, tiers low, mlr, brainstem.
- **low (0.5-8 Hz forward): pass.** Mean r 0.035 (median 0.031), **20/20 subjects** above the circular-shift
  null, p_circ 0.020, p_mismatch 0.048. TRF GFP peaks ~50 and 125 ms. (Raw KIT forward r is low because it
  averages over all 157 sensors; brodbeck2022 gave 0.032 the same way.)
- **mlr (30-60 Hz, 18-45 ms): fail.** SNR 0.97, p 0.28, 2/20. The 30-60 Hz TRF peaks at ~60 ms, outside the
  window.
- **brainstem tier (30-250 Hz, MEG window 28-45 ms): pass.** SNR 1.75, p 0.0099, **19/20 subjects**. The TRF
  is flat at negative lags and has a sharp peak at ~38-40 ms (consistent with the ~40 ms cortical high-gamma TRF
  of Kulasingham et al. 2020, NeuroImage, same lab and system), so this measures high-frequency cortical
  alignment (PLAN section 5), and the absence of anything before 0 ms supports the trigger onset to within a few
  ms.
- Per condition group (`scripts/validate_subset.py`, low + brainstem; `validation/cond_{quiet,english,dutch}/`):

  | condition (trials/subject) | low r | low sig | low TRF peak | 30-250 SNR | p | sig |
  |---|---|---|---|---|---|---|
  | quiet (6) | 0.038 | 16/20 | 47 ms | 1.26 | 0.010 | 12/20 |
  | english, 4 SNRs (12) | 0.029 | 14/20 | 141 ms | 1.39 | 0.010 | 16/20 |
  | dutch, 4 SNRs (12) | 0.032 | 18/20 | 125 ms | 1.37 | 0.010 | 14/20 |

  The 30-250 Hz peak sits at ~38-40 ms in each group. The low-frequency GFP peak is earlier in quiet (47 ms) than
  with a competing talker (125-141 ms).
- Validation tier: `low` by the validator's ordering (mlr fails); the 30-250 Hz tier passes as well.
- Figures: `validation.png` (pooled), `validation/cond_{quiet,english,dutch}/validation.png`,
  `figures/trigger_interval_per_subject.png`, `figures/decoder_lag_per_subject.png`,
  `figures/decoder_mapping.png`, `figures/background_lag.png`.

## Data size (recorded)
46 participants (17 younger, 15 older NH, 14 older HI), 30 trials x 59.999 s = **30.0 min each (all
identical)**, **23.0 h in total**. Per condition per participant: quiet 6 min (two segments x 3), each masker x
SNR 3 min (English and Dutch 12 min each). Each 60 s mixture is repeated 3 times, so the unique audio is 6
foreground minutes + 2 background minutes. Not yet in `tmp/review/data_size.md` (shared file).

## Upstream issues
- `Minus_6_H.wav` = `Quiet_H.wav` and `Minus_6_L.wav` = `Quiet_L.wav` byte for byte; the paper says 8
  different noise segments. The MEG confirms the -6 dB blocks used these foregrounds.
- The "condition" wavs are the foreground only; the mixtures and the background placement are not documented.
- No licence on the DRUM item; no channel names or sensor geometry in the MEG files; `bad_channels` empty in the
  younger / older NH files while some channels are zeroed, and 0-based in the HI files.
- Three file-naming schemes in the HI group; S04 HI `S04HL_M6L_II.mat`.
- S15 HI `S15_HL_M6H.mat` repetition 2: no offset trigger inside the epoch.
