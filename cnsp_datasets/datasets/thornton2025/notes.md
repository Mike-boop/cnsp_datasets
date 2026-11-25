# thornton2025: two competing talkers, dry-contact in-ear EEG (Zenodo 10260082)

Explorer and standardiser notes (2026-11-24). Evidence, logs and figures: `/data_storage/gu08wuvu/datasets/tmp/review/thornton2025/`
(temporary; the numbers that matter are copied here).

## 1. Source
- Zenodo 10260082, "Imperial College Ear-EEG Dataset for Auditory Attention Decoding", one archive
  `icl_earEEG_dataset.zip` (560.9 MB, md5 84692382ccc59a513e78188acd4ad667). Licence **CC-BY-4.0**.
- Paper: Thornton MD, Mandic DP, Reichenbach T (2025). Comparison of linear and nonlinear methods for decoding
  selective attention to speech from ear-EEG recordings. *IEEE Access* 13:127615ff, doi:10.1109/ACCESS.2025.3590490
  (`data_campaign/papers/thornton2025.pdf`; the Zenodo record cites the arXiv preprint 2401.05187).
- No code shipped. Copied from woody (the user's Zenodo pull), md5 checked on both ends, `unzip -t` OK.

## 2. Layout
- `upload_folder/eeg_data.h5`: `channels` = [`left_ear`, `right_ear`]; `eeg/sub-NNN/trial_TT`, float64
  (2, n) at 256 Hz, NNN = 000..018, TT = 01..16.
- `upload_folder/audio/trial_TT_{attended,ignored}.wav`: 44.1 kHz mono float32, RMS ~1 (normalised by the
  authors), 134.6-240.0 s.

## 3. Subjects, trials, conditions
- **19 subjects** in the h5 (sub-000..sub-018); the paper reports 18 participants. Which one is extra (pilot?) is
  unknown; all 19 are standardised. **sub-002 trial_01 is empty** (shape (2, 0)) and skipped: 303 trials.
- Paradigm (paper II.A, Fig. 1): two audiobooks narrated by a male and a female talker, presented **diotically**
  (no spatial separation) over Sennheiser HD450 headphones placed over the ear modules, equal level. Four short
  stories, each split into four trials of ~2.5 min; the to-be-attended talker alternates with each story.
- The wavs are named attended/ignored and are the same for every subject, so all subjects attended the same
  talker in a given trial. Talker sex from the median f0 of each wav (autocorrelation, 20-30 s): attended
  110-145 Hz (male) in trials 1-4 and 9-12, 169-205 Hz (female) in trials 5-8 and 13-16; the ignored wav is always
  the other sex. Condition `attend-male` / `attend-female`; story = (trial - 1) // 4 + 1 in the provenance.
- EEG length per trial = round(wav duration x 256) samples, identical across subjects (cut by the authors).

## 4. Speech features
- Raw audio of both streams, as shipped (float32, 44.1 kHz). Stimulus names `trial_TT_attended` /
  `trial_TT_ignored` (attended first). No transcripts or word alignments.

## 5. Neural data
- Custom dry-contact in-ear device (Imperial College), Bluetooth, sampled at 256 Hz (stored at 256 Hz).
  Two in-ear electrodes, both referenced to an electrode taped at **FT7** (lower left forehead); ground on the
  right earlobe (paper II.C). `left_ear`-FT7 is the unilateral channel, `right_ear`-FT7 the cross-head one.
- **The shipped EEG is z-scored per trial** (mean 0, SD exactly 1 in every channel of every trial) although the
  record calls it "unprocessed"; it is otherwise unfiltered (broadband spectrum, small 50 Hz peak; L/R correlation
  ~0.86 because of the common FT7 reference). No physical units can be recovered. Stored as `eeg` with the
  z-scores x 1e-6 (so 1 SD reads as 1 uV); `units_as_shipped` in the provenance says so.
- No positions (ear-canal electrodes), no EOG, no bads marked (two channels, both carry signal).

## 6. Alignment
- The ear modules contain microphones that recorded the headphone sound; the authors cross-correlated those
  recordings with the original audio offline and cut EEG and audio to start together (paper II.B; record: "The
  onsets of the EEG and speech material are already aligned"). The microphone signals are **not shipped**, so the
  onset cannot be re-measured here. `alignment_method` = `stimtrack_xcorr` (authors), trigger type hardware
  (microphone), shipped timing kept.
- Drift: not estimable from the release (no markers; EEG cut to the audio length). Whether the authors corrected
  drift between the Bluetooth EEG clock and the audio is not stated. The backward-decoder lag sweep (below) shows
  no offset at the 30-ms level.
- Match-mismatch DNN offset (WORKFLOW 6): **not applicable** (the accou2023 classifier interpolates a 64-channel
  10-20 montage; two ear channels without positions cannot be mapped).

## 7. Validation (all 19 subjects, 303 trials; original FT7 reference, both channels)
- Repo validator, low tier (forward model 0.5-8 Hz, attended audio): mean r 0.021 (median 0.022), population
  p_circ 0.020, p_mismatch 0.048, **10/19 subjects individually significant**; pass. TRF GFP peak 172 ms.
  MLR tier (30-60 Hz): SNR 1.00, p 0.60, fail (not expected at 256 Hz with two dry ear channels). Brainstem not
  run (256 Hz). Figure `validation/validation.png`.
- Attended vs ignored: section 8.

## 8. Attention contrast (backward decoders)
`/data_storage/gu08wuvu/datasets/tmp/review/scripts/earEEG/aad_check.py`: per subject, leave-one-trial-out ridge
decoder of the attended stream (both channels, 0.5-8 Hz, 64 Hz, EEG lags 0-500 ms, ridge = mean diagonal of
X'X), held-out r with the attended and the ignored stream, 30-s decoding accuracy, and a sweep of the held-out
stimulus shift (+-1 s, 31-ms steps).
- Hilbert envelope: attended median r 0.025 vs ignored 0.009, attended > ignored in **17/19** (Wilcoxon p 7e-5);
  30-s accuracy median 0.58.
- Onset envelope (half-wave rectified derivative): 0.027 vs 0.012, **16/19** (p 2e-4); 30-s accuracy 0.65. The
  paper also found the onset envelope better.
- Lag sweep peak 0 ms (bootstrap CI [0, 0] at 31-ms resolution) for both features. The decoders are trained on the
  same alignment, so this shows that trials and subjects share one offset; the absolute latency check is the
  forward TRF (GFP peak 172 ms, nothing before 0 ms above the null).
- Figures: `figures/r-attended-vs-r-ignored_env.png`, `figures/r-attended-vs-r-ignored_onset.png`; numbers in
  `figures/aad_env.json`, `figures/aad_onset.json`.

## 9. Data size
19 participants, 0.786 h per participant (0.748-0.788; sub-002 misses trial 1), 14.9 h in total.
attend-male 6.83 h (0.36 h per participant), attend-female 8.09 h (0.43 h).

## 10. Alignment grade
Proposed **medium**: hardware-derived onsets (microphone cross-correlation by the authors) that cannot be
re-verified from the release; the low tier passes with a plausible TRF latency and the decoder lag sweep peaks at
0 (section 8).

## Open questions (defaults taken)
- Units: z-scored EEG stored x 1e-6 as `eeg` (default) vs dimensionless `misc`. Default keeps the EEG tools working.
- 19 vs 18 subjects: all 19 standardised (no information on which is extra).
- Grade medium vs good: medium, because the microphone alignment cannot be checked here.

## Upstream issues
- The record calls `eeg_data.h5` "unprocessed EEG", but every trial is z-scored per channel.
- 19 subjects in the release vs 18 in the paper; sub-002 trial_01 is empty.

## Restructure 2026-11-25 (not yet re-validated on data)
- Adaptor subclasses BaseAdaptor; h5 subjects and trials iterated in sorted order; wavs read with iohelpers.read_wav
  (float32 as stored, mono checked).
