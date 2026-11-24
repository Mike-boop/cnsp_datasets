# miran2020b: notes

Instructed attention switching experiment of Miran et al. (2020), 7 subjects, KIT MEG, DSS-denoised epochs at 200 Hz.
Sibling dataset: `miran2020` (at-will switching, one subject, raw). Scratch: `tmp/review/miran2020b/`, scripts
`tmp/review/scripts/miran2020/`.

## 1. Source
- DRUM hdl 1903/26352, item d935265d-895c-4fc7-aec2-36dc7682d87d ("instructed attention switching"). One file,
  `Instructed Attention Switch Experiment.zip` (659,184,825 B, stored uncompressed). No licence stated (open
  access).
- Paper: Miran S, Presacco A, Simon JZ, Fu MC, Marcus SI, Babadi B (2020). Dynamic estimation of auditory temporal
  response functions via state-space models with Gaussian mixture process noise. PLoS Comput Biol 16(8):e1008172,
  doi:10.1371/journal.pcbi.1008172 (`data_campaign/papers/miran2020.pdf`). The data are from Akram S, Presacco A,
  Simon JZ, Shamma SA, Babadi B (2016), NeuroImage 124:906-917 (their ref. 50).
- No code shipped. README.txt in the zip (quoted in section 3).
- Download 2026-11-24 (registry `miran2020b`, DRUM, 1 worker): size and md5 = DRUM listing (`integrity.tsv`).
  Extracted by hand into `tmp/review/miran2020b/x/` (the zip is kept for the vault). `download_dataset(...,
  extract_archives=True)` gives the same tree; the adaptor globs recursively.
- **Vault backup** (2026-11-24, `scripts/miran2020/backup.sh`): zip + `download_log.tsv`, `integrity.tsv`,
  `drum_listing.json`, `backup_manifest.tsv` in `csnhr:/home/vault/iwpm/iwpm104h/miran2020b/`; every file checked
  with `stat` against the manifest, 0 mismatches (`backup_verify.txt`).

## 2. Layout
- `MEG/S{8,9,10,11,14,15,16}/ssbj<N>_epochData{5,6}_DSSed.mat` (MATLAB v5, `scipy.io.loadmat`), 14 files:
  - `data_DSSed` float64 (12000 samples, 156 channels, 3 repetitions); **S9: 155 channels**;
  - `data_DSSDomain` float64 (12000, 10, 3): the 10 DSS components.
- `Speech/Sp1.wav`, `Speech/Sp2.wav`: mono int16, 44.1 kHz, 60.000 s (2,646,000 samples).
- `README.txt`.

## 3. Stimulus <-> trial mapping
- README: "Two speakers presented monaurally (7 subjects). Listeners attended to one of the speakers for 0-28 s and
  switched to the other speaker for 30-60 s (a pause presented at 28-30 s as a switching cue). 5. 2-speakers
  (Sp1+Sp2, Sp1 attended from 0-28 s, Sp2 attended from 30-60s); 6. 2-speakers (Sp1+Sp2, Sp2 attended from 0-28 s,
  Sp1 attended from 30-60s)". 1000 Hz recording downsampled by 5 to 200 Hz.
- Paper (Methods): 7 normal-hearing young adults (20-31 years); four segments of *A Child's History of England*
  (Dickens) read by a male and a female reader; "two different 60 s-long speech mixtures", each presented
  **diotically** for three trials; attend one talker for 0-28 s, switch after a 2 s pause (28-30 s), keep the other
  until the end; comprehension questions after each mixture. Recorded at **2 kHz** (the README says 1 kHz; either
  way 200 Hz after decimation).
- **Both conditions carry Sp1 and Sp2, as the README says** (`halves_scan.py`, `explore/halves_scan.{txt,json}`):
  backward decoder on the 10 DSS components (1-8 Hz, 100 Hz, lags 0-400 ms, ridge), leave-one-trial-out over the
  subject's 6 trials, mean over 7 subjects: every stream x condition x half peaks at 0 shift (5 s scan, 50 ms
  steps), r 0.066-0.135 at 0 vs |r| <= 0.027 at +-2 s. So the paper's "two different mixtures" does not describe
  these files; the four segments are presumably the two halves of each wav. Mixture = Sp1 + Sp2 at lag 0.
- **No 2 s pause in the wavs**: speech continues through 28-30 s in both (RMS per second 924-1557 in Sp1, 941-1302
  in Sp2; `stim_check.py`). The second half peaks at 0 shift, not +2 s, so no pause was inserted into the timeline;
  whether the talkers were muted at 28-30 s during playback is unknown. The adaptor keeps the wavs as shipped and
  marks 28-30 s with a `switch_cue` annotation.
- Talkers (F0, `consistency_b.py`): Sp1 male (123-129 Hz in both halves), Sp2 female (178-184 Hz).
- Diotic (paper) vs "monaurally" (README): not resolvable from the data; only the separate talkers are shipped.
  Recorded as diotic per the paper, with the README wording in the README of this dataset.
- Trials: 3 repetitions per file; presentation order unknown. Adaptor: trials 1-3 = file 5 (`sp1_then_sp2`), 4-6 =
  file 6 (`sp2_then_sp1`).
- Earlier pilot correlation (`consistency_b.py`, previous session): DSS component 1, 1-8 Hz, |r| between trials
  0.25-0.40 within a file vs 0.12-0.28 across files, i.e. a shared stimulus with an attention difference.

## 4. Speech features available
- Raw audio of both talkers (44.1 kHz, as shipped). No mixture, transcripts or annotations.
- **Overlap with brodbeck2018 stimuli** (`stim_check.py`; brodbeck2018 `stimuli.zip` from its vault backup, in
  `tmp/review/miran2020b/overlap/`): same book and, by the envelope match, the same LibriVox readings, in a
  different edit: Sp1 10-60 s matches brodbeck2018 `male_1` (envelope r 0.51-0.64 per 10 s chunk, at a lead that
  grows from 0.4 to 1.7 s, consistent with brodbeck2018's shortened pauses); Sp2 20-40 s matches `female_2` 0-10 s
  (r 0.48-0.60). Not identical files. Chance level of this search is r ~0.35-0.45 with random lags.

## 5. Neural data
- KIT 157-channel axial-gradiometer MEG (UMD; MNE type `mag`, coil `FIFFV_COIL_KIT_GRAD`). No reference sensors,
  MISC lines, positions, head shape or `meas_date` shipped. Sampling 200 Hz.
- **Preprocessing by the authors**: `data_DSSed` = `data_DSSDomain @ M` exactly (least-squares residual 8e-16; rank
  10 in every file, `nn_test.py`), i.e. the 10 DSS components back-projected to the sensors. Not band-pass filtered:
  the PSD falls ~15 dB from 0.2 to 4-8 Hz and stays flat to 90 Hz, with a 60 Hz line relatively ~20 dB stronger
  than in R2082's raw data (`units_b.py`). The paper's 2-8 Hz filter and the reference-channel TSPCA were analysis
  steps; whether TSPCA preceded the DSS here is not stated.
- **Units: unknown.** Values: broadband SD median 1.5-4.2e5 per subject (1-8 Hz: 0.7-1.9e5), DC offsets of a few
  hundred, vs 88 fT broadband / 47 fT at 1-8 Hz in the raw data of the same lab's R2082 (miran2020) in fT. Neither
  fT nor T; the DSS components have SD ~0.01, so the scale is set by the authors' back-projection. **Adaptor:
  multiplied by a nominal 1e-18** (amplitudes then 70-190 fT at 1-8 Hz, the KIT range); `units_as_shipped` in the
  sidecar says so. Absolute amplitudes are arbitrary; correlations and TRF shapes are unaffected. (Open question 1.)
- **Channel labels are not shipped**; 156 channels (S9: 155) for 157 sensors. Nearest-neighbour test
  (`nn_test.py`, `nn_test2.py`, `nn_test.txt`, `nn_test2.txt`): neighbours on MNE's `KIT-UMD-3.lout` correlate
  most (checked on R2082's 157 raw sensors: k=3 neighbour r 0.916 in file order vs 0.105 shuffled and 0.487
  shifted by one; `KIT-157.lout` does not fit, 0.18). For each file, every candidate missing sensor was scored:
  - 156-channel files: the best candidate is always within MEG 054-058 (k = 1, 3, 6 neighbours; all 3 trials of
    both files), margins <= 0.005, because the rank-10 data are spatially smooth. **MEG 056 is assumed missing**: it
    lies in that window for every subject and is the UMD system's dead channel (all zero in presacco2016 and every
    brodbeck2022 subject). If the true missing sensor is a neighbour, at most 2 channels (between 054 and 058) carry
    the label of the adjacent sensor.
  - S9 (155): best pairs within MEG 054-058 and MEG 142-145; **MEG 056 and MEG 144 assumed**.
  - The adaptor writes MEG 001-157 in file order with the missing sensors zero-filled and listed in
    `info['bads']` (sidecar `missing_sensors`). No other channel is flat.
- Subjects: S8, S9, S10, S11, S14, S15, S16 (folder names; subject numbers 8-16). Original R-numbers are not shipped,
  so participant overlap with other Simon-lab datasets cannot be checked (no participant list is shipped).
  Content-hash duplicates are impossible (DSS-processed, 200 Hz; no other dataset ships these files).

## 6. Alignment
- No triggers shipped. The epochs are 60 s, cut by the authors at stimulus onset (README, 12000 samples = the wav
  length). Trigger hardware/software: unknown (Akram 2016 not consulted for this; the KIT lab's TTL lines as in
  presacco2016).
- **Adaptor: shipped timing kept** (t = 0 = epoch start), `alignment_method` `onset_only`, `drift_ppm` null. No
  stimulus cut.
- Check (section 3, `halves_scan.py`): every stream peaks at 0 shift in both halves and conditions (50 ms
  resolution); the low-tier lag sweep is in section 8.
- Drift: not estimable (no triggers; 60 s epochs). At the lab's typical tens of ppm, < 3 ms at 60 s, irrelevant at
  200 Hz.

## 7. Cross-subject duration check
- Every epoch is exactly 12000 samples = the 60.000 s wavs; nothing more can be checked.

## 8. Standardisation and validation (2026-11-24)
- Full run (7 subjects = the pilot; `scripts/miran2020/standardise.sh`): 42 trials, 0 errors, 323 MB
  (`tmp/review/miran2020b/standardised/`, log `standardise.log`). One trial was written first: 7.6 MB MEG.
- **Final run** (after the code review, `scripts/miran2020/standardise_v4.sh`, `standardised_v4/`; comparison
  `tmp/review/miran2020/compare_v4.txt`): data, bads, annotations and audio identical to the validated run; the
  sidecar now carries `validation_tier` `low`. Superseded runs `standardised/`, `standardised_v2/`,
  `standardised_v3/` can go.
- **Validator, low tier** (`scripts/miran2020/validate.sh`; `--picks mag`, no re-reference, all 7 subjects;
  `validation.json`, figure `tmp/review/miran2020b/validation/validation.png`): **pass**. Mean r 0.091 (median
  0.096), 6/7 subjects above the circular-shift null (p_circ 0.020; S8 at r 0.030 is not), TRF peak 47 ms with a
  second component at ~375 ms, GFP at the null level at negative lags. The validator scores the first stimulus
  (Sp1) in every trial, attended or not. Its per-trial offset estimates scatter (jitter SD 60 ms, MAD 15 ms;
  drift -30 +- 716 ppm): noise of 60 s trials at 200 Hz, not a timing finding.
- **Per condition** (symlinked subsets, `tmp/review/miran2020b/by_condition/<cond>/validation.{json,png}`): both
  pass. `sp1_then_sp2` r 0.082, `sp2_then_sp1` r 0.096; 6/7 subjects each, p_circ 0.020, TRF peak 47 ms in both.
- **Attended vs ignored, switch respected** (`scripts/miran2020/attention.py`; `attention.json`, figure
  `tmp/review/miran2020b/r-attended-vs-r-ignored.png`): forward TRF 0.5-8 Hz, 100 Hz, lags -100..500 ms, each
  attention span (0.5-28 s, 30.5-60 s) paired with its attended or ignored talker from the `attend/*` annotations,
  leave-one-trial-out, 20 best sensors chosen on training trials. **Attended > ignored in 6/7 subjects** (mean r
  0.171 vs 0.132; Wilcoxon p = 0.11, n = 7; S8 the exception, also the weakest subject overall). Mean lag sweeps of
  both models peak at 0 shift (100 ms steps).
- Higher tiers: not applicable (200 Hz, DSS rank 10).
- **Alignment grade: medium.** Shipped onsets (authors' epochs, trigger source unknown), confirmed by the low tier
  (47 ms TRF peak, nothing at negative lags), the decoder and forward lag sweeps at 0 shift in both halves and
  conditions, and the attention contrast; no correction.
- Data size (`scripts/data_size.py`): 7 participants x 0.10 h (6 x 60 s), 0.70 h in total; 0.05 h per condition.

## 9. Open questions (defaults applied)
1. Units: nominal 1e-18 scale (default) or another factor; could the authors say? [1e-18, documented as arbitrary]
2. Missing sensor labels: MEG 056 (S9: + MEG 144) assumed from the neighbour test + the dead-channel prior. [yes]
3. Both talkers stored as shipped with `attend/<talker>` and `switch_cue` annotations; is_attended False. [yes]
4. Ship `data_DSSDomain` too? It carries no extra information (DSSed = components @ M). [no]
5. Positions: none (as presacco2016); `KIT-UMD-3.lout` fits the order and could provide 2-D positions. [none]

## 10. Upstream issues (also in `R/upstream_issues.md`)
- Shipped scale of `data_DSSed` unknown (values ~1e5, neither fT nor T).
- Channel labels not shipped; 156 (S9: 155) of 157 sensors with no record of which are missing.
- README vs paper: "monaurally" vs diotic; 1 kHz vs 2 kHz recording; the paper's "two different 60 s mixtures" vs
  the README's Sp1 + Sp2 in both conditions (the MEG agrees with the README); a 2 s pause cue at 28-30 s that is not
  in the wavs.
- Original R-numbers not shipped (participant overlap with other Simon-lab datasets cannot be checked).
