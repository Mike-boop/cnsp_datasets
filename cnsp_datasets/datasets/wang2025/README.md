# wang2025: Le Petit Prince multi-talker, Mandarin (EEG)

EEG while young Mandarin listeners hear *Le Petit Prince* read by synthetic voices in four ~10-min sections, played
**continuously** (one wav per section): two sections with a female and a male talker mixed (one talker to attend,
instructed on screen) and one section of each talker alone. The fMRI part of the dataset is not used.

- **Source:** OpenNeuro ds005345 v1.0.1 (latest), doi:10.18112/openneuro.ds005345.v1.0.1 (registry entry
  `wang2025`; derivatives not used). **Licence: CC0.**
- **Paper:** Wang Q, Zhou Q, Ma Z, Wang N, Zhang T, Fu Y, Li J (2025). Le Petit Prince (LPP) multi-talker:
  naturalistic 7 T fMRI and EEG dataset. *Scientific Data* 12:829. doi:10.1038/s41597-025-05158-7
- **Code (authors):** https://github.com/compneurolinglab/lpp_multi-talker (preprocessing only; no onset code).

## Size
**26 participants, 101 trials (one per section) of 455.3-603.0 s, 16.85 h in total; per participant mean 0.648 h
(range 0.126-0.669 h; 0.669 h when complete).** sub-15 is truncated upstream and has 455 s of its first (mixed)
section only. Totals from the standardised trials (pilot of all 26 participants); not yet in the shared
data-size table.
- `mixed`: 51 trials, 8.50 h (two per participant; mean 0.327 h, 0.126-0.335 h per participant);
- `single-female`: 25 trials, 4.19 h (0.168 h each);
- `single-male`: 25 trials, 4.17 h (0.167 h each).

Only 16 participants (10.7 h) have all 64 channels working; the other 10 have 33 (see Caveats).

## What is provided
- **EEG:** BrainAmp DC at 500 Hz (native rate, not resampled except for the drift correction below), 64 scalp
  channels (`eeg`), in V. No EOG, ECG, mastoid or stimtrack channels. **Original reference, documented
  inconsistently** (JSON Cz, which is a live channel; paper "nose"); the data indicate an online FCz reference
  (inferred, actiCAP default). Template positions (`standard_1005`). `meas_date` is unset (the recording PC clock
  was wrong); the EEG date is in the metadata.
- **Stimuli**, the shipped 44.1 kHz mono wavs:
  - `mix`: 0.5 x female + 0.5 x male, what was played in the `mixed` sections (sample-exact sum);
  - `single_female` (603.0 s) and `single_male` (599.8 s): the two talkers (different parts of the story);
  - `mixed` trials carry all three (none marked attended: the attended talker is unknown); single trials carry
    their talker's wav (attended);
  - `textgrid` for `single_female` and `single_male`: tier `words` (Chinese words) from the upstream word tables,
    which are in **centiseconds** (10 ms precision). No phone tier. For the `mix`, use the two single TextGrids
    (same time base, both start at sample 0).
- Trial metadata (`raw.info["description"]`, JSON): position (1-4), group (A/B) and its confidence, `attended`,
  onset and its source, `timeline_sd_ms` (for timeline onsets), drift applied, bad and low-variance channels,
  `short_pause_session`, `truncated_upstream`, age, sex, EEG date, reference.

## Alignment
- **Constant timing offset, not corrected: the sound most likely started ~0.18-0.20 s after the markers.** Two
  independent measures agree, and the offset is present in the triggered first section too:
  - match-mismatch DNN (trained on accou2023): -197 ms over all trials (95% CI -270..-184), position 1 (first
    marker) -198 ms, positions 2-4 -254 / -173 / -205 ms (negative = response later than in accou2023; clean
    single-talker speech scores within +-5 ms in hand-aligned datasets);
  - forward TRF (fronto-central cluster, all 26 participants): the P1-like peak is at ~220-240 ms instead of
    ~35 ms in herrmann2025 with the same code; template shift against herrmann2025 +164..+188 ms per condition and
    position (+234 ms at position 2, +227 ms with the male talker as regressor in mixed sections).

  Probably software triggers with non-low-latency audio output (inferred). Handled like das2019 and bentum2023:
  **the onsets are left as found, pending a decision.** If you need absolute latencies, shift the stimulus by about
  +0.19 s (sound later) yourself. Relative to position 1, the timeline onset of position 2 is a further ~+35-55 ms
  late (backward sweep +33, DNN +51, TRF template +55 ms) and position 3 ~15-60 ms early (TRF -16, DNN -29,
  backward sweep -62 ms); position 4 agrees with position 1 within ~25 ms.
- One trial per section, cut from the continuous recording.
- **Section order and labels come from the EEG, not the paper.** Envelope tracking shows positions 1-2 are the two
  mixed sections and 3-4 the single sections, as `single-male`, `single-female` (group A, 17 participants) or
  the reverse (group B, 8; sub-15 unknown). The paper's Table S2 run order does not match the EEG (agreement at
  chance, 21 vs 25; probably the fMRI order, unverified). Group calls are low-confidence for sub-05 and medium for
  sub-09, sub-10 and sub-23 (`group_confidence`).
- **Onsets** (`alignment/onsets.csv`, from the explorer's analysis, notes.md sections 3 and 6): section 1 at the first
  marker (`S 11`, or `S 31` in six recordings); sections 2-3 at `S 32`/`S 33` where present, otherwise at the
  first marker + 735.07 / 1470.14 s (trigger timeline of the six `S 3x` recordings); section 4 at the first marker +
  2192.2 s (group A) or 2196.2 s (B), confirmed by EEG envelope tracking. `S 34` is ~0.95 s late and ignored.
  sub-16 and sub-18 ran with shorter pauses (offsets 615.06 / 1230.12 / 1832.2 or 1836.2 s, from the authors'
  epochs, confirmed by the EEG within ~0.25 s).
- `alignment_method`: `sw_trigger` for the 38 triggered onsets; `onset_only` for the 63 timeline onsets.
  Triggers are software (inferred: 60 Hz frame grid, undocumented), jitter 4.1 ms (residual SD of the six
  `S 3x` timelines); timeline onsets add a cross-subject spread of 19 / 31 / 40 ms SD (positions 2 / 3 / 4,
  `timeline_sd_ms`).
- **Drift correction +164 ppm** (default; `drift_correction=None` disables it): the EEG lag slides linearly by
  ~0.1 s per section in every subject with strong tracking (pooled EEG estimate, median +164 ppm, IQR +138..+176,
  32 sections of 18 subjects). It is applied with the onset in one interpolation (`clock.crop_on_audio_clock`).
  After correction the within-section slope is gone (7 strong sections: median +183 -> +9 ppm, all corrected 95%
  CIs include 0). Per-subject estimates (~+-50 ppm) are too noisy to use.

## Validation
**Low tier for all 101 trials** (`validation_tier: low`; average reference over each subject's live channels, 64
or 33). The low tier passes in every condition and every position; mlr and brainstem fail everywhere, and with a
~0.2 s offset and software triggers they could not pass.
- **Backward** (decoder, review script, 0.5-8 Hz, 0-250 ms, leave-one-section-out): single-talker sections median
  r **0.069, 25/25 subjects** above the circular-shift and the other-talker (mismatch) nulls (female 0.070, male
  0.067). Mixed sections: mix 0.026 (20/25), female talker 0.021 (15/25), male talker 0.032 (20/25).
- **Backward lag sweep** peaks at ~0 ms in single sections (+4 ms, 95% CI -11..+22) but at +76..+103 ms in mixed
  sections (mix +88 ms; position 1 +74, position 2 +103). The decoder is trained on trials with the same timing,
  so the common ~0.2 s offset does not show here; the mixed-section shift reflects the position 2 timing error and
  the later response to competing speech, which cannot be separated.
- **Forward, low tier** (validator, 64 Hz): all trials median r 0.015, 12/25 subjects above the circular-shift
  null (p_circ 0.020, p_mismatch 0.048, the latter conservative because the mismatch pairs the mix with its own
  components); single sections 0.020, 12/25 (21/25 above the mismatch null). TRF peak at 234-250 ms (the offset).
- mlr: mean SNR 0.96 (p 0.86, 1/25 subjects); brainstem 1.04 (p 0.12, 3/25). Same in every condition/position.
- **Talker tracking in mixed sections** (decoder trained on the single sections): the male talker is tracked
  better than the female (median r 0.031 vs 0.021, Wilcoxon p 0.002; male significant in 27/50 sections, female
  17/50, both 13/50). There is no attention-switch signature between the two mixed sections (female-minus-male
  sign flips in 9/25 subjects, binomial p 0.23), so the attended talker cannot be recovered.
- **Coherence** (EEG vs the trial's primary envelope, ratio to one global-shift surrogate; bands up to 60 Hz at
  128 Hz, above at the native 500 Hz, which agrees within 0.01 below 60 Hz):

  | condition | 0.2-1 Hz | 1-4 Hz | 4-8 Hz | 8-15 Hz | 15-30 Hz | 30-60 Hz | 60-120 Hz | 120-250 Hz |
  |---|---|---|---|---|---|---|---|---|
  | mixed (mix) | 2.32 | 2.14 | 1.51 | 1.09 | 0.99 | 1.06 | 1.00 | 1.02 |
  | single-female | 2.92 | 1.99 | 1.12 | 1.09 | 1.06 | 1.02 | 1.01 | 1.00 |
  | single-male | 2.54 | 2.09 | 1.28 | 1.10 | 0.98 | 1.03 | 1.03 | 1.00 |

  Clearly above the surrogate up to 8 Hz, ~1.1 at 8-15 Hz, nothing above 15 Hz.
- Weak subjects (not above the null in at least one single-talker condition): sub-03, 09, 10, 11, 13 and 23;
  sub-10, 11, 13 and 23 are among the 33-channel recordings. All kept.
- The validator's per-trial jitter and drift estimates (SD 230 ms; 81 +- 178 ppm) are dominated by noise and say
  nothing about timing.
- Suitable for low-frequency envelope tracking of single and competing talkers, and word-level analyses with
  relative timing. **Not suitable** for absolute latency claims without shifting the stimulus (see Alignment),
  for middle-latency or brainstem responses (software triggers, ~0.2 s unexplained offset, 500 Hz), or for
  attention decoding (attended talker unknown).

## Caveats
- **Timing offset ~0.19 s, not corrected** (see Alignment); positions 2 and 3 carry an extra few tens of ms.
- **Condition labels are inferred from the EEG**; the paper's Table S2 does not match (see Alignment). Decided
  without the authors' confirmation; the session order of the EEG is not documented.
- **The attended talker in the two mixed sections is unknown**; do not use them for attention decoding. Mixed
  trials carry the `mix` (as played) and both talkers, none marked attended.
- **Drift +164 ppm is an EEG-based estimate**, not a measured clock rate (no stimtrack, design durations unknown);
  the before/after slope check above supports it, a residual DNN check (first vs last 60 s) is inconclusive.
- **31 dead channels in 10 recordings** (sub-10, 11, 12, 13, 14, 22, 23, 24, 25, 26): the whole first actiCAP
  32-channel set except Cz; marked bad, data kept. sub-17 FC1 and sub-21 C1/Pz have low variance (~1 uV) and are
  listed in `low_variance_channels`, not marked bad.
- **Reference inferred**: JSON says Cz (a live channel), the paper says nose; the lowest-variance channels point to
  an online FCz reference (actiCAP default; inferred, not verified). Ground unknown (JSON AFz, paper forehead).
- Onsets of 63 sections come from a timeline, not a trigger; the trigger-to-sound latency is unknown.
- **sub-15 is truncated upstream** (455 s of section 1 only; the stimulus is longer than the EEG and is cut at
  use). The sub-26 header points to missing files and is read through a temporary patched copy.
- Upstream issues (to report): Table S2 mismatch, derivative section-4 epochs ~1-4 s off, dead channels, sub-15
  truncation, sub-26 header, participant names in the original file names, inconsistent reference (notes.md
  section 11).

Details: `notes.md`.
