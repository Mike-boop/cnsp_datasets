# li2025: notes

Explorer/standardiser notes (2026-11-23). Scratch: `/data_storage/gu08wuvu/datasets/tmp/review/li2025/`
(`listing.json`, `download.log`, `survey/` (survey.json, psd.npz, psd_per_subject.png), validation folders);
scripts in `/data_storage/gu08wuvu/datasets/tmp/review/scripts/li2025_*.py`.

## 1. Source
- OpenNeuro ds005346 v1.0.5, doi:10.18112/openneuro.ds005346.v1.0.5, "Naturalistic fMRI and MEG recordings during
  viewing of a reality TV show" (BABA). Licence **CC0** (dataset_description.json; the paper itself is CC BY-NC-ND).
- Paper: Li, Wang, Wang, ..., Ma 2025, Sci Data 12:1809, doi:10.1038/s41597-025-06110-5
  (`data_campaign/papers/li2025.pdf`; cites v1.0.4).
- Code: github.com/compneurolinglab/baba (fMRI GLM/ISC, Whisper transcription, Praat pitch/intensity). No MEG
  preprocessing or cropping code, no presentation script.
- Snapshot: 120 GB, 939 files (fMRI sub-01..30 + derivatives ~100 GB). Downloaded only the MEG half and the
  stimuli (registry `include`/`exclude`): 191 files, 18.9 GB, 2026-11-23, 2 workers, 9 min, 0 failures; every size
  matches the listing (OpenNeuro exposes no hashes; every fif was read completely in the survey).

## 2. Layout
- `sub-31..60/meg/sub-XX_task-{baba,question,replay}_meg.{fif,json}`: no events.tsv, channels.tsv or scans.tsv.
  The three files are crops of one continuous recording (`first_samp` of question/replay follow baba's end by
  ~3.6-5.4 s and ~2 s).
- `sourcedata/stimuli/baba_video.mp4` (h264 640x368 15 fps + AAC stereo 44.1 kHz, 1519.33 s);
  `sourcedata/annotation/{word_information,transcripts,wav_acoustics}.csv`; `sourcedata/quiz/*.csv`.
- Not downloaded: fMRI (`sub-01..30`), `sub-*/anat` (MEG participants' T1), `derivatives/` (fMRIPrep; MEG
  `desc-preproc` fifs: 1-38 Hz, ICA-cleaned, bads interpolated, ~100 Hz; sub-44/45/46 derivatives are only
  0.1-0.6 MB, i.e. empty).

## 3. Stimulus <-> trial mapping
- One trial per participant: task `baba` = the whole 25 min 19 s video excerpt (episode 1 of "Where Are We Going,
  Dad?" season 1, 2013), same for everybody, watched with sound through insert earphones (Sinorad ComfortBuds 24;
  README "air-conduction headphones" in one place). Condition label `audiovisual`.
- `question` (5 visual multiple-choice items, button presses, 14-37 s) and `replay` (15 min eyes closed, "mental
  replay") have **no auditory stimulus**: not standardised.
- **sub-54 is truncated upstream**: its baba (181857342 bytes) and replay (181501853 bytes) uploads stop inside the
  700th/699th 1 s data buffer, so only 698 s (baba) / 697 s (replay) are readable. MNE raises "buffer size must be
  a multiple of element size" on the last buffer; the adaptor drops it (`readable()`). Upstream issue.
- The authors excluded 6 MEG participants from their analyses ("different PSD patterns", README figure psd.png);
  which ones is not stated. All are included here.

## 4. Speech features
- **Audio**: only inside the mp4. Decoded with ffmpeg (`-map 0:a:0`, f32le, both channels): 66998272 samples =
  1519.235 s at 44.1 kHz. ffmpeg applies the mp4 edit list, which removes the AAC encoder priming (stream
  `duration_ts` 66998396, 124 samples more). L and R are nearly identical (r 0.9995): stored as shipped, 2
  channels, float32 (peaks up to 1.21, i.e. AAC overshoot beyond full scale; not clipped).
- The authors' `wav_acoustics.csv` (Praat intensity every 10 ms from their `baba_audio.wav`, 151900 frames =
  1519.00 s) peaks at lag 0 (10 ms resolution, r 0.80) against an intensity computed from the ffmpeg decode: same
  time base, no offset between their wav and the mp4 audio.
- `word_information.csv`: 2930 words (Whisper large-v3 timestamps, manually reviewed), with speaker (13 labels),
  onset/offset/duration (s from the start of the audio), log frequency, POS, top-down/left-corner/bottom-up parse
  counts. 16 word pairs overlap in time (simultaneous speakers), so it is stored verbatim as a CSV text feature
  (`words_csv`) rather than as a single-tier TextGrid. `transcripts.csv`: 738 sentences (`transcript`). Both are
  stored as `.txt` files holding the CSV (UTF-8; the shipped files start with a BOM, which the loader strips).
- `wav_acoustics.csv` (f0, intensity, speaker-switch flag at 10 ms) is model/derived and not stored (recomputable
  from the audio and the word table).

## 5. Neural data
- Quanmag OPM-MEG, 64 single-axis radial magnetometers (MEG001-MEG064, `mag`, coil type point magnetometer, T),
  plus STI1 (trigger). 1000 Hz, online 0-500 Hz (paper). Rigid helmet: sensor positions/orientations identical in
  all 30 files; `dev_head_t` identity; fiducials are placeholders (LPA -80/0/0, nasion 0/70/0, RPA 80/0/0 mm) but
  each file has its own 1763-3437 head-shape points (paper: "without additional digitization" of sensors).
- Raw as shipped: no projectors, no `proc_history`, no HFC; large DC offsets (up to ~13 nT) and ~0.1 nT
  low-frequency drifts. Lines at 50 Hz harmonics and at 125/250/375/500 Hz (the 250 Hz line is the largest), as
  shown in `survey/psd_per_subject.png`.
- `meas_date` looks unreliable (12 participants on 2024-10-30, 9 on 2025-01-20).
- Spectra fall into two groups: sub-31..47 vs sub-48..60 (different shape between ~10 and 30 Hz and a lower
  100-300 Hz floor in the second group). The cause (system settings, recording period) is unknown.
- **Bad channels** (`info['bads']`, kept in the data; the authors' PyPREP/visual bads are not shipped; only sub-33..38
  ship MEG019 in `info['bads']`):
  - paper: "for sixteen participants, Channel 19 and Channel 48 were consistently identified as bad due to
    equipment-related issues". In the data MEG019 is flat (exact zeros: sub-33..38) or ~3000x noisier than the
    median channel at 1-40 Hz (sub-32, 39..47) in exactly sub-32..47, and fine elsewhere; MEG048 is 1.2-13x the
    median in those subjects and ~1x in sub-48..60. So the paper's numbers are 1-based like the channel names, and
    MEG019 + MEG048 are marked bad in sub-32..47.
  - plus, per subject, channels whose 1-40 Hz amplitude spectral density exceeds 10x the subject's channel median
    (survey): sub-34 MEG023, MEG040; sub-42 MEG005; sub-47 MEG005; sub-48 MEG040 (~750x).
  - borderline (5-10x, not marked): sub-34 MEG005; sub-36 MEG040; sub-41 MEG011, MEG023; sub-42..44 MEG011;
    sub-44 MEG040; sub-53 MEG063.
- Sensor locations: MEG062 sits on the z-axis (x = y = 0); MNE's `compute_proj_hfc` returns non-finite projectors
  for it, so the validation's HFC leaves MEG062 out (validation only).
- STI1 is dropped (it holds one non-zero sample; its value is in the sidecar as `first_sample_trigger`).

## 6. Alignment
- STI1 per baba file: one non-zero sample, **at sample 0**, code 6 (28 participants), code 1 (sub-49), none
  (sub-40). Same pattern at the start of replay (sub-56 none). No other events, no end trigger, no audio copy or
  photodiode channel. So the authors cut each recording at the video's start trigger and to a fixed 1519.001 s
  (= `RecordingDuration`; their acoustic features are also cut to 1519.00 s).
- Trigger type (hardware/software), presentation software and the audio latency after the trigger are **not
  documented**. A video start trigger from presentation software typically leads the sound by a constant or
  variable amount (LESSONS: 40-500 ms).
- **Adopted: brain-based onset correction per subject, on by default** (user decisions 2026-11-23: group delays
  first, then "try it out" for per-subject delays, adopted after the held-out test in section 7). The trial starts
  the subject's delay into the shipped file (`alignment/onset.csv`, written by `alignment/subject_delays.py`;
  0.39-1.26 s, whole ms at 1000 Hz, so the correction is a crop, no resampling). `Li2025Adaptor(onset=...)`:
  `"subject"` (default), `"group"` (`ONSET_DELAY_S`: 0.80 s sub-31..47, 0.42 s sub-48..60; the previous default) or
  `"none"` (shipped first sample). Native 1000 Hz kept; the audio (1519.235 s) is longer than the remaining recording
  and is not cut. Sidecar (user decision 2026-11-23): `alignment_method = brain_trf` with the onset correction
  (`"subject"` and `"group"`; `onset_only` with `onset="none"`), `trigger_type` "unknown (inferred software ...) +
  onset_correction_s", plus `onset_correction_s`, `onset_correction_method`, `recording_group` and, only with
  `onset="subject"`, `onset_match_r`, `onset_parts_mad_ms`, `onset_fallback`, `onset_ambiguous`. Drift:
  `drift_ppm` = the brain-based pooled Theil-Sen estimate (-16.7 ppm, section 7), `drift_source` (method, CIs, OLS
  and sensitivity values for reference), `drift_corrected_ppm` = the applied value (-16.7 by default, 0 with
  `drift_ppm=0`). `onset_correction_s` is the actual start of the crop and `onset_estimate_s` the table/group delay
  (see the drift bullet below). `alignment_method = onset_only` only with `onset="none"` and the drift off.
- This is an exception to the campaign rule that constant brain/DNN-based offsets are documented, not applied
  (PLAN.md section 8): the delays are large (0.4-0.8 s) and the shipped onset is a software trigger, not the sound.
- Estimation: section 7; code in `alignment/` (reads the download through the adaptor with `onset="none"`,
  `drift_ppm=0`, so it reproduces the delays from code alone; see `alignment/README.md`).
- **Drift correction on by default (user decision 2026-11-23: "apply Theil-Sen")**: no clock reference exists, so the
  brain-based pooled Theil-Sen estimate (**-16.7 ppm**, 95% CI -27.4..-9.5; section 7) is corrected in the single crop
  (`standardise.clock.crop_on_audio_clock`, one quintic-spline resampling, as chen2023); `Li2025Adaptor(drift_ppm=0)`
  turns it off and reproduces the previous output bit-exactly. **Sign**: `alignment/drift.py`'s slope is d(delay)/dt (>
  0: the sound delay grows, MEG clock fast); `clock.py`'s drift is MEG samples per audio sample - 1 (> 0: neural clock
  fast; the delay grows by drift x t). Same convention, so the estimate is passed unchanged: -16.7 ppm = MEG clock slow,
  the delay shrinks by ~25 ms over 1519 s. **Anchor**: the delays (onset.csv, group delays) are whole-recording
  estimates, i.e. the delay at the session midpoint, so the crop starts at delay - drift x midpoint (+12.7 ms for a full
  recording, +5.8 ms for sub-54's 698 s); `onset="none"` starts at the first sample. The output is ~12 samples longer
  than before (1518460 for sub-52 vs 1518448).

## 7. Cross-subject duration check and brain-based timing
- Durations: all baba files 1519.001 s (sub-54 698 s, truncated); audio 1519.235 s. Fixed-length crops, so they
  carry no drift or jitter information.
- All timing analyses use HFC (order 1, MEG062 left out) and a 0.1 Hz high-pass of the **whole** recording
  (validation only; the stored data stay raw). Figures/numbers under `tmp/review/li2025/`.
- **The sound starts well after the shipped onset** (brain-based; circular; applied by default since the user's
  decision of 2026-11-23, see section 6):
  - Whole-recording population TRF (`scripts/li2025_poptrf.py`, `poptrf/poptrf.png`): envelope (0.5-8 Hz, 64 Hz)
    -> magnetometers over lags -1.5..+1.5 s, ridge alpha 1 x mean eigenvalue, 29 participants (sub-54 left out),
    50 circular-shift nulls. GFP peaks at **+0.92 s** (2.1x the null median, far above its 95th percentile).
  - The two recording groups differ (`poptrf/poptrf_groups.png`): **sub-31..47 peak at +0.92 s, sub-48..60 at
    ~+0.5-0.66 s** (less sharp). Per-subject peaks: `onset_evidence_per_subject.png` (left; single-subject GFP
    peaks are noisy, median 0.86 s).
  - Segment validation at candidate offsets (section 9): with the stimulus delayed by 0.8 s the pooled TRF peaks at
    109 ms (as shipped: at the 0.5 s window edge) and r doubles; group B alone peaks at 94 ms when delayed by 0.55 s
    and at -141 ms when delayed by 0.8 s.
  - **Estimate**: sound onset ~0.80 s after the trigger sample for sub-31..47 and ~0.55 s for sub-48..60 (+-~50 ms;
    assumes an envelope-TRF peak near 100 ms). Typical of a software video trigger sent before playback starts
    (LESSONS: chen2026 ~0.5 s); the group difference matches the change in spectra between the two recording
    periods (different setup or presentation settings). The visual stream may contribute to the TRF.
  - **Group B refined (main session, 2026-11-23)**: 0.55 s overshoots (a component lands at -141 ms). Group B's
    uncorrected multichannel TRF matched to group A's corrected TRF (space-time r over -0.2..0.6 s, 58 channels good
    in all subjects; `alignment/match_groups.py`): best **0.44 s** (r 0.60; bootstrap 95% CI 0.41-0.80 s, skewed;
    r 0.50 at 0.55 s, 0.10 at 0.30 s). The user's reading (B's +109 ms at 0.55 s = A's +250 ms component) gives
    0.41 s; **adopted 0.42 s**. A B component at ~-40 ms remains unexplained (possibly visual / lip-driven).
  - Group A confirmed: with 0.80 s the corrected TRF peaks at +94 / +250 ms with right temporal / posterior
    topographies (main session, `trf_weights/butterfly_topo.png`).
  - **Check with the adopted delays** (`alignment/poptrf.py <download> <out> 0.80,0.42`, 20 nulls; figure
    `tmp/review/li2025/alignment/poptrf/poptrf_0.8_0.42.png`): group A GFP peaks at **+0.125 s** (2.5x the null
    median), group B at **+0.062 s** (2.1x), with a shoulder at ~0 / -0.04 s; nothing remains at the uncorrected
    positions.
  - Uncertainty: A +-~50 ms (assumes an envelope-TRF peak near 0.1 s); B CI 0.41-0.80 s (skewed), leftover -40 ms
    component.
- **Superseded first estimate** (kept for the record): a cross-validated lag sweep with lags 0-0.5 s and a weak ridge
  (alpha 1e-2; `scripts/li2025_shiftsweep.py`, `shiftsweep/`) peaked at a shift of -0.47 s in 29/30 subjects with
  an identical curve shape in all of them (dip at 0, side peaks at -0.47 and +0.5 s). The population TRF, the
  segment validation at +0.469 s (worse, r below null) and at -0.8 s (better) contradict it; the cause (probably the
  near-singular fit) was not pursued. Likewise `widetrf/` (alpha 1e-1) only shows the ridge solution's shape.
- **Audio-locked artefact**: none. Audio waveform or its half-wave rectification vs every magnetometer at 30-200 /
  30-60 Hz (notched; raw or HFC; `scripts/li2025_artefact.py`, `artefact_test*/`) and the 45-55 Hz band (the
  soundtrack's 50 Hz hum is only 1.8x its neighbours) give nothing above the noise maximum in single subjects. No
  stimtrack-like leakage, so the onset cannot be measured precisely.
- **Drift** (not measurable from triggers; brain-based; **applied since 2026-11-23, see "Applied" below**). First
  estimate, per group (the earlier `alignment/drift.py`, commit b90915c; superseded by the pooled estimate below): per
  subject, ridge
  TRFs on the three thirds of the uncorrected recording (~506 s each, centres 4.2 / 12.7 / 21.1 min); delay of each
  third = shift of best space-time match to group A's corrected template (-0.2..0.6 s, 58 channels, parabolic
  refinement); slope over the thirds (> 0: MEG clock fast vs audio); bootstrap over subjects (1000). Figure
  `tmp/review/li2025/alignment/drift/drift.png`, numbers `alignment/drift/drift.json`.
  - **Group A (n = 17): delays 0.806 / 0.797 / 0.791 s -> -14 ppm (95% CI -22 to -6 ppm)**, i.e. ~-21 ms over the
    1519 s session; per-subject median -13 ppm. Small, and the template comes from the same subjects (circular).
  - **Group B (n = 12): delays 0.551 / 0.429 / 0.423 s -> -127 ppm (95% CI -380 to +8 ppm)**: not a drift estimate;
    the first third sits 0.12 s later than the other two (a step, or the ambiguous match between B's -40 ms and
    +60 ms components). Per-subject median -31 ppm.
  - **Five parts** (`drift ... 5`, centres 2.5 / 7.6 / 12.7 / 17.7 / 22.8 min): group A -11 ppm (95% CI -20 to
    -2; delays 0.807 / 0.798 / 0.799 / 0.792 / 0.793 s), consistent with three parts. Group B 0.564 / 0.544 / 0.426 /
    0.426 / 0.423 s: a **step of ~0.12 s between ~8 and ~13 min**, flat before and after, i.e. not a clock drift.
    Either the sound delay changed once during playback (e.g. a player hiccup) or the template match switches between
    B's two components; per subject this is too noisy to tell. The adopted 0.42 s fits the last ~60 % of the session;
    the first ~40 % may be ~0.12 s later than corrected. **Open question for the user.**
  - The refactored repo scripts (`alignment/`, rerun 2026-11-23 into `tmp/review/li2025/alignment_v2/`) reproduce
    the main session's match (0.4375 s, r 0.602) and the three-part drift exactly.
  - Earlier estimate from the low-tier segment offsets (6 x 250 s, -0.8 s offset): -9.8 +- 117 ppm (too loose).
  - Conclusion: no correction. Group A's -14 ppm would move the end of the session by ~21 ms.
  - **Pooled estimate (2026-11-23, v4; superseded by v5 below)**. The per-group averages above mix subjects with
    different delays (A/B mixture). Now per subject: the five parts' delays (wide window, same template match as
    `onset.csv`; sub-54 two halves) **relative to the subject's own whole-recording delay**, fallback subjects left
    out (sub-37/40/52/55; n = 26); parts > 150 ms off (another peak; 10 of 127) dropped; pooled OLS slope over the
    part centres, bootstrap over subjects (1000) for the 95% CI; Theil-Sen over all parts as a check. Figure
    `tmp/review/li2025/alignment_v4/drift/drift.png`, numbers `drift/drift.json`.

    | set | n | OLS (ppm) | 95% CI | Theil-Sen (ppm) | 95% CI |
    |---|---|---|---|---|---|
    | all | 26 | **-17.2** | -30.9..-4.3 | -16.3 | -28.8..-8.2 |
    | A (sub-31..47) | 15 | -9.0 | -22.0..+5.3 | -11.2 | -19.6..-0.5 |
    | B (sub-48..60) | 11 | -30.1 | -59.7..-8.7 | -28.4 | -60.3..-11.5 |
    | B without sub-50/53 | 9 | -11.3 | -19.7..-2.0 | -16.4 | -32.6..-7.0 |
    | all without sub-50/53 | 24 | -10.0 | -20.4..+0.0 | -12.8 | -20.2..-5.3 |

    Per-subject slopes (noisy, 5 points): mostly -50..+50 ppm; sub-50 -106 and sub-53 -159 ppm are their later early
    parts (section 8 item 1), not a clock drift, and they carry group B's estimate. Circular: the template is group
    A's own corrected TRF; a latency change of the response over the session (adaptation) would look like drift.
  - **Decision rule (main session): apply only if the 95% CI excludes 0 and |drift| > 20 ppm (> ~30 ms over 1519 s).**
    v4: all subjects -17 ppm, CI excludes 0 but |drift| < 20 ppm -> documented, not applied (~-26 ms over the
    session). Group B alone met the rule only because of sub-50/53; without them -11 ppm.
  - **Pooled estimate v5 (2026-11-23, current `alignment/drift.py`; user decision: the same restricted part matching
    as `onset.csv`)**. Each part's delay is now matched only within +-0.3 s of the subject's whole-recording delay
    (`common.PART_WINDOW`), which replaces the ad-hoc "> 150 ms off" drop; OLS and Theil-Sen use the same points (no
    part on the window edge). sub-52/55 are no longer fallbacks, so n = 28 (137 parts). Figure
    `tmp/review/li2025/alignment_v5/drift/drift.png`, numbers `alignment_v5/drift/drift.json`.

    | set | n | OLS (ppm) | 95% CI | Theil-Sen (ppm) | 95% CI |
    |---|---|---|---|---|---|
    | all | 28 | **-28.7** | -49.9..-8.0 | -16.7 | -27.4..-9.5 |
    | A (sub-31..47) | 15 | -9.3 | -30.6..+12.6 | -11.0 | -19.3..-0.9 |
    | B (sub-48..60) | 13 | -51.6 | -90.4..-20.0 | -27.9 | -52.2..-13.6 |
    | all without sub-50/52/53 | 25 | -16.3 | -34.1..+1.5 | -12.5 | -19.4..-5.8 |

    On v4's 26 subjects the restricted matching alone moves OLS from -17 to -27.5 ppm (Theil-Sen -16.3 both times):
    the window now admits parts 150-300 ms off that the old drop removed (sub-50/52/53's later first parts, +121 /
    +145 / +152 ms; sub-59's last part -192 ms, sub-47's -156 ms, sub-38's +160 ms), and OLS follows them. Theil-Sen is
    stable (-12..-17 ppm in every variant). **Formally the OLS estimate now meets the rule (CI excludes 0, |-28.7| >
    20 ppm); Theil-Sen (-16.7) and OLS without sub-50/52/53 (-16.3, CI includes 0) do not. Not applied: a drift
    correction changes the data and needs the user's sign-off (open, section 8 item 2).** Recorded as `drift_ppm =
    -28.7` (OLS, the headline estimator so far) with both estimators in `drift_source`.
  - **Applied (user decision 2026-11-23: "apply Theil-Sen")**: the pooled Theil-Sen estimate, **-16.7 ppm** (95% CI
    -27.4..-9.5), is corrected by default (section 6; `drift_ppm` / `drift_corrected_ppm` -16.7; OLS and the
    without-sub-50/52/53 values kept in `drift_source` for reference). **Check on the corrected data**
    (`tmp/review/scripts/li2025_drift_check.py`, `tmp/review/li2025/alignment_v6/drift_check.json`): the same per-part
    template match on the drift-corrected recordings (shipped onset, 28 non-fallback subjects) gives a pooled
    Theil-Sen slope of **-0.9 ppm** (before -16.7) and OLS -10.5 (before -28.7; the rest is the far parts that drive
    OLS). Per subject the slope rises by a median 16.9 ppm (sub-46: -17.9 -> 0.0 ppm), confirming the sign. The
    whole-recording delays move by the expected +12.7 ms (median 13.5; sub-54 +5.8 ms), except sub-50/55/58 (+20-26
    ms) and **sub-53 (0.429 -> 0.553 s: it switches to its second peak, already flagged `onset_ambiguous`)**. The
    adopted delays stay those of `onset.csv` (estimated on the uncorrected data, anchored at the midpoint).
- **Per-subject delays (adopted 2026-11-23, `alignment/subject_delays.py`; figures and tables in
  `tmp/review/li2025/alignment_v3/`)**. The per-part view (`alignment_v2/per_subject/`) showed that the delay
  varies per subject, not per spectral group: sub-48/49/60 (group B) sit at ~0.80 s and sub-43 (group A) at ~0.49 s,
  i.e. ~0.4 / ~0.3 s off with the group delays. Group B's "step" above is largely this mixture (and sub-50/52/53,
  whose weak early parts sit later) rather than a change during playback.
  - Method: per subject, shift (**0..1.9 s** since 2026-11-23 v4, see below; parabolic refinement) of the
    whole-recording uncorrected TRF (refitted over lags **-1.5..+2.5 s**, `common.match_trfs`) that best matches group
    A's corrected TRF (space-time r over lags -0.2..0.6 s, 58 common channels); cross-checked with the median and MAD
    of the five parts' delays (same fits). Fallback to the group delay (flagged) if the peak r < 0.15 or the parts'
    MAD > 50 ms (since v5 each part is matched only within +-0.3 s of the whole-recording delay, see below).
    **`onset_ambiguous`** (adopted delays only): another local maximum of the match curve (search edges
    included) > 100 ms away comes within 0.15 of the best r; the delay is kept. sub-54 (truncated) fitted on its
    698 s, two halves as parts. Group A also against a leave-one-subject-out template (circularity).
  - **Wide lag window (user "do it", 2026-11-23; v4, `tmp/review/li2025/alignment_v4/`)**. The first version fitted
    lags -1.5..+1.5 s, so the search stopped at 0.906 s, and sub-36/39/47's LOSO matches sat at that edge. The main
    session's refit with lags -1.5..+2.5 s (`scripts/li2025_wide_lag_refit.py`, `alignment_v3/wide_lag/`) is now the
    repo method; the repo code reproduces its delays, r, part delays and LOSO delays within 0.5 ms (rounding).
    The template (trf_weights, lags -1.5..+1.5 s) and thresholds are unchanged. Changes against the narrow window:
    sub-35 0.80 (fallback, "no match") -> **1.256 s** (r 0.62, parts MAD 24 ms, LOSO 1.257: its peak lay beyond the
    old window); sub-47 0.834 -> **0.977 s** (the old value was a shoulder at the window edge; LOSO 0.991); **sub-52
    0.553 -> fallback 0.42 s and sub-55 0.429 -> fallback 0.42 s**: with the wider search some of their weak parts lock
    onto far peaks (sub-52 parts 1.246 / 0.566 / 0.417 / 0.527 / 1.399 s, MAD 149 ms; sub-55 1.597 / 0.518 / 0.417 /
    1.734 / 0.443 s, MAD 101 ms), so the unchanged MAD rule now rejects them, although their whole-recording peaks did
    not move (0.553 / 0.433 s). All others within 2 ms. sub-37 (own peak 0.621 s, r 0.26, MAD 62 ms) and sub-40
    (r 0.16, MAD 760 ms) stay fallbacks. **Ambiguous: sub-33, 39, 47, 53** (expected only sub-39): sub-39's second
    peak 0.94 s (r 0.25 vs 0.29) is the one LOSO prefers; sub-33's at 0.72 s (0.50 vs 0.57, LOSO 0.70); sub-47's
    shoulder 0.83 s (0.57 vs 0.68; the old value); sub-53's 0.53 s (0.31 vs 0.34). sub-53's parts MAD is 50.0 ms, at
    the limit.
  - **Restricted part matching (user decision 2026-11-23, v5, `tmp/review/li2025/alignment_v5/`)**: sub-52 and sub-55
    keep their own delays. Their fallback came from the reliability check, not from their whole-recording match: with
    the wide search, 2 of their 5 weak parts locked onto far peaks (1.2-1.7 s). Fix in the check, not the threshold:
    each part is matched only within +-0.3 s of the subject's whole-recording delay (`common.PART_WINDOW`; MAD rule
    50 ms and r rule 0.15 unchanged). Result: **sub-52 0.553 s (parts MAD 21 ms), sub-55 0.433 s (25 ms; now
    `onset_ambiguous`: second peak 1.72 s, r 0.36 vs 0.45)**, no longer fallbacks. sub-37 (MAD 62 ms, unchanged) and
    sub-40 (MAD 760 -> 118 ms, r 0.16) stay fallbacks. All other delays unchanged; parts MAD changes only for sub-44
    (16 -> 5 ms), sub-46 (6 -> 5) and sub-56 (9 -> 7), whose single far parts are now matched near their delay.
    Caveat (review): the MAD check now detects scatter within +-0.3 s only; a part whose own best peak is farther away
    is no longer counted against the subject.
  - Result (`onset.csv`; figure `alignment_v5/subject_delays/subject_delays.png`; v4 (unrestricted parts) in
    `alignment_v4/subject_delays/`, the narrow-window version in `alignment_v3/subject_delays/`):

    | sub | grp | delay (s) | r | parts MAD (ms) | LOSO (s) | note |
    |---|---|---|---|---|---|---|
    | 31 | A | 0.770 | 0.32 | 18 | 0.720 | weak |
    | 32 | A | 0.753 | 0.59 | 4 | 0.733 |  |
    | 33 | A | 0.821 | 0.57 | 9 | 0.696 | ambiguous: second peak 0.72 s (r 0.50); LOSO picks it |
    | 34 | A | 0.796 | 0.69 | 2 | 0.796 |  |
    | 35 | A | 1.256 | 0.62 | 24 | 1.257 | was fallback (peak beyond the old 0.906 s window); now clean, 1.256 s (LOSO 1.257) |
    | 36 | A | 0.888 | 0.65 | 32 | 0.905 | was near the old search edge; LOSO 0.905 now inside |
    | 37 | A | 0.80 | 0.26 | 62 | 0.614 | fallback (parts disagree; own peak 0.621 s, r 0.26) |
    | 38 | A | 0.791 | 0.51 | 10 | 0.786 |  |
    | 39 | A | 0.805 | 0.29 | 8 | 0.938 | ambiguous: second peak 0.94 s (r 0.25); LOSO picks it |
    | 40 | A | 0.80 | 0.16 | 118 | 1.378 | fallback (no match; best 1.38 s, r 0.16, parts MAD 118 ms; 760 ms unrestricted) |
    | 41 | A | 0.761 | 0.41 | 14 | 0.742 |  |
    | 42 | A | 0.813 | 0.54 | 6 | 0.834 |  |
    | 43 | A | 0.493 | 0.45 | 27 | 0.488 | 0.31 s earlier than group A |
    | 44 | A | 0.812 | 0.49 | 5 | 0.822 |  |
    | 45 | A | 0.791 | 0.68 | 7 | 0.788 |  |
    | 46 | A | 0.765 | 0.68 | 5 | 0.752 |  |
    | 47 | A | 0.977 | 0.68 | 13 | 0.991 | was 0.834 s (a shoulder, at the old window edge); ambiguous: shoulder 0.83 s (r 0.57) |
    | 48 | B | 0.840 | 0.60 | 4 |  | 0.42 s later than group B |
    | 49 | B | 0.798 | 0.70 | 8 |  | 0.38 s later |
    | 50 | B | 0.438 | 0.54 | 26 |  | early parts later |
    | 51 | B | 0.518 | 0.56 | 12 |  |  |
    | 52 | B | 0.553 | 0.36 | 21 |  | own delay (user, v5); early parts later; v4 fallback (unrestricted parts 1/5 at 1.25 / 1.40 s, MAD 149 ms) |
    | 53 | B | 0.429 | 0.34 | 50 |  | early parts later; ambiguous: second peak 0.53 s (r 0.31); parts MAD 50.0 ms (at the limit) |
    | 54 | B | 0.505 | 0.50 | 3 |  | truncated, 698 s; 2 halves |
    | 55 | B | 0.433 | 0.45 | 25 |  | own delay (user, v5); ambiguous: second peak 1.72 s (r 0.36); v4 fallback (unrestricted parts 1/4 at 1.60 / 1.73 s, MAD 101 ms) |
    | 56 | B | 0.392 | 0.53 | 7 |  |  |
    | 57 | B | 0.403 | 0.55 | 13 |  |  |
    | 58 | B | 0.442 | 0.41 | 26 |  |  |
    | 59 | B | 0.410 | 0.34 | 25 |  |  |
    | 60 | B | 0.774 | 0.44 | 11 |  | 0.35 s later |

    LOSO vs full template (group A, non-fallback, wide window): within 25 ms for 12 of 15; sub-31 -50 ms, sub-33
    -125 ms and sub-39 +133 ms (both at their second peaks). None at the search edge any more. Group B's delays do not
    depend on its own data's template. (Narrow window: sub-39/47's LOSO sat at the 0.906 s edge.)
  - **Held-out test** (`alignment/heldout.py`; run as `tmp/review/scripts/li2025_heldout_validate.py`, the same
    code before it moved into the repo; results `alignment_v3/heldout_test/`): delays
    estimated on parts 1,3,5 (same rule; group A against the leave-one-out template in a second variant) and scored
    on parts 2,4 with the low tier (shipped files, HFC + 0.1 Hz HP + notches on the whole recording, each held-out
    part cut in halves), and the reverse; 29 subjects (sub-54 not in the part caches). With only two parts the MAD
    rule is stricter (half the range): sub-33/43/44/53 fall back on parts 2,4.

    | scored on | run | mean r (all) | A | B | max GFP ratio | better than group (subjects) | sub-43 | sub-48 | sub-49 | sub-60 |
    |---|---|---|---|---|---|---|---|---|---|---|
    | parts 2,4 | shipped | 0.0001 | -0.0024 | 0.0036 | 1.34 | 1/29 | 0.0060 | -0.0103 | 0.0012 | -0.0063 |
    | parts 2,4 | group | 0.0165 | 0.0170 | 0.0159 | 1.69 | - | 0.0136 | 0.0154 | 0.0177 | 0.0078 |
    | parts 2,4 | subject | 0.0180 | 0.0171 | 0.0192 | 1.93 | 17/29 (B 10/12) | 0.0200 | 0.0277 | 0.0250 | 0.0149 |
    | parts 2,4 | subject, LOSO | 0.0180 | 0.0172 | 0.0192 | 1.89 | 16/29 | 0.0217 | 0.0277 | 0.0250 | 0.0149 |
    | parts 1,3,5 | shipped | 0.0087 | 0.0036 | 0.0158 | 1.73 | 8/29 | 0.0100 | 0.0124 | 0.0120 | 0.0123 |
    | parts 1,3,5 | group | 0.0186 | 0.0192 | 0.0178 | 1.83 | - | 0.0073 | 0.0205 | 0.0208 | 0.0112 |
    | parts 1,3,5 | subject | 0.0190 | 0.0187 | 0.0194 | 2.14 | 9/29 (B 7/12) | 0.0073 (fallback) | 0.0220 | 0.0266 | 0.0143 |
    | parts 1,3,5 | subject, LOSO | 0.0193 | 0.0192 | 0.0194 | 2.17 | 12/29 | 0.0073 (fallback) | 0.0220 | 0.0266 | 0.0143 |

    Per subject beats per group in both directions for group B and for the misaligned subjects (sub-48/49/60 every
    time, sub-43 when its delay was estimable), with sharper TRFs (higher GFP ratio); across all subjects the gain is
    small and not significant (Wilcoxon on non-tied subjects: p 0.05 and 0.87, pooled 0.10), because most group-A
    delays move by < 50 ms and the low tier's -0.2..0.6 s window partly absorbs delay errors. LOSO gives the same
    picture, so the circularity in group A does not drive the result. **Decision (by the instruction "if per-subject
    beats per-group held-out ... make it the default"): per-subject delays by default** with the full template
    (LOSO reported only; it differs mainly where it hits the search edge). The held-out test ran with the narrow
    window (0..0.906 s) and was not repeated for the wide one.

## 8. Open questions (defaults in bold)
1. Onset: **decided 2026-11-23: brain-based per-subject delays applied by default** (`onset.csv`, section 7;
   `onset="group"` for 0.80 s sub-31..47 / 0.42 s sub-48..60, `onset="none"` for the shipped onset).
   **Per-subject confirmed as the default by the user (2026-11-23).** **Fallbacks accepted (user, 2026-11-23)**:
   sub-35/37/40 (no reliable match; sub-37's own peak ~0.62 s) take the group-A delay, 0.80 s, flagged
   `onset_fallback`. **Documented, not corrected (user, 2026-11-23)**: sub-50/52/53 sit ~150 ms later in their first
   ~10 min (parts 1-2: sub-50 0.56/0.47 s, sub-52 0.70/0.57 s, sub-53 0.58/0.54 s, vs whole-recording 0.437 / 0.553 /
   0.428 s; `tmp/review/li2025/alignment_v2/per_subject/parts_per_subject.json`). Their early parts are the weakest
   fits (match r 0.12-0.14 in part 1), so a real latency change during playback cannot be told apart from noise; the
   adopted single delay fits the remaining ~60 % of their sessions. Users who need sub-second timing early in these
   three recordings should treat it as uncertain by ~0.15 s. **Wide window (user "do it", 2026-11-23)**: search
   0..1.9 s; sub-35 1.256 s and sub-47 0.977 s adopted, sub-52/55 now fall back to 0.42 s by the unchanged MAD rule
   (their whole-recording peaks stay at 0.553 / 0.433 s; validation r unchanged or slightly higher, section 9);
   sub-33/39/47/53 flagged `onset_ambiguous` (section 7). **sub-52/55 keep their own delays (user, 2026-11-23)**:
   parts matched within +-0.3 s of the whole-recording delay (section 7, v5) -> sub-52 0.553 s, sub-55 0.433 s
   (now also `onset_ambiguous`); fallbacks are sub-37/40. Open for the user: whether the ambiguity flag should be
   stricter (sub-33/39/47/53/55 flagged; only sub-39 was expected).
2. Drift: **decided 2026-11-23 (user: "apply Theil-Sen"): corrected by default, -16.7 ppm** (pooled Theil-Sen, 95% CI
   -27.4..-9.5; `drift_ppm=0` turns it off; sections 6-7). Brain-based, pooled relative to each subject's own delay with
   the restricted part matching (v5, 28 subjects); for reference OLS -28.7 ppm (-49.9..-8.0), without sub-50/52/53 OLS
   -16.3 (-34.1..+1.5). OLS had formally met the decision rule, Theil-Sen not; the user chose Theil-Sen and to apply it.
   v4 (parts > 150 ms dropped, 26 subjects): -17 ppm (-31..-4). Earlier per-group estimate: group A -14 ppm, group B a
   ~0.12 s step. Group B's "step" is resolved: it was mostly the mixture of subjects at ~0.8 and ~0.4 s (now
   per-subject), plus sub-50/52/53's later early parts (documented in item 1).
3. Bads: **paper's MEG019/MEG048 for sub-32..47 + the 10x rule**.
4. sub-54: **include the 698 s readable part** (flagged `truncated_upload` in the sidecar).
5. quiz/replay runs: **not standardised** (no auditory stimulus).

## 9. Validation
`scripts/li2025_validate.py` (2026-11-23): each trial cut into 6 x 250 s segments (sub-54: 2 + 198 s), each with its
own stimulus name, so the low tier can cross-validate across segments; standard validator (`validate.validate`,
picks `mag`, bads excluded); HFC + 0.1 Hz high-pass + notches (50 Hz and 125 Hz harmonics) on the whole recording
before cutting (validation only). `LI_OFFSET` shifts the stimulus in the validation only (< 0: sound later than the
shipped onset). Results in `tmp/review/li2025/validation_offset{0,-0.8,5_control}/`,
`validation_groupB_offset{-0.55,-0.8}/` (validation.json + validation.png).

| run | mean r | p_circ / p_mismatch | subjects sig | TRF peak | segment jitter MAD |
|---|---|---|---|---|---|
| as shipped (0) | 0.0113 | 0.020 / 0.048 | 67 % | 0.48 s (window edge) | 68 ms |
| stimulus delayed 0.8 s | 0.0234 | 0.020 / 0.048 | 90 % | 109 ms | 16 ms |
| group B, delayed 0.55 s | 0.0247 | 0.020 / - | 100 % | 94 ms | 16 ms |
| control, +5 s (wrong) | -0.0020 | 1.0 / 1.0 | 0 % | - | - |
| onset-corrected standardisation, per group (previous default) | 0.0236 | 0.020 / 0.048 | 90 % | 234 ms (109 / 219 per group) | 13 ms |
| onset-corrected standardisation, per subject, narrow window (0..0.906 s) | 0.0238 | 0.020 / 0.048 | 87 % | 78 ms (78 in both groups) | 13 ms |
| onset-corrected standardisation, per subject, wide window, unrestricted parts (v4) | 0.0242 | 0.020 / 0.048 | 87 % | 94 ms (A 94, B 78) | 13 ms |
| onset-corrected standardisation, per subject, wide window, parts within 0.3 s (v5) | 0.0241 | 0.020 / 0.048 | 87 % | 94 ms (A 94, B 78) | 13 ms |
| **v5 + drift correction -16.7 ppm (v6, adaptor default)** | 0.0245 | 0.020 / 0.048 | 90 % | 94 ms (A 94, B 78) | 13 ms |

Per recording group (`validation_corrected/groups_before_after.png`; GFP / null median, lags -0.15..0.5 s):

| group | run | mean r | subjects sig | TRF peak | max GFP ratio | jitter MAD |
|---|---|---|---|---|---|---|
| A (sub-31..47, n 17) | shipped onset | 0.0070 | 41 % | 469 ms (edge) | 1.38 | 186 ms |
| A | corrected 0.80 s | 0.0230 | 82 % | 109 ms (2nd ~235 ms) | 2.35 | 11 ms |
| B (sub-48..60, n 13) | shipped onset | 0.0170 | 100 % | 484 ms (edge) | 2.18 | 33 ms |
| B | corrected 0.42 s | 0.0245 | 100 % | 219 ms (also ~65 ms, bump ~-30 ms) | 2.21 | 15 ms |
| A | per subject (onset.csv) | 0.0234 | 82 % | 78 ms | 2.75 | 12 ms |
| B | per subject (onset.csv) | 0.0243 | 92 % | 78 ms | 2.75 | 19 ms |
| A | per subject, wide window | 0.0240 | 82 % | 94 ms | 2.97 | 12 ms |
| B | per subject, wide window | 0.0244 | 92 % | 78 ms | 2.72 | 16 ms |
| A | per subject, v5 (unchanged delays) | 0.0240 | 82 % | 94 ms | 2.96 | |
| B | per subject, v5 (sub-52/55 own delays) | 0.0242 | 92 % | 78 ms | 2.73 | |
| A | v6 (drift corrected) | 0.0238 | 82 % | 94 ms | 2.97 | |
| B | v6 (drift corrected) | 0.0253 | 100 % | 78 ms | 2.85 | |

Per subject vs per group (re-standardised 2026-11-23, all 30; `validation_subject/`, comparison
`alignment_v3/validation/before_after.png` via `scripts/li2025_compare_runs.py`): mean r unchanged (0.0238 vs 0.0236;
11/30 subjects higher, most changes within +-0.003 because most delays move < 50 ms), but the TRF is sharper and the
same in both groups (max GFP / null 2.75 vs 2.16; peak 78 ms in both groups instead of 109 / 219 ms). The misaligned
subjects gain: sub-43 0.0167 -> 0.0215, sub-48 0.0242 -> 0.0288, sub-49 0.0278 -> 0.0303; sub-60 0.0227 -> 0.0209.
sub-54 (truncated, 3 segments; 0.42 -> 0.505 s) drops from p 0.02 to 0.08 (r 0.0205 -> 0.0177), hence B 92 %
significant. These segments are not held out from the delay estimate; the held-out test is in section 7.

Wide window vs narrow (re-standardised 2026-11-23, all 30; `alignment_v4/validation_subject/`, comparison
`alignment_v4/validation/before_after.png` + `.md`): mean r 0.0238 -> 0.0242 (11/30 higher), group A max GFP ratio
2.75 -> 2.97. **sub-35 0.0276 -> 0.0386** (0.80 -> 1.256 s); sub-47 0.0494 -> 0.0465 (0.834 -> 0.977 s; within the
noise below); sub-52 0.0212 -> 0.0225 and sub-55 0.0275 -> 0.0280 (now fallbacks at 0.42 s). Subjects whose delay
moved by only 1-2 ms change by up to +-0.003 (e.g. sub-31 +0.0019, sub-34 -0.0022, sub-36 +0.0017, sub-50 -0.0028,
sub-58 -0.0020), so that is the noise floor of this comparison.

Restricted part matching (v5; re-standardised 2026-11-23, all 30; `alignment_v5/validation_subject/`, same settings
as `alignment_v4/validation_subject/`): only sub-52 and sub-55 change. **sub-52 0.0225 -> 0.0212** (0.42 -> 0.553 s;
its TRF peak moves from 125 ms to 0 ms) and **sub-55 0.0280 -> 0.0275** (0.42 -> 0.433 s), both back to their
narrow-window values and within the +-0.003 noise floor above, both still p 0.02. Mean r 0.0242 -> 0.0241; everything
else identical. The validation does not favour the own delays over the group delay for these two (nor clearly
against); the user's decision rests on their whole-recording matches.

Drift correction (v6; re-standardised 2026-11-24, all 30; `alignment_v6/validation_subject/`, same settings as
`alignment_v5/validation_subject/`): mean r 0.0241 -> 0.0245 (16/30 higher, changes -0.0026..+0.0036), 90 % of
subjects significant (sub-54 0.0177 -> 0.0207, p 0.08 -> 0.02); group B 0.0242 -> 0.0253 (13/13 significant, max GFP
ratio 2.73 -> 2.85), group A unchanged (0.0240 -> 0.0238). Largest gains sub-50 +0.0036, sub-47 +0.0034, sub-60
+0.0032; sub-36 -0.0026. The validator's segment-offset drift (median over subjects, SE ~90 ppm) moves from -29.6 to
+8.7 ppm. Not independent of the estimate (same data, circular), and the changes are mostly within the +-0.003 noise
floor; the pooled check in section 7 is the direct test.

The corrected standardisations give the low tier with TRF peaks at plausible
latencies in both groups; the HF tiers again "pass" nominally (p 0.01) but are the lag-0 artefact (see above).

- **Tier: `low`** (0.5-8 Hz forward model above circular-shift and mismatched-segment nulls; with the shipped onset
  it passes too, but the TRF sits at the window edge, i.e. misaligned by the delay above).
- **High-frequency tiers: not credible.** Every run, including the wrong-offset control, shows the same lag-0 peak
  in the 30-60 Hz TRF (~2.2x, ringing at +-20 ms) and nominal mlr "passes" (p 0.01), and the 30-250 Hz TRF shows no
  response in its window. So the peak is an analysis artefact independent of the alignment (likely the segment
  boundaries; filtering per segment made it ~5x larger before the whole-recording preprocessing was added). No
  high-frequency cortical response is claimed; `validation_tier` stays `low`.
- First runs filtered each 250 s segment separately: the nT DC offsets of the raw OPMs then gave edge transients
  that correlate with the stimulus at lag 0 (TRF peak at 0 in all bands; moved to `superseded/`). Lesson: high-pass
  OPM data on the whole recording before cutting.
- Data size: 30 participants, 12.43 h recorded (0.422 h each; sub-54 0.194 h); 12.42 h after the onset crop
  (1518.20 s group A, 1518.58 s group B, sub-54 697.58 s); listening time per participant = the 1519.2 s video.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**poor**: no usable hardware timing (one trigger at sample 0, no audio copy, no end trigger); per-subject brain-based
onset delays (template match to group A's TRF, wide search 0-1.9 s; 0.39-1.26 s; fallbacks sub-37/40; ambiguous
sub-33/39/47/53/55) and a pooled brain-based Theil-Sen drift of -16.7 ppm, both applied by default (`brain_trf`, user
decisions 2026-11-23); low tier only (mean r 0.0245, 90 % of subjects); circular (estimated and validated on the same
MEG).

## Upstream issues
- sub-54 `task-baba` and `task-replay` fifs are truncated in v1.0.5 (181857342 / 181501853 bytes, last data buffer
  incomplete; ~698 s of 1519 s / 697 s of 900 s). The derivative `sub-54_task-baba_desc-preproc_meg.fif` (39 MB)
  appears complete, so the authors have the full raw file.
- sub-44/45/46 MEG derivatives are near-empty (0.1-0.6 MB).
- The paper says sensor positions were not digitised; the fifs contain head-shape points and placeholder fiducials
  with an identity device-to-head transform.

## Restructure 2026-11-25 (not yet re-validated on data)
- Adaptor subclasses BaseAdaptor; onset checked with choice(). onset.csv moved to `alignment/onset.csv`
  (subject_delays.py writes it there through ONSET_CSV). Bads via iohelpers.mark_bads (strict). The ffmpeg reader is
  kept (float32 f32le, full scale +-1, not clipped) and so is raw._raw_extras (tests/test_mne_private_api.py). No
  change to the onsets or the drift.
- Bads: iohelpers.mark_bads adds the adaptor's list to any bads stored in the shipped fif (the old code replaced
  them); the second pass should check whether the fifs carry their own bads.
