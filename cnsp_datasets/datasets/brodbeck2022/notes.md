# brodbeck2022 (Appleseed audiobook MEG): notes

Explorer notes (2026-11-22). Review scripts: `tmp/review/brodbeck2022/scripts/`, results
`tmp/review/brodbeck2022/results/` (both deleted when the dataset is done; numbers that matter are copied here).
Shared code with the lab's other KIT datasets in `datasets/simon_base/common.py` (2026-11-23; output unchanged).
Sidecar fields `units_as_shipped` ("T") and `reference` ("not applicable (MEG)") on every trial, as in the
lab's other KIT datasets (user decision, 2026-11-23).

## 1. Source
- OpenNeuro ds007870 v1.3.4 "Appleseed Audiobook MEG", doi:10.18112/openneuro.ds007870.v1.3.4, BIDS 1.7.0,
  licence CC0 (`dataset_description.json`). Converted with MNE-BIDS 0.17.0 by the curators (2026), not by the
  original authors' pipeline.
- Paper: Brodbeck C, Bhattasali S, Cruz Heredia AAL, Resnik P, Simon JZ, Lau E (2022). Parallel processing in
  speech perception with local and global representations of linguistic context. eLife 11:e72056,
  doi:10.7554/eLife.72056.
- Original release: Dryad doi:10.5061/dryad.nvx0k6dv0 (same recordings; adds `make_clips.py`, which cuts the
  clips from the commercial audiobook, ISBN 978-1480555280). The audio is copyrighted and is in neither release
  (README "Original audio files are copyrighted and cannot be shared").
- Code: Eelbrain and TRF-Tools (github.com/christianbrodbeck/TRF-Tools, commit 0928036 cited in the paper).
  `derivatives/scripts/` holds only the curators' fsaverage-scaling scripts (`download_fsaverage.py`,
  `get_mri.py`); no experiment or alignment code is shipped.
- Download: 305 files, all `downloaded` in `download_log.tsv`. The 100 Hz `stimuli/*-gammatone.pickle` were
  deliberately not downloaded.

## 2. Layout
- `sub-01..12/meg/sub-XX_task-Appleseed_split-0{1,2}_meg.fif` (one continuous recording, written as two FIF
  split files; MNE joins them when `split-01` is opened), `_events.tsv`, `_channels.tsv`, `_meg.json`;
  `sub-XX_task-Tone_meg.fif` (+ events/channels); `sub-XX_scans.tsv` (acquisition times).
- `sub-emptyroom/ses-YYYYMMDD/meg/*_task-noise_meg.fif`: 8 empty-room recordings, one per recording day
  (`AssociatedEmptyRoom` in each `_meg.json`).
- `stimuli/{1..11,11b}-gammatone1000.pickle` (eelbrain NDVar pickles, see section 4) and `stimuli/{..}.TextGrid`.
- `derivatives/predictors/{stim}~gammatone-{1,8}.pickle`, `~gammatone-on-{1,8}.pickle` (eelbrain NDVars, see
  section 4); `derivatives/mne/sub-XX/meg/sub-XX_desc-ica_ica.fif`, `sub-XX_trans.fif`; `derivatives/freesurfer/`
  (scaled fsaverage, not individual MRIs).

## 3. Stimulus <-> trial mapping
- 11 consecutive excerpts of the audiobook "The Botany of Desire" (Michael Pollan), presented in chronological
  order (paper, Methods "Stimuli"), one recording per subject. `events.tsv`: one `onset` (value 162) and one
  `offset` (value 167) per segment; the `stimulus` column (onset rows) names the stimulus file. Every subject
  heard 1..11 in order; **sub-04 and sub-05 heard `11b` instead of `11`** (README, events.tsv). Same stimuli
  across subjects otherwise.
- Trial = segment number (1-11) in presentation order; trial 11 of sub-04/05 is stimulus `11b` (205.5 s, a
  different and shorter excerpt than `11`, 284.9 s).
- Verification: the trigger interval (offset - onset) matches the stimulus duration to within -6..+17 ms for
  126 of 132 trials (sub-11 trial 5 from `onset`); the six exceptions are explained in section 7.
- Stimulus durations (s; from the 1 kHz `derivatives/predictors` length, which equals `TextGrid` `xmax` exactly):
  1: 224.6, 2: 320.3, 3: 213.4, 4: 210.1, 5: 235.4, 6: 270.0, 7: 231.7, 8: 250.1, 9: 331.4, 10: 232.0, 11: 284.9,
  11b: 205.5. All durations are whole 0.1 s (clips cut by `make_clips.py`, presumably on a 0.1 s grid).
- The `duration` column of `events.tsv` onset rows is the stimulus duration **+ 1.0 s** for every stimulus and
  subject (e.g. 225.6 for stimulus 1). Origin unknown (perhaps a 1 s pad in the original presentation list).
  Do not use it.
- Segments are separated by 31 s to 25 min (questions and breaks; paper "Procedure").
- Tone task (`task-Tone`): ~100 tones (value 163; 96-100 events per subject), 166 s; not continuous speech,
  skipped by default. Tone parameters are not in the paper or sidecars (unknown).

## 4. Speech features available
- **No audio** (copyright). What is shipped:
- `stimuli/{k}-gammatone1000.pickle`: eelbrain `NDVar`, `x` float64 `(256, n)`, dims `Scalar('frequency')`
  20.0 .. 4938.2 Hz (256 ERB-spaced centre frequencies, ascending; index 0 = 20 Hz) and `UTS(tmin=0, tstep=0.001,
  nsamples=n)`; `name='{k}.wav'`. 1000 Hz, n = stimulus duration - 10 ms (1: 224590 ... 11b: 205490). ~430-680 MB
  each.
  - Values are **linear RMS amplitude per band** (no log, no power-law compression): mean ~320-400, max ~1e4
    (int16-like wav scale), PSD of the summed envelope falls by ~4 decades from 1-8 Hz to 100-200 Hz and by
    another ~2.5 decades above 200 Hz (10 ms boxcar), so it is genuine 1 kHz content, not upsampled from 100 Hz.
  - The parameters and length match TRF-Tools `gammatone_bank(wav, 20, 5000, 256, location='left', pad=False,
    tstep=0.001)` at commit 0928036 (`trftools/_sound.py`): squared ERB-filter output averaged over a 10 ms window
    starting at each output sample, then sqrt; `pad=False` gives `floor((len - 10 ms) / 1 ms)` samples, i.e.
    10 ms short, and `location='left'` keeps `tmin = 0`. **Inferred** from the parameters and lengths; the script
    that produced the shipped files is not shipped. Consequence: sample i summarises audio [i, i+10) ms, i.e. the
    feature leads the centred envelope by ~5 ms (TRF latencies come out ~5 ms late).
  - A few values are slightly negative (min -3.4 .. -8.9 against means of ~350; 0.02% of samples, only in the
    high bands). sqrt of a mean square cannot be negative, so the files were post-processed after the filterbank
    (resampling?). Unknown; clip at 0.
- `derivatives/predictors/{k}~gammatone-1.pickle` (1 band), `-8` (8 bands), `~gammatone-on-{1,8}` (acoustic
  onsets): 1000 Hz, full stimulus length (n = duration exactly), `info.longname = 'log(k.wav + 1)'`, 8 bins
  80-274-...-9126-None Hz (centres 165 .. 11707 Hz). These follow the current Eelbrain "Alice" tutorial
  (`gammatone_bank(wav, 80, 15000, 128, location='left', tstep=0.001)`, then log(x + 1), binned) and **not** the
  paper (20-5000 Hz, exponent 0.6). They are log-compressed model features; not used by default.
- `stimuli/{k}.TextGrid`: Praat, tiers `words` and `phones` (Montreal Forced Aligner 1.0.1, paper), `xmin = 0`,
  `xmax` = stimulus duration. Stimulus 1 starts with a word at 0.000 s (clips start in speech).
- **Recommended stimulus feature (per the user decision below):** broadband envelope
  `env[t] = sum over the 256 bands of max(x[f, t], 0)` (linear amplitude, no compression), 1000 Hz, `tmin = 0`,
  n = duration - 10 ms. Optionally pad 10 samples at the end so the length equals the stimulus duration (open
  question 3). Any compression (^0.6 as in the paper, or log) is a model feature and stays off by default.
  Also store the 256-band spectrogram as is (float32) if a spectrogram feature is wanted (open question 4).
- Reading without eelbrain: eelbrain is not installed in the venv. The pickles need only eelbrain's class names:
  a restricted `pickle.Unpickler` whose `find_class` returns stub classes for `eelbrain._data_obj.{NDVar, Scalar,
  UTS}` (state is a dict: NDVar `x`, `dims`, `name`, `info`; Scalar `values`, `unit`; UTS `tmin`, `tstep`,
  `nsamples`) and allows only `numpy.core.multiarray._reconstruct`, `numpy.ndarray`, `numpy.dtype`,
  `numpy.core.numeric._frombuffer` (remapped to `numpy._core` on numpy 2) works
  (`tmp/review/brodbeck2022/scripts/ndvar_stub.py`). Restricting `find_class` also keeps the untrusted pickles
  from importing anything else. The adaptor should carry this reader (small; no eelbrain dependency).

## 5. Neural data
- KIT/Yokogawa 157-channel whole-head system at UMD (paper), stored as FIF by MNE-BIDS (`Manufacturer: Elekta`
  in `_meg.json` is a conversion artefact). 1000 Hz, online 200 Hz low-pass and 60 Hz notch (paper; FIF
  `highpass 0`, `lowpass 200`); recording ~57-60 min per subject (3446-3627 s).
- Channels (all subjects identical, 193): `MEG 001-157` axial gradiometers (MNE `mag`, coil
  `FIFFV_COIL_KIT_GRAD`, unit T, cal 1; values ~1e-12 T), `MEG 158-160` reference magnetometers (`ref_meg`,
  `KIT_REF_MAG`), `MISC 001-032` (V), `STI 014` (synthesised trigger channel). Units as shipped: T and V
  (output: T only; MISC dropped). No EEG/EOG/ECG. No software compensation applied (`comps` empty,
  `GradientOrder 0`), no projectors.
- MISC content (sub-01, full recording, `misc_scan.py`, `misc_rms.py`): MISC 003 and MISC 008 are 0/5 V trigger
  lines (pulses of 5 ms); MISC 002, 004-007, 009-029 are constant 5.0 V (idle lines; MISC 004 is the Tone line,
  code 163); MISC 001, 030, 031, 032 are low-level noise (std 1.9 mV, 1.5e-4 V steps), with the same power during
  speech and between segments (ratio 0.98-1.00 at 1-30 and 80-200 Hz) and envelope correlation with the
  gammatone |r| < 0.03 at any lag within +-2 s. **There is no audio copy or stimtrack in the MEG.**
- Reference: not applicable (MEG). Reference sensors kept as `ref_meg` for optional denoising.
- Bad channels (`channels.tsv` status = FIF `info['bads']`): sub-01 001,016,030,056,067,099,116; sub-02
  001,016,024,030,056,067,099,118,135; sub-03 001,016,030,056,062,067,099; sub-04 001,030,056,067; sub-05
  001,016,024,030,056,067,115,147; sub-06 001,016,024,030,056,067,115; sub-07 016,030,056,067,115; sub-08
  016,030,056,067,118; sub-09 016,030,056,067,099,118; sub-10 056,067; sub-11 016,030,056,067,118; sub-12
  016,030,056,067,118 (all `MEG nnn`). MEG 056 and 067 are bad in every subject.
- Digitisation: 3 fiducials, 5 HPI (marker coils), 1137 Polhemus head-shape points (Appleseed FIF; the Tone FIF
  has no HPI points); `dev_head_t` present (paper: average of pre and post measurements). `derivatives/mne`
  `*_trans.fif` coregisters to scaled fsaverage.
- Split files: sub-01 split-01 holds samples 0-2,779,999, split-02 2,780,000-3,463,999 (continuous, no gap);
  segment 9 of sub-01 crosses the boundary. Open `split-01` with `mne.io.read_raw_fif` and the split is
  transparent; never open split-02 on its own (its `first_samp` is 2,780,000).
- Subject facts: 12 native English speakers, 19-23 y; sub-11 left-handed (`participants.tsv`, paper). Recording
  dates (`scans.tsv`): sub-04, 05 on 2019-12-11, sub-06 2019-12-12, sub-07 2019-12-13, the rest 2020-02-19 to
  2020-03-06.

## 6. Alignment
- Trigger codes (MNE KIT "channel" coding: value = KIT channel index of the line): **162 = segment onset**
  (MISC 003), **167 = segment offset** (MISC 008), 163 = tone (Tone task, MISC 004). 5 ms pulses.
- `events.tsv` onsets and offsets equal the `STI 014` events to the sample in all 12 subjects (`sti_check.py`),
  with two exceptions in sub-11:
  - offset of segment 5: `sample` = 142111 in `events.tsv`, but `onset` = 1421.113 s (a dropped digit; STI 014
    has 1421113). Use `onset` (or STI 014), not `sample`.
  - STI 014 has **12 onset triggers**: an extra 162 at 1510.677 s with no offset, 89 s after the offset of segment
    5 and 131 s before the onset that `events.tsv` uses for segment 6 (1641.303 s; that onset-offset interval
    matches stimulus 6 to 1 ms). A false start of segment 6: how much of it was played is unknown (no audio
    channel). `events.tsv` (CHANGES 1.1.0 "fixed events.tsv for sub-11") keeps the restart; so should the adaptor.
- Trigger pulses are 4-5 samples long.
- Hardware vs software triggering: **unknown**. The paper does not describe the presentation software or how
  the triggers were generated (Methods "Procedure" and "Data acquisition"). The triggers are TTL lines recorded by
  the KIT system (hardware-recorded), but whether they are locked to the sound output is not documented.
- Stimtrack: none (section 5). The onset cannot be measured from the data; the absolute audio latency relative
  to trigger 162 (sound-card buffer, earphone tubing: "foam pad earphones inserted into the ear canal") is
  unknown.
- **Proposed alignment:** trial starts at the trigger-162 sample (= `events.tsv` `onset`, or STI 014; not the
  `sample` column, see sub-11), no offset correction, no drift correction (section 7). Neural trial length =
  stimulus duration (the trigger interval is 1-17 ms longer, 1.265 s for six trials); stimuli are not cut.
  `onset_source = trigger`, `jitter_ms` ~10. Main risk: the absolute audio latency after trigger 162 is unknown
  (no stimtrack); the validator's DNN offset check against accou2023 is the only handle on it.
- Independent check (no audio): envelope-reconstruction lag from the MEG, `decoder_lag.py` (backward model:
  good axial gradiometers, 1-8 Hz, 100 Hz, 40 PCA components, ridge on lags 0-500 ms, trained leave-one-trial-out
  without trials 6-7; shift of the test trial swept +-3 s, 10 ms steps, in the first half, the second half and
  the last 60 s of each trial; `results/decoder_lag_halves.txt`). This is relative (the training trials define
  zero lag) and resolves ~10-20 ms at best; it cannot measure the absolute audio latency. Results in section 7.

## 7. Cross-subject duration check
Trigger interval (offset - onset, ms) minus stimulus duration, all 12 subjects x 11 trials (`durations.py`,
`results/durations.csv`):

| sub | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | -2 | 2 | -2 | 4 | -3 | 1 | 3 | 8 | 2 | 3 | -4 |
| 02 | 7 | -5 | 8 | 14 | 7 | 11 | 13 | 1 | 12 | 13 | 6 |
| 03 | -3 | 3 | -2 | 4 | -3 | 1 | 2 | 8 | 2 | 4 | -4 |
| 04 | 8 | -5 | 8 | -2 | 7 | **1265** | **1266** | 1 | 12 | -4 | 17 (11b) |
| 05 | 8 | -4 | 8 | 15 | 7 | **1265** | **1266** | 2 | 12 | 14 | 1 (11b) |
| 06 | 7 | 11 | 8 | 14 | 7 | **1264** | **1266** | 1 | -5 | 13 | 5 |
| 07 | 7 | -5 | 7 | -3 | 7 | -6 | -4 | 1 | -5 | 14 | 5 |
| 08 | 8 | 11 | 8 | 15 | 7 | 11 | -4 | 1 | -5 | 13 | 5 |
| 09 | -3 | 2 | -2 | 4 | -3 | 1 | 2 | 8 | 2 | 3 | -4 |
| 10 | 8 | 2 | -2 | 4 | -3 | 1 | 3 | 8 | 3 | 3 | -4 |
| 11 | -5 | 2 | -3 | 4 | -3* | 1 | 3 | 8 | 2 | 3 | -4 |
| 12 | -4 | 2 | -3 | 4 | -3 | 1 | 2 | 8 | 3 | 4 | -5 |

(* sub-11 trial 5 from `onset`; the `sample` column gives -1,279,005 ms, see section 6.)

- Errors do not scale with length: per-subject least-squares drift ranges -80 to +10 ppm with intercepts of
  -2 to +22 ms, i.e. no consistent drift; the values are stimulus-specific and take a few discrete states per
  stimulus, ~6-10 ms apart (stimulus 1: -2/-3 or +7/+8; stimulus 4: -3, +4 or +14/15). Six subjects (01, 03, 09,
  10, 11, 12; all recorded 2020-02-26 .. 03-06) share one pattern to +-1 ms; the others (02, 04-08) switch
  between states from trial to trial. Read as: trigger-to-sound timing has a ~10 ms quantisation (consistent
  with software triggers or audio buffers of ~10 ms), plus a stimulus-specific constant of a few ms (e.g.
  silence/rounding at the clip ends). Which of onset or offset trigger carries the jitter cannot be separated
  without audio; with 1 ms trigger resolution and no drift visible, the onset uncertainty is of order +-10 ms
  (unknown sign).
- Fit `error = drift * length + c + noise` over the 126 regular trials (without the six 1.265 s trials; sub-11
  trial 5 from `onset`): drift -26 ppm (bootstrap 95% -54..-2), c 10.0 ms, residual SD 5.7 ms. Split by pattern:
  subjects 01, 03, 09-12: **drift +3.4 ppm (95% -14..+18), c 0.3 ms, residual SD 3.7 ms**, where the residual is
  the stimulus-specific constant (-4..+8 ms, the same in every subject to +-1 ms; one outlier state, sub-10 trial
  1, +8 instead of -3); subjects 02, 04-08: -53 ppm (95% -98..-6), c 19 ms, residual SD 6.3 ms, driven by the
  discrete ~10 ms states rather than by length. No clock drift is established: the clean group shows none, and a
  real clock drift would not differ between subjects recorded on the same day with the same setup (sub-02 and
  sub-01, both 2020-02-26, are in different groups).
- Jitter: per trial, one of the two triggers is displaced by a multiple of ~7-10 ms in about half of the
  recordings. If the displaced one is the onset, the onset error is up to ~10-15 ms in those trials; it cannot
  be resolved without audio. Recommended provenance `jitter_ms`: 10 (order of magnitude; open question 2).
- **sub-04, 05, 06 trials 6 and 7 (stimuli 6, 7): trigger interval 1.264-1.266 s longer than the stimulus.**
  Only the three earliest-recorded subjects (2019-12-11/12); sub-07 (2019-12-13) onward have normal intervals.
  So these subjects heard a different (longer) version of clips 6 and 7 than the shipped gammatone/TextGrid,
  or playback paused, or the offset trigger was late. Where the extra 1.265 s sits (start, end, inside) is
  unknown from the triggers.
- **MEG check (sub-04, 05, 06, all 33 trials):** where the reconstruction is clear (peak r >= ~0.12 and within
  0.01 of the zero-shift r), the best shift is within -30..+30 ms of the trigger in every window, and so
  for trials 6 and 7: sub-04 trial 6 +20 / -10 / +20 ms (first half / second half / last 60 s), trial 7 -10 ms
  (second half; first half and last 60 s too noisy, r 0.10-0.12); sub-05 trial 6 0 / 0 / 0, trial 7 +10 / +10 /
  +10; sub-06 trial 6 +10 / -10 / (noisy), trial 7 +10 / 0 / +20. Windows with poor reconstruction give random
  shifts (+-0.6..3 s), in normal trials as well. **So the shipped stimuli 6 and 7 start at the onset trigger
  and run to their end without a pause; the extra 1.265 s lies after the end of the shipped stimulus** (late
  offset trigger, or a longer clip with extra audio at the end). Trigger onset is usable for these six trials;
  any extra audio after the shipped end is not modelled.

## 8. Data size
12 participants, 0.779 h each (sub-04/05: 0.757 h, with 11b), **9.30 h in total**, from the stimulus durations
(sum of the 11 segments per subject; paper: "46 min and 44 s" = 0.779 h). The recorded neural data cover every
trial completely (last offset 3373-3576 s, recordings 3446-3627 s). `tmp/review/scripts/data_size.py` on the
standardised output (2026-11-22) agrees: 12 participants, 132 trials, 9.3 h, 0.775 h per participant (0.76-0.78);
one condition (`appleseed`). Run on a scratch copy; not yet added to `tmp/review/data_size.csv`.

## 9. Validation tiers (expected)
- `low` (0.5-8 Hz): expected to pass; the 1 kHz gammatone envelope is fine for it.
- `mlr` (30-60 Hz): possible in principle; the gammatone envelope has content to ~200 Hz. Risks: ~10 ms trigger
  jitter (section 7) smears a 30-60 Hz response (half period 8-17 ms), unknown audio latency, the 5 ms lead of
  the `location='left'` window. Only 12 subjects x 47 min. Worth a try.
- `brainstem` (30-250 Hz, 28-45 ms MEG window): not meaningful. Without the waveform there is no fine-structure
  or rectified-audio regressor; the 10 ms integration window low-passes the envelope (first null at 100 Hz) and
  the ~10 ms trigger jitter alone would cancel 100-250 Hz responses. Report as not attempted.

## 10. Upstream issues
- sub-11 `task-Appleseed_events.tsv`, offset of segment 5: `sample` 142111, should be 1421113 (`onset` 1421.113
  is right; STI 014 agrees with `onset`).
- sub-11 STI 014: an extra onset trigger (162) at 1510.677 s, a false start of segment 6 (section 6).
- `events.tsv` onset-row `duration` is stimulus duration + 1.0 s for every row.
- `derivatives/predictors` gammatone predictors use 80-15000 Hz and log(x+1), not the paper's 20-5000 Hz and
  exponent 0.6.
- `_meg.json` says `Manufacturer: Elekta` and `MEGCoordinateSystem: ElektaNeuromag` for a KIT system.
- Stimuli 6 and 7 for sub-04/05/06: trigger interval 1.265 s longer than the shipped stimulus; the shipped
  stimulus matches the MEG from the onset trigger on (section 7), so the clips played to these three subjects
  were probably longer at the end.

## 11. Open questions (human checkpoint)
1. **sub-04/05/06 trials 6-7** (1.265 s longer trigger interval). The MEG check puts the shipped stimulus at the
   onset trigger with no pause (section 7). Recommended default: keep them with the trigger onset, flag them in
   the trial notes; the neural trial is the stimulus length (the extra 1.265 s at the end is not used).
2. **Onset offset/latency**: no stimtrack; recommended default trigger 162 as onset, `jitter_ms` ~10 (from the
   duration check), no offset correction; DNN offset check at validation decides whether a constant shift is
   needed.
3. **10 ms-short feature**: keep the shipped length (n = duration - 10 ms, `tmin = 0`) or pad 10 samples (zero /
   edge) to the nominal duration. Recommended: keep as shipped; record in the provenance. Also whether to shift
   the feature by +5 ms to centre the 10 ms window (recommended: no shift; document the 5 ms lead).
4. **Feature set**: broadband envelope only (recommended), or also the 256-band spectrogram (~3.1 GB float32 for
   all 12 stimuli, 3009 s) as a second feature.
5. **Drift**: none measurable from the triggers (errors do not scale with length); recommended no correction.
6. **Tone task**: skip (recommended), or export as a separate non-speech condition.
7. **11b**: treat as its own stimulus name (recommended), trial 11 of sub-04/05.
8. **Negative values**: clip at 0 before summing (recommended).
9. **sub-11 segment 6 false start** (extra trigger at 1510.677 s): keep segment 6 from the restart at 1641.303 s
   as `events.tsv` does (recommended), flagged in the trial notes (the listener may have heard its beginning
   twice).

## User decisions (2026-11-22)
- The 1000 Hz gammatone spectrograms (`stimuli/*-gammatone1000.pickle`) are accepted as the stimulus feature,
  since no audio was ever released. The recommended envelope (section 4) is derived from them.
- (2026-11-22, later) All recommended defaults accepted: onset = trigger 162, no onset shift (DNN offset check decides
  later), no drift correction; keep sub-04/05/06 trials 6-7 (flagged); sub-11 segment 6 from the restart (false start
  flagged); Tone task skipped; 11b as its own stimulus; negative gammatone values clipped at 0; shipped feature length
  kept, ~5 ms lead documented, not shifted.
- Features: broadband envelope (sum over the 256 bands, linear, 1000 Hz) AND the 256-band gammatone spectrogram.

## 12. Validation (2026-11-22; `/data_storage/gu08wuvu/datasets/tmp/review/brodbeck2022/validation/`, `validation.json`)
Tier: **low, with marginal mlr** (`validation.json` says `mlr`; the mlr pass is population-level only). Basis: the
standardised data as stored, good axial gradiometers (MEG 001-157 minus `info['bads']`), no re-referencing.
Review scripts `brodbeck2022_validate.py`, `brodbeck2022_summary.py`.
- **Low tier passes.** Backward model (LOTO ridge decoder over the 11 trials, lags 0-250 ms, 0.5-8 Hz, 64 Hz;
  50 circular-shift and mismatched-stimulus nulls): mean r **0.281** (median 0.296, range 0.171 (sub-04) -
  0.335), **12/12 subjects** above both nulls; all 132 trials above the circular-shift null. Lag-sweep peak
  +2.8 ms (bootstrap 95% +1.2..+4.7), every subject within one 64 Hz sample. Repo forward low tier: mean r 0.032,
  12/12 significant, TRF peak 109 ms.
- **mlr: marginal.** Repo HF SNR (30-60 Hz, response 18-45 ms vs noise -75..-20 ms, 100 circular-shift nulls), with
  the 1000 Hz envelope as the hf feature (section 15): mean SNR 1.11 (median 1.01; null median 0.94),
  population p = 0.0099 (Wilcoxon vs null median p = 0.021), but only **4/12 subjects** individually (sub-06,
  09, 10, 12). The HF GFP peak is at 58 ms, outside the 18-45 ms window: the response is late and smeared, as
  expected from the ~10 ms trigger jitter and the 10 ms integration window of the feature (section 9).
- **Brainstem: not attempted** (no audio, so no waveform regressor; 10 ms boxcar envelope; ~10 ms jitter).
- **Forward TRF** (envelope -> good gradiometers, 128 Hz, 1-10 Hz, lags -200..600 ms, GFP averaged over subjects):
  **M50 44 ms, M100 105 ms** (subject medians 41 / 109 ms; M50 a local maximum in 6/12 subjects, M100 in 12/12).
  For comparison, gwilliams2023 (KIT, audio-aligned) has its repo low-tier TRF peak at 47 ms. No sign of a large
  trigger-to-sound latency. These latencies include the ~5 ms feature lead (section 4), which is not shifted.
- Trigger-pattern groups (section 7): group A (01, 03, 09-12) vs group B (02, 04-08): M50 39 vs 49 ms, M100 104 vs
  117 ms, relative latency 1.4 vs 10.6 ms, Mann-Whitney p = 0.94 (no difference established). The repo per-trial
  offsets do not track the trigger-interval error (Spearman rho 0.065, p = 0.48, 121 regular trials).
- **Flagged trials do not differ from the rest:** the 7 flagged trials (sub-04/05/06 trials 6-7, sub-11 trial 6)
  have median r 0.238 vs 0.253 for the other trials of the same subjects (Mann-Whitney p = 0.90); all 7 are above
  the circular-shift null; lag-sweep peaks 2-19 ms. Unflagged trials only: mean r 0.281, 12/12.
- Reference-regression variant (3 reference magnetometers regressed out, validation only), sub-04: removes 0.1%
  of variance (median over trials), r 0.171 -> 0.167; no benefit, so the raw data are the basis.
- DNN offset check: not run here (unverified whether a constant offset relative to accou2023 exists).

## 13. Dead channel (found during coherence, 2026-11-22)
- Every subject has **exactly one dead (zero-variance) MEG channel, MEG 056**, at a constant -1.5e-11 T
  (-1.49999995e-11) in all trials. Checked on the standardised files (trials 1 and 11 of all 12 subjects, first
  60 s, all 160 MEG + ref channels: MEG 056 is the only channel with std 0; the next lowest are the reference
  magnetometers at ~2-9e-14 T). The validation sanity check agrees (1 flat channel in each of the 132 trials,
  0 NaN).
- **MEG 056 is already in `info['bads']` as shipped** (`channels.tsv`; bad in every subject, section 5). The first
  report of this finding ("between MEG 057 and MEG 061, different per subject, not in bads") was a check error:
  channel names from the full list were paired with data from `pick('mag')`, which drops bads, so names after the
  first bad were shifted. The low and mlr validation picks (good gradiometers = MEG 001-157 minus
  `info['bads']`) never included MEG 056.
- A first native-rate coherence run gave NaN in every band because it included the bads and with them MEG 056
  (`coherence/native/cache_v1_nan`); the rerun excluded bads and dead channels.
- The user asked for the dead channel to be marked bad; it already is, so the adaptor is unchanged.

## 14. Coherence (2026-11-22; `/data_storage/gu08wuvu/datasets/tmp/review/brodbeck2022/coherence/{128,native}/`)
MEG-envelope coherence, complex mean over subjects, 5 s Hann windows with 4 s overlap, 1 surrogate; bads and the
dead channel excluded (section 13). Ratio to the null:

| band | 128 Hz | native 1 kHz |
|---|---|---|
| 0.2-1 Hz | 6.4 | 6.4 |
| 1-4 Hz | 2.9 | 2.9 |
| 4-8 Hz | 2.7 | 2.7 |
| 8-15 Hz | 1.34 | 1.37 |
| 15-30 Hz | 1.05 | 1.08 |
| 30-60 Hz | 1.04 | 1.06 |

Native only: 60-120 Hz 1.02; 120-250 Hz and 250-500 Hz ~1.00. Consistent with the tiers: strong below 8 Hz, a weak
excess at 30-60 Hz, nothing above 120 Hz.

## 15. Repo validator gaps (found here; both fixed in `validate/load.py` on 2026-11-22, after this validation)
- `load.stimulus_feature(.., 'hf')` returns None for envelope-only stimuli (it builds the hf feature only from
  audio), so `--tiers low,mlr` silently skips mlr for this dataset. The review script patched it to use the
  1000 Hz envelope as the hf feature.
- `--picks mag` keeps the bad channels (`raw.pick('mag')` does not exclude bads). The review script picks good
  gradiometers itself; the repo CLI run (`validation/repo/validation.json`) includes the bads (low mean r 0.032,
  12/12, unaffected in practice).
- Fixes (user, 2026-11-22): `load_neural` now excludes `info['bads']` when picking by type, and the 'hf' feature
  uses a shipped envelope when it is sampled at the hf rate or above. The numbers above predate the fixes.
