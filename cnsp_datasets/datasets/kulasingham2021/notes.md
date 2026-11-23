# kulasingham2021: isochronous sentences and arithmetic equations, single talker and two-talker (attend one), KIT MEG (DRUM, preprocessed epochs)

Explorer notes (2026-11-23). Review scripts: `tmp/review/scripts/kulasingham2021/` (named per finding); outputs in
`tmp/review/kulasingham2021/` (`survey.json`, `wav_survey.json`, `integrity.tsv`, `decode*.json`, `figures/`,
`validation/`). Nothing in the data was changed beyond what is listed in section 9.

## 1. Source
- DRUM (University of Maryland) item `93067450-51d7-43c6-bb8f-53d4195db334`, hdl 1903/27201, DOI
  **10.13016/xd2i-vyke**, "Cortical Processing of Arithmetic and Simple Sentences in an Auditory Attention Task -
  Dataset" (2021). Authors Kulasingham JP, Joshi NH, Rezaeizadeh M (DRUM); paper also Simon JZ.
- Licence: **none stated** (`dc.rights` absent; checked 2026-11-23, `drum_item_meta.json`). Open question 1.
- Paper: Kulasingham JP, Joshi NH, Rezaeizadeh M, Simon JZ (2021). Cortical processing of arithmetic and simple
  sentences in an auditory attention task. J Neurosci 41(38):8023-8039, doi:10.1523/JNEUROSCI.0269-21.2021
  (`data_campaign/papers/kulasingham2021.pdf`); preprint doi:10.1101/2021.01.31.429030.
- Code: github.com/jpkulasingham/cortical-sentence-equation (one notebook, `sensor_FFT.ipynb`: reads the shipped
  epochs and uses 0-18 s as the stimulus; no epoching or trigger code). Read, not run.
- Files (ORIGINAL bundle, 5 files, 4.88 GB): `readme.txt`, `stimuli.zip` (114 MB), `subject_data_part{1,2,3}.zip`
  (1.73, 1.73, 1.30 GB). Downloaded 2026-11-23 (registry `kulasingham2021`, 1 worker, read_timeout 120 s, zips
  kept, 14 min, 0 failures; `download.log`). Size and md5 of all 5 = DRUM listing, `unzip -t` clean
  (`integrity.tsv`). Backed up to the NHR vault `/home/vault/iwpm/iwpm104h/kulasingham2021/` (`backup_verify.txt`:
  all 10 files present with matching sizes).

## Relation to other datasets (overlap check, 2026-11-23)
**No participant or recording overlap with any dataset in the campaign.**
- Participants R2522 and R2566-R2589 (22), recorded **2019-04-15 to 2019-05-20** (`meas_date`).
- `karunathilake2023_aging` (DRUM, same KIT system): R2509-R2672, but none of its listed R-numbers is one of these
  (nearest: R2565, R2591). Same recording period on the same system, different people and paradigm (Sleepy
  Hollow). `karunathilake2023` / `karunathilake2025`: R2383 and R2682 onwards (2021-2022); `brodbeck2018`:
  R2262-R2375 (2015-2016); `brodbeck2022`, `presacco2016`: no R-numbers shipped, other years and paradigms.
- `kulasingham2020` (separate candidate, DRUM `da9293b8-cc3c-4965-8b4f-dd1bc91daca5`; listing in
  `tmp/review/kulasingham2021/drum_listing_kulasingham2020.json`): its DRUM description says it **extends the
  presacco2016 MEG dataset (hdl 1903/21184) with 8 more subjects** (17 younger + 23 older, Sleepy Hollow, 60 s
  narrations). So kulasingham2020 overlaps presacco2016's recordings, not this dataset.
- Stimuli are synthesised (ReadSpeaker "James" and "Kate") and not used by any other dataset here.

## 2. Layout
- `subject_data/R####/R####_single_speaker_meg-epo.fif` (40 epochs) and `R####_cocktail_party_meg-epo.fif` (48
  epochs): MNE Epochs, 193 channels, **200 Hz**, t = 0 .. 19.995 s (4000 samples), float64; `sourcespace/`
  (forward solution, noise covariances, `-trans.fif`, `MRI scaling parameters.cfg`; not used). `__MACOSX/` junk in
  the zips (skipped when extracting).
- `stimuli/single_speaker_stimuli/{01jamesMATH,02jamesLANG,03kateMATH,04kateLANG}/trial{00-09}.wav` and
  `stimuli/cocktail_party_stimuli/{05kateLANG,06kateMATH,07jamesLANG,08jamesMATH,09kateLANG,10kateMATH,11jamesLANG,
  12jamesMATH}/{fg,bg,mix}_trial{00-05}.wav`; **block 10kateMATH names them `{fg,bg,mix}_block0_trial{00-05}.wav`**.
  Each block has `trials.csv` (old-Mac CR line endings): one row per sentence/equation of the attended (fg) stream
  (`order, sent` = the word wav names, e.g. `james_4=3+1.wav`, `frogs-croak-all-night.wav`, `deviant` 0/1, `block`,
  `trial`, `verbpos`). The background stream's text is not listed.
- Extracted for exploration and the adaptor into `tmp/review/kulasingham2021/x/` (11 GB incl. source-space
  files); the zips are kept too (md5, vault).

## 3. Stimulus <-> trial mapping (verified)
- Paper (Methods, Table 1): monosyllabic words synthesised with a male ("james") and a female ("kate") voice,
  fixed durations 375 ms (words) / 360 ms (symbols), 4-word sentences (1.5 s) and 5-symbol equations (1.8 s);
  **each trial 18 s** (12 sentences or 10 equations), low-passed < 4 kHz, loudness-normalised. 4 single-speaker
  blocks x 10 trials, then 8 cocktail-party blocks x 6 trials (attended stream + the other type in the other
  voice, summed diotically). 50% of blocks contain one deviant trial (4 wrong equations or 5 nonsense sentences);
  "Outlier?" yes/no button after each trial, 2 s pause, next trial.
- Readme: single epochs 1-10, 21-30 = equations, 11-20, 31-40 = sentences; cocktail epochs 1-6, 13-18, 25-30, 37-42
  = attend sentences, the rest attend equations. Block order **male first** (1, 2, ..., 12) for R2522, R2566,
  R2568, R2571, R2572, R2574, R2576, R2579, R2582, R2584, R2585, R2588 and **female first** (3, 4, 1, 2, 7, 8, 5, 6,
  11, 12, 9, 10) for R2567, R2569, R2570, R2573, R2575, R2578, R2581, R2583, R2586, R2587, R2589. Within a block,
  epoch k = `trial{k-1}`. **R2567 is listed but not shipped** (22 subjects = the paper's N).
- Every subject (`survey.py`, `survey.json`): 40 + 48 epochs, nothing dropped, all event codes 4. The single file
  was recorded first (its `meas_date` is ~18 min earlier in 20 subjects; equal in R2522 and R2566).
- **Check with the deviant task** (`buttons_vs_deviants.py`, `figures/buttons_vs_deviants_per_subject.png`): MISC
  025 = "yes" (right), MISC 024 = "no" (left). Under the readme order, "yes" follows 63% of the deviant trials and
  15% of the others ("no": 9% vs 49%); with the counterbalancing groups swapped the contrast disappears (16% vs
  20%). Per subject, deviant > non-deviant "yes" rate in 21/22, so block order, counterbalancing group and trial
  order within blocks are confirmed at the deviant positions.
- **R2522 is female-first, not male-first as the readme says** (open question 2): its 6 single-speaker "yes"
  presses hit 3 of the 4 deviant epochs of the female-first order (1, 27, 38) and none of the male-first ones
  (Fisher one-sided p 0.008 vs 1.0); cocktail p 0.10 vs 0.41. The MEG agrees independently (`decode_map.py`,
  section 10): the backward decoder trained on the female-first assignment gives r 0.282 vs 0.259 (single) and
  0.146 vs 0.123 (cocktail), and the held-out reconstruction ranks the assigned wav first in 9/40 vs 0/40 single
  trials. With R2567 missing, R2522 as female-first also balances the groups at 11/11. The adaptor uses
  female-first for R2522 (sidecar `block_order_source`).
- **The wavs** (`wav_survey.py`, `wav_survey.json`): 184 files, 22,050 Hz mono int16, no clipping (peak 31350).
  Equation trials 396,900 samples (18.000 s); sentence trials 396,912 (18.0005 s; 375 ms is not a whole number of
  samples). Every `mix` = g (fg + bg) with one gain per trial, **g 0.703-0.711** (loudness normalisation),
  residual <= 1.4 LSB in all 48: `fg`/`bg` are the unscaled streams, the played streams are g x fg and g x bg.
  Only `mix` was played (readme). First sound sample (> 1% of peak) 0.8-49 ms into the files.
- Same stimuli for every participant; every trial heard once.

## 4. Speech features available
- Raw audio of everything played: single-talker trials; cocktail mixtures as played plus the attended (fg) and
  ignored (bg) streams unscaled.
- Text: the attended stream's sentences/equations per trial with deviant flags (`trials.csv`); not the background
  text. Word timing is fixed by design (375 / 360 ms slots, words time-scaled to fill them), so word onsets could be
  generated, but no TextGrids are shipped (open question 6).

## 5. Neural data
- KIT 157-channel axial-gradiometer MEG (UMD), recorded at 2 kHz with a 500 Hz online low-pass and 60 Hz notch
  (paper). **Shipped only as the authors' preprocessed epochs** (readme): TSPCA, SNS, FIR 0.3-40 Hz, ICA artefact
  removal, decimated to **200 Hz**; no `proc_history`, no raw data released. **The `info` low-pass is 30 Hz, not
  40 Hz, in the single-speaker files of 20 subjects** (all but R2522 and R2566, the two whose single and cocktail
  files share one `meas_date`); 40 Hz in every cocktail file; high-pass 0.3 Hz everywhere. The sidecar
  `preprocessing` field gives each file's band from its `info`.
- Channels (all subjects): `MEG 001-157` (`mag`, KIT_GRAD, T), `MEG 158-160` (`ref_meg`), `MISC 001-032` (V),
  `STI 014` (all zero). Median gradiometer rms ~1.3e-13 T.
- MISC lines are decimated with a low-pass too (a TTL pulse rings over +-6 samples, overshoot to 5.7 V):
  - **MISC 014: end-of-stimulus pulse at 18.00 s** in every epoch (below);
  - MISC 024 / 025: "no" / "yes" buttons, mostly pressed 0.4-2 s after the end pulse; 4 presses come before it
    (only press of R2579 single epoch 7, "yes" at 11.27 s, and of R2584 cocktail epoch 3, "no" at 6.11 s);
  - MISC 013 pulses together with MISC 014 in all R2585 single-speaker epochs; MISC 001 sits at a different
    constant level in R2579; MISC 030-032 low-level noise; the rest constant 5 V.
  - No audio copy / stimtrack. MISC and STI are dropped by the adaptor (brodbeck2018 precedent).
- Bads: `info['bads']` lists **MEG 040 and MEG 056 in every file**, with duplicates (`['MEG 056', 'MEG 040',
  'MEG 040', 'MEG 056']`; upstream quirk; the adaptor de-duplicates). No zero-variance, flat (< median/20) or loud
  (> 10x median) channel in any file (SNS reconstructs the bad channels).
- Digitisation: head shape only in R2522 (both files, 1948 points) and R2588 single (2709 points); the other files
  have none, though each subject has a `-trans.fif` in `sourcespace/`. Kept as shipped.
- Participants (paper): 22 adults, mean age 22.6, 10 female, 21 right-handed; no per-subject table shipped.

## 6. Alignment
- The epochs start at t = 0 with no pulse on any line; **the end pulse on MISC 014 is at 17.996-17.998 s** (pulse
  centroid at sub-sample resolution; 1882 trials at 17.996-17.997 s, 13 at 17.998 s) in 1895 trials, one 200 Hz
  sample later (18.001-18.002 s) in all 40 R2585
  single-speaker trials, and missing in R2570 cocktail epoch 36 (1-based; index 35; `survey.json`). The button presses come after it
  and the next trial starts only 2 s after a press, so the pulse marks the end of the 18 s stimulus. The authors
  evidently cut each epoch 18.0 s before the end pulse (constant to < 1 ms, so the cut was made from that pulse
  or from an onset trigger exactly 18 s earlier; which one cannot be told from the epochs).
- **The MEG confirms t = 0 = sound onset** (`edges.py`, `figures/evoked_edges.png`): the grand-average evoked GFP
  rises from ~30 ms and peaks at 75 ms (cocktail) / 120 ms (single) after t = 0, and an offset response follows
  18 s. A decoder lag sweep is not decisive here: the isochronous envelopes repeat every 360-375 ms, so the sweep
  has side lobes of near-equal height one word period away (section 10).
- Hardware vs software: **unknown** (paper silent; KIT TTL lines; presentation software not named; insert-tube
  delay not given).
- Implemented: trial = shipped epoch as is (t = 0 = onset, 4000 samples at 200 Hz, i.e. 18 s of stimulus + 2 s
  after it); no offset correction. The loader checks that the end pulse is at 18.00 +- 0.01 s (R2570 cocktail
  epoch 36 is accepted without it).
- Drift: not measurable (only the end pulse is in the epochs; its constant position reflects how the epochs were
  cut). An 18 s trial at a typical 10-50 ppm sound-card drift moves < 1 ms. `drift_ppm` null.

## 7. Cross-subject duration check
- Not possible beyond section 6 (one pulse per epoch). Stimulus durations are all 18.000-18.0005 s.
  `jitter_ms` null.

## 8. Data size
22 participants x 88 trials x 18 s = **26.4 min each (all identical), 9.68 h in total** (= the sheet's 9.7 h):
single speaker 12 min (6 min equations, 6 min sentences), cocktail party 14.4 min (7.2 min attend equations, 7.2
min attend sentences). The stored neural epochs are 20 s (29.3 min per participant).

## 9. Adaptor (implemented 2026-11-23)
- Shared code with the lab's other KIT datasets (R-number subjects, wav loaders, epoch/continuous-raw helpers,
  bad-channel rules) in `datasets/simon_base/common.py` (2026-11-23; output unchanged except subject numbers).
- Reads `**/R####/` epoch folders and `**/stimuli/` under the root (the extracted zips, `tmp/review/kulasingham2021/x/`).
- Subject = full R-number (user, 2026-11-23); earlier outputs used R-number mod 1000 (R2522 -> 2522, was 522). Checked
  unique, as in brodbeck2018 / karunathilake2023; R-number also in the sidecar (`participant`). `validation.json`
  subject fields relabelled to the full R-number (results unchanged). Session 1. Trials 1-40 = single-speaker file,
  41-88 = cocktail file, each in epoch order (= presentation order; checked: 40 / 48 epochs, increasing event samples).
- Block order per subject from the readme groups, **R2522 female-first** (section 3; `block_order`,
  `block_order_source`). Conditions `single_equations`, `single_sentences`, `cocktail_attend_equations`,
  `cocktail_attend_sentences`.
- Neural data: the shipped epoch as Raw, 157 gradiometers (`mag`) + 3 reference magnetometers (`ref_meg`), T,
  **200 Hz as shipped (native; no resampling)**, 4000 samples (0-19.995 s); `info` (dig where present,
  dev_head_t, filter band) kept; bads = de-duplicated shipped bads (MEG 040, MEG 056) + any zero-variance channel;
  MISC/STI dropped. The loader checks the end pulse at 18.00 +- 0.01 s.
- Stimuli (22.05 kHz float32, as shipped): single = `{block}_trial{k}` (attended); cocktail = `{block}_fg_trial{k}`
  (attended), `{block}_mix_trial{k}` (played), `{block}_bg_trial{k}` (ignored).
- Sidecar: `onset_only`, trigger type unknown, `validation_tier` low, plus `participant`, `block_order(_source)`,
  `block`, `block_trial`, `epoch_file`, `epoch_index`, attended/ignored voice and task, `attended_items` (text from
  `trials.csv`), `deviant_items`, `deviant_trial`, `mix_gain`, `stimulus_end_s` 18.0,
  `end_pulse_first_low_sample_s` (5 ms grid), `button_presses_s` (all, incl. early ones), `response` (first press
  after the stimulus: yes/no/None), `response_time_after_end_s`, `preprocessing` (with the file's filter band).
- Run 2026-11-23 (after the review fixes): all 22 subjects, 1936 trials, 184 audio files, **5.0 GB**, ~5 min, no
  errors (`tmp/review/kulasingham2021/standardised/`, `standardise.log`). Reviewer findings applied (filter band
  per file, epoch count/order check, all button presses kept, end-pulse field name, code simplifications); the
  shared helpers for `_one`/`_read_wav`/epoch-to-Raw later moved to `datasets/simon_base/common.py`.

## 10. Decoder check and validation (2026-11-23; `tmp/review/kulasingham2021/`)
Basis: standardised data as stored (all 22 subjects, 1936 trials), gradiometers (`--picks mag`, bads excluded), no
re-referencing (MEG), attended stream as the stimulus (`--first-attended`). Only the low tier can run (data
0.3-30/40 Hz at 200 Hz).
- **Sanity:** all trials 20.0 s neural vs 18.0 s stimulus (the 2 s after the stimulus are kept); no flags.
- **low (0.5-8 Hz forward): pass.** Mean r 0.051 (median 0.048), **22/22 subjects** above the circular-shift null,
  p_circ 0.020, p_mismatch 0.048 (`validation.json`, `validation.png`). TRF GFP peaks at ~31 ms and ~280 ms.
  The isochronous envelope repeats every 360/375 ms, so a response at lag L also fits L +- one period: the TRF
  rises from ~-40 ms, and the validator's per-trial offsets (19 at the +-0.5 s edge, jitter SD 223 ms) and drift
  (202 +- 1083 ppm) are aliasing, not timing errors. Timing rests on the evoked onset response (section 6).
- Per condition (`validate_subset.py`, `validation/cond_*/`):

  | condition (trials/subject) | low r | sig | TRF peak |
  |---|---|---|---|
  | single_equations (20) | 0.067 | 22/22 | 47 ms |
  | single_sentences (20) | 0.065 | 22/22 | 31 ms |
  | cocktail_attend_equations (24) | 0.053 | 21/22 | 47 ms |
  | cocktail_attend_sentences (24) | 0.043 | 20/22 | 47 ms |

- **Backward decoder** (`decode_map.py`, `decode.json`, `decode_figures.py`): per subject and file, 157 good
  gradiometers, 1-8 Hz, 100 Hz, 40 PCs, lags 0-250 ms, ridge, leave-one-epoch-out, trained on the attended
  envelope over 0-18 s. Mean r 0.299 (single), 0.205 (cocktail attended) vs **0.121 ignored; attended > ignored in
  20/22** (Wilcoxon p 7e-6; `figures/r-attended-vs-r-ignored.png`). Stimulus-shift sweep (+-500 ms): central peak
  at 0 ms (single) / +10 ms (cocktail), per-trial median 0 / +10 ms, IQR -10..+10 / -10..+20 ms; side peaks of
  similar height at +-370 ms (`figures/decoder_lag_sweep.png`). The block-mean-removed (trial-specific) envelope
  ranks the assigned wav at median 11/40 (single) and 16/48 (cocktail) vs chance 19.5 / 23.5.
- **Block-order control** (`SWAP=1 decode_map.py`, `decode_swapped.json`, `figures/block_order_decoder_check.png`):
  the same decoder with the counterbalancing groups swapped gives lower r in **22/22 subjects (single, +0.004 to
  +0.046) and 21/22 (cocktail; R2576 -0.014)**; for R2522 the female-first order used here beats the readme's
  male-first by +0.023 (single) and +0.022 (cocktail).
- Validation tier: **low** (highest possible with the shipped data).
- Figures: `validation.png`, `validation/cond_*/validation.png`, `figures/evoked_edges.png`,
  `figures/buttons_vs_deviants_per_subject.png`, `figures/r-attended-vs-r-ignored.png`,
  `figures/decoder_lag_sweep.png`, `figures/block_order_decoder_check.png`.
- Not run: coherence batch and DNN offset check (WORKFLOW 5-6); the DNN check is EEG-specific, and the data are
  0.3-30/40 Hz at 200 Hz.

## Upstream issues
- No licence on the DRUM item.
- Only preprocessed (TSPCA, SNS, ICA, 0.3-40 Hz, 200 Hz) epochs are shared; no raw recordings. The single-speaker
  files of 20 subjects are low-passed at 30 Hz (`info`), not 40 Hz as the readme says.
- R2522 is listed as male-first in the readme; the button presses and the MEG say female-first. R2567 is listed but
  not shipped.
- `info['bads']` has duplicate entries; head-shape digitisation is missing in 41 of 44 files.
- Block 10kateMATH uses different wav names (`*_block0_trial*`); `trials.csv` has CR line endings and lists only
  the attended stream.

## Open questions (human checkpoint; recommended default in brackets)
1. Licence: none stated. [include; note "no licence stated"; ask the authors via the user]
2. R2522 block order: readme says male-first, buttons (p 0.008) and MEG decoding say female-first.
   [female-first, flagged in the sidecar; report upstream]
3. Neural rate: shipped 200 Hz (authors' decimation), 0.3-40 Hz (0.3-30 Hz in 20 single-speaker files). [keep 200 Hz (native <= 1024 Hz, never upsample);
   only the low tier can be validated]
4. Epoch length: keep the shipped 20 s epochs (18 s stimulus + 2 s with the offset response and button press) or
   crop to 18 s? [keep 20 s; the stimulus end is at 18 s in the sidecar]
5. Stimuli for cocktail trials: attended `fg` (is_attended), the played `mix`, and the ignored `bg`, all as shipped
   (fg/bg unscaled; played level = g x stream, g in the sidecar)? [yes]
6. Word/symbol onset annotations generated from the fixed design (375 / 360 ms slots) with the `trials.csv` text?
   [not now; carry the text and deviant flags in the sidecar]
7. MISC lines dropped; button response ("yes"/"no"/none) and end-pulse time go to the sidecar. [yes]
8. Conditions `single_equations`, `single_sentences`, `cocktail_attend_equations`, `cocktail_attend_sentences`;
   voice in the sidecar. [yes]

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**medium**: Authors' 200 Hz epochs cut 18 s before the end pulse; t=0 supported by evoked onset responses; TRF rise from -40 ms attributed to stimulus periodicity; low tier.
