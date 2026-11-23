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
   No audio copy in the recording, so drift cannot be measured on hardware; none is applied.
4. MaxFilter SSS already applied by the authors: the 30-250 Hz validation can run on the data as shipped.

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
  length (ceil at 1000 Hz), no resampling (native 1000 Hz), **no drift correction** (no hardware reference).
  Trial = 3 x (run - 1) + position.
- Drift and latency are estimated from the data in section 7 and **not applied**.

## 7. Validation
(filled after the pilot)

## 8. Data size
19.39 h over 24 subjects (525 trials, longest = only stimulus per trial): mean 0.81 h per subject, range
0.10-0.88 h; the 19 complete subjects 0.88 h each. Per condition 3.15-3.36 h in total; per complete subject
6.8-11.3 min per condition (means 8.4-9.2 min).

## 9. Open questions (user decisions), with recommended defaults
1. **Vocoded stimuli.** Default `vocoded="clean"`: vocoded trials carry the clean source wav (envelope r 0.97-0.99
   with the vocoded one). `"rebuild"` gives a vocoded rebuild with fresh noise (band envelopes right, fine structure
   not); `None` keeps the original condition only. Recommended: keep "clean" as the default and document it.
2. **The 16 ms delay** is applied by default (authors' measurement, hardware-measured, like habersetzer2025's
   acoustic delay). Approve, or set `sound_delay_ms=0`.
3. **Licence**: no redistribution of standardised copies without the custodian's permission.
4. Upstream questions: the 5 incomplete subjects, the events.tsv gaps, the `sub-520e215b49cf` date.
