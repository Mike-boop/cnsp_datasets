# polonenko2026: multiband peaky speech, three experiments (OpenNeuro ds008065)

## 1. Source
- OpenNeuro ds008065 v1.0.1 (`10.18112/openneuro.ds008065.v1.0.1`), EEG-BIDS, licence CC0.
- Polonenko MJ & Eisenreich BR (2026). Optimal parameters for measuring multiband auditory brainstem responses to
  continuous speech. *Trends in Hearing*. doi:10.1177/23312165261465722 (bioRxiv 10.64898/2025.12.24.696406).
- Code in the dataset (`code/exp1_phases`, `code/exp2_f0s`, `code/exp3_f0s2`: experiment, BIDS conversion,
  analysis) and https://github.com/polonenkolab/multibandABR_optimal_params. Shared code:
  `datasets/maddox_base/common.py`.

## 2. Layout
- `sub-exp1NN` (phases, 17), `sub-exp2NN` (f0s, 30), `sub-exp3NN` (f0s2, 15): different participants per
  experiment. `eeg/sub-*_task-<task>_run-0N_eeg.{vhdr,vmrk,eeg}`, `_events.tsv`; two runs for sub-exp221, 301, 303.
- Stimuli `stimuli/<exp>/<story>/<stem>_NNNN.hdf5` (1-based): exp1 `wizardofoz_original_0001..0725`
  (`x_play_band_zero`, `x_play_band_chirp`, `pulse_inds`, `fake_pulse_inds`; no `fs`), exp2
  `{toto,wizardofoz}_{original,shifted}_0001..0900` (`x_play_band_chirp_CE`, `pulse_inds`, `fake_pulse_inds`,
  `fc_band`, `fs`), exp3 `{wizard,wonderland,drdolittle}_shifted_0001..0210` (`x_play_band_chirp_CE`,
  `pulseinds_true`, `pulseinds_fake`, `fs`).
- Audio: 2 x 480000 (left/right ear, 48 kHz, 10 s); dichotic multiband peaky speech (5 audiological bands per
  ear, bands interleaved between ears). 10 pulse trains (row `2 * band + ear`, as the authors' `x[:, ei::2]`) and 5
  "fake" trains for the common component.
- 101 GB (57 GB EEG, 44 GB stimuli).

## 3. Stimulus <-> trial mapping
- 10 s trials, passive listening (no clicks in this dataset). exp1: 720 (360 zero-phase, 360 chirp-phase, the same
  wizardofoz file `NNNN` = trial number in either profile); exp2: 840 (210 per narrator x f0); exp3: 630 (210 per
  narrator).
- ID bits after each start trigger: exp1 (1 stimulus, 10 trial, 10 token), exp2/exp3 (2, 10, 10). Played file
  (experiment and analysis code): exp1 `token + 1`, exp2 `token + 1`, exp3 `trial + 1`.
- **events.tsv is off by one in exp2 and exp3**: the BIDS scripts (`01_eeg_bids_f0s.py:112`, `..._f0s2.py`) write
  `{token:04d}` without the `+ 1`, so every exp2/exp3 event names the file *before* the played one (119 events name
  `_0000` files, which do not exist). exp1's published events.tsv has the `+ 1` (matches the README example).
  **Confirmed from the EEG** (`tmp/review/scripts/polonenko2026_fileoffset.py`, 200 trials per subject, ABR to the
  pulse trains of candidate files, SNR 5-10 ms vs -10..-2 ms):

  | subject | events -1 | events | events +1 | events +2 |
  |---|---|---|---|---|
  | exp102 | 0.95 | **6.59** | 0.77 | 1.08 |
  | exp201 | 1.64 | 1.37 | **6.92** | 1.92 |
  | exp202 | 0.98 | 1.23 | **3.96** | 0.97 |
  | exp203 | 0.68 | 0.92 | **2.84** | 0.90 |
  | exp301 | 0.82 | 1.56 | **3.99** | 0.94 |
  | exp302 | 0.61 | 1.17 | **2.38** | 1.56 |

  (exp101: no response at any offset; the authors excluded it.) Worth reporting to the authors.
- All 46,608 trials with a complete ID decode to their events.tsv row (with the offset). 24 trials have garbled
  IDs and are skipped: sub-exp225 trials 658-676 (19 start markers within 9 ms, a trigger burst; one real trial is
  among them) and 459, sub-exp224 714, sub-exp226 383, sub-exp230 82. Four more cross a pause or the end of a run
  (sub-exp117 13, 206 82, 223 81, 301 run-01 349). 46,604 trials remain.
- exp2/exp3 scaled each trial to std 0.01 when playing (`trial_audio *= rms / trial_audio.std()`; files are at
  ~0.0095); exp1 played the files unscaled. The adaptor does the same.

## 4. Speech features
- Audio as played (2 channels), pulse trains (`pulses`, 10 x 48 kHz, uint8) and common-component trains
  (`pulses_fake`, 5 x 48 kHz, uint8). No ANM regressors, transcripts or alignments.

## 5. Neural data
- BrainVision actiCHamp + EP-PreAmp, **10 kHz**, float32. Channels `FCzA1` (FCz minus left earlobe, bipolar),
  `FCz`, `A2`; the authors use `FCzA1` and `FCz - A2` (`02_analysis_*_loop.py:162-167`).
- **Gain:** values are 100x too large as shipped (800-1600 µV vs 8-11 µV in ds005340/ds005408); the authors divide
  by 100 ("account for gain": EP-PreAmp). The adaptor divides by 100.
- Channels kept as recorded (no re-referencing); validation uses `FCzA1`.

## 6. Alignment
- Sound-card triggers (expyfun; RME Digiface USB), S 1 start, S 2 20 ms before the end, ER-2 tube delay 0.81 ms
  (events.tsv `sample` = S 1, `sample_corrected` = S 1 + 8).
- **Drift 8.5-10.2 ppm** (median 9.6) per run: a different sound card from ds005340/ds005408 (25 ppm).
- Recording pauses (`New Segment`) in most runs; trials crossing them are skipped (above).

## 7. Authors' exclusions (data kept; flag for users)
- exp1: sub-exp101 (no responses), sub-exp113 (last hour not saved: 479 trials).
- exp2: sub-exp223 and 230 (poor responses, recording problems), sub-exp206, 208, 217 (noisy), sub-exp222 first
  40 min dropped in the analysis (`min_bad = 40`).

## 8. Data size (from the adaptor's trials)
62 participants, **129.5 h** in total, 2.09 h per participant (1.33-2.33).
- phases: 17 x 1.96 h (33.3 h); chirp, zero 17 x 0.98 each.
- f0s: 30 x 2.33 h (69.9 h); toto/wizardofoz x original/shifted 30 x 0.58 each.
- f0s2: 15 x 1.75 h (26.2 h); drdolittle, wizard, wonderland 15 x 0.58 each.

## 9. Adaptor
One TrialRecord per trial; subject = label number (101..315); condition `<task>-<label>` (`phases-zero`,
`f0s-toto-shifted`, `f0s2-wizard`, ...); trials numbered across runs. Onset = S 1 + tube delay; drift correction
(default on); 1000 Hz default. Provenance: `hw_trigger` (sound-card), drift per run, jitter ~0.

## 10. Upstream issues (to report; collected in `tmp/review/upstream_issues.md`)
1. events.tsv `audio` names the file before the played one in exp2/exp3 (section 3; BIDS scripts drop `+ 1`).
2. EEG 100x too large: the EP-PreAmp gain is not in the .vhdr resolution (section 5).
3. 24 trials with garbled trigger IDs still get (decoded) files in events.tsv, one of which does not exist
   (section 3).

## 11. Validation (2026-11-20; FCzA1, 1000 Hz, no re-reference; first run failed on a resampler bug, re-run)
`tmp/review/polonenko2026/validation.{json,png}`; per condition `by_condition/`. Confirms the gain (/100) and
the exp2/exp3 file offset (section 3) end to end.

| condition | low r (sig) | mlr SNR (sig) | brainstem SNR (sig) | tier |
|---|---|---|---|---|
| all (62 subjects) | 0.072 (1.00) | 4.53 (0.89) | 3.27 (0.84) | brainstem |
| phases-zero / chirp | 0.065 / 0.066 | 1.72 / 2.32 | 1.96 / 2.21 | brainstem |
| f0s-toto-original / shifted | 0.075 / 0.091 | 2.57 / 3.33 | 1.63 / 2.10 | brainstem |
| f0s-wizardofoz-original / shifted | 0.069 / 0.071 | 1.78 / 2.64 | 1.34 / 1.69 | brainstem |
| f0s2-wizard / wonderland / drdolittle | 0.072 / 0.069 / 0.066 | 2.95 / 2.86 / 3.26 | 2.11 / 2.40 / 2.86 | brainstem |

Chirp > zero phase and shifted (lower f0) > original, as in the paper.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**good**: Sound-card triggers + 0.81 ms; replicating ER-2 artefact ('markers at the transducer', polonenko2021 notes sect. 9); drift 9.6 ppm corrected; brainstem tier.

## Restructure 2026-11-25
- Restructure 2026-11-25 (not yet re-validated on data): adaptor on `BaseAdaptor`; dataset.json: participants 62,
  listening hours 129.5, paper DOI. No other change.
