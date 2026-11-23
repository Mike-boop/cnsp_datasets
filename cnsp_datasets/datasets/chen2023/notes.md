# chen2023: Chen et al. (2023, NeuroImage), TRIUX MEG, audiobook at six noise-vocoding levels

> **Licence: ANC Data Use Agreement 1.0.2.** Use, modification and combination for scientific or educational
> purposes are allowed, but **section 2.2 forbids redistributing the dataset "in whole or in part, in any form"**,
> and publications must cite it with the commit hash. Local standardisation is fine; standardised copies must not be
> shared or uploaded without the data custodian's permission (user decision).

Explorer + standardiser notes, 2026-11-23. Scratch: `/data_storage/gu08wuvu/datasets/tmp/review/chen2023/`
(`download/`, `meta/` = API tree and LFS pointers, `explore/events/*.json` = STI101 per run, `explore/trials.csv`,
`code/` = authors' repository and Gaudrain's vocoder toolbox, `standardised/`, `validation_cond/`, figures, logs).
Scripts: `tmp/review/scripts/chen2023_*.py`. That folder is temporary; the numbers that explain the code are here.

**Headline.**
1. 24 subjects, 525 trials (one per excerpt heard), 19.4 h. Clean audio is shipped, **the vocoded sounds are not**.
2. Trial -> wav: STI101 code = condition base + wav number (authors' code), confirmed by response times and by no
   subject hearing a wav twice (section 3). **events.tsv misses 5 trials** and has no wav numbers: the adaptor uses
   the trigger table `triggers.csv` built from STI101 by `triggers.py`.
3. Onset = trigger + **16 ms trigger-to-sound delay measured by the authors** (Black Box Toolkit v2, paper 2.2).
   With drift corrected, the 30-60 Hz TRF matches habersetzer2025 (audio-copy onsets) to +1 ms [0, 3].
4. **Audio vs MEG clock drift of about +500 ppm**, measured from the MEG itself (no audio copy; section 7): best
   drift per subject 352-631 ppm (median 525, 12 subjects), like the +485 ppm (habersetzer2025) and +538 ppm
   (yang2026) of other TRIUX setups. Uncorrected, it costs 14% of the low-tier r and all of the 30-60 / 30-250 Hz
   response. A fine scan (350-650 ppm, 30-60 Hz TRF SNR) puts the peak at **510.5 ppm, 95% CI 502-518**
   (per subject 469-541). **Applied by default: `drift_ppm=510`** (data-derived; approved by the user 2026-11-23);
   4 held-out subjects standardised with it reach the brainstem tier (4/4 subjects significant in every tier).
5. MaxFilter SSS already applied by the authors: the 30-250 Hz validation runs on the data as shipped.

## 1. Source
- Austrian NeuroCloud (ANC) BIDS server, a public GitLab with the data in Git LFS:
  `https://data.anc.plus.ac.at/bids-datasets/auditory/yc_audiobook_vocoding` (landing page
  `https://bids-datasets.data-pages.anc.plus.ac.at/auditory/yc_audiobook_vocoding/`, DOI 10.60817/v2fd-cq35).
  Registry entry `chen2023`, source `gitlab_lfs`, pinned to commit `0a5a02a22a3c41e2eba6fff3e2a25fdc1ddda6bf`
  (2026-10-21). 761 files, 108.6 GB (175 fif = 107.5 GB, 24 wav = 1.12 GB). Downloaded 2026-11-23 (44 min, 3
  workers, no failures); every LFS file matched its pointer's size and sha256 (`verify_sha256.log`).
- Paper: Chen, Schmidt, Keitel, Rösch, Hauswald & Weisz (2023), "Speech intelligibility changes the temporal
  evolution of neural speech tracking", NeuroImage 268:119894, doi:10.1016/j.neuroimage.2023.119894
  (`data_campaign/papers/chen2023.pdf`). Same MEG data as Study 2 of Hauswald et al. (2020).
- Authors' code: https://gitlab.com/yapingchen/vocoded-speech-trf-meg (commit 7a8409c, MATLAB/FieldTrip; read, not
  run). Vocoder: Gaudrain's toolbox, https://github.com/egaudrain/vocoder (commit 09e4452; read, not run).

## 2. Layout
BIDS 1.11.2, raw. `sub-<12 hex>/ses-1/meg/sub-*_ses-1_task-audiobook_run-0[1-8]_{meg.fif,meg.json,channels.tsv,
events.tsv}` + `coordsystem.json`; `participants.tsv` (age, sex, handedness, acq_time); `stimuli/01.wav ... 24.wav`.
No derivatives, no MRI.

- 24 subjects (pseudonymised ids; 11 F, ages 18-45), one session, one run per block of 3 excerpts (8 blocks).
- **Missing runs (upstream question; not fixable here):** `sub-400fb1b90f57` has only run-08 and `sub-520e215b49cf`
  only run-02 (3 trials each); `sub-2bf97e558a62` lacks run-02, `sub-2224b4d06ea2` run-05, `sub-78f50f9a795e` run-04.
  Every run present holds exactly 3 stimulus triggers. 525 of 576 presentations remain. The README says that no one
  was excluded, so the runs were probably lost in the BIDS conversion.
- **Date mismatch (upstream question):** `sub-520e215b49cf` run-02 `meas_date` is 2019-04-26, `participants.tsv`
  acq_time 2019-04-10.
- Subjects are numbered 1-24 in the order of their sorted ids (`sub-001` = `sub-0c8a4f5c9ada` ...); the original id
  is in each trial's provenance (`original_subject`).

## 3. Stimulus <-> trial mapping
- STI101 codes (authors' `c02_sens_coh_vocoding.m`, `src_audio.m`): original 51-74, 7-ch 81-104, 5-ch 111-134,
  3-ch 141-164, 2-ch 171-194, 1-ch 201-224, i.e. **code = base + wav number** (bases 50, 80, 110, 140, 170, 200).
  `my_lip_noise_5lev_trials_audio.m` defines trials on codes 51-224.
- `find_events(min_duration=2 ms)`: a 1-sample transition value precedes some codes (48 -> 53).
- Evidence (`scripts/chen2023_mapping.py`, all 175 runs, 525 trials):
  - the response button (8192) always comes after the mapped wav has ended: 0.9 s minimum, median 3.1 s (411
    trials with a button event). With random code -> wav mappings, 25% of responses would fall before the end;
  - no subject hears any wav twice, and the 19 complete subjects hear all 24;
  - no trial runs past the end of its recording.
- events.tsv: onset = trigger to within 1 ms and the same condition labels, but **it misses one stimulus in 5 runs**
  (`sub-0c8a4f5c9ada` run-08, `sub-2bf97e558a62` run-05, `sub-8c0c8958b4cc` run-03, `sub-b9675d54460d` run-08,
  `sub-d972c43b1205` run-02): 520 rows vs 525 triggers. Other STI101 values: 16384 (button press that starts the
  next trial), 8192 then 8214 (response; 22 = answer code); AnsCorrect/AnsWrong/NoResp in events.tsv.
- Each excerpt is heard once per subject; 3-5 excerpts per condition per subject (Latin square by blocks; the same
  condition can occur twice in a run).

## 4. Speech features
- `stimuli/NN.wav`: clean audio (the "original" condition), 44.1 kHz, float32, **dual mono** (L = R exactly), 12
  excerpts of 180-194 s (01-12) and 12 of 16-152 s (13-24); 3174.5 s in total (0.88 h of unique audio).
- **Vocoded sounds are not shipped.** Parameters (paper 2.2 + toolbox defaults): Gaudrain vocoder, 200-7000 Hz,
  n = 7/5/3/2/1 bands equidistant on the Greenwood map (a = 0.06, k = 165.4), 3rd-order Butterworth band filters
  applied with filtfilt, envelope = half-wave rectification + 2nd-order Butterworth low-pass at 250 Hz (filtfilt),
  normalised to its maximum, binary noise carrier (`sign(rand - 0.5)`, the same noise for every band because
  `rng(seed)` is called per band), re-filtered in the band, band RMS matched to the analysis band, total RMS
  matched to the 200-7000 Hz band of the input. The noise seed was `sum(100*clock)` (toolbox default), so the noise
  fine structure **cannot be reproduced**. Band edges and filter orders are toolbox defaults the paper does not
  restate (the paper's "two Butterworth filters with a range of 200-7000 Hz" is read as that range).
- Port: `vocoder.py` (seed = 100 x wav + n, deterministic). Rebuilt broadband 0.5-8 Hz envelopes correlate
  0.97-0.99 with the clean ones (wav 15), as the paper's Fig. 1B says; so the clean envelope is a good regressor for
  the low-frequency tier, while the high-frequency feature of a vocoded trial is unknown either way.
- No transcripts or word timings shipped.

## 5. Neural data
- MEGIN TRIUX, 1000 Hz, online 0.1-330 Hz, SI units (T, T/m, V). **MaxFilter 2.2.15 SSS applied by the authors**
  (movement compensation between blocks to a common head position); `info['bads']` empty in every file.
- Channels kept: 204 grad + 102 mag, EOG001, EOG002 (type eog; vertical/horizontal assignment unknown: EOG001
  correlates 0.95 with lateral magnetometers on both sides at 1-15 Hz, so neither looks like a clean VEOG), ECG003,
  **EEG010** (one EEG electrode, placement unknown; correlates 0.98 with EOG001 at ~1/9 of its amplitude; kept as
  misc). Dropped: IASX/Y/Z (internal active shielding), SYS201, STI001-008, STI101 (triggers are in triggers.csv).
- **No stimtrack/audio channel** (no MISC), so no audio copy.
- cHPI coil info present; digitised head shape in the fif.

## 6. Alignment
- Presentation: Psychtoolbox via the obob toolbox, VPixx SOUNDPixx pneumatic in-ear phones, TOUCHPixx response box.
  Trigger type is not documented; VPixx systems usually time triggers and sound from one device. The authors
  measured a **16 ms trigger-to-sound delay** (Black Box Toolkit v2; it includes the tubes) and shifted their data
  by 16 samples (`preproc_ICA_lag16.m`).
- Adaptor: onset = STI101 trigger sample + `sound_delay_ms` (default 16, the authors' value), trial length = wav
  length (ceil at 1000 Hz), no resampling (native 1000 Hz). Drift: `drift_ppm`, default `DATA_DRIFT_PPM` = 510
  (MEG-derived, approved by the user 2026-11-23; 0 = no correction), folded into the crop (`crop_on_audio_clock`,
  one interpolation). Provenance: `drift_ppm` (estimate), `drift_corrected_ppm` (applied), `drift_source`
  ("data-derived ... approved by the user 2026-11-23").
  Trial = 3 x (run - 1) + position. Every recording extends >= 6.3 s past its stimulus even at +1000 ppm.
- Drift and latency are estimated from the data in section 7.

## 7. Validation
Pilot standardisation (default options: clean stimuli, 16 ms, no drift): 498 trials of 22 subjects, 80 GB, in
`R/chen2023/standardised/` (`sub-5551a7b45438` and `sub-400fb1b90f57`, 27 trials, failed in that run because of
their other peripheral channel set; fixed in 5bc9cd4 and checked in memory, not written, to save storage).
Validator `checks.validate_subject` on magnetometers (102), no re-referencing (SSS data); scripts
`R/scripts/chen2023_validate.py`, `chen2023_summary.py`, `chen2023_drift_scan.py`, `chen2023_drift_summary.py`,
`chen2023_latency.py`; results `R/chen2023/validation_cond/summary.json`, `R/chen2023/drift_scan/summary.json`.

**As standardised (no drift correction), 22 subjects:**

| subset | low r | subjects sig. | 30-60 Hz SNR (p) | 30-250 Hz SNR (p) |
|---|---|---|---|---|
| all | 0.0350 | 21/22 | 0.99 (0.16) | 1.02 (0.13) |
| original | 0.0326 | 13/21 | 0.98 (0.28) | 1.02 (0.15) |
| vocoded, clean wav | 0.0352 | 21/22 | 0.98 (0.24) | 1.02 (0.19) |
| vocoded, rebuilt | 0.0337 | 21/22 | 0.95 (0.65) | 1.01 (0.28) |

Low tier passes in every subset (p_circ 0.02 and p_mismatch 0.048, the minima of 50 and 20 nulls); r per level,
clean / rebuilt: 7-ch 0.0390 / 0.0369, 5-ch 0.0319 / 0.0316, 3-ch 0.0310 / 0.0299, 2-ch 0.0295 / 0.0281, 1-ch
0.0239 / 0.0218 (tracking falls with fewer bands; the clean wav is never worse than the rebuild). Figure
`R/chen2023/r_by_condition.png`. High tiers fail; `R/chen2023/hf_trf_vs_habersetzer.png` shows no response at all,
against habersetzer2025 (tSSS, audio-copy aligned: 30-60 Hz SNR 1.40, 30-250 Hz 1.25, both p = 0.01).
The validator's half-to-half drift (+508 +- 729 ppm SE) and jitter (MAD 28 ms) are uninformative with these short
trials (`R/chen2023/drift_jitter_per_subject.png`).

**Drift scan (validation only; 12 complete subjects, 24 trials each):** each trial resampled for an assumed drift
d (MEG samples per audio sample - 1) before the validator. Low-tier r relative to d = 0: -500 ppm 0.84, +250 1.10,
**+485 1.14**, +750 1.12, +1000 1.05; the r curve peaks at a positive drift in every subject (352-631 ppm, median
525). High tiers, 0 vs +485 ppm: 30-60 Hz SNR 1.02 (p 0.07, 0/12 subjects) vs **1.61 (p 0.01, 10/12)**;
30-250 Hz 1.02 (p 0.16, 2/12) vs **1.39 (p 0.01, 9/12)**. Figures `R/chen2023/drift_scan_r.png`,
`R/chen2023/drift_scan_hf.png`. With +485 ppm the dataset reaches the brainstem tier (MEG window 28-45 ms).

**Onset latency (not applied):** with +485 ppm, the 30-60 Hz TRF GFP is shifted against habersetzer2025's by
**+1 ms [0, 3]** (group, bootstrap 95% CI; per subject -9 to +11 ms; peaks 40 vs 38 ms), i.e. the authors' 16 ms
delay is right to a few ms. The 30-250 Hz curves differ in shape (chen2023 peak 39 ms vs 20 ms), so their +13 ms
shift is not read as an onset error. Figure `R/chen2023/latency_per_subject_drift485.png`
(`R/chen2023/latency_per_subject.png`: the same without drift correction, flat TRFs, uninformative).
The DNN offset check (accou2023) is EEG-only and was not run.

**Fine drift scan (validation only; same 12 subjects):** 350-650 ppm in 25 ppm steps. The drift is applied to the
stimulus instead of the MEG (the MEG sample t pairs with stimulus time t / (1 + d): the feature is stretched by
1 + d), which to first order equals the adaptor's resampling of the MEG; checked on S001, 1.17 / 1.25 at
475 / 500 ppm against 1.22 at 485 ppm from MEG resampling. Scores: the validator's 30-60 Hz TRF SNR (same
settings) and its low-tier r. Peak of the subject-mean curve (parabola through the maximum), bootstrap over
subjects (2000):
- 30-60 Hz SNR: **510.5 ppm, 95% CI 502.1-518.2**; per subject 469-541 ppm (median 507); mean SNR 0.99 at
  350 ppm, 1.67 at 500 ppm, 1.07 at 650 ppm; 11/12 subjects significant (p < 0.05) at the grid maximum;
- low-tier r: 535 ppm, 95% CI 486-571 (flat over this range: r changes by < 1%).
Figure `R/chen2023/drift_scan_fine.png`; script `R/scripts/chen2023_drift_fine.py`, summary
`chen2023_drift_fine_summary.py`, results `R/chen2023/drift_fine/summary.json`. Default set to 510 ppm (the
pooled peak rounded to 5 ppm).

**Drift-corrected pilot (default `drift_ppm=510`):** 4 complete subjects held out from both scans (11 =
`sub-5551a7b45438`, the other channel setup, 19, 20, 21), 96 trials, 16 GB, `R/chen2023/standardised_drift/`;
validator on magnetometers (`R/chen2023/validation_drift.json`, figure
`R/chen2023/validation_drift/validation.png`):

| | low r | 30-60 Hz SNR (p) | 30-250 Hz SNR (p) | tier |
|---|---|---|---|---|
| subjects 19-21, no drift correction (pilot 1) | 0.035 (3/3 sig.) | 0.92 (0.60; 0/3) | 0.96 (0.77; 0/3) | low |
| subjects 11, 19-21, +510 ppm | 0.042 (4/4) | **1.87 (0.01; 4/4)** | **1.64 (0.01; 4/4)** | **brainstem** |

Per subject (+510 ppm): 30-60 Hz SNR 1.95 / 1.34 / 2.08 / 2.10, 30-250 Hz 1.34 / 1.21 / 1.62 / 2.38 (subjects 11,
19, 20, 21). Low r of 19-21: 0.029 / 0.033 / 0.044 -> 0.035 / 0.035 / 0.048. The TRFs peak at 20-50 ms with nothing
at negative lags. Trial-offset jitter MAD 17 ms (0.5-8 Hz; not a hardware measure).

The first pilot (`R/chen2023/standardised/`, 498 trials, 80 GB, no drift correction) was deleted on 2026-11-23 at
15:12 CET with the user's approval.

Validation tier: **brainstem** with the default `drift_ppm=510` (`low` without drift correction).

## 8. Data size
19.39 h over 24 subjects (525 trials, longest = only stimulus per trial): mean 0.81 h per subject, range
0.10-0.88 h; the 19 complete subjects 0.88 h each. Per condition 3.15-3.36 h in total; per complete subject
6.8-11.3 min per condition (means 8.4-9.2 min).

## 9. Open questions (user decisions), with recommended defaults
1. **Vocoded stimuli.** Default `vocoded="clean"`: vocoded trials carry the clean source wav (envelope r 0.97-0.99
   with the vocoded one). `"rebuild"` gives a vocoded rebuild with fresh noise (band envelopes right, fine structure
   not); `None` keeps the original condition only. Recommended: keep "clean" as the default and document it.
2. **The 16 ms delay** is applied by default (authors' measurement, hardware-measured, like habersetzer2025's
   acoustic delay; confirmed to +1 ms [0, 3] by the drift-corrected 30-60 Hz TRF). Approve, or set
   `sound_delay_ms=0`.
3. **Drift correction: decided.** Approved by the user 2026-11-23; default `drift_ppm=510` (fine-scan pooled
   peak 510.5 ppm, 95% CI 502-518). One dataset value, not per subject (per-subject peaks 469-541 ppm are within
   the scan's noise).
4. **Licence**: no redistribution of standardised copies without the custodian's permission.
5. Upstream questions: the 5 incomplete subjects, the events.tsv gaps, the `sub-520e215b49cf` date.
6. Subject numbering 1-24 (sink needs ints; PLAN says keep original names): original ids are in the provenance.
7. Storage: the first 80 GB pilot was deleted (user approval, 2026-11-23); `R/chen2023/standardised_drift/` (16 GB,
   4 subjects) remains. A full run would be ~85 GB (19.4 h x 1.24 MB/s).

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**poor**: STI101 trigger + 16 ms (authors' Black Box Toolkit); drift +510 ppm is brain-derived (30-60 Hz TRF-SNR scan), user-approved; no audio copy; brainstem with drift.
