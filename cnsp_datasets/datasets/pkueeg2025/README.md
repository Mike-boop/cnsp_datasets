# pkueeg2025: 50 Mandarin stories over three days (PKUEEG)

EEG of 25 native Mandarin listeners hearing 50 synthesised chapters retelling the Three Kingdoms story (~4 h per
listener), recorded over three days with two different EEG systems.

- **Source:** OpenNeuro ds008834 v1.0.4 ("PKUEEG"), doi:10.18112/openneuro.ds008834.v1.0.4. Licence CC0. Registry
  entry `pkueeg2025` (the authors' preprocessed NPZ files and stimulus features are not downloaded).
- **Papers:** no data paper. The data are used in Zhang A, Wang B, Wu X, Cheng H, Chen J (2026). Cross-subject
  generalization in decoding perceived speech from non-invasive brain recordings. arXiv:2608.22420; and in Xu X,
  Yan Y, Li S, Zheng L, ... Chen J. SHINE: sequential hierarchical integration network for EEG and MEG.
- **Code (authors):** https://github.com/boda-xiao/PKUEEG (copy in the download's `code/`).

## Size
25 participants x **4.00 h** (all 50 stories each), 100.1 h, 1,250 trials (pilot: 12 participants, 48.0 h). Per
day: day 1 1.40 h (17 stories), day 2 1.32 h (16), day 3 1.28 h (17). Per voice: `female` 2.09 h, `male` 1.91 h
per participant.

## What is provided
- **EEG** at 1000 Hz (native), one trial per story, cut from one continuous recording per day:
  - days 1-2: NeuroScan SynAmps2, 62 scalp channels + `HEO`, `VEO` (bipolar EOG);
  - day 3: Neuracle NeuSen Wireless, 59 scalp channels (upper-case labels renamed to 10-10 case, e.g. `FPZ` ->
    `Fpz`; original labels in the sidecar) + `ECG` and `HEOR`, `HEOL`, `VEOU`, `VEOL` (monopolar EOG).
  - Original reference (undocumented: unknown on days 1-2; CPz inferred on day 3). No digitisation: template
    standard_1005 positions. The authors' bad channels are marked bad.
- **Stimuli** (shared across participants): `story-01` ... `story-50`:
  - `audio`: the mp3 decoded gapless (ffmpeg), one channel (the two channels are identical), 48 kHz;
  - `textgrid`: `words` (Chinese words: the authors' word segmentation, timed by the forced-aligned syllables),
    `syllables` (Pinyin with tone) and `phones`, from the shipped Montreal Forced Aligner output;
  - `transcript`: the story text (UTF-8 Hanzi, no punctuation).
- **Conditions:** `female` (stories 1-25, TTS voice "Dapiaoliang") and `male` (26-50, "Huazai"). Session = day;
  trial = presentation order within the day. Story, day, EEG system and voice are in the sidecar.
- **Not used:** the 300 s eyes-open rest of each day; the first plays of six stories that were played twice (the
  last play is used, flagged `repeated_presentation` in the sidecar).

## Alignment
- One start and one end marker per story (`events.tsv`; the raw `.vmrk` codes are not story IDs). The markers'
  source and the presentation software are undocumented; their ~2 ms jitter shows they are not locked to the audio.
  There is no recorded copy of the sound.
- The player kept the mp3 encoder padding, so the trial starts **23.0 ms after the start marker** (1105 samples at
  48 kHz; inferred from the marker intervals, not measured; option `onset_shift_s`).
- **Clock drift:** the marker intervals exceed the audio by 76.8 ppm on the NeuroScan days (fitted across all
  subjects and stories), ~23 ms by the end of a story; corrected in the interpolation that cuts the trial. Day 3
  (Neuracle, 27 ppm, not significant) is not corrected. Option `drift_correction=None` turns it off.
- **Session offsets:** in sub-01 and sub-11 day 3 every story starts 12.66 s and 10.44 s before its marker in the
  EEG. The marker-to-story mapping is correct; the offset is the same in every trial. It was measured by
  envelope reconstruction with a decoder trained on other subjects (+-~10 ms), and these trials are labelled
  `quality: "corrected: ..."` in the sidecar. sub-25 day 3 has no usable EEG after ~400 s (all channels, including
  ECG and EOG, carry the same common signal; there is no tracking at any lag). Its trials are kept and labelled
  `quality: "suspect: ..."`.

**Open questions:**
- **Constant offset (not applied).** Responses are ~75 ms (days 1-2) and ~42 ms (day 3) later than in other
  datasets: probably an undocumented sound-output latency that differs between the two setups.
- **Drift may overshoot.** The 76.8 ppm correction on days 1-2 may be ~30-40 ppm too large (the DNN check finds the
  late part of each story ~6-9 ms earlier than the early part).

## Validation
**Low tier** (pilot: sub-01..sub-12, 600 trials, average reference over the 57 common channels; `validation.json`).
- Backward model (0.5-8 Hz): median r 0.238 / 0.218 / 0.237 (days 1 / 2 / 3), significant in 12/12 subjects
  (against circular-shift and other-story nulls); lag sweep peak +2 ms. Forward model: 0.059 / 0.061 / 0.056.
- MLR (30-60 Hz) passes only on day 2 (p 0.0099, 2/12 subjects) and is treated as **not established**: with the
  ~75 ms offset below, a genuine MLR would fall outside the test window. Brainstem (30-250 Hz) fails.
- TRF dominant peak at 207 / 213 / 178 ms (herrmann2025 reference: 152 ms; shape-matched shift +47 / +63 /
  +31 ms), i.e. ~25-30 ms later on days 1-2 than on day 3, in the same direction as the DNN offsets below.
- Match-mismatch DNN (trained on accou2023): responses 74 / 79 / 42 ms later than in accou2023 (days 1 / 2 / 3).
- Stimulus-EEG coherence (128 Hz, ratio to a circular-shift null): 0.2-1 Hz 13.6 / 9.8 / 11.4, 1-4 Hz 7.1 / 7.5 /
  5.7, 4-8 Hz 4.5 / 4.0 / 4.1, 8-15 Hz 1.8 / 2.0 / 1.9; ~1.0-1.2 above 30 Hz (native rate). The strongest
  low-frequency coherence of its validation batch.
- Before correction, sub-11 and sub-01 day 3 showed no tracking (the numbers above include them uncorrected): their
  stories start 10.44 s and 12.66 s before the markers. This is now corrected (see Alignment). sub-25 day 3 (not in
  the pilot) is a recording failure, and its trials are flagged.

## Caveats
- Timing rests on undocumented markers and an inferred 23 ms shift, with an uncorrected ~40-80 ms constant latency
  (see above). Only the low tier is established, so do not use these data for MLR or brainstem analyses without
  your own latency check.
- sub-25 day 3 is a recording failure (flagged, not dropped).
- Days 1-2 have an undocumented steep online low-pass above ~200 Hz; day 3 rolls off gently.
- EEG system, day and story set are confounded, and the voice is confounded with the stories (day 1 female only,
  day 3 male only).
- Sound delivery (headphones or loudspeaker, level) is undocumented.
- The authors' word times (`word_boundaries/legacy`) are ~300 ms late on stories 1-33; they are not used.

Details: `notes.md`.
