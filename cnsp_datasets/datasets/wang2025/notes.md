# wang2025: Le Petit Prince multi-talker, EEG part (OpenNeuro ds005345)

Explorer notes, 2026-11-22. Scratch scripts, tables and figures: `/data_storage/gu08wuvu/datasets/tmp/review/wang2025/`
(`scripts/*.py`, `*.txt`, `*.json`, `proposed_onsets.csv`, `drift_windows_per_subject.png`, `supp.pdf`). That folder
is temporary; every number that explains a choice is copied here.

**Headline.**
1. The stimuli were played **continuously** (one wav per ~10-min section), not sentence by sentence as in
   momenian2024 (section 6).
2. **Only the first section onset has a trigger** in 20 of 26 recordings (`S 11`). Six recordings have `S 31`-`S 34`
   (one per section), but `S 34` comes **~0.95 s after** the sound onset of section 4.
3. **The section order in the paper's Table S2 does not match the EEG.** EEG envelope tracking shows the same structure
   in every subject: positions 1-2 are the two mixed-talker sections, positions 3-4 the two single-talker sections, in
   one of two orders (section 3). Which talker was attended in each mixed section is unknown.
4. **Clock drift +164 ppm** (sound slower than the EEG clock; about 0.1 s per section), seen in the EEG of every subject
   with strong tracking (section 7).
5. Upstream data problems:
   - **10 recordings have 31 dead channels**;
   - sub-15 is truncated;
   - the header of sub-26 points to a non-existent data file;
   - the reference is documented inconsistently (section 5).

## 1. Source
- OpenNeuro ds005345 v1.0.1 (doi:10.18112/openneuro.ds005345.v1.0.1), registry entry `wang2025` (func/anat/derivatives
  excluded), licence **CC0**. v1.0.1 (2025-04-17, "add IRB info") is the **latest snapshot** (OpenNeuro GraphQL:
  snapshots 1.0.0 and 1.0.1 only). There is no newer version with sentence wavs or corrections.
- Paper: Wang Q, Zhou Q, Ma Z, Wang N, Zhang T, Fu Y, Li J (2025). Le Petit Prince (LPP) multi-talker: Naturalistic
  7 T fMRI and EEG dataset. *Scientific Data* 12:829, doi:10.1038/s41597-025-05158-7. Supplementary PDF
  (`41597_2025_5158_MOESM1_ESM.pdf`): Table S1 lists the quiz questions, Table S2 the "participants run order".
- Code: https://github.com/compneurolinglab/lpp_multi-talker. The relevant files are `preproc_eeg.py` (PyPREP, 0.1-39 Hz
  filter, ICA; montage `CACS-64.bvef`), `compute_evoked.py` and `compute_isc_eeg.py`. The code has **no epoching or
  onset code**: the per-section `.npy` files it uses are not shared.
- Same lab family as momenian2024 (Jixing Li, CityU HK). Stimulus text from xiaowangzi.org; the TTS voices come from
  the Institute of Automation, CAS (paper).

## 2. Layout
- `sub-XX/eeg/sub-XX_task-multitalker_eeg.{vhdr,vmrk,eeg,json}`: one continuous BrainVision recording per participant
  for 26 participants (sub-01..26). There are no `events.tsv`, `channels.tsv` or `electrodes.tsv` files.
- Original lab file names (`subjN_case|control_<sex>_<name>_<n>.eeg`) are still in the `.vmrk` `DataFile=` lines and in
  sub-26's `.vhdr`. They contain participant names (privacy; upstream issue). The "case"/"control" labels are
  undocumented. The paper describes only healthy participants.
- `stimuli/single_female.wav` (603.000 s), `stimuli/single_male.wav` (599.818 s), `stimuli/mix.wav` (603.000 s). All
  three are 44.1 kHz mono int16 wavs.
- `annotation/single_{female,male}_word_information.csv` (columns word, onset, offset, duration, logfreq, pos, td, bu,
  lc) and `annotation/{single_female,single_male,mix}_acoustic.csv` (f0 and intensity every 1 ms).
- `quiz/multitalker_quiz_question.csv` (16 questions; used in the fMRI session).
- Not downloaded: `derivatives/sub-XX/eeg/sub-XX_task-multitalker_run-{1..4}_eeg_preprocessed.fif`. These are MNE
  `Epochs` with one epoch each, 500 Hz, -0.5..600.5 s, 0.1-39 Hz, ICA. The event sample of every one of the 104 files
  was read with HTTP range requests (`scripts/fif_events3.py`; result in `deriv_events.txt`). They show the onsets the
  authors used (section 6).

## 3. Stimulus <-> trial mapping (verified with the EEG; differs from the paper)
- **Paper design:** four ~10-min sections presented in random order:
  - single female (`single_f`);
  - single male (`single_m`);
  - mixed, attend female (`mixed_f`);
  - mixed, attend male (`mixed_m`).

  An on-screen instruction ("Attend female") preceded each mixed section. Sound came through ER-3C insert earphones,
  with both talkers diotic in one channel. Table S2 gives a run order per participant.
- **Stimuli:**
  - `mix.wav` = 0.5 x `single_female.wav` + 0.5 x `single_male.wav`, sample-exact: least-squares coefficients
    0.50006/0.50007, residual RMS 0.31 LSB (rounding), both start at sample 0 (`scripts/wavcheck.py`).
  - After the male wav ends at 599.818 s, the mix is female only (r = 1.0000).
  - The female story ("section 1" of the book) and the male story ("section 2") are different texts.
  - Sound starts at 0.0007 s in the female wav and at 0.314 s in the male wav.
- **What the EEG shows** (`scripts/decode.py`, `classify.py`, `labeltest.py`, `sweep.py`): each section was decoded
  separately with a backward model:
  - preprocessing: 64 channels, average reference, 1-8 Hz, 50 Hz sampling, EEG lags 0-400 ms;
  - 5-fold cross-validation within the section;
  - targets: the female, male or mix envelope (rectified audio, 1-8 Hz);
  - the shift between EEG and envelope was scanned over +-10 s.

  The results:
  - In 23 of 26 subjects, **positions 3 and 4 are clean single-talker sections**: one tracks only the female envelope
    (male r < 0.03), the other only the male (female r < 0.03). For example:
    - sub-04: p3 female r 0.013 / male r 0.244, p4 female 0.158 / male 0.008;
    - sub-22: p3 0.157 / -0.009, p4 0.002 / 0.171.
  - **Positions 1 and 2 track both talkers in many subjects**: female and male r both >= ~0.04 in at least one of them
    in sub-01 (p2), 02 (p2), 04, 05, 07 (p2), 08 (p2), 12, 13, 14, 19, 20, 22 and 25. Each subject heard exactly one
    `single_f` and one `single_m`, so positions 1-2 are the **two mixed sections**. The male talker is tracked better
    than the female overall (single-section r: male 0.06-0.24, female 0.05-0.17).
  - Two orders, called **group A** and **group B** below:

    | group | p1 | p2 | p3 | p4 | p4 onset after first marker | subjects |
    |---|---|---|---|---|---|---|
    | A | mixed | mixed | `single_m` | `single_f` | 2192.2 s | 01 02 04 05(?) 06 10 11 12 13 14 17 18 21 23 24 25 26 |
    | B | mixed | mixed | `single_f` | `single_m` | 2196.2 s | 03 07 08 09 16 19 20 22 |

    sub-15 is truncated within p1. Low-confidence calls:
    - sub-05: only a weak male-only p3 (r 0.030);
    - sub-10: p3 male 0.056, and at p4 female 0.059 at the A timing, male 0.057 at the B timing;
    - sub-09 and sub-23: medium confidence.

    The p4 timing is a second, independent signal for the group. Within each group, the timing agrees with the talker
    tracked at p4 (`scripts/losotab.py`, `loso_table.txt`):
    - group A: the female at p4 starts at 2192.13-2192.27 s after the first marker;
    - group B: the male at p4 starts at 2196.15-2196.30 s.
- **Table S2 does not describe the EEG sessions.** Counted over positions predicted to be single-talker, Table S2 agrees
  with the EEG in 21 cases and disagrees in 25 (chance). It puts mixed sections at positions 3-4 for many subjects
  (e.g. sub-04 p3 `mixed_m`, p4 `single_m`; the EEG shows p4 female-only with r_f 0.158 / r_m 0.008). Table S2 probably
  gives the fMRI run order: the paper calls the order randomised, and the fMRI was recorded two years later. That is
  not stated anywhere.
- **The authors' derivative "run" labels are not a fixed condition code either.** Run k maps to a recording position
  differently across subjects (`deriv_onsets_table.txt`). Relative to Table S2, the labels are consistent for 13
  subjects and f/m-swapped for 13 (`scripts/deriv_table.py`).
- **The attended talker in the two mixed sections is not recoverable.** Comparing (r_f - r_m) between p1 and p2 gives
  no consistent pattern: p1 is "more female" in 15 of 25 subjects, median difference 0.002. The male voice dominates
  tracking in both mixed sections. Single-trial attention decoding at 1-8 Hz with this SNR is not reliable enough to
  label them.

## 4. Speech features available
- Raw audio for all three streams: female, male, and their mix (the mix is what was played in the mixed sections).
- Word timings (`*_word_information.csv`):
  - units are **centiseconds** (integers: e.g. `onset 60273` = 602.73 s), relative to the start of the wav;
  - female: 1753 words, 0.00-602.98 s; male: 1514 words, 0.25-596.55 s (the first male word is marked 64 ms before
    the first non-zero male audio sample);
  - inter-word gaps exist (female 441, male 290), there are no negative gaps or durations, and onsets are monotonic.
    The timings look forced-aligned (unlike momenian2024's interpolated timings);
  - extra columns: POS, log frequency, and parser node counts (td/bu/lc).
- No phoneme annotation and no transcript text file; the words are in the CSVs. f0 and intensity are at 1 ms in
  `*_acoustic.csv`, although the paper says 10 ms.

## 5. Neural data
- **System:**
  - JSON: Brain Products BrainAmp DC with an EasyCap "M10" cap (M10 is an equidistant layout, but the channel names are
    10-20);
  - paper: 64-channel actiCAP and Brain Vision Recorder, "0.016-80 Hz", impedances < 20 kOhm;
  - header: low cutoff 10 s (0.016 Hz), **high cutoff 1000 Hz** (hardware), no software filters. The 80 Hz in the
    paper is not in the header.
- **Rate and units:** 500 Hz in all files, INT_16 at 0.1 µV resolution, multiplexed. MNE reads them in V correctly.
  Median 1-40 Hz SD is 7-16 µV for good subjects (`headers.txt`). 500 Hz is a "nice" rate, so no resampling is needed
  for the rate itself.
- **Segments:** one `New Segment` at sample 1 in every file (no pauses). Durations 2468-3259 s, except sub-15.
- **Channels:** 64 EEG, identical order in all files. MNE reads them all as `eeg`. There are **no EOG, ECG, mastoid,
  aux or stimtrack channels**. TP9/TP10 (near the mastoids) and FT9/FT10 are ordinary scalp electrodes. FCz is absent
  from the channel list.
- **Reference: inconsistent documentation.**
  - The JSON says `EEGReference: Cz`, but Cz is a normal active channel in every file (1-40 Hz SD 10-15 µV, not flat).
  - The paper says "against a nose reference".
  - The data point to an online **FCz** reference (the actiCAP default; FCz is missing from the list): the lowest-
    variance channels in every good subject are FC1/FC2 (2-3 µV), then F1/Fz/C1/C2 (`scripts/refcheck.py`).
  - Ground: AFz per the JSON, but AFz is a recorded channel; the paper says "forehead". Unknown.
  - Record: "online reference not documented consistently (JSON Cz, paper nose); data indicate FCz (inferred)".
- **Dead channels (upstream):** in **10 recordings (sub-10, 11, 12, 13, 14, 22, 23, 24, 25, 26)**, physical channels
  1-23 and 25-32 are dead (`scripts/flatcheck.py`, `flatlist.py`):
  - the 31 channels are C3 C4 CP1 CP2 CP5 CP6 F3 F4 F7 F8 Fz FC1 FC2 FC5 FC6 Fp1 Fp2 FT10 FT9 O1 O2 Oz P3 P4 P7 P8 Pz
    T7 T8 TP10 TP9;
  - signs: 1-40 Hz SD 0.8 µV, inter-correlated r = 0.97, uncorrelated with the live channels, dominated by 50 Hz;
  - this is the whole first 32-channel actiCAP set except Cz (physical 24). Only 33 channels are usable there;
  - this holds throughout each recording, in all 4 sections;
  - the authors' derivatives went through PyPREP "interpolation", which cannot recover 31 channels.

  Isolated low-variance channels: sub-17 FC1 (~1 µV; next to the reference, possibly fine), sub-21 C1 and Pz (~1.1 µV).
- **Digitisation:** none; template positions only. The authors used `CACS-64.bvef`; use `standard_1005`, which covers
  all 64 names.
- `meas_date` is in 2010 (vmrk New Segment timestamps), while `participants.tsv` gives 2021 acquisition dates. The
  recording PC clock was wrong. Use `participants.tsv` for dates, or leave them unset.
- **sub-15 is truncated upstream:** the `.eeg` is 30,544,873 bytes, which equals the S3 Content-Length and is not a
  multiple of 128 bytes/sample. That is 238,631 samples (477.3 s) out of the expected ~2850 s. The first marker is at
  21.91 s, so only **455 s of section 1** is present. The authors' derivatives for sub-15 contain all four sections, so
  the original file was complete.
- **sub-26 `.vhdr` is broken upstream:** `DataFile=`/`MarkerFile=` point to the original lab file names, so MNE raises
  `FileNotFoundError`. The adaptor has to read it through a patched header copy pointing at
  `sub-26_task-multitalker_eeg.{eeg,vmrk}` (as done in `tmp/.../patched/`). The data are fine: 1,411,950 samples,
  `S 11` at 24.83 s.

## 6. Alignment
- **Markers** (`.vmrk`, all files checked; `headers.txt`):
  - `S 11` once per file (20 recordings: sub-01..11, 15..22, 26): start of section 1;
  - `S 31`, `S 32`, `S 33`, `S 34` (6 recordings: sub-12, 13, 14, 23, 24, 25): one per section;
  - `Comment/actiCAP Data On` at the start of every file.

  There are no end markers and no other codes. The code meanings are not documented. The meaning given here is
  inferred from the timing and the EEG.
- **Hardware or software triggers:** not documented, and the presentation software is not named. **Inferred software**
  triggers:
  - the inter-trigger intervals fall on a ~16.7 ms grid (735.052 / .068 / .084 / .102 s), i.e. they are locked to
    60 Hz screen frames;
  - `S 34` is ~0.95 s after the EEG-estimated sound onset of section 4 in all 6 recordings. Compared with the EEG
    estimates: sub-12 2193.156 s vs ~2192.18 s; sub-14 2193.220 vs 2192.266; sub-25 2193.204 vs 2192.266; sub-24
    2193.204 vs ~2192.3.

  `S 32`/`S 33` agree with the EEG-estimated onsets within +-0.15 s, which is the precision of the EEG method.
- **Continuous, not sentence-wise:**
  - one wav per section with one (or no) trigger per section, and no sentence files in any version;
  - the mixed stimulus is a sample-exact sum of two different stories, so it cannot have been played sentence by
    sentence;
  - the EEG lag within each section moves linearly by ~0.1 s per 600 s (section 7). momenian2024 showed 0.8-1.9 s per
    5 min from inter-sentence gaps.
- **Stimtrack:** none.
- **Section timeline relative to the first marker** (sound onsets):
  - From the six `S 3x` recordings (fit in section 7), design intervals are **735.071 s** (p1 to p2) and
    **1470.137 s** (p1 to p3); `S 34` is at 2193.204 s but late (see above).
  - EEG estimates, leave-one-section-out decoders on strong subjects (`scripts/loso.py`, `loso_table.txt`):
    p2 735.04-735.22 s, p3 1469.99-1470.12 s, p4 2192.13-2192.27 s (group A) or 2196.15-2196.30 s (group B).
  - sub-16 and sub-18 ran with shorter pauses. Following the authors' derivative onsets, their offsets are 615.06,
    1230.12, and 1832.2 (sub-18, A) or 1836.2 (sub-16, B) s. The EEG agrees within ~0.25 s (p2 614.95-614.96 s,
    p3 1229.87-1229.95 s, p4 1831.94 or 1835.98 s).
  - Gaps between sections: 132.1 s after each mixed section; 122.2 s (A) or 123.1 s (B) after p3. Not explained.
- **The authors' derivative epochs** (`deriv_events.txt`, `deriv_onsets_table.txt`):
  - for `S 11` subjects they place sections 2-4 at fixed sample offsets: +367530, +735060, and +1096590 or +1098090;
  - group A p4 is therefore **~1 s late**;
  - for sub-04 (group A) and sub-24 (whose `S 34` is at +2193.204 s) they used +2196.18 s, **~4 s late**;
  - for sub-22 (group B) they used 2193.18 s, ~3 s early.
- **Proposed alignment (one trial per section; `proposed_onsets.csv`):**
  - p1 = first marker (`S 11`/`S 31`);
  - p2/p3 = `S 32`/`S 33` where present, otherwise first marker + 735.07 / 1470.14 s (615.06 / 1230.12 s for sub-16
    and sub-18);
  - p4 = first marker + 2192.2 s (group A) or 2196.2 s (B); 1832.2 / 1836.2 s for sub-18 / sub-16. Do **not** use
    `S 34`.

  Sidecar fields:
  - `alignment_method`: `sw_trigger` for p1 and for p2/p3 of the 6 trigger subjects; `onset_only` (timeline from the
    first trigger, confirmed by EEG envelope tracking) for the rest;
  - `trigger_type`: software (inferred; 60 Hz frame grid; no documentation);
  - `jitter_ms`: ~4 for triggered onsets (section 7). For timeline onsets the cross-subject spread of the trigger
    timeline is SD 19-40 ms and up to 0.12 s at p4. The trigger-to-sound latency is unknown; the validator's lag sweep
    estimates it.
- **Stimuli per trial:**
  - single sections: the single wav (`single_female` / `single_male`);
  - mixed sections: `mix` (what was played) **plus `single_female` and `single_male` as separate streams**.

  Attended talker: "unknown" (section 3). Optionally keep Table S2's claim as a note marked unreliable.

## 7. Cross-subject duration check, drift and jitter
- **Triggers** (6 recordings, `scripts/drift.py`, `drift.txt`): fit of t_k - t_1 = D_k (1 + delta_s) + noise.
  - D = 735.0713, 1470.1367, 2193.2040 s.
  - Per-subject delta relative to the mean: -22, +32, +9, -19, 0, 0 ppm (sub-12, 13, 14, 23, 24, 25).
  - **Residual SD 4.1 ms** (jitter).
  - Raw interval SD across subjects: 19, 31, 40 ms (p2, p3, p4). The between-subject spread grows with length, so it is
    drift-like, not jitter.
  - The design durations are unknown, so these triggers cannot give the absolute drift.
- **EEG slide within sections** (`scripts/drift.py`, `drift_plot.py`, figure `drift_windows_per_subject.png`):
  - method: backward-model reconstruction in held-out 60-s windows (decoder trained on the rest of the section), with
    the peak lag found per window at 20-ms steps; Theil-Sen slope over the 10 windows;
  - result over sections with z >= 6 (32 sections, 18 subjects): **median +164 ppm, IQR +138..+176**;
  - 30 of 32 sections give +75..+204 ppm. The two outliers are noisy sections (sub-07 p2 +31, sub-22 p1 -2);
  - every subject's panel shows the same linear rise, about -45 ms to +45 ms across a section;
  - per-subject estimates have about +-50 ppm uncertainty, so there is no evidence of subject clusters;
  - positive means the sound runs slower than the EEG clock: stimulus time tau appears at EEG time t0 + tau(1 + 164e-6),
    i.e. 99 ms over 603 s;
  - this slide comes from the playback or EEG clock, not from sentence gaps: it is linear and 20-30x smaller than
    momenian2024's.
- **Recommendation:** correct +164 ppm for every trial: resample the EEG by 1/(1 + 164e-6) in the same step as any other
  resampling, or stretch the stimulus timeline. Set `drift_ppm` = 164 (pooled EEG estimate; per-subject values are too
  noisy to use). The onsets above are section-mean estimates. After drift correction, the onset of each section is
  ~50 ms earlier than its section-mean lag, which is below the precision of the EEG estimate.
- All proposed trials except sub-15 fit inside their recordings, including +0.1 s for drift. Closest margins between
  the end of p4 and the end of the file: sub-08 1.1 s, sub-05 3.6 s, sub-26 3.8 s, sub-16 3.8 s, sub-04 4.4 s.

## 8. Data size
- Per complete participant: 3 x 603.000 s + 599.818 s = 2408.8 s (0.669 h). Per condition: mixed 1206 s, `single_f`
  603 s, `single_m` 599.8 s.
- **26 participants, 16.85 h** (mean 0.648 h, range 0.126-0.669 h). Of these, 25 are complete and sub-15 has 455 s of
  one mixed section.
- Per condition:
  - mixed: 8.50 h (2 sections x 25 + 455 s);
  - `single_f`: 4.19 h;
  - `single_m`: 4.17 h.
- Only 16 participants (10.7 h) have all 64 channels working; the other 10 have 33.
- Not yet added to `tmp/review/data_size.csv`/`data_size.md` (leave to the standardiser with the final trial list).

## 9. Proposed adaptor
- Registry: keep v1.0.1 (latest). Derivatives are not needed (their onsets are in `tmp/.../deriv_events.txt` and
  summarised above).
- Trials: participant x position, 4 trials each (sub-15: 1 trial cut at the end of the data). Label the conditions as
  `mixed` (p1, p2; attended talker unknown) and `single_f`/`single_m` (p3/p4 by group).
  - The group table (A/B) is a static per-subject table in the adaptor, from this EEG analysis. It cannot be derived
    from the shipped files.
  - Onsets as in section 6 (`proposed_onsets.csv` has every value).
- Stimuli:
  - single sections: the single wav;
  - mixed sections: `mix`, `single_female`, `single_male`.

  Word TextGrids for the single wavs from the word CSVs (centiseconds to seconds). The mix gets two word tiers
  (`words_female`, `words_male`) or two TextGrids. No phones tier.
- Channels: all 64 `eeg` (template `standard_1005`). Put the 31 dead channels of the 10 affected subjects in
  `info['bads']`, keep the data, and note it in the sidecar. Keep the original reference (no re-referencing) and record
  it as in section 5.
- sub-26: read through a patched `.vhdr` copy (or a direct int16 memmap at 0.1 µV scaling, 64 channels multiplexed).
  sub-15: MNE reads the 238,631 complete samples.

## 10. Open questions (recommended default in brackets)
1. **Condition labels:** the EEG shows positions 1-2 = mixed and 3-4 = single (groups A/B), contradicting the paper's
   Table S2. [Use the EEG-based labels and record "Table S2 does not match the EEG; labels from envelope tracking" in
   the metadata. Flag sub-05 (low confidence) and sub-10/09/23 (medium) in the sidecar. Ask the authors which order
   the EEG used.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): EEG-based labels (`onsets.csv`, group A/B);
   `condition_source` in the sidecar says Table S2 does not match; `group_confidence` low for sub-05, medium for
   sub-09/10/23, high otherwise, n/a for sub-15.
2. **Attended talker in mixed sections:** unknown. [Store as `attended: unknown` with both talker streams and the mix
   as stimuli; do not guess. Optionally keep Table S2's mixed_f/mixed_m order as `attended_claimed` with a warning.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): `attended: unknown`; mixed trials carry `mix` (as
   played), `single_female` and `single_male`, none marked attended; conditions `mixed`, `single-female`,
   `single-male`. Table S2's attended claim not stored (Table S2 does not describe the EEG sessions, so its
   per-position claim is meaningless).
3. **Onsets of untriggered sections** (20 subjects x 3 sections): timeline from the first marker, with no trigger. The
   EEG confirms it within ~+-0.15 s in strong subjects. [Use the timeline of section 6 and `alignment_method:
   onset_only`. Let the validator's per-position lag sweep report residual offsets. Do not refine onsets per subject
   from the EEG, which is no more precise than the timeline.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): timeline onsets from `onsets.csv` (copy of
   `proposed_onsets.csv`); `alignment_method` `sw_trigger` where S 11/S 31-S 33 exist (38 trials), `onset_only`
   otherwise (63 trials); `jitter_ms` 4.1 for all trials, plus `timeline_sd_ms` 19.3/31.4/40.2 (positions 2/3/4) for
   timeline onsets.
4. **`S 34` (section 4 trigger) is ~0.95 s late:** [ignore it; use first marker + 2192.2/2196.2 s.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): S 34 ignored.
5. **Drift +164 ppm** (EEG-based, plotted per subject): [apply one pooled correction of +164 ppm to all trials (stimulus
   stretched / EEG resampled in the same step) and record `drift_ppm: 164`. Alternative: no correction plus a warning.
   99 ms per section matters for TRF latency, so correction is recommended.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): +164 ppm applied to every trial
   (`drift_correction=164e-6`, None disables), with the onset in one quintic-spline interpolation
   (`clock.crop_on_audio_clock`; drift > 0 = neural clock counts more samples per stimulus second, same sign as the
   explorer's tau(1 + 164e-6)). Post-correction check: see section 13.
6. **Dead channels in 10 subjects** (31 of 64): [mark as bads and keep the subjects; the validator uses average
   reference over good channels. An alternative is excluding them from the pilot.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): 31 channels in `info['bads']` for the 10 subjects,
   subjects kept. sub-17 FC1 and sub-21 C1/Pz listed as `low_variance_channels`, not bad.
7. **sub-15** (455 s of section 1 only): [keep the partial trial; its stimulus is longer than the EEG and is cut at use,
   per convention.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): kept (227,638 samples = 455.3 s of position 1; positions
   2-4 skipped).
8. **Reference:** documented as Cz (JSON) and nose (paper); data indicate FCz. [Record "unknown; inferred FCz (actiCAP
   default)", with no re-referencing; validate with an average reference as usual.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): reference recorded as 'unknown ... inferred FCz'; not
   re-referenced.
9. **sub-16/sub-18 timeline** (615-s spacing) relies on the authors' offsets, which the EEG confirms within ~0.25 s.
   [Use them; flag `timeline: short-pause session`.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): authors' offsets; `short_pause_session: true` in the
   sidecar.
10. **Group assignment for sub-05** (weak tracking, A by p3 male-only r 0.030): [A, flagged. If the validator shows no
    tracking at p3/p4 for sub-05, drop its single-talker trials.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): group A, `group_confidence: low`; revisit after validation.

## 11. Upstream issues (to report)
1. Table S2 run order (and the derivative run labels) do not match the EEG recordings. In the EEG, mixed sections are
   at positions 1-2 for every subject, and single sections at 3-4 in one of two orders.
2. The derivative epochs for section 4 are ~1 s late for most subjects and ~4 s off for sub-04, sub-22 and sub-24.
   Sections 2-4 of the `S 11` recordings have no triggers.
3. 31 channels are dead in 10 recordings (sub-10, 11, 12, 13, 14, 22, 23, 24, 25, 26).
4. sub-15 raw `.eeg` is truncated (477 s of ~2850 s), although the derivatives are complete.
5. The sub-26 `.vhdr` `DataFile`/`MarkerFile` point to the original file names, so the file is unreadable as shipped.
6. Original file names containing participant names remain in the `.vmrk` (all subjects) and the sub-26 `.vhdr`.
7. Reference documented as Cz (JSON) and nose (paper); the data indicate FCz. The ground is given as AFz (JSON), which
   is a recorded channel. The JSON `SoftwareFilters` lists 0.02-1000 Hz Butterworth, while the header has none.
8. The README is partly copied from the multilingual LPP dataset (French cohort, visual stimuli, 70-min fMRI session,
   25 participants vs 26 in the paper).
9. The paper describes 10-ms acoustic features; the CSVs are at 1 ms.

## 12. Related datasets
- momenian2024 (same lab): sentence-wise presentation with per-sentence triggers. wang2025 differs: continuous wavs,
  section-level triggers (mostly only the first), and a ~164 ppm clock drift.

## 13. Adaptor (standardiser, 2026-11-22)
- `adaptor.py` reads `onsets.csv` (a copy of the explorer's `proposed_onsets.csv`: one row per participant and
  position with group, condition, onset in s from the first sample, onset source and the explorer's r_f/r_m). The
  adaptor checks the position-1 onset against the first `S 11`/`S 31` marker of each `.vmrk`.
- sub-26 is read through a patched header copy in a temporary directory (absolute `DataFile`/`MarkerFile`); the
  download is not modified. `meas_date` is cleared (wrong PC clock); the EEG date from `participants.tsv` is in the
  sidecar.
- Pilot (all 26 participants): 101 trials, 0 failures, all 500 Hz, 64 channels; every trial is
  ceil(longest stimulus x 500 / 44100) samples except sub-15 (227,638 samples = 455.3 s). mixed 51 trials 8.50 h,
  single-female 25 trials 4.19 h, single-male 25 trials 4.17 h; 16.85 h in total. 38 `sw_trigger` onsets
  (S 11 x 20, S 31/S 32/S 33 x 6 each), 63 `onset_only` (timeline).
- **Post-correction lag-slope check** (explorer method: backward model, held-out 60-s windows, Theil-Sen;
  `tmp/.../scripts_std/drift_check.py`, `drift_check_corrected.png/.json`), 7 strong sections of sub-04, sub-20,
  sub-22, uncorrected -> corrected (ppm): sub-04 p3 +198 -> +16, p4 +182 -> +9; sub-20 p3 +176 -> -3,
  p4 +202 -> +33; sub-22 p2 +183 -> -4, p3 +177 -> -7, p4 +220 -> +13. Median +183 -> +9 ppm; corrected 95 % CIs
  all include 0. The sign convention of `crop_on_audio_clock` (drift > 0 = the EEG counts more samples per stimulus
  second) matches the explorer's tau(1 + 164e-6).
- In the same check the absolute backward-model peak differs between sections by up to ~0.2 s (e.g. sub-04 p3
  ~0 ms vs p4 ~190 ms; sub-22 p2 ~200 ms vs p4 ~100 ms). This is the timeline-onset uncertainty the explorer
  reported (+-0.15 s); the validator's per-position lag sweep should report it.

## 14. Timing check: match-mismatch DNN (2026-11-22; note only, no change)
`fs128_1020-64_broadband` classifier (trained on accou2023; `tmp/review/scripts/dnn_drift_check.py` + per-position
pooling) on the pilot output (+164 ppm drift applied; onsets as in `onsets.csv`), stimulus = the trial's first
(attended-flagged) stimulus (the mix in mixed sections). Offsets relative to accou2023; negative = neural response
later than in accou2023. Lag curves z-scored per trial, pooled over subjects per position; CIs by subject bootstrap.

| position | condition | n | offset | 95% CI | minus position 1 (paired) |
|---|---|---|---|---|---|
| 1 (first marker, S 11/S 31) | mixed | 26 | -198 ms | -220 .. -184 | |
| 2 | mixed | 25 | -254 ms | -282 .. -228 | -51 ms [-87, -24] |
| 3 | single talker | 25 | -173 ms | -187 .. -165 | +29 ms [+9, +52] |
| 4 | single talker | 25 | -205 ms | -215 .. -193 | -3 ms [-21, +18] |

- **A constant ~-200 ms offset in every section, including the triggered first one**: the sound most likely started
  ~0.2 s after the markers (software trigger with default, non-low-latency audio output; typical for such setups).
  Clean single-talker speech scores within +-5 ms in hand-aligned datasets and competing speech ~-15..-45 ms, so most
  of this is timing, not response latency. Largest offset in the collection (das2019 -81 ms, bentum2023 -68 ms).
  **Not applied** (same handling as das2019/bentum2023); open question for the user: shift all onsets by ~+0.19 s
  Decided by the user (2026-11-22): document only, no onset correction for now.
  (sound later)?
- Timeline-derived positions 2 and 3 deviate from position 1 by -51 and +29 ms: the timeline is good to tens of ms
  (explorer: 19-40 ms SD), consistent with the validator's per-section lag spread. A per-section DNN refinement
  (PLAN alignment_method `dnn`) would be possible; not done.
- Residual drift (first vs last 60 s): pooled +21 ms over ~536 s but per-subject median -6 ms: inconclusive, so the
  EEG-slope-based +164 ppm correction stands.

## 15. Validation and coherence (2026-11-22)
Results in `validation.json` (this folder; validator plus review backward/TRF-latency/talker scripts). Coherence
in `/data_storage/gu08wuvu/datasets/tmp/review/coherence_batch/{128,native}/` as
`wang2025_{mixed,single-female,single-male}.json` (temporary; numbers copied here). Reference: average over each
subject's live channels (64, or 33 for the 10 dead-channel subjects).
- **Tier: low for all 101 trials** (`trial_validation_tier_counts`); set as `validation_tier="low"` in the adaptor.
  Low passes in every condition (mixed, single-female, single-male; mixed also with each talker as regressor) and
  every position 1-4 (backward); mlr and brainstem fail everywhere.
- **Backward** (ridge decoder, 64 Hz, 0.5-8 Hz, lags 0-250 ms, leave-one-trial-out; 50 circular shifts >= 5 s;
  mismatch = other talker, single trials only): single median r 0.0686, 25/25 above circ and mismatch nulls
  (female 0.0702, 22/25 circ, not 3/11/13; male 0.0674, 19/25, not 3/9/10/11/13/23); mixed: mix 0.0261 (20/25),
  female 0.0213 (15/25), male 0.0320 (20/25); all primary 0.0462 (25/25). sub-15 (one trial) has no decoder.
- **Lag sweep** (+ = stimulus delayed): single +3.8 ms [-11, +22]; mixed_mix +88 ms [+70, +107], mixed_female +85,
  mixed_male +76; pos1 +74, pos2 +103, pos3 +3, pos4 +5 ms. Relative position offsets (paired, median):
  pos2-pos1 +33 ms [+11, +97], pos3-pos1 -62 ms [-97, -9], pos4-pos1 -24 ms [-74, +30]. The decoder is trained on
  trials with the same timing, so the common offset does not appear in the sweep.
- **Forward (validator `all`)**: median r 0.0148, 12/25 subjects sig (p_circ 0.020, p_mismatch 0.048, mismatch
  contaminated: mixed trials are paired with their own components), TRF peak 0.25 s; `single` 0.0202, 12/25 circ,
  21/25 mismatch, peak 0.234 s. mlr: SNR 0.957, p 0.86, 1/25; brainstem 1.042, p 0.12, 3/25 (same pattern in all
  subsets). Validator jitter/drift: SD 230 ms, 81 +- 178 ppm (noise).
- **TRF latency** (`latency_trf_fc`, 128 Hz, 1-15 Hz, fc2 cluster F1 F2 FC3 FC4 C1 C2 Cz, all 26 subjects):
  main positive peak at 219-234 ms (pos2 266 ms); P1 in a window shifted by 200 ms at 225-275 ms. Template shift
  vs herrmann2025 clear (P1 35 ms, N1 89 ms in the same code): all +180, pos1 +180, pos2 +234, pos3 +164, pos4
  +188, single +172, mixed_mix +188, mixed_male +227 ms (corr 0.68-0.86). The fc cluster (Fz Cz F3 F4 C3 C4,
  16 subjects without dead channels) gives +180..+219 ms for mixed/pos1-3 but +86..+94 ms for single/pos4
  (secondary early maximum at ~130-140 ms); fc2 is the better-powered estimate.
- **DNN** (section 14; `dnn_offsets_log_tail`): all -197 ms [-270, -184]; early/late halves -210/-189 ms.
  Together with the TRF: constant offset, the sound most likely started ~0.18-0.20 s after the markers. **Not
  corrected** (pending the user's decision; same handling as das2019/bentum2023); the README tells users to shift
  the stimulus by ~+0.19 s for absolute latencies.
- **Talker tracking in mixed sections** (`mixed_talker_tracking`, decoder trained on the single sections): median r
  female 0.0213, male 0.0307 (Wilcoxon male > female p 0.0022); significant female 17/50 sections, male 27/50,
  both 13/50; female > male in 17/50. Female-minus-male changes sign between p1 and p2 in 9/25 subjects (binomial
  p 0.23): no attention-switch signature; attended talker stays unknown.
- **Weak subjects**: 3, 9, 10, 11, 13, 23 (not above the circ null in single-male and/or single-female). Kept.
- **Coherence** (ratio to one global-shift surrogate, 5 s Hann windows, 4 s overlap; 128 Hz and native 500 Hz):

  | condition | n trials | 0.2-1 | 1-4 | 4-8 | 8-15 | 15-30 | 30-60 | 60-120 | 120-250 Hz |
  |---|---|---|---|---|---|---|---|---|---|
  | mixed | 51 | 2.32 | 2.14 | 1.51 | 1.09 | 0.99 | 1.06 | 1.00 | 1.02 |
  | single-female | 25 | 2.92 | 1.99 | 1.12 | 1.09 | 1.06 | 1.02 | 1.01 | 1.00 |
  | single-male | 25 | 2.54 | 2.09 | 1.28 | 1.10 | 0.98 | 1.03 | 1.03 | 1.00 |

  Native and 128 Hz agree within 0.01 below 60 Hz; the two highest bands are native only.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**poor**: Software triggers for section 1, the rest from a timeline; drift +164 ppm brain-derived applied; DNN ~-200 ms documented, 'mostly timing'; low tier.
