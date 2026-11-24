# holtze2021: two competing talkers, own name in the ignored stream (OpenNeuro ds003516 + ds004015)

**v2 (2026-11-24, user decision): combined dataset.** Scalp EEG from ds003516 (sections 1-11, unchanged; the scalp
files are byte-identical to v1) plus the concurrent cEEGrid (around-ear) recordings from OpenNeuro ds004015, which
also brings the cEEGrid of 15 Jaeger et al. (2020) sessions (the recordings behind jaeger2025). One file per montage
and trial. New: sections 12-16 and the grade section. Evidence for v2: `tmp/review/holtze2021_v2/` (`agent_log.md`,
`figures/`), scripts in `tmp/review/scripts/holtze2021_v2/`.

Explorer notes (2026-11-22). Evidence scripts and plots: `/data_storage/gu08wuvu/datasets/tmp/review/holtze2021/`
(`scripts/`, `plots/`); that folder is temporary, so the numbers that matter are copied here.

## 1. Source
- OpenNeuro ds003516 v1.1.3, "EEG: Attended Speaker Paradigm (Own Name in Ignored Stream)",
  doi:10.18112/openneuro.ds003516.v1.1.3, licence CC0 (dataset_description.json).
- Paper: Holtze B, Jaeger M, Debener S, Adiloglu K, Mirkovic B (2021). Are they calling my name? Attention capture
  is reflected in the neural tracking of attended and ignored speech. Front. Neurosci. 15:643705,
  doi:10.3389/fnins.2021.643705.
- Code: https://github.com/BjoernHoltze/EEGCompetingSpeakerNameDistraction (Zenodo concept DOI
  10.5281/zenodo.4541039, v1.2; MIT-style licence). MATLAB/EEGLAB. Relevant: `extract_envelope.m` (how the
  shipped envelopes were made), `bjh_06_create_struct_seg_xcorr.m` (envelope sample 1 = `StartTrigger`, 600 s per
  block), `bjh_05_add_control_events.m` / `bjh_06_create_struct_seg_xcorr_name.m` (which name table goes with which
  attended side).
- Narratives previously used in Mirkovic et al. (2016) and Jaeger et al. (2020) (paper, "Narratives").

## 2. Layout
- `sub-0NN/eeg/sub-0NN_task-AttendedSpeakerParadigmOwnName_eeg.{set,fdt}`: **the raw data** (EEGLAB, one
  continuous file per subject, 25 subjects), plus `_channels.tsv`, `_electrodes.tsv`, `_coordsystem.json`,
  `_eeg.json`, `_events.tsv/json`.
- `sourcedata/sub-0NN_ica_tmp_prob_2_kurt_2.{set,fdt}` and `sub-0NN_ica_weights_and_badcomps.mat` (21 included
  subjects only): **derivatives**, not raw. The `.set` is the authors' ICA training copy (2-40 Hz filtered, cut into
  1-s epochs, 2683 epochs for sub-001 after `pop_jointprob` rejection; `bjh_02_ica.m`); the `.mat` holds the ICA
  weights and the hand-picked artefact components (`badcomps`, e.g. sub-001: 1 7 9 3 5) for their
  `run_mode='reproduce'`. Not needed by the adaptor.
- `stimuli/`: `sig{1,2}_{1..5}.mat` (envelopes, see 4), `name_time.mat`, `control_time.mat`, `name_quest.mat`,
  `control_envelope_order.mat`. **No audio** (see 4).
- `participants.tsv`: `attended_ch` (left/right), `cond_order` (OBOB/BOBO), `incl` (incl/excl). Note:
  `participants.json` describes level `incl` as "participants were excluded for analysis" (upstream typo).

## 3. Stimulus <-> trial mapping (verified)
- Paradigm (paper, README): 5 blocks of ~10 min. Two German audiobook narratives (two male talkers), one spatialised
  front-left (-30 deg) and one front-right (+30 deg) with HRIRs; the participant attends the same side throughout.
  Block 1: equal loudness ("omni"), no names. Blocks 2-5 alternate omni (equal loudness; "higher name
  intelligibility") and beam (steering beamformer attenuates the ignored talker, frequency dependent; "lower name
  intelligibility"), order OBOB or BOBO. In blocks 2-5 the participant's first name (TTS voice "Markus", 379-597 ms)
  replaces a sentence-final verb 10 times in the ignored narrative (20 ms fade-out, 700 ms mute, 20 ms fade-in, name
  added at RMS of the preceding 2 s).
- **Every subject hears the same 5 block pairs in the same order**: block b = `sig1_b` + `sig2_b`. Trial = block.
  `sig1` = story 1 = **left**, `sig2` = story 2 = **right**: the code's `attended_ch = 1` rows are exactly the
  `participants.tsv` `left` rows for all 25 subjects.
- Name tables: `name_time_c2` (s from `StartTrigger`, rows = blocks 2-5) when attending left (names in story 2),
  `name_time_c1` when attending right (code). Checked for all 25 subjects (`scripts/check_names.py`): the 40
  `omni`/`beam` events sit at `StartTrigger` + the table of the tsv side (error 0..1 ms, i.e. rounding; the other
  table is off by up to 67 s), block 1 has none, and the event labels per block reproduce `cond_order` in all 25.
  Consequence: the name events are **derived from the tables**, they are not independent timing markers.
- Attended side checked from the EEG, two independent signals:
  1. Leave-one-block-out backward decoders for `sig1` and `sig2` (avg ref, 1-15 Hz, 100 Hz, lags 0-300 ms;
     `scripts/decoder.py`, `plots/decoder_summary.png`): right-attenders r(right) 0.06-0.22 vs r(left) 0.02-0.07;
     left-attenders r(left) 0.05-0.12 vs r(right) 0.05-0.12. The decoder agrees with the tsv in 21/25; the four
     disagreements (002, 006, 013, 018) are all tsv=left and small (|dr| <= 0.036), and the right talker is tracked
     better overall (bias), so the decoder alone cannot overturn them.
  2. Name-onset ERP at both candidate tables (`scripts/name_erp.py`, `plots/name_erp_side_check.png`): the tsv-side
     table gives a clear N1 and/or P3 (500-1000 ms) in most subjects, including 002, 006 (N1 at ~100 ms, 7 uV GFP)
     and 013 (P3, 9 uV); the other table gives nothing comparable. sub-018 is weak in both tests.
  Conclusion: **no evidence of a swapped side; keep `participants.tsv`**. sub-018 is unconfirmed (no contradiction).

## 4. Speech features available
- **Audio: not in v1.1.3.** CHANGES: 1.1.2 "removed audio files", 1.1.3 "deleted audio files" (2022-10-04). The
  older snapshot **v1.1.1 (and 1.1.0) lists `stimuli/Block_{1..5}_32k.wav`** (76.9-79.7 MB each) and the S3 objects
  are still served (HEAD 200 on 2026-11-22, e.g.
  `https://s3.amazonaws.com/openneuro.org/ds003516/stimuli/Block_1_32k.wav?versionId=GFk_9_XctuWhugh.rhQLyb40Eui6p_fk`;
  URLs for all five via the OpenNeuro GraphQL `snapshot(datasetId:"ds003516", tag:"1.1.1")`). Their sizes match
  2-channel 16-bit 32 kHz files of exactly the envelope durations ((size - 44)/4/32000 = 600.510, 611.540, 622.563,
  609.814, 610.625 s vs envelopes 600.510, 611.540, 622.564, 609.816, 610.626 s), so they are most likely the two
  dry narratives as left/right channels (inferred; not downloaded). The authors removed them on purpose (reason not
  stated; probably audiobook rights). **User decision 2026-11-22: download v1.1.1 audio** (registry entry
  `holtze2021_audio`, into `<download>/stimuli_v1.1.1/`; local use only, never redistributed).
- **What the two wav channels are** (`scripts/audio_channels.py`, `scripts/audio_check2.py`, 2026-11-22): 32 kHz,
  stereo int16, n = 19216310, 19569274, 19922006, 19514050, 19539990 samples (600.510-622.563 s); ceil(n/64) equals
  the envelope length in every block. **Channel 0 = story 1 = `sig1` = left, channel 1 = story 2 = `sig2` = right,
  two separate dry talkers:**
  - the authors' recipe applied to each channel reproduces the shipped envelope at lag 0: r = 0.974-0.976 (ch 0 vs
    `sig1`) and 0.954-0.959 (ch 1 vs `sig2`) with a Hamming window, **0.993 / 0.985** (block 2) with EEGLAB
    `firws`' default Blackman window; cross pairs r = 0.005-0.020 (max over +-500 ms 0.02-0.03). Amplitude scale
    sig/ours ~0.78 (level differs from what the authors read; shape matches);
  - between channels: waveform r = -0.001..0.001, Hilbert-envelope r = 0.011-0.026, RMS 0.089-0.103 (L) vs
    0.110-0.127 (R). A binaural HRIR/beamformer mix would put both talkers in both ears; this is not one;
  - **no names inserted, no mute**: in the 1 s after each name onset of the ignored story (tables, block 2) the
    longest run of 10-ms frames below -50 dB re channel RMS is 0-110 ms (story 1) and 10-370 ms (story 2), i.e.
    natural pauses, not the 700 ms mute. RMS in 0.05-0.65 s after the name onsets is ~half the RMS before
    (sentence-final verb then pause), while the other story at the same times is unchanged. So the wavs are the
    dry narratives before spatialisation, beamforming and name insertion; the shipped envelopes were made from
    them.
- Shipped instead: `sig{s}_{b}.mat`, one column, float64, **500 Hz**, same length for s = 1, 2. Made with
  `extract_envelope.m`: |hilbert(audio at 32 kHz)| -> `firws` low-pass "15 Hz" of **order 4** (barely filters) ->
  first difference -> half-wave rectification -> `resample` to 500 Hz. So it is an **onset envelope (rectified
  derivative)**, not a plain envelope; it carries small negative values (min about -0.002, max 0.03-0.06) from the
  resampling. Sample 1 = block onset.
- The envelopes are of the **unprocessed narratives**: no HRIR, no beamformer attenuation, and the ignored stream
  still contains the replaced verbs (envelope at the name times is not muted: median max |env| 0.006-0.011 in the
  0.6 s after the name onset). The name audio (per participant, a first name) is not shared; only its onset
  (events/tables) and length (`name_quest.len`, ms) are. So around each of the 40 name events (~0.74 s each) the
  ignored-stream envelope does not describe what was played.
- No transcripts, no word/phoneme annotations. `control_time.mat`: 10 control nouns per block (blocks 2-5) per story.
  `name_quest.mat`: per subject retrospective name-detection counts (both, beam, omni) and name length.

## 5. Neural data
- EEG only. BrainAmp (Brain Products), equidistant 64-channel Easycap layout of which **49 recorded**: 47 scalp
  (`E01`..`E60` subset) + `E19`, `E20` = EOG below each eye (MNE reads them as `eog`). 5 occipital and 10 around-ear
  positions were not recorded (cEEGrid recorded concurrently, not shared). Identical channel list in all 25 files.
- **500 Hz** (nominal); recording band-pass 0.0159-250 Hz, AC coupled, 100 nV resolution.
- Units: EEGLAB data in uV (`channels.tsv` microV); MNE `read_raw_eeglab` scales to V. Plausible amplitudes
  (sub-001: median |x| 60 uV, sample-difference SD 13 uV).
- Reference: **nose tip**; ground fronto-polar (paper; `EEG.ref = 'nose'`). The authors re-reference to the average
  for envelope tracking.
- Positions: template only (`elec_64ch_original.elp` spherical coordinates; `electrodes.tsv` unit sphere, "Other"
  coordinate system). No head-shape digitisation.
- No stimtrack, aux or audio channel.
- Recording via **Lab Streaming Layer** (inferred: `EEG.etc.info` is an XDF stream header, `BrainAmpSeries`,
  host `recorder3`, `nominal_srate` 500, `effective_srate` 500.0036-500.0159 = **+7 to +32 ppm vs the recording
  PC clock**, per subject in `lsl_info.txt`). Only one XDF stream header is kept per subject (span ~1000 s of the
  ~3250 s), so the files were assembled from several recordings.
- Every file is 3250.014 s and has the same structure (all 25): 60 s calibration (`Calib_Start`, rest; content not
  documented), 40 s beep period (`Beep`, 20 `beep` events, same relative times in every subject = table-derived),
  then 5 x 630.002 s blocks starting at `StartTrigger` = 100.106, 730.108, 1360.110, 1990.112, 2620.114 s.
  `boundary` events at 0.101, 60.103, 100.105, 730.107, ... s: the authors cut the recordings to these fixed
  windows and concatenated them.
- **The real splice points are ~101 ms before each `boundary`/`StartTrigger` annotation**, not at it: the data
  discontinuity sits at -100/-102 ms in every subject where it is detectable (`scripts/discont.py`; e.g. sub-006:
  all six splices after the file start at -102/-100 ms). The authors cut at the raw marker and then moved the
  events by the paper's "constant delay of 102 ms between the EEG data and the event marker stream". Consequence
  for the adaptor: the EEG from `StartTrigger` - 0.1 s to `StartTrigger` + 629.9 s belongs to the block; anything
  earlier is another recording.
- Exclusions (paper): 4 of 25 excluded: two failed the normal-hearing criterion, one had asymmetric thresholds, one
  moved excessively. `incl` = excl for sub-004, 007, 010, 016; which reason applies to whom is unknown.

## 6. Alignment
- Markers: one real marker per block, `StartTrigger` (block onset). All other events (`beep`, `omni`, `beam`,
  `Calib_End`) are placed from tables relative to `Beep`/`StartTrigger`. No end-of-block marker.
- Trigger type: **software, LSL marker stream** (inferred from the XDF header and the paper's "event marker
  stream"; the source program is not documented; audio ran in openMHA on an Intel NUC with an RME Fireface UCX,
  EEG on a separate recorder PC). The constant 102 ms marker delay was **already applied** in the shipped events
  (documented in the paper, Data Analysis; confirmed by the splice offset above). Checks that `StartTrigger` = sound
  onset:
  - grand-average forward TRF (attended onset envelope, avg ref, 1-15 Hz; `scripts/forward_trf.py`,
    `plots/forward_trf_grand_gfp.png`): GFP peaks at **50 and 160 ms**, the paper reports 50 and 156 ms with the
    same convention (the authors' code epochs from `StartTrigger` with no further shift);
  - beep-locked GFP (`plots/beep_erp_gfp.png`): N1 at ~90-110 ms in most subjects;
  - name-locked ERP: N1 at ~100 ms where visible (sub-006).
  Absolute accuracy of these checks is about +-10-20 ms; no stimtrack exists to do better.
- Proposed alignment: trial = block b, onset = `StartTrigger` b (no extra shift), stimuli `sig1_b` (left) and
  `sig2_b` (right) both starting at the onset; EEG needed = 600.5-622.6 s, available 629.9 s, so every block fits.
  `alignment_method = sw_trigger`, `trigger_type = software` (LSL markers; delay corrected by the authors).
- Drift: **no correction proposed** (section 7).

## 7. Cross-subject duration / drift / jitter
- No end markers and blocks were cut to a fixed 630.002 s, so trigger-derived durations carry no information (the
  StartTrigger spacing is 630.002 s in every subject by construction). Drift and jitter were estimated from the EEG.
- Drift (`scripts/decoder.py` + `scripts/drift_robust.py`, `plots/drift_robust.png`,
  `plots/window_lag_per_subject.png`): lag of the leave-one-block-out reconstruction of the attended envelope in
  100-s windows (50 % overlap), Theil-Sen of lag vs time within block, block offsets removed, windows with r > 0.08
  and |lag| < 60 ms (1025 of 1375). Pooled **-5.6 ppm [95 % CI -9.2, -1.9]** (all windows: -4.3 [-8.0, -0.6]);
  per condition omni -6.8 [-11.4, -2.4], beam -3.3 [-9.3, 2.0]; per subject median -5.5 ppm, IQR [-14.8, 3.9],
  individual CIs +-15-50 ppm, no visible clusters. Over a 610-s block this is ~3 ms, below the window-lag noise
  (residual SD 12 ms per window) and below the block-onset jitter. Per-subject drift is not resolvable; LSL's
  amp-vs-PC rate (+7..+32 ppm) says nothing about the audio clock.
- Block-onset jitter: per-block lag of the reconstruction relative to the subject mean has SD 9.7 ms; the
  estimation noise (from first- vs second-half lags within blocks) is ~6.8 ms, giving **~7 ms SD onset jitter**
  (10 best subjects: 8.0 ms total, 4.3 ms noise -> ~6.7 ms). No block position is systematically offset (mean
  relative lag by block -1.6..+2.0 ms). Consistent with software markers; limits high-frequency analyses.
- Sidecar suggestion: `drift_ppm = null` (not corrected; pooled estimate -5.6 ppm in the notes), `jitter_ms = 7`.

## 8. Data size
- 25 participants (21 included by the authors), 5 blocks each, stimulus durations 600.51 + 611.54 + 622.56 +
  609.81 + 610.63 = 3055.05 s = **0.849 h per participant** (identical for all), **21.2 h total** (17.8 h for the
  21 included). Simultaneous streams counted once. Recorded EEG per block covers the full stimulus.
- Per condition per participant: block 1 omni without names 0.167 h; omni 0.339 h (OBOB: blocks 2, 4) or 0.343 h
  (BOBO: blocks 3, 5); beam the other 0.343 / 0.339 h.
- Not yet added to `tmp/review/data_size.csv` (that script reads standardised output).

## 9. Suggested adaptor shape (for the standardiser)
- Subjects 1-25; read `sub-0NN/eeg/*_eeg.set` with `mne.io.read_raw_eeglab`; ignore `sourcedata/`.
- Trials: the 5 `StartTrigger` annotations (in order = block 1..5). Condition per block from
  `'O' + cond_order`: `omni-noname` (block 1), `omni`, `beam`; plus attended side from `participants.tsv`
  (e.g. `attend-left-omni`). Keep `incl` in subject metadata.
- Stimuli per trial: `story1_block{b}` (left) and `story2_block{b}` (right), feature `onset_envelope` (the shipped
  500 Hz rectified-derivative envelope), with attended/ignored role per subject; name onsets (`omni`/`beam` events,
  relative to the trial) as trial annotations.
- **As implemented (2026-11-22):** `story{s}_block{b}` with features `audio` (wav channel s-1, 32 kHz, float32
  = int16/32768) and `onset_envelope_authors` (`sig{s}_{b}`, 500 Hz, as shipped); `is_attended` from the
  subject's side. Condition `attend-{left|right}-{omni-noname|omni|beam}`. EEG = StartTrigger sample to
  + envelope length (600.51-622.56 s). Annotations `own_name` (onset from the `omni`/`beam` events, duration =
  `name_quest.len`; relative to the trial start = `onset - raw.first_time`); the adaptor checks 0 names in block
  1, 10 per block 2-5 and labels = `cond_order`. Trial metadata (JSON in `raw.info["description"]`): block, side,
  cond_order, `incl`, sex, age, StartTrigger time, name length, drift_ppm null, jitter_ms 7. `info["highpass"]`
  set to the recording's 0.0159 Hz.
- Neural rate: keep 500 Hz (native <= 1024 Hz, never upsample). Reference: nose (keep). `E19`, `E20` as `eog`.
- Skip calibration and beep periods (no speech; the beep sound is not shared).

## 10. Open questions (recommended default in bold)
1. Audio: fetch `Block_{1..5}_32k.wav` from the v1.1.1 snapshot (still served by OpenNeuro's S3) or not? The authors
   deleted them in 2022, presumably for rights reasons, while the dataset is CC0. **Decided (user, 2026-11-22):
   download v1.1.1 (`holtze2021_audio`), use locally, never redistribute.** Channel order checked (section 4).
2. Which subjects: **default: all 25, with `incl` (authors' exclusion) in the metadata**; alternative: the 21
   included only. Two of the excluded did not meet the hearing criterion, one had asymmetric hearing, one moved a
   lot (who is who is unknown).
3. Drift: **default: no correction** (pooled -5.6 ppm, ~3 ms per block, no per-subject evidence).
4. Onset: **default: `StartTrigger` as shipped, no extra shift** (102 ms already applied; TRF peaks reproduce the
   paper). DNN offset vs accou2023: -7.9 ms, no correction (section 11).
5. Stimulus feature: the only speech feature is the onset envelope of the dry narratives at 500 Hz, which ignores
   HRIR, beamformer attenuation and the name insertions. **Default: ship it as `onset_envelope` and say so in the
   README**; mark the 40 name intervals (~0.74 s, from the events and `name_quest.len`) as annotations rather than
   editing the envelope.
6. sub-018's attended side is unconfirmed by the EEG (no contradiction either). **Default: trust participants.tsv.**
7. Calibration (60 s) content is undocumented (likely rest). **Default: skip.**

## 11. Validation, DNN offset and coherence (2026-11-22)
Scripts: `tmp/review/scripts/holtze2021_{validate,backward,summary}.py`; summary in `validation.json` (this folder).
Evidence in `/data_storage/gu08wuvu/datasets/tmp/review/holtze2021/{validation,dnn_offsets}/` and
`tmp/review/coherence_batch/{128,native}/holtze2021_{attended,ignored}.{json,png}` (temporary; numbers copied here).
- Setup: average reference over the 47 scalp channels (E19/E20 excluded), feature = the v1.1.1 `audio` (Hilbert
  envelope at 64 Hz for low / backward; half-wave rectified audio at 500 Hz for mlr / brainstem, brainstem band
  clipped to 30-225 Hz).
- **Tier: low** (all 25 and the 21 included); `validation_tier="low"` set in the adaptor for all trials.
  Per subject (attended): 21 low, 3 mlr (sub-007, 018, 023; ~ the false-positive rate), sub-001 none.
- Forward (repo validator): attended median r 0.033 (mean 0.034), 24/25 above both nulls; ignored 0.018, 20/25.
  Per condition (attended): omni 0.030 (20/25), beam 0.029 (21/25); low tier not run for block 1 alone.
  MLR SNR 1.03, p 0.18, 3/25; brainstem SNR 1.00, p 0.32, 1/25. Ignored stream, 21 included: MLR p 0.050 (4/21),
  formally a pass, not taken as evidence. Validator jitter/drift (SD 66 ms, 12 +- 55 ppm) is noise.
- Backward (leave-one-block-out, nulls: 50 circular shifts, 40 mismatched envelopes): attended median r 0.153,
  ignored 0.073, 25/25 above both nulls for each; attended > ignored in 25/25 (Wilcoxon p 6e-6). Authors' onset
  envelope: 0.110 (our Hilbert envelope better in 20/25).
- Lag sweep (+-1 s, 15.6 ms steps, parabolic peak): attended +0.8 ms [0.1, 1.5], ignored +0.6 ms; per condition
  attended omni-noname -0.3, omni -0.4, beam +2.5 ms; ignored omni-noname -6.6, omni -5.7, **beam +13.0 ms
  [9.8, 16.6]**. Stream-specific within the same trials, so beamformer delay or a later response to the
  attenuated talker, not a marker error.
- Attention decoding (median accuracy, all blocks): 10 s 0.82, 30 s 0.94, 60 s 0.98; 25/25 above chance in each.
  Side check: attended > ignored in 25/25; smallest margins sub-014 (dr 0.005, 2/5 blocks, AAD-30 0.74) and
  sub-006 (dr 0.007, 2/5 blocks, AAD-30 0.87). sub-018 (unconfirmed in section 3) is clear here (dr 0.075, 5/5).
- TRF (attended, 15.6 ms steps): central P1 39 ms, N1 109 ms; GFP peaks 47 and 109 ms (paper: 50 / 156 ms GFP with
  the onset envelope; validator TRF peak with the authors' envelope 172 ms).
- The authors' 4 excluded subjects look normal: forward 4/4 (median r 0.037), backward r 0.08-0.21, AAD-30
  0.72-1.00 (sub-010 lowest).
- Why mlr/brainstem fail: ~7 ms software-marker jitter, 500 Hz, dry audio (no HRIR or beamformer, no names).
  fuglsang2018 is comparable on all tiers (low, mean r 0.033; 30-60 and 30-250 Hz not passed).
- **DNN match-mismatch offset vs accou2023** (blocks 2-5, 100 trials; accou2023 itself +0.6 ms): all -7.9 ms
  [-10.4, -5.6], omni -5.7 [-8.6, -3.0], beam -9.3 [-12.8, -6.7]; per subject +4.9 to -27.9 ms (sub-010 most
  negative). Within ~10 ms of accou2023: **no correction**.
- **Coherence** (EEG-envelope, average reference, 5 s Hann / 4 s overlap, one global-shift surrogate; 500 Hz
  native, 128 Hz within 0.05): ratio to surrogate attended / ignored 0.2-1 Hz 9.2 / 5.7, 1-4 Hz 3.3 / 3.6,
  4-8 Hz 4.7 / 3.7, 8-15 Hz 2.2 / 1.6 (8-10 Hz 3.9 / 2.3, 10-12 Hz 2.2 / 1.7, 12-14 Hz 1.25 / 1.36),
  15-30 Hz 1.1 / 1.2, 30-250 Hz 1.0-1.1. Above the surrogate to ~10-12 Hz; attended > ignored at 0.2-1 and 4-8 Hz.

## 12. Second source: OpenNeuro ds004015 (cEEGrid), added 2026-11-24
- **"Attended speaker paradigm (cEEGrid data)"**, OpenNeuro ds004015 v1.0.2 (2022-10-04),
  doi:10.18112/openneuro.ds004015.v1.0.2, **CC0**. Registry `holtze2021_ceegrid`; the adaptor expects it in
  `<download>/ds004015` (or `ceegrid_dir=`). Paper: Holtze B, Rosenkranz M, Jaeger M, Debener S, Mirkovic B (2022).
  Ear-EEG measures of auditory attention to continuous speech. Front. Neurosci. 16:869426,
  doi:10.3389/fnins.2022.869426. Code: https://github.com/BjoernHoltze/EarEEGAuditoryAttentionMeasures (v1.1,
  doi:10.5281/zenodo.6379903; analysis only, no BIDS conversion; epochs from `StartTrigger` with no shift).
- Pooled cEEGrid of two studies, 36 participants, one continuous EEGLAB file per participant (whole session:
  calibration (Holtze), 20-beep period, all blocks and breaks; one `boundary` where two XDF files were merged,
  between blocks 1 and 2). Not cut into fixed windows like ds003516. 6.48 GB.
  - sub-016..036 = **holtze2021** `bjh_s01, 02, 03, 05, 06, 08, 09, 11..15, 17..25` (`sourcedata/subj_info.mat`,
    same order as `participants.tsv`): = ds003516 sub-0NN for bjh_sNN. Attended side, sex, age and condition order
    match in **21/21**. The 4 missing (bjh_s04, 07, 10, 16) are the authors' excluded subjects (`incl` = excl), and
    the cross-correlation of the two files (section 13) confirms every pairing (peak z 5-880, all at -30..-70 ms).
  - sub-001..015 = **Jaeger et al. (2020)** `maj_s07, 08, 09, 10, 12, 14, 15, 18, 20, 22, 23, 24, 25, 26, 27`
    (Front. Neurosci. 14:603, doi:10.3389/fnins.2020.00603): the recordings behind the results-only jaeger2025 entry
    (attended side matches its code in 15/15). Their 94-channel BrainAmp cap was never shared. Free-field
    loudspeakers at -45/+45 deg, 1.1 m, 70 dB SPL, both talkers at equal level, six 10-min blocks separated by ~5 min
    breaks; no names inserted (Jaeger 2020).
- `participants.tsv`: `attended_ch`, `gender`, `age`, `orig_study`, `first_bl/second_bl/third_bl` (the 3 blocks the
  2022 paper analysed; the files hold all blocks), `con_order` (Holtze only).
- Events: `StartTrigger` per block, `Beep`/`beep` (20), `Calib_Start/End` (Holtze), `omni`/`beam` name onsets
  (Holtze, 40, table-derived as in ds003516: onset - StartTrigger = the same tables). Markers past the end of the data
  (52 ms after the last sample: blocks whose EEG was not saved) are dropped by MNE: **sub-002 (maj_s08) blocks 1-4,
  sub-005/006 (maj_s12/14) blocks 1-3, sub-013 (maj_s23) blocks 1-5**; every other Jaeger session has 6 blocks.
  The last usable block of each lies fully inside its file.
- **Jaeger block 6 has no stimulus** (no envelope, no audio in any version): skipped. Jaeger blocks 1-5 used
  holtze2021's five block pairs: the paper says "the same audio books were used in both studies", the ds004015 64-Hz
  envelopes `Mirkovic2016_{s}_{b}` are shared by both halves, and a cEEGrid backward decoder (leave-one-block-out)
  reconstructs block k's attended story best among the 5 blocks' stories in **68/70 Jaeger blocks** (mean r on the
  diagonal 0.052-0.065, off-diagonal <= 0.008; `figures/ceegrid_raw_timing.png`).
- **Audio:** v1.0.0/1.0.1 shipped `stimuli/Stream_{s}_{b}_fs32k.wav` (mono, 32 kHz; removed in v1.0.2). Downloaded
  (registry `holtze2021_ceegrid_audio`) and compared: each is **sample-identical** to channel s-1 of holtze2021's
  v1.1.1 `Block_{b}_32k.wav` (all 10). The shipped 64 Hz envelopes match wav channel s-1 (r 0.94-0.95; cross pairs
  <= 0.03). So both halves use holtze2021's existing stimuli; nothing new is needed.
- Sidecar error: `eeg.json` says BrainAmp and copies the cap's filter settings. The cEEGrid was a **SMARTING
  (mBrainTrain) 24-channel Bluetooth amplifier** (paper: "connected to a 24-channel mobile amplifier (SMARTING ...)
  which transmitted the data via Bluetooth"; the XDF stream header kept in each `.set`, `EEG.etc.info`, says
  `name EEG, source_id SMARTING, channel_count 18`, while ds003516's is `BrainAmpSeries`, 64 channels). Same host
  (`recorder3`) and same XDF file as the scalp (first timestamps 20 ms apart in bjh_s01).

## 13. cEEGrid alignment (2026-11-24)
- **What the shipped markers contain.** The 2022 paper: "To account for the constant delay between the onset
  markers ... and the corresponding EEG, we presented 20 beep tones"; the cEEGrid was shifted so that its beep N1
  matched the cap's (whose delay came from a timing test), giving **70 ms (Holtze) and 54 ms (Jaeger)**. Their
  analysis code applies no shift, so the shift is already in ds004015's events. Consistent with that, the
  cEEGrid beep-ERP GFP peaks at **108 ms in both halves** with the shipped `beep` markers
  (`scripts/holtze2021_v2/ceegrid_raw_check.py`).
- **Hardware check against the concurrent scalp file** (`scalp_vs_ceegrid.py`, all 21 Holtze sessions, 105 blocks):
  per block, the ds003516 scalp block (StartTrigger - 0.05 s to + 629 s) is cross-correlated with the cEEGrid at the
  ds004015 StartTrigger + the same offset: sum over all 49 x 18 channel pairs of the squared normalised
  cross-correlation (1-40 Hz), +-3 s, plus the same in 60-s windows (+-60 ms around the block peak).
  Shared artefacts (blinks, muscle, movement) give sharp peaks: z 5-880 (median ~150).
  - **The cEEGrid is 37 ms early relative to the scalp**: the scalp sample at its StartTrigger appears in the cEEGrid
    at the ds004015 StartTrigger **-37.0 ms** (median over blocks of the median 60-s window lag; IQR -39.0..-34.9,
    range -29.7..-69.5). Between subjects SD 5.5 ms; within subject between blocks SD 2.5 ms; precision per block
    ~0.8 ms (SD of the window lags). **bjh_s06**: -39 ms in block 1, then -58.5, -62.4, -66.1, -69.5 ms (a step at
    the XDF merge, then ~3.5 ms per block). bjh_s08 block 4: the whole-block peak failed (-1799 ms, z 5.5,
    artefact-dominated); every 60-s window gives -36..-40 ms (z 34-203); the window median (-37.7 ms) is used.
    Figures: `figures/scalp_vs_ceegrid_summary.png`, `figures/scalp_vs_ceegrid_bjh<NN>.png` (per subject: window
    lags vs time per block, peak z).
  - Interpretation: with the cap delay of 102 ms and the authors' 70 ms in the markers, the SMARTING stamps the same
    instant ~69 ms earlier than the BrainAmp (70 - 37 - 102), and the true cEEGrid delay (~33 ms after the raw
    marker) is ~37 ms shorter than the authors' N1-matched 70 ms: the around-ear N1 (reference R04b) peaks ~37 ms
    later than the cap N1, so matching the peaks misaligned the montages. Matching shared artefacts measures the
    montages' relative timing directly.
  - **Drift cEEGrid vs scalp: +4.0 ppm** (Theil-Sen of the window lags, IQR 2.9-4.8) and **+3.8 ppm** from the 50 Hz
    line-noise phase difference (blocks with line coherence > 0.5, IQR 3.4-4.1); LSL headers: 500.0093 vs
    500.0067 Hz effective (+5.3 ppm, bjh_s01). Separate amplifier clocks, as expected. Over a block the cEEGrid
    moves ~2.5 ms against the scalp; with the onset taken as the block's median window lag (~block centre) the error
    is <= 1.3 ms at the block edges. **Not corrected** (below the ~7 ms marker jitter; the scalp's own drift vs the
    audio is not corrected either).
- **Holtze half: onset = ds004015 StartTrigger + this block's lag** (`ceegrid_onsets.csv`, written by
  `scalp_vs_ceegrid_summary.py`; columns: ids, StartTriggers of both files, lag, whole-block lag, peak z, window SD,
  drifts). This carries the scalp onset (validated, medium) over to the cEEGrid clock, i.e. both files of a trial
  share one stimulus timeline. Derived from the two recordings, not from a brain response: on by default (hardware
  rule).
- **Jaeger half: onset = ds004015 StartTrigger + median(Holtze lags) + 2 ms = -35.0 ms.** Reasoning: the same
  SMARTING and BrainAmp setup and recorder; markers = raw + 54 ms (paper); cap delay 88 ms (jaeger2025 code,
  "BrainAmp delay between marker and sound onset"); so onset = raw + 88 + (SMARTING - BrainAmp stamp difference) =
  StartTrigger + L_Holtze + (88 - 54) - (102 - 70). Inputs are the authors' stated constants and the Holtze hardware
  lag; no brain-based estimate of ours. Uncertainty per session ~ +-5.5 ms (between-subject SD of the Holtze lags),
  plus XDF-merge steps like bjh_s06's (20 ms) that cannot be seen without a scalp file: `jitter_ms` 9 for the Jaeger
  trials (7 for the Holtze half). The beep N1 at the shipped markers (108 ms in both halves) supports the same
  marker treatment in both halves.
- Relative checks (shipped markers, `ceegrid_raw_check.py`): leave-one-block-out backward decoder lag sweep peaks at
  -0.2 ms [-3.5, 3.0] (Holtze, attended) and +1.3 ms [-1.0, 4.6] (Jaeger). These only show that the blocks are
  consistent with each other (a constant offset is absorbed by the decoder); no block is off.
- Adaptor option `ceegrid_onset="shipped"` uses ds004015's markers unchanged (both halves; the authors' N1-based
  shift).
- **User decision 2026-11-24:** the default above is approved: cEEGrid onset = StartTrigger + the block's lag vs the
  concurrent scalp file (Holtze, median -37 ms), Jaeger = median Holtze lag + 2 ms (-35.0 ms);
  `ceegrid_onset="shipped"` stays an option; the +4 ppm cEEGrid-vs-scalp drift is documented, not corrected.
- The match-mismatch DNN (accou2023) cannot check the cEEGrid: it needs the 64-channel 10-20 montage.

## 14. cEEGrid channels
- 18 channels `L01..L08, L04a, L04b, R01..R08` minus `R04a` (ground) and `R04b` (reference), as shipped (MNE reads
  them as `eeg`); uV in the files -> V. 500 Hz (no resampling). Original reference R04b kept.
- Large DC offsets (|x| ~ 9 mV mean per channel; SMARTING is DC-coupled; the sidecar's 0.0159 Hz high-pass is the
  cap's): `info["highpass"]` left at 0. 1-40 Hz SD 4-10 uV per channel (median per subject 4.1-9.6 uV).
- Positions: template, from the EEGLAB file (= `electrodes.tsv`, "Other"/EEGLAB unit sphere).
- **Bads** (`ceegrid_bads.py`, `figures/ceegrid_channel_sd.png`): per block, flat (1-40 Hz SD < 0.5 uV) or SD > 5x the
  subject's median: sub-002 R05 (flat, all blocks), sub-010 R04 + R05 (flat, all), sub-018 R05 (b1, b3), R07 (b2-b4),
  sub-020 R05 (b1), sub-028 R07 + L02 (b3), sub-029 R01 (b5), sub-031 L03 (all), sub-032 R05 + R04 + L04b + L03 (b3),
  L02 (b5), sub-033 R01 (b2-b4): 36 channel-blocks (ds004015 ids; `GRID_BADS` in the adaptor). sub-013 (maj_s23)
  blocks 4-5 reach 3.6-4.5 mV on all channels at once with normal SD (8-15 uV): a common-mode event through the
  reference, not bad channels; kept.

## 15. v2 structure, ids and size
- **One file per montage and trial** (PLAN.md montage rule): `ns_type` **`eeg`** (scalp, ds003516; unchanged) and
  **`around-ear-eeg`** (cEEGrid, ds004015; name chosen so that in-ear files can get their own type). Same trial
  numbers, conditions and stimuli for both files of a Holtze trial; both aligned to the same stimulus timeline
  (section 13).
- **Subject ids:** Holtze subjects keep their ds003516 ids (1..25 = bjh_s01..s25). Jaeger subjects are
  **100 + maj number** (107..127 = maj_s07..s27), so they cannot collide with the Holtze ids and stay traceable to
  jaeger2025's numbering. Every cEEGrid file's provenance has `ds004015_id`, `ds003516_id` (Holtze), `original_id`
  (`bjh_sNN`/`maj_sNN`), `original_study`, `presentation`, `blocks_analysed_2022`.
- Map (also in the README):

| subject | original id | ds003516 | ds004015 | files |
|---|---|---|---|---|
| 1, 2, 3, 5, 6, 8, 9, 11-15, 17-25 | bjh_sNN | sub-0NN | sub-016 .. sub-036 (in this order) | scalp + cEEGrid |
| 4, 7, 10, 16 | bjh_sNN | sub-0NN | - | scalp only (authors' excluded) |
| 107, 108, 109, 110, 112, 114, 115, 118, 120, 122, 123, 124, 125, 126, 127 | maj_sNN | - | sub-001 .. sub-015 | cEEGrid only |

- Session 1 for everyone (one session per participant in both studies). Conditions: Holtze as before
  (`attend-<side>-<omni-noname|omni|beam>`); Jaeger **`attend-<side>-freefield`** (loudspeakers +-45 deg, equal
  level, no names); the setup is also in the provenance (`presentation`).
- Records: 125 scalp + 105 Holtze cEEGrid + 70 Jaeger cEEGrid = 300 files. Size (from one written trial each):
  scalp 58 MB, cEEGrid 22 MB per trial, stimuli 0.4 GB: ~12 GB.
- **Hours** (stimulus time): scalp 21.2 h (25 subjects); cEEGrid Holtze 17.8 h (21 x 3055 s, concurrent with the
  scalp), Jaeger **11.9 h** (12 x 5 blocks + 4 + 3 + 3 = 70 blocks, 42774 s; 0.79 h per participant, 0.51-0.85 h);
  cEEGrid total 29.7 h; distinct recording time 33.1 h (36 + 4 = 40 participants).

## 16. cEEGrid validation (2026-11-24)
Default cEEGrid onsets (section 13), 500 Hz, union of a subject's bads excluded, average reference over the cEEGrid
channels. Scripts `scripts/holtze2021_v2/{validate.py, backward.py, validation_summary.py}`, results
`tmp/review/holtze2021_v2/validation/` (`summary.json`, `run.log`).
- **Low tier (repo validator, forward 0.5-8 Hz), attended:** Holtze 21/21 subjects significant against both nulls,
  median r 0.025 (pass); Jaeger 14/15, median r 0.029 (pass). By condition (Holtze): omni 14/21 (r 0.019), beam
  15/21 (r 0.023). **Ignored:** Holtze 7/21 (r 0.006), Jaeger 8/15 (r 0.009); both pass the group test.
- **Backward (LOBO decoder, 0-250 ms):** attended r median 0.047 (Holtze) / 0.051 (Jaeger), every subject above both
  nulls (21/21, 15/15); ignored 0.024 / 0.022 (13/21, 9/15). **Attended > ignored: Holtze 20/21, Jaeger 15/15**
  (Wilcoxon p < 1e-4 both). AAD median accuracy 10/30/60 s: Holtze 0.62/0.73/0.78 (20/21 above chance at each),
  Jaeger 0.61/0.68/0.74 (14, 12, 13 of 15).
- Lag sweep peaks: Holtze -0.7 ms [-2.6, 1.0], Jaeger +1.6 ms [-0.1, 3.9]. Relative only (the decoder absorbs a
  constant offset); cEEGrid forward TRF GFP has no clear peak (flat 0-400 ms), so the validation **cannot check the
  absolute cEEGrid onset**; that rests on section 13.
- Scalp (byte-identical to v1; v1 forward tiers stand), backward re-run on the v2 files: attended r median 0.153,
  ignored 0.072, attended > ignored 25/25, AAD-30 median 0.94, lag sweep peak 0 ms.
- Figures: `figures/r-attended-vs-r-ignored_around-ear-eeg.png`, `figures/lag_sweep_per_subject_around-ear-eeg.png`.
- Attended < ignored in one cEEGrid subject (13 = bjh_s13: 0.035 vs 0.048); its scalp file confirms the side
  (0.165 vs 0.128). 30-60 / 30-250 Hz tiers not run for the cEEGrid (they fail for the scalp).
- **Tier: low** for both halves; `GRID_VALIDATION_TIER = "low"` in the adaptor (the 175 cEEGrid files were
  re-written with it after validation, provenance only).

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides); scalp accepted by the user 2026-11-24, cEEGrid (v2) accepted
2026-11-24. **medium** for both montages.
- Scalp: software LSL markers with the authors' 102 ms delay (paper; confirmed by splices); ~7 ms jitter; DNN
  -7.9 ms, no correction; drift brain-based -5.6 ppm, not applied; low tier.
- cEEGrid: carried onto the scalp timeline by cross-correlating the concurrent recordings (-37 ms, IQR 4 ms over
  105 blocks; section 13), Jaeger half by the same lag plus the papers' stated constants (-35.0 ms); low tier in
  both halves (section 16).

Evidence line: "scalp: software markers with the authors' 102 ms delay, validated (low tier, DNN -7.9 ms, no
correction); cEEGrid: carried onto the scalp timeline by cross-correlating the concurrent recordings (-37 ms, IQR
4 ms), Jaeger by the same lag plus the paper's constants."
