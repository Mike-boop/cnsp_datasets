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
  the foreground, foreground regressed out of the prediction, lag scan +-10 s; peaks +0..+30 ms, r 0.14-0.31 for
  S01, S02; `bg_scan.py`, `explore/bg_scan_S01-03.npz`). So each mixture = foreground + background from their
  starts, the same background file at every SNR. English_F / Dutch_F start with 1.3 s of silence.
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
- **Check with the MEG** (S01; backward decoder, leave-one-condition-out, `decode_map.py`): peak lag of the
  reconstruction vs the assumed wav -20..+10 ms in all 10 conditions (10 ms resolution), r 0.27-0.43. No sign of
  an onset error larger than ~10-20 ms.
- Drift: trigger interval (offset edge - onset edge) = 59,997 or 59,998 samples against 60.000 s wavs, i.e. the
  offset trigger comes 2-3 ms early per minute (~-33 to -50 ppm if it marks the sound end; 1 ms resolution; the
  offset pulse is truncated, its start is not). Distribution over all subjects in section 7. **No drift correction
  applied** (pending the user: unknown trigger type, ~2-3 ms over a 60 s trial).

## 7. Cross-subject duration check
- (filled in from `explore/survey.tsv` once all subjects are surveyed)

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

## Upstream issues
- `Minus_6_H.wav` = `Quiet_H.wav` and `Minus_6_L.wav` = `Quiet_L.wav` byte for byte; the paper says 8
  different noise segments. The MEG confirms the -6 dB blocks used these foregrounds.
- The "condition" wavs are the foreground only; the mixtures and the background placement are not documented.
- No licence on the DRUM item; no channel names or sensor geometry in the MEG files; `bad_channels` empty while
  some channels are zeroed.
