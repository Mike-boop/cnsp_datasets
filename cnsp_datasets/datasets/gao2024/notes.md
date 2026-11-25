# gao2024: echoic speech, MEGIN TRIUX neo MEG (Zenodo, authors' preprocessed 100 Hz MEG)

Explorer + standardiser notes (2026-11-24, worker session, autonomous: open questions answered with the
recommended default, listed at the end). Review scripts: `tmp/review/scripts/gao2024/`; figures and logs
`tmp/review/gao2024/` (`figures/`, `agent_log.md`).

## 1. Source
- Zenodo 10472483 (DOI 10.5281/zenodo.10472483), **CC BY 4.0**. "Original Speech and Its Echo are Segregated and
  Separately Processed in the Human Brain": "preprocessed MEG response (resampling to 100 Hz), auditory stimulus,
  individual quantitative observations underlying the data summarized in figures, and the analysis codes".
- Paper: Gao J, Chen H, Fang M, Ding N (2024). PLoS Biol 22(2):e3002498, doi:10.1371/journal.pbio.3002498
  (`data_campaign/papers/gao2024.pdf`).
- Code: `Fig*_new.m` (figure scripts on the `Fig*_data.mat` results only) and `tools.zip` (FDR, colormap, readme).
  No preprocessing or trigger code is shipped. Read, not run.
- Download: not from Zenodo on this server (blocked); the user's `zenodo_slowpull` fetched all 43 files (32.4 GB,
  md5 checked) to woody on 2026-11-24 00:59-01:29; rsync'd to `tmp/review/gao2024/download/`, md5 identical on both
  ends (`md5_woody.txt`, `md5_local.txt`) and against the record (`MD5SUMS`); `unzip -t` OK for all 12 zips; zips
  kept, extracted to `tmp/review/gao2024/extracted/`. No vault backup (woody holds the copy).
- Registry `exclude`: `Fig*_data.mat` (1.1 GB of figure results), `Fig*_new.m`, `tools.zip`.

## 2. Layout
- `exp{1,2,3}_PreData_{k}/sub{n}_{s}.mat` (MATLAB v5, ~185 MB): one file per subject and **segment** s = 1..3
  (story order; file sizes match the segment lengths whatever the condition). Variables:
  - `sig_meg_sum` (1 x 27 cell): the MEG of each story chunk, `n x 306` float64 at 100 Hz;
  - `st`, `et` (1 x 27 int32): start/end trigger of each chunk, in samples at 1 kHz from the start of the
    recording;
  - `sig_eog` (1 x N, 100 Hz): the EOG of the whole recording (absent for exp1 sub13-15 and exp3 sub14, sub16).
- `exp{1,2,3}_behave_result/sub_{n}.mat`: `order_sub` (1 x 3) = condition of segment 1, 2, 3 (section 3).
  `exp{1,2}_question_sum/{n}.mat` (`con_order` = `order_sub`, key codes and correctness of the comprehension
  questions per block), `exp3 .../sub_question_sum.mat` (24 x 3 correctness). `The order of three conditions.txt`
  is empty.
- `Experiment_Stimuli/`: 48 kHz mono int16 chunk wavs.
  - `exp1_stimuli/new/{a}-{b}-{clean-1, delay-2, delay-3, echo-2, echo-3}.wav`, a = 1..12, b = 1..9;
  - `exp2_stimuli/Fir_half_Sti/` same names;
  - `exp3_stimuli/new/{a}-{b}-{clean,delay,echo}.wav` (variable delay) and `exp3_stimuli/vocode/` (1-channel
    noise-vocoded), with `echolist-{a}-{b}.mat` (delays in ms, per pause-delimited stretch) and whole-part
    `{a}.wav`, `{a}-delay.wav` (not used);
  - `exp1_stimuli/question/*.mp3|*_new.wav` (16 kHz): comprehension questions, not standardised.

## 3. Stimulus <-> trial mapping
- Story chunks: segment s holds the 27 chunks (3s-2)-1 .. (3s)-9 (a = 3s-2..3s, b = 1..9). Chunks 10-* to 12-* are
  never used. Established from durations: every file's 27 `et - st` match the 27 wavs of its segment to
  16.8 +- 2 ms (all 144 files; `survey.py`; offset explained in section 7).
- Paper: 3 segments of 12'59", 13'11", 12'56", always in story order; the condition per segment randomised.
- **Conditions.** `order_sub[s]` = condition of segment s. Evidence: in experiment 3 conditions 2 and 3 were
  presented in one block, so they must occupy adjacent segments; with this reading every exp3 order
  ([1,2,3], [1,3,2], [2,3,1], [3,2,1]) does, with the inverse permutation [2,3,1] would put 2 and 3 in segments 3
  and 1. Exp1/2 orders are all 6 permutations; only [2,3,1]/[3,1,2] (subjects 4, 6, 10, 12 of each) depend on the
  reading; confirmed against the authors' own per-condition results in section 9 (27/27 exp1/2 subjects, 21/21
  exp3 subjects for the vocoded segment).
  - exp1: 1 anechoic (`clean-1`), 2 0.125 s 0-dB echo (`echo-2`), 3 0.25 s 0-dB echo (`echo-3`);
  - exp2: 1 anechoic, 2 0.125 s, 3 0.25 s, echo 6 dB above the direct sound;
  - exp3: 1 variable-delay echo, attended (story task), 2 variable-delay echo during a silent movie, 3 vocoded
    variable-delay echo during the movie (`vocode/`).
  - Wav names checked against the paper: `delay-2` = `clean-1` delayed by exactly 125.0 ms, `delay-3` by 250.0 ms
    (r = 1.000); exp1 `echo-k = clean-1 + delay-k` exactly; exp2 `echo-k = 0.5 clean-1 + delay-k` (lstsq gains
    0.500/1.000; A = 0.5 in the paper); exp3 `echo = clean + delay` in `new/` and `vocode/`. Exp1/2/3 `clean` chunk
    wavs are identical (md5), as are the exp1 and exp2 `delay-k` wavs; `vocode/` clean is the vocoded version.
- Subjects: exp1 sub1-15, exp2 sub1-12, exp3 21 of 24 (sub10, 11, 13 missing: the paper excluded 3 whose onset
  trigger was missing). 48 subjects, 3 segments x 27 chunks each = 3888 trials, all present.
- Size (`data_size.py`, from the wavs): 0.652 h per participant (3 x 13.0 min, chunk gaps excluded), 31.3 h in
  total; per condition 0.216-0.220 h per participant.

## 4. Speech features available
- Raw audio of every chunk as played (48 kHz mono int16) plus its two components (direct sound, echo). No
  transcripts or TextGrids.

## 5. Neural data
- MEGIN TRIUX neo, 102 magnetometers + 204 planar gradiometers, sampled at 1 kHz; authors' preprocessing (paper):
  **tSSS**, then **down-sampled to 100 Hz**. The 0.8-10 Hz FIR band-pass of the paper is **not** applied to the
  shipped data (power falls smoothly from 0.1 to 49 Hz; no pass band). Per-channel means are ~5% of the SD
  (mean-removed or high-passed, unknown). Only the 100 Hz data are shipped: no raw fif, no sensor positions, no
  head digitisation, no channel names.
- Units: SI. Magnetometer SD ~3.5e-13 T, gradiometer ~5e-12 T/m (ratio as expected); EOG ~1e-4 V.
- **Channel order**: triplets in Neuromag location order (0110, 0120, ..., 2640), magnetometer first: the
  authors' code takes magnetometers as `1:3:306`, and channels 1, 4, 7, ... have magnetometer amplitudes. The
  location order is confirmed by nearest-neighbour correlation on the Vectorview-all layout (mean |r| with the
  nearest magnetometer 0.88 vs 0.34 for random orders, 1-20 Hz). The order of the two gradiometers within a
  triplet is not verifiable without positions; assumed name order (xxx2, xxx3).
- **Chunks**: each chunk is `ceil(wav length x 100)` samples starting at the chunk's start trigger (`st`), i.e.
  cut by the wav length, not by `et`. The 0.2-5 s gaps between chunks are not in the MEG (only in `sig_eog`).
- EOG: one channel, direction not documented -> `EOG`. Sliced from `sig_eog` at `round(st / 10)`; its blink
  correlation with frontal magnetometers peaks at lag 0 or +1 sample (10 ms) in 30 chunks of 3 files.
- No flat channels (checked in 3 files; the adaptor marks zero-variance channels as bads).

## 6. Alignment
- Triggers: one start (`st`) and one end (`et`) per chunk, at 1 kHz. Hardware or software: **unknown** (not in the
  paper; no trigger code shipped; no audio channel shipped). Headphone model and tube delay unknown.
- Onset: chunk sample 0 = start trigger, as cut by the authors; no shift.
- Drift: corrected by default from the trigger durations (section 7): the MEG is resampled onto the audio clock
  with `crop_on_audio_clock(raw, 0, n, 490e-6)` (one quintic-spline interpolation at 100 Hz; output 1-2 samples
  shorter than shipped). `drift_correction=False` keeps the shipped samples.

## 7. Cross-subject duration check (`duration_fit.py`, `figures/duration_check.png`)
- All 3888 chunks: `(et - st) - wav length = 2.5 ms + 490 ppm x length` (least squares 485.3 ppm, offset 2.7 ms;
  Theil-Sen 489.8 ppm, 95% 484.5-494.3), **residual SD 0.98 ms**. Percentiles of the difference (ms): 1% 8.3,
  50% 17.1, 99% 19.8. The same in all three experiments.
- So the MEG clock counts ~490 ppm more samples per audio second than nominal (the same order as the other TRIUX
  datasets: yang2026 English +538 ppm, habersetzer2025 +485 ppm, the latter measured on an audio copy). Over a 34 s
  chunk this is 16.6 ms (1.7 samples at 100 Hz).
- **Drift, not a stimulus-rate mismatch.** A wrong nominal rate would be a fixed ratio between standard rates
  (e.g. 44.1/48 kHz = 8.1%, or 48/47.952); 490 ppm is a crystal-level clock difference. It is linear in chunk
  length with 1 ms residual SD and the same in all 3 experiments and 48 subjects, and it matches the audio-copy-
  verified +485 ppm of another TRIUX (habersetzer2025): most likely the MEG sampling clock vs the sound card.
  It is measured by the triggers (in MEG samples) against the wav length, i.e. **trigger-derived, not brain-based**,
  so it is corrected by default (CLAUDE.md: hardware/trigger-derived corrections on by default; option
  `drift_correction=False`). Caveat: the trigger source is unknown; if the end trigger was timed by the stimulus
  PC's system clock instead of the end of playback, the 490 ppm would be PC clock vs MEG clock. Either way the
  correction is at most 17 ms at the end of a chunk (< 2 samples at 100 Hz), below what the 100 Hz validation can
  resolve.
- Outliers: the last chunk of segment 1 (2-9, 13.4 s) and of segment 3 (9-9, 11.0 s) are +8-9 ms for every subject
  (wav-specific, constant). First chunk of segment 1 in five subjects: exp1 sub4 +43.8 ms, exp3 sub16 +41.8 ms,
  exp3 sub2/7/8 -1.2 ms (others ~+19 ms), i.e. a start trigger ~25 ms early or ~20 ms late relative to the rest
  (first playback of the session). Not corrected; listed as an upstream issue.
- `jitter_ms`: not set (1 ms residual SD of the durations includes both trigger jitters and wav rounding).

## 8. Adaptor (`adaptor.py`)
- Reads `**/exp{e}_PreData_*/sub*_*.mat`, `**/exp{e}_behave_result/sub_{n}.mat` and `**/Experiment_Stimuli`
  under the download root (extracted zips). The mat file of the current segment is cached (`lru_cache(1)`).
- Subject = 100 x experiment + subject number (exp2 sub3 -> 203); the original name is in the sidecar
  (`participant`, `experiment`). Session 1. Trial = (segment - 1) x 27 + chunk index (1-81, presentation order).
- Conditions: `exp1-anechoic`, `exp1-echo125`, `exp1-echo250`, `exp2-anechoic`, `exp2-echo125-6dB`,
  `exp2-echo250-6dB`, `exp3-echo-attend`, `exp3-echo-movie`, `exp3-vocoded-echo-movie`.
- Neural data: 306 MEG channels (`MEG0111`, `MEG0112`, `MEG0113`, ...; mag coil 3024, grad 3012, no positions)
  + `EOG` (eog) where shipped, 100 Hz, SI as shipped, drift-corrected onto the audio clock (default).
- Stimuli (audio, 48 kHz, int16 / 32768 as float32, uncut): the played sound first (marked attended, also in the
  movie conditions, where attention was on the movie: see sidecar `task`), then the direct sound (`clean`) and the
  echo (`delay`) it was mixed from. Names `<sound>_<chunk>`: played `clean`, `echo125`, `echo250`, `echo125-6dB`,
  `echo250-6dB`, `varecho`, `vocoded-varecho`; components `clean`, `delay125`, `delay250`, `vardelay`,
  `vocoded-clean`, `vocoded-vardelay`. Identical wavs share one name (section 3). In exp2 the direct sound was
  played at half amplitude (`direct_gain` 0.5 in the sidecar; the `clean-1` file is stored as shipped).
- Sidecar: `sw_trigger`, trigger_type `unknown (...)`, `drift_ppm` 490, `drift_corrected`, `experiment`,
  `participant`, `segment`, `chunk`, `chunk_index`, `direct_gain`, `task`, `validation_tier` (low), `units_as_shipped`,
  `reference`.
- Size: ~4 MB per trial (307 channels float32) -> ~15 GB MEG, plus ~1300 unique wavs (~7 GB as float32).

## 9. Condition-label check (`tmp/review/scripts/gao2024/label_*.py`, figures `label_authors.png`, `label_brain.png`)
- A first brain-based check (`label_check.py`: per echo segment, forward-model r with the 0.125-s vs the 0.25-s
  echoic-mixture envelope) put the label on the better envelope in only 33/54 segments. It is a **biased, weak
  test**: r(echo-125) > r(echo-250) in 78-80% of segments whatever was played (the 0.125-s mixture envelope is
  closer to the direct sound's), and the within-subject contrast is right in only 15-17/27. A double-centred
  3-candidate version (clean / echo-125 / echo-250 per segment, all 6 assignments) is at chance too (labels best in
  10/27). Expected from the paper's main result: the MEG tracks the direct sound, not the echoic mixture, so the
  mixture envelope carries little delay-specific signal.
- **Decisive check, against the authors' own results** (`label_authors.py`): the paper's phase coherence (MEG vs
  the direct-sound envelope, 2-s epochs; invariant to linear filtering) recomputed per subject and segment
  correlates with the authors' per-subject, per-condition `phy_coh_clean` (Fig2_data B, exp1; Fig3_data C, exp2;
  0.5-10 Hz x 306 sensors, r up to 0.7). The adaptor's labels (`order_sub[s]` = condition of segment s) are the
  best of the 6 assignments in **27/27 subjects** (margin >= 0.22 in summed r; the authors' subject index = subject
  number - 1), including all 8 subjects with a 3-cycle order (exp1/2 sub4, 6, 10, 12) for which the inverse reading
  would differ. So the labels are those the authors analysed.
- **exp3** (no per-condition coherence shipped): physical check, r(vocoded envelope) - r(natural echoic envelope)
  is largest in the segment labelled vocoded in **21/21 subjects** (incl. sub4, 9, 15 with order [2,3,1], where
  the inverse reading differs). Attend vs movie (conditions 1/2, same stimuli) cannot be told apart this way
  (r attend > movie in 9/21); it rests on the block constraint of section 3.
- Conclusion: no labelling error in the release or the adaptor; the 21 MISMATCH lines came from the weak test.

## 10. Validation (`tmp/review/scripts/gao2024/validate_all.sh`, `validate_cond.py`; `tmp/review/gao2024/validation/`)
- Low tier, 0.5-8 Hz forward model on the played sound (first stimulus), 102 mags, no reference, standardised_v2
  (drift-corrected default). **Pooled: 48 subjects, median r 0.049, mean 0.050, 48/48 significant, p_circ 0.020,
  p_mismatch 0.048, pass** (`validation.json` copied here). Per condition (median r, significant): exp1-anechoic
  0.045 15/15, exp1-echo125 0.062 15/15, exp1-echo250 0.063 15/15, exp2-anechoic 0.054 12/12, exp2-echo125-6dB
  0.055 12/12, exp2-echo250-6dB 0.054 11/12, exp3-echo-attend 0.055 20/21, exp3-echo-movie 0.058 21/21,
  exp3-vocoded-echo-movie 0.033 19/21. Figures `validation/<set>/validation.png`.
- TRF GFP peaks: anechoic 172 ms (exp1, exp2); exp1-echo125 281, exp1-echo250 391, exp3 echo 297, vocoded 62
  (second peak ~270) ms; **exp2-echo125-6dB 31 ms and exp2-echo250-6dB -109 ms** (peaks at -110, +110, +250 ms).
  The mixture regressor 0.5 s(t) + s(t - d) is dominated by the delayed copy, so a response to the direct sound
  appears at about latency - d. Checked (`trf_component.py`, `figures/trf_component.png`, 12 subjects, mags 1-8 Hz,
  lags -300..600 ms): on the direct-sound component the exp2 echo TRFs are flat at negative lags and rise from 0 ms;
  on the played mixture they peak at 50 ms (echo125) and -180 ms (echo250), anechoic 170 ms for both. No onset
  error.
- Validator jitter (SD 127 ms, MAD 59 ms) and drift (-121 +- 350 ppm) estimates are noise for 11-34 s trials at
  100 Hz; the drift is set from the triggers (section 7).

## 11. Alignment grade: **medium**
Onsets = the authors' start triggers (source undocumented, durations consistent with the wavs to 1 ms SD), drift
+490 ppm from the trigger durations (not brain-based), shipped timing kept; low tier passes (48/48), anechoic TRF
peak 172 ms, nothing at negative lags on the direct sound.

## Upstream issues
- Five first chunks with a start trigger ~20-25 ms off the others (section 7).
- `The order of three conditions.txt` in `exp3_behave_result.zip` is empty; the meaning of `order_sub` is
  undocumented.
- No channel names or sensor positions in the MEG files; EOG missing for exp1 sub13-15 and exp3 sub14, sub16.

## Open questions (defaults chosen 2026-11-24, user to confirm)
1. Apply the trigger-derived 490 ppm drift by default (not brain-based; trigger type unknown; section 7). [yes;
   option `drift_correction=False`]
2. `order_sub[s]` = condition of segment s (design constraint, section 3). [settled: matches the authors' own
   per-condition results, section 9]
3. Mark the played mixture as attended in the movie conditions so that it is the first stimulus. [yes; `task`
   in the sidecar says movie]
4. Store the exp2 `clean-1` file at its shipped amplitude with `direct_gain` 0.5 in the sidecar. [yes]
5. Gradiometer pair order within a triplet (xxx2, xxx3) unverified. [keep; documented]

## Restructure 2026-11-25 (not yet re-validated on data)
- Adaptor subclasses BaseAdaptor; drift_correction checked with choice(). No longer imports simon_base (REFERENCE and
  find_one are local; wavs through iohelpers.audio_loader: float32 /32768 as before, rate checked, mono no longer
  enforced). Sorted globs; a subject-segment .mat found twice raises. Zero-variance channels set as bads with
  iohelpers.mark_bads after building the Raw (same list).
