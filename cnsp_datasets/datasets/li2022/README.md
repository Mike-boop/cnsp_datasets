# li2022: ESAA, Mandarin two-talker auditory attention (EEG)

EEG of 17 listeners (S1-S17) attending one of two simultaneous Mandarin stories, a male and a female professional
narrator, HRTF-filtered to 90 deg left and right and played over insert phones (Etymotic ER4SR, 60 dBA). 32 trials
of 55.7-93.0 s per listener; every listener hears all 32 stimulus files once and answers comprehension questions
after each trial.

- **Source:** Zenodo record 7795585 (registry entry `li2022`): `S1.zip`..`S17.zip` (one MATLAB file per subject,
  two for S4, S9, S12, S13, S14), `clean.zip` and `hrtf.zip` (32 stimulus wavs each), the authors' code
  (`preprocess.zip`, `cnn_baseline.zip`) and a readme; 13.6 GB.
- **Licence: CC BY 4.0.**
- **Paper:** Li P, Su E, Li J, Cai S, Xie L, Li H (2022). ESAA: An EEG-speech auditory attention detection database.
  O-COCOSDA 2022. doi:10.1109/O-COCOSDA202257103.2022.9997944. Twenty listeners were recorded; the authors excluded
  three (< 80% correct answers), and the release holds the other 17.
- **Code (authors):** loader and CNN baseline (read, not used; see Caveats).

## Size
**17 participants x 0.640 h = 10.87 h** (from the stimuli; every participant heard all 32 files, 38.38 min).
Recorded EEG is 10.85 h: two trials are truncated (Caveats). Conditions by attended side: `competing-fL-hrtf` and
`competing-fR-hrtf`, 16 trials each per participant (5.43 h each). The standardised output is 11 GB (544 trials).

## What is provided
- **EEG:** BrainAmp, 64 Easycap 10-10 channels + ECG at **1000 Hz** (native; the paper's 8192 Hz is wrong), in V.
  - **Channels:** 64 scalp channels (`eeg`, including FCz) and `ECG` (`ecg`). No EOG, no mastoid electrodes beyond
    TP9/TP10, no stimulus channel.
  - **Reference:** as shipped, **the common average of the 64 EEG channels** (the channels sum to zero; not
    documented). The online reference is not available.
  - **Positions:** template positions (`standard_1020`).
  - **Bad channels:** S4 P4 and PO4 (`info['bads']`). `raw.pick("eeg")` keeps bads; exclude them yourself.
    Frontal channels carry blinks in several subjects.
- **Stimuli** per trial (44.1 kHz, as shipped):
  - the attended talker, `Trail<k>_left` or `Trail<k>_right` (mono; the dry `clean` wav channel of that side), flagged
    `is_attended`;
  - the ignored talker (the other channel);
  - `Trail<k>_hrtf`: the binaural mix that was played (stereo, left/right ear), not attended.

  In the flat file names `audio01` is the attended talker, `audio02` the HRTF mix and `audio03` the ignored talker.
  The clean wavs are dry, and each HRTF wav is its clean wav through one fixed HRTF per side (checked;
  notes.md 6). No transcripts or alignments.
- **Trials and conditions:** trial = presentation position (1-32), one session. S1-S8 heard Trail1..32 in order;
  S9-S17 in the authors' permuted order. The marker names give the stimulus file, so the mapping does not rely on the
  order table. Condition `competing-f{L,R}-hrtf` by the attended side.
- **Attention labels:** the authors' table; S9-S17 attended the other talker of the same file than S1-S8 (as in the
  authors' code). Checked on the EEG: the label-free match-mismatch DNN tracks the labelled attended talker better
  than the ignored one in every subject.
- **Trial metadata** (`raw.info["description"]`, JSON): participant, wav, attended side and talker (male/female),
  `s_marker_sample`, `onset_sample`, `onset_correction_s` and its method, `eeg_truncated_s`, units as shipped,
  reference.

## Alignment
- **Markers are software.** Each trial has `trial<k>D`, `trial<k>S` (start) and `trial<k>E` (end) markers. All
  positions sit on 20 ms recorder blocks, and the end-minus-start durations differ from the wav durations by
  -20..+60 ms (mean +17, SD 19): about 13 ms of jitter per marker (`jitter_ms` 13). No audio channel was recorded.
- **Onset: S marker + 0.216 s, applied by default** (`onset="dnn"`, `alignment_method = dnn`). The EEG runs from the
  onset to the end of the sound (or of the recording).
  - `onset="marker"` keeps the shipped timing (`alignment_method = sw_trigger`). Instantiate
    `Li2022Adaptor(download_dir, onset="marker")` directly: `format_dataset` uses the default.
- **Where the 0.216 s comes from (brain-based, circular).** The accou2023 match-mismatch DNN, scanned over +-2 s on
  all 544 trials at the marker onset, finds the attended talker 0.216 s after the S marker (95% CI 0.210-0.219;
  subject median 0.217; the ignored talker 0.213). Every subject and 8-trial block agrees (apparent outliers are the
  DNN's side lobe; their TRFs align within 23 ms), so it is one constant, presumably the playback software's
  latency. The HRTF mix as stimulus gives 0.202 s (13 subjects). On the same model, datasets with verified triggers
  sit within +-5 ms, but Mandarin data have shown unexplained offsets of tens of ms, so treat the absolute value as
  +-~50 ms. Because it was estimated from this EEG, **`alignment_quality = poor`**. Estimates per subject, block and
  file: `alignment/dnn_offsets.csv`, `alignment/dnn_summary.json`.
- **Drift:** none measurable (DNN early vs late windows -54 ppm, within noise); not corrected.

## Validation
**Tier: low** (all 17 participants, 544 trials, default `onset="dnn"`, 64 EEG channels, average reference).
- 0.5-8 Hz forward model (attended clean talker): mean r 0.031 (median 0.030); p = 0.020 against circular shifts
  and 0.048 against mismatched stimuli; significant in 15/17 participants (not S1, S13). TRF global field power
  peaks at 0.156 s, with a second peak at ~0.25 s.
- 30-60 Hz (MLR) and 30-250 Hz (brainstem) TRFs: not above the null (SNR 1.02, p 0.22; 0.97, p 0.74), as expected
  with software markers.
- Attention labels: the ignored clean talker also gives a response (mean r 0.020), but the attended talker's r is
  higher in 14/17 participants (Wilcoxon p = 7e-4). With `onset="marker"` (6-participant pilot) the low tier also
  passes, but the TRF peaks late (0.36 s).

**Suitable for** low-frequency (0.5-8 Hz) envelope TRFs and attention decoding, with the corrected onset.
**Not suitable for** MLR or brainstem analyses (software markers, ~13 ms jitter, brain-based onset), or for absolute
latency claims (the onset is circular by construction).

## Caveats and upstream issues
- **Truncated trials:** S13 Trail15 (position 6) ends 6.5 s before the sound (the recording stopped), and S14 Trail22
  (position 26) has only 16.1 s of 85.8 s. Both are kept; `eeg_truncated_s` gives the missing part. The stimuli are
  not cut.
- **Trials the authors dropped for poor comprehension answers are kept** (answers are not shipped). Their list
  (`scut_remove_trail`, trial = presentation position): S1 1, 2, 3, 9, 14, 24, 31; S2 9, 29; S3 1, 9, 19; S4 31; S5 14;
  S6 7, 9, 10, 13, 15, 29; S7 9, 25; S8 25-32; S9 15; S10 12, 15, 16; S11 12, 17, 30; S13 27, 29; S14 9, 14, 26, 27;
  S16 1.
- The paper gives 8192 Hz; the files are 1000 Hz (as the authors' code assumes).
- The shipped EEG is average-referenced, which is not documented.
- The authors' loader reads `S13_1.mat` before `S13_2.mat`, which shifts S13's labels by six trials in their
  pipeline, and it cuts a fixed 55 s per trial.
- The D marker (2 s before S for S1, 3 s for the others) is not documented.
- The HRTF path band-limits the played sound to about 0.3-4 kHz; the clean wavs are full-band.

Details: `notes.md`.
