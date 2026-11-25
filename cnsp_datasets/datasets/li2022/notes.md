# li2022: ESAA Mandarin two-talker auditory attention EEG

Scratch: `R/li2022/` (`R = /data_storage/gu08wuvu/datasets/tmp/review`); scripts `R/scripts/li2022/`; figures
`R/li2022/figures/`; progress log `R/li2022/agent_log.md`.

## 1. Source
- Zenodo 7795585 (CC-BY-4.0, published 2022-09-21), "ESAA: an EEG-Speech auditory attention detection database".
  Registry entry `li2022`. 23 files, 13.6 GB: `S1.zip`..`S17.zip`, `clean.zip`, `hrtf.zip`, `preprocess.zip`,
  `cnn_baseline.zip`, `readme.txt`.
- Paper: P. Li, E. Su, J. Li, S. Cai, L. Xie, H. Li (2022), "ESAA: An EEG-speech auditory attention detection
  database", O-COCOSDA 2022, doi:10.1109/O-COCOSDA202257103.2022.9997944 (`data_campaign/papers/li2022.pdf`).
- Copy used here: the vault node's archive on woody (`csnhr:/home/woody/iwpm/iwpm104h/zenodo/li2022/7795585/`,
  complete, 23 files + `record.json` + `MD5SUMS`), rsynced 2026-11-24; md5 of all 23 files OK here, and sizes and
  checksums equal `record.json`. That woody copy is the vault-side copy (not duplicated to `/home/vault`). Zips kept in
  `R/li2022/download/`, extracted per zip into `R/li2022/extracted/<zip>/`.
- Authors' code (`preprocess.zip`, `cnn_baseline.zip`; read, not run): `db/SCUT.py` holds the trial table
  (`scut_label`, `scut_suf_order`, `scut_remove_trail`), `preproc/preprocess.py` the loader.

## 2. Layout
- `S<k>.zip` -> `S<k>/S<k>.mat` (S8.zip: `S8.mat` at the top level). S4, S9, S12, S13, S14 are split into
  `S<k>_1.mat` and `S<k>_2.mat` (recording restarted); S17 has only `S17_1.mat` (complete). MATLAB v5, one
  `(n, 1)` double vector per channel, plus `Markers` (struct: ChannelNumber, Description, Points, Position, Type),
  `t` (0..n-1), `Channels` (spherical Phi/Theta), `ChannelCount` 65, `MarkerCount`, `SampleRate` 1000,
  `SegmentCount` 1. A BrainVision Analyzer export (field names, 'New Segment').
- `clean.zip` -> `clean/Trail<k>.wav` and `hrtf.zip` -> `Trail<k>.wav` (top level), k = 1..32: 44.1 kHz, 16-bit,
  stereo, 55.7-93.0 s (38.38 min in total). `__MACOSX/` junk in every zip. The repo downloader extracts every zip
  into the download root, so the adaptor finds files by walking the tree (works for both layouts).

## 3. Stimulus <-> trial mapping
- 17 subjects (20 recorded; 3 excluded by the authors for < 80% correct answers). 32 trials each, one per wav:
  every subject heard all 32 wavs once.
- **The S/E marker names give the wav number**: `trail<k>D`, `trail<k>S`, `trail<k>E` with k = wav. Presentation
  order = marker order: S1-S8 heard Trail1..32 in order; S9-S17 heard them in the authors' `scut_suf_order`
  (24, 8, 32, 31, 7, ...; their first marker is `trail24`). Checked independently: (E - S) matches the duration of
  wav k (never another wav) for all 542 complete trials (`figures/markers.csv`).
- Wav channels: clean channel 0 is the left talker, channel 1 the right one: the HRTF left ear correlates with c0
  (envelope r 0.69-0.91) more than with c1 in all 32 wavs, and vice versa (`figures/wavs.csv`). The HRTF wav is the
  binaural mix as played (insert phones, +-90 deg, paper 2.2).
- Talkers: per wav one male (median F0 108-130 Hz) and one female (197-225 Hz); the side of each alternates.
- Attended stream: the authors' `scut_label[k-1] = [direction, speaker]` per wav (direction 0 = left = c0;
  speaker 0 = male; both match the F0 and HRTF checks for all 32 wavs). **For S9-S17 both labels are flipped**
  (`_reverse_label`): the second group attended the other talker of the same wav. Verified on the EEG with the
  label-free DNN: the labelled attended talker scores higher than the ignored one in every subject (21-31 of 32
  trials; Wilcoxon p 0.036 to 1e-9; strongest in S9-S17), section 6.
- Behavioural answers are not shipped. The authors drop trials with poor answers (`scut_remove_trail`, 1-based
  EEG trial positions: S1 1,2,3,9,14,24,31; S2 9,29; S3 1,9,19; S4 31; S5 14; S6 7,9,10,13,15,29; S7 9,25; S8 25-32;
  S9 15; S10 12,15,16; S11 12,17,30; S13 27,29; S14 9,14,26,27; S16 1). Kept here (all data), listed in the
  README.
- **Authors' code bugs** (upstream issues): (a) the loader reads files `sorted()` and takes every third marker as a
  trial start: for S13 this puts `S13_1.mat` (positions 7-32) before `S13_2.mat` (positions 1-6), so S13's
  labels are shifted by 6 trials in their pipeline; (b) it cuts a fixed 55 s from the S marker and assumes
  `fs = 1000` (correct, unlike the paper).
- Missing data: S13 Trail15 (position 6) ends 6.5 s before the sound (recording stopped; no E marker); S14
  Trail22 (position 26) has 16.1 s of 85.8 s. Both kept; `eeg_truncated_s` in the provenance.
- Data size: 38.38 min of stimulus per subject; 17 subjects = 10.87 h (paper: 12.7 h for 20); recorded 10.85 h
  (the two truncated trials).

## 4. Speech features
- Raw audio only (no envelopes, transcripts or alignments). Stimuli stored per trial: attended clean talker,
  ignored clean talker (mono, `Trail<k>_left` / `Trail<k>_right`), and the as-played binaural HRTF mix
  (`Trail<k>_hrtf`, stereo, not attended). File order in the flat filename: audio01 = attended, audio02 = HRTF mix,
  audio03 = ignored (the sink sorts the non-attended by name).

## 5. Neural data
- BrainAmp (paper), 64 Easycap 10-10 channels + ECG; **1000 Hz** (`SampleRate`, `t` steps of 1, durations match
  the wavs; the paper's 8192 Hz is wrong, the authors' own code uses 1000). Kept at 1000 Hz, not resampled.
- Units: microvolts as MATLAB doubles (1-40 Hz SD 4-35 uV; ECG ~530 uV). Scaled to volts.
- Reference: **shipped re-referenced to the common average of the 64 EEG channels** (they sum to 0 within 1e-12;
  ECG excluded); FCz is a channel (presumably the recovered online reference, not documented). The original
  reference is not available; kept as shipped.
- Spectrum falls steeply above ~300 Hz (hardware anti-alias filter); 50 Hz line noise.
- No EOG, no stimtrack/audio channel (the only non-EEG channel is ECG, which carries ECG).
- Bad channels (screen `R/li2022/analysis/bads_scan.json`; 1-40 Hz SD > 4x or < 0.25x the median, or neighbour
  r < 0.3): S4 P4 and PO4 (neighbour r 0.18-0.23, 3.3-3.8x SD). Fp1/Fp2/Fpz/AF8 flags in other subjects are blinks
  (neighbour r >= 0.84) and stay good.
- Positions: `standard_1020` template (the files' Phi/Theta are template spherical coordinates).

## 6. Alignment
### Markers (why "no reliable triggers")
- Per trial `trial<k>D`, `trial<k>S`, `trial<k>E` (Type STIM); S = start, E = end (readme); D 2.0 s (S1) or 3.0 s
  (others) before S, meaning undocumented (probably the direction cue). All 97 markers are present in every subject
  (except the two truncated trials' E).
- **Every marker position is 1 mod 20**: markers land on 20 ms BrainVision blocks, so they are software markers
  (e.g. sent to Recorder over the network), not TTL triggers at sample resolution. S - D varies 1980-2120 /
  2980-3140 ms in 20 ms steps.
- (E - S) - wav duration is -20..+60 ms (mean +17, SD 19 ms, on the 20 ms grid), in every subject, independent of
  trial length (Theil-Sen slope 0): per-marker jitter ~10-20 ms, no drift visible at this resolution
  (`figures/markers_duration_error.png`, `figures/markers.csv`).
- Nothing in the release or paper documents the playback-to-marker latency, and there is no audio channel.

### Brain-based evidence: the sound starts ~0.216 s after the S marker
- **Wide forward TRF** (0.5-8 Hz, lags -2..+3 s re S, `scripts/li2022/lagscan.py`): every subject shows the attended
  response as a fronto-central positivity at +0.30..0.37 s and negativity at +0.45..0.5 s after S; mismatched
  envelopes give nothing (`figures/trf_wide_frontocentral.png`). Late for an envelope TRF. A LOTO backward decoder
  (0-250 ms) peaks at shift ~0 for 15/17 subjects, but it absorbs offsets inside its own window, so it cannot
  measure this (`figures/decoder_shift_scan.png`). Per-trial cross-correlation is too noisy for single trials
  (`figures/xcorr_per_trial.png`).
- **DNN match-mismatch scan** (accou2023 classifier fs128_1020-64_broadband; EEG from the 128 Hz cache, spec EEG
  and stimulus steps; 5 s windows, 1 s hop; d = -2..+2 s; attended, ignored and two mismatched wavs as null;
  `scripts/li2022/dnn_scan.py`, `dnn_analyse.py`, `dnn_blocks.py`; results `R/li2022/analysis/dnn/`):
  - population (17 subjects, 544 trials): **d = +0.216 s (95% CI 0.210-0.219, subject bootstrap)**; subject median
    0.217 s. The ignored talker, an independent stimulus, gives +0.213 s. Nulls flat.
  - per subject: 15/17 at 0.186-0.231 s with tight CIs; S4 0.43 and S6 0.37 s are side lobes (below).
    `figures/dnn_scan_per_subject.png`.
  - per 8-trial block: 0.17-0.24 s except S4 `S4_1` (0.43), S6 blocks 1/3/4 (~0.37), S8 block 2 and S2 block 1
    (~0.36), all with CIs reaching ~0.21 s (`figures/dnn_offset_per_block.png`, `analysis/dnn/dnn_blocks.csv`). The
    forward TRFs of these blocks align with the 13-subject reference TRF within +-23 ms (`figures/trf_outlier_blocks.png`):
    they are the DNN's secondary lobe (~0.15 s after the main peak), not latency changes. **One constant offset
    for all subjects and blocks.**
  - single trials: 78/544 have p < 0.01 against the null trials (null rate 1%); their d: median 0.210 s, robust SD
    27 ms (estimation noise included); weak correlation with the marker duration error (r 0.15). Per-trial onsets
    are not resolvable; `figures/dnn_per_trial.png`, `analysis/dnn/dnn_trials.csv`.
  - drift: DNN on early (< 20 s) vs late (40-75 s) windows, pooled: 0.2176 vs 0.2150 s, -54 ppm (2.5 ms over 47 s,
    within noise). Not corrected.
  - reference: on the same classifier, fuglsang2018 (two talkers, HRTF, verified triggers) gives -1.4 ms and
    weissbart2019 +3.4 ms, so a two-talker HRTF design does not by itself shift d. Mandarin datasets have shown
    unexplained DNN offsets of tens of ms (pkueeg2025), so +-~50 ms of the 0.216 s is not assured.
- Interpretation: the playback software starts the sound ~0.22 s after it sends the S marker (output buffer /
  scheduling), plus marker jitter of ~10-20 ms. With the correction the TRF peaks move to ~+0.1 / +0.25 s.

### Audio audit (2026-11-24; user asked: are all clean wavs dry, is clean TrailK = HRTF TrailK?)
- **All 32 clean wavs are dry** (two isolated talkers): inter-channel coherence 100-4000 Hz 0.000-0.002 (HRTF wavs
  0.26-0.37), max waveform xcorr within +-1 ms 0.002-0.013 (HRTF 0.35-0.51), envelope r between channels
  -0.07..0.10 (HRTF 0.65-0.73), level difference within +-0.7 dB, spectral tilt -26.5..-29.7 dB/oct with no outlier
  (|z| < 3); no clean channel equals or is a delayed copy of an HRTF ear (waveform r 0.43-0.67).
  `R/li2022/figures/audio_channel_diagnostics.png`, `audio_channel_diagnostics.csv` (`scripts/li2022/audio_check.py`).
- **Transfer functions** clean talker -> HRTF ear (`audio_transfer_functions.png`, `scripts/li2022/audio_tf.py`): the
  same filter in every file (RMS deviation from the median 1.9-3.6 dB, no outlier), i.e. each HRTF wav is its clean
  wav through one fixed HRTF per side; ipsilateral group delay 33-45 samples, contralateral 58-91 (ITD ~0.7 ms; the
  32 vs 67 sample lags in `wavs.csv` are ipsi vs contra peaks). The HRTF path also band-limits to ~0.3-4 kHz
  (paper: "band-limited at 4 kHz"); the clean wavs are not band-limited.
- **Pairing**: 64 x 64 envelope similarity (each clean talker vs each HRTF ear, max xcorr over +-1 s;
  `audio_similarity_matrix.png`, `audio_similarity.npz`): for every clean TrailK the best HRTF file is TrailK
  (min margin over the best other file 0.69), at lag 0; c0 dominates the left ear and c1 the right ear in all 32;
  clean and HRTF durations equal for every K. Only Trail16/17 share a duration (72.6 s) but do not match each other.
  No duplicates (max envelope r between different clean talker channels 0.18). No mapping change needed.
- **What was played**: the HRTF wavs (paper 2.2: "After head-related transfer function filtering, two auditory streams
  were played 90 deg to the left ... and right ... via a pair of insert phones"). DNN scan with HRTF stimuli
  (`scripts/li2022/dnn_scan_hrtf.py`; stopped at 13 subjects / 396 trials on request): clean attended d = 0.214 s
  [0.206, 0.219], HRTF mix 0.202 s [0.197, 0.207] (higher z: 7.0 vs 5.3), HRTF attended-side ear 0.204 s; mismatched
  HRTF mix flat. HRTF - clean = -12 ms [-15, -8]: within the stated uncertainty, so the 0.216 s onset (clean
  attended talker, all 17 subjects) is kept. `audio_dnn_clean_vs_hrtf.png`.

### Applied (user decision 2026-11-24)
- Adaptor default `onset="dnn"`: onset = S + 0.216 s (`alignment_method` `dnn`); `onset="marker"` = S.
- No drift correction (none measurable). Insert phones ER4SR (no tube delay); HRTF filter delay ~0.7-1.6 ms (c0 vs
  left ear) not corrected.

### Grade
- **poor**: the onset is estimated from the neural data (DNN, constant 0.216 s); the markers are software with
  ~10-20 ms jitter (~13 ms per marker).

## 7. Validation (full, 2026-11-24)
All 17 subjects, 544 trials, default `onset="dnn"` (`R/li2022/standardised/`, 11 GB), validator tiers low, mlr,
brainstem, average reference (64 EEG channels); `R/li2022/validation.json`, `validate.log`, figure
`R/li2022/validation.png` (script `scripts/li2022/validate_full.sh`).
- **low: pass.** mean r 0.0310 (median 0.0304), p_circ 0.020, p_mismatch 0.048, 15/17 subjects significant (S1 r
  0.007 p 0.25, S13 r 0.011 p 0.12 not; both also failed in the pilot). TRF GFP peaks 0.156 s and ~0.25 s; a small
  shoulder above the null at -0.02..0 s is the 0.5-8 Hz smoothing of the onset lobe plus ~13 ms marker jitter, not
  a separate negative-lag response. Validator per-trial offsets are noise (SD 191 ms, 34 at the edge; single trials
  are too short, as in the DNN per-trial scan); drift median 23 ppm (SE 512), none.
- **mlr: fail** (SNR 1.02, p 0.22, 3/17 nominal); **brainstem: fail** (0.97, p 0.74, 0/17). Validation tier `low`.
- **Attended vs ignored** (`scripts/li2022/attended_ignored.py`; ignored = the other clean talker, not the HRTF mix):
  ignored low tier mean r 0.0198 (also passes, 14/17 significant, as expected for a two-talker mix). Attended -
  ignored r > 0 in 14/17 subjects (S8, S13, S16 slightly negative, -0.002..-0.004), Wilcoxon p = 6.6e-4;
  `R/li2022/r-attended-vs-r-ignored.png`, `validation_ignored.json`, `attended_ignored.log`. Confirms the labels
  (including the S9-S17 flip: S9-S17 differences +0.005..+0.037 except S13, S16).

### Pilot (2026-11-24)
Pilot: S1, S4, S7, S10, S13, S16 (both groups; S4 bads; S13 split + truncated), all 32 trials each, standardised with
both onsets (`R/li2022/pilot_{dnn,marker}/`), validator tiers low, mlr, brainstem, average reference (64 ch).

| onset | low: mean r | p_circ / p_mismatch | subj. sig. | TRF peak | mlr | brainstem |
|---|---|---|---|---|---|---|
| dnn (S + 0.216 s) | 0.0224 | 0.020 / 0.048 (pass) | 4/6 (not S1, S13) | 0.156 s | fail (SNR 1.02, p 0.20) | fail (0.98, p 0.50) |
| marker (S) | 0.0205 | 0.020 / 0.048 (pass) | 4/6 | 0.359 s | "pass" (SNR 1.08, p 0.04, 1/6) | fail (0.96, p 0.73) |

- With the marker onset the 0.5-8 Hz TRF peaks late (GFP ~0.2 and ~0.36 s, the later part cut by the 0.5 s
  window); with the DNN onset at ~0.15 and ~0.27 s (`pilot_dnn/validation.png`, `pilot_marker/validation.png`).
- The marker-mode mlr "pass" is chance: the 30-60 Hz TRF stays inside the null band, and with a 0.216 s offset a
  real MLR would lie outside the +-0.1 s HF lag window. No MLR / ABR is expected with ~10-20 ms marker jitter (and
  only 1-2 h per subject); validation tier `low`.
- Attended vs ignored (0.5-8 Hz forward model, dnn pilot): attended > ignored in 4/6 subjects (differences
  +0.001..+0.014; S13, S16 slightly negative; Wilcoxon p 0.31; `pilot_dnn/r-attended-vs-r-ignored.png`). The DNN
  contrast over all 17 subjects (section 3) is the stronger label check.
- Offsets stored in `alignment/dnn_offsets.csv` (per subject, block and file) and `alignment/dnn_summary.json`.

## 8. Decisions (user, 2026-11-24)
1. The 0.216 s brain-based onset is applied by default (`onset="dnn"`, grade poor); `onset="marker"` keeps the
   shipped timing.
2. The trials the authors dropped for poor comprehension answers are kept (listed in the README).
3. The two truncated trials are kept, flagged (`eeg_truncated_s`).

## Upstream issues
- Paper: 8192 Hz sample rate; the files are 1000 Hz.
- Authors' loader: `sorted()` file order puts `S13_1.mat` before `S13_2.mat` (S13 labels shifted by 6 trials).
- Shipped EEG is average-referenced (not documented).

## Restructure 2026-11-25 (not yet re-validated on data)
- Adaptor subclasses BaseAdaptor; onset checked with choice(). Download walked in sorted order (directories and files;
  S<k>_1.mat before S<k>_2.mat); two copies of one Trail<k>.wav (clean or HRTF) raise; a trial-start marker found
  twice for one subject raises (was: the later file in walk order won). Clean talkers still read as the left (0) /
  right (1) channel of the clean wav, now through iohelpers.read_wav(channel=...) (float32, unchanged values;
  synthetic test). Bads via iohelpers.mark_bads (strict).
