# winchester2026: uninstructed listening to two-voice polyphonic piano music (OSF bjdh6, CND)

31 participants x 32 MIDI-synthesised classical pieces (~50-166 s; mostly J.S. Bach), each heard once in one of six
variants: the original two-voice piece (`Original`, paper "PolyOrig"), the pitch-inverted piece (`Inverted`,
"PolyInv"), or one of its two voices alone (`<Original|Inverted>_Mono_<Left|Right>`, "Monophonic"). 24-channel
mBrainTrain Smarting wireless EEG. Shared as CND `.mat` files: **raw EEG epochs** (no filter, no re-reference) at
250 Hz (9 subjects) or 500 Hz (22 subjects), and **125 Hz stimulus features only** (Hilbert envelopes of the wavs
as played and of each voice, MIDI note onsets, model surprisal/entropy). No audio, no MIDI, no triggers.

## 1. Source
- OSF project bjdh6 (https://osf.io/bjdh6/), no child components: `code/` (8 MATLAB scripts) and `dataCND/`
  (`chanloc.mat`, 31 `dataSub<N>.mat`, 31 `dataStim<N>.mat`); 71 files, 5.69 GB. Listing saved as
  `tmp/review/winchester2026/osf_listing.json`; all 71 files matched OSF size and md5 (2026-11-23). Download took
  90 s (`download.log`, `download/download_log.tsv`).
- Licence: **not stated on OSF** (no LICENSE/README). The paper is CC BY 4.0; the data licence is unknown.
- Paper: Winchester MM, Reynolds R, Nebo M, Scott IC, Di Liberto GM (2025/2026). eLife reviewed preprint
  RP108767 (v2), https://doi.org/10.7554/eLife.108767.2 (`data_campaign/papers/winchester2026.pdf`).
- Shared code (read, not run): `globals.m` (variant and feature names), `create_features.m` (features from
  `Stimuli/Wavs/<variant>/audio<k>.wav` and MIDIs, not shared), `create_dataStims.m` (per-subject `dataStim`),
  `preProcessCND.m` (1-8 Hz, 125 Hz, bad-channel interpolation, average reference; **not applied** to the shared
  `dataSub` files), `run_bTRF.m`, `run_fTRF_env.m`, `run_behavioural.m`, `create_paper_figures.m`.

## 2. Layout
- `dataSub<N>.mat` (v7.3/HDF5), struct `eeg`: `dataType` 'EEG', `deviceName` 'Mobi Steamer', `fs` (250 or 500),
  `chanlocs` (24, same as `chanloc.mat`), `data` {32} of [n x 24] (sub25: {33}, see 3), `audioNames` {32} (e.g.
  `Original_Mono_Left1`), `origTrialPosition` (32).
- `dataStim<N>.mat` (v7.3), struct `stim`: `names` (48 features), `data` {48 x 32} (MATLAB order; h5py
  shows (32, 48); pymatreader flattens it, so the adaptor reads these files with h5py), `condIdxs`, `condNames`
  (6 variants, `globals.m` order: 1 Original_Mono_Left, 2 Original_Mono_Right, 3 Inverted_Mono_Left,
  4 Inverted_Mono_Right, 5 Original, 6 Inverted), `stimIdxs`, `fs` 125.
- Subjects 1-31 (the paper's 31; 9 of 40 recruited were excluded upstream for trigger problems).

## 3. Stimulus <-> trial mapping (all 31 subjects; `tmp/review/scripts/winchester_explore.py`)
- Index i (0..31) of `data` = **piece i+1** (`audioNames[i]` ends in i+1 in every subject); the variant is the
  name prefix and matches `condIdxs`. `origTrialPosition[i]` = presentation position (1..32; sub25 2..33).
- Conditions per subject: ~10-11 Original, ~10-11 Inverted, ~11 Monophonic (random voice/variant). Over all
  subjects: 324 Original, 324 Inverted, 89/71 Original_Mono_Left/Right, 89/95 Inverted_Mono_Left/Right.
- **sub25** has a 33rd trial (index 32): empty audio name, empty data, condIdx 0, position 0 (a false start?).
  Skipped.
- The 192 envelopes (32 pieces x 6 variants) are **bit-identical across subjects**, and a monophonic trial's
  envelope equals that voice's envelope in the polyphonic trials of the same piece (all subjects checked).
- **Epoch length**: each EEG epoch starts at the stimulus onset and runs to the next piece's onset (self-paced:
  1-124 s after the stimulus ends, median 4.2 s); the last-presented trial runs to the end of the recording
  (up to +1533 s). The adaptor keeps the epochs as shipped (stimuli are not cut and the EEG is not cut to them).
- **sub16**: the recording ends 3.4 s into position 31 (piece 25, Original: 844 samples, stimulus 79.6 s; kept,
  users cut at the point of use); position 32 (piece 14, Inverted) holds a single sample and is **skipped**.
  So 991 trials are standardised (31 x 32 - 1).
- Stimulus time per subject 0.84-0.85 h; **26.2 h in total** (EEG epochs 31.2 h). The sheet's 41.3 h estimate
  assumed 150 s pieces; pieces are 50.6-166.4 s.

## 4. Features available
- No audio. `env` = |hilbert(wav)| (wav channels averaged) resampled to 125 Hz with MATLAB `resample`
  (`create_features.m`); `env_left`/`env_right` = the same for each voice's wav (`<variant>_Mono_<side>`);
  `env_del*` its derivative. Voice envelopes can be up to ~2 s shorter or longer than the mix of the same
  piece (e.g. Inverted_04: 13977 / 13977 / 13766 samples). These are **stored**: per trial the envelope of what was played (`is_attended`) and,
  for polyphonic trials, the two voices' envelopes as extra stimuli named like the monophonic trials.
- Not stored: `onset*` (MIDI note onsets), `s_*`/`h_*` (surprisal/entropy from a music transformer: model-derived),
  `env_mean`/`env_std` ("envelope trick" features), combined feature sets.
- "Left"/"Right" are the two voices, not ears (both voices are presented together in the polyphonic variants;
  the wavs are averaged across channels before the envelope). Which voice is high/low per variant is not stored;
  paper: the original high voice is the main melody, and `Inverted` swaps the pitch heights. Presumably
  Left = piano left hand (low voice in `Original`); **unverified**.

## 5. Neural data
- mBrainTrain Smarting (24 ch, wireless). Paper: 250 Hz; **shipped: 250 Hz for subjects 1-5 and 16-19, 500 Hz for
  6-15 and 20-31**. Native rates are kept (<= 1024 Hz).
- Channels (`chanlocs`, same order in all subjects): Fp1 Fp2 F3 F4 C3 C4 P3 P4 O1 O2 F7 F8 T7 T8 P7 P8 Fz Cz Pz
  **M1 M2** AFz CPz POz. M1/M2 = mastoids (`misc`). No EOG, ECG, stimtrack or trigger channel.
- Reference: not stated. The Smarting 24-channel cap records against FCz (ground AFz on some caps, but AFz is a
  recorded channel here); stored as "unknown (Smarting default FCz, not documented)". Not re-referenced.
- Units: uV (median channel SD 19-174 uV after a 1 Hz high-pass, first six trials); scaled by 1e-6. Unfiltered:
  DC offsets, 50 Hz mains, and at 250 Hz a 62.5 Hz (fs/4) line in most subjects (`explore_psd.png`).
- Bad channels (`explore_channels.json`): **sub4 C4, P3, O2 flat in every trial** -> `info['bads']`. Frontal/
  temporal high-variance channels (sub11 T7, sub22 Fp1/Fp2/F7, sub23 F4, sub26 F3, sub29 Fp2) look like ordinary
  artefacts and are not marked.
- **sub5**: every channel ~30-80x larger than other subjects (median SD 4336 uV) with a ~5 Hz harmonic comb and a
  62.5 Hz line (`explore_psd.png`): likely a broken recording (bad ground/reference?). Kept as shipped; see
  open questions and validation.
- No NaNs. Positions: the shipped `chanlocs` are idealised (unit sphere); MNE `standard_1020` template positions
  are set instead.

## 6. Alignment
- Paper: Neurobehavioral Systems Presentation, audio at 44.1 kHz through Sennheiser HD 280 Pro headphones
  (circumaural: no tube delay). EEG sync triggers: how they reached the wireless Smarting is not stated (Smarting
  takes triggers through its USB receiver / LSL); 9 subjects were excluded for "technical issues with the
  synchronisation triggers". Triggers are not shared: the authors cut the epochs at the onset trigger.
- `trigger_type` = `software (Presentation -> Smarting; paper, route unknown)`; latency and jitter unknown.
- **Proposed alignment**: trial onset = epoch start as shipped (`sw_trigger`), no onset correction.
- **Drift**: cannot be measured (no end triggers, no audio copy, self-paced gaps between pieces). Not corrected
  (`drift_ppm` null). At 100 ppm a 166 s piece drifts 17 ms by its end: irrelevant for the 0.5-8 Hz tier.

## 7. Cross-subject duration check
- Not possible: only onsets are implied (epoch starts); epoch ends are the next onset, not a stimulus-end trigger.
  Sanity only: every epoch is at least 0.7 s longer than its stimulus except sub16 positions 31-32.

## 8. Open questions (recommended default in brackets)
1. Data licence not stated [standardise for internal use; ask the authors before redistribution].
2. sub5 (broken-looking recording) [keep, mark nothing; report its validation separately; users may drop it].
3. Voice identity of Left/Right [store as shipped names; document as voices, not ears; ask the authors].
4. Polyphonic trials: also store the voice envelopes [yes, `is_attended=False`, names shared with mono trials].
5. Constant trigger latency [none applied; check with the lag sweep; documented only].

## 9. Standardisation (2026-11-23)
- Adaptor: `adaptor.py` (reviewed by the `reviewer` agent; findings applied: cross-check of each EEG trial's variant
  against the stimulus file's `condIdxs`/`stimIdxs`, unique presentation positions, strict montage). Output in
  `tmp/review/winchester2026/standardised/` (all 31 subjects = the pilot): 991 EEG trials, 192 envelope stimuli,
  4.4 GB, written in 4.5 min (`standardise.log`). Native 250/500 Hz kept; no resampling, no drift correction.
  The stored sidecars were written before the review edits (no `validation_tier`, an extra `reference` field);
  EEG and stimuli are identical.
- Data size (stimulus time; sub16 position 31 counted at its 3.4 s): **26.15 h**, 0.84 h per subject (0.79-0.85).
  Original 8.44 h (0.27 h/subject, 0.14-0.42), Inverted 8.82 h (0.28, 0.14-0.44), Mono 8.89 h (0.29, 0.14-0.43).

## 10. Validation (average reference, 22 EEG channels, bads excluded; `validation.json` here)
- **Low tier (0.5-8 Hz), all 31 subjects, all 991 trials: pass.** Mean r 0.023 (median 0.020), population
  p_circ 0.020, p_mismatch 0.048 (the smallest values these nulls allow); 21/31 subjects significant. TRF (played
  envelope): peaks at ~70, ~190 and ~300 ms, nothing above the null at negative lags (`validation.png`); pooled
  per-trial best lag median +1 ms (per-trial offsets themselves are noise: SD 231 ms, weak music SNR).
  Not significant: 1, 2, 5, 7, 9, 14, 16, 17, 25, 29 (r 0.005-0.017). **sub5** r 0.007 (p 0.31).
- **Per condition** (`tmp/review/scripts/winchester_validate_conditions.py`, `validation_by_condition/<cond>/`):
  Original (324 trials) mean r 0.020, 10/31 subjects; Inverted (323) 0.019, 11/31; Mono (344, the four single-voice
  variants) 0.020, 13/31. All pass at population level; TRFs show the same peaks, no negative-lag response.
- **mlr and brainstem tiers cannot be run**: the stimuli are 125 Hz envelopes (content only below 62.5 Hz, and the
  validator's high-frequency feature needs a stimulus at least at the EEG rate), and 9 subjects are at 250 Hz.
  The 30-250 Hz tier would in any case be impossible at 250 Hz (Nyquist 125 Hz).
- DNN timing check (accou2023 match-mismatch) not run: the model is trained on speech; this is piano music.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**medium**: Authors' epochs at a software trigger (Presentation to Smarting); no audio; per-trial best lag +1 ms, nothing at negative lags; low tier.
