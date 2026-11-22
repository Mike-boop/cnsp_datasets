# wang2022: 60 Mandarin stories (SMN4Lang, MEG part)

MEG of 12 native Mandarin speakers (4 female, 23-30 years, right-handed, normal hearing; paper) listening to 60
news-commentary stories (Renmin Daily Review, one male broadcaster, 4-7 min each, 5.06 h in total) over six
visits. The same participants also did the stories in fMRI (not in scope).

- **Source:** OpenNeuro ds004078 v1.2.1, doi:10.18112/openneuro.ds004078.v1.2.1 ("A synchronized multimodal
  neuroimaging dataset to study brain language processing", SMN4Lang). **Licence CC0.** Registry entry `wang2022`
  (MEG, stimuli, annotations and code only; fMRI, anatomy, diffusion, embeddings and the authors' preprocessed
  data are not downloaded).
- **Paper:** Wang S, Zhang X, Zhang J, Zong C (2022). A synchronized multimodal neuroimaging dataset for studying
  brain language processing. *Sci Data* 9:590. doi:10.1038/s41597-022-01708-5
- **Code (authors):** `code/meg/` in the dataset (Psychtoolbox presentation, MNE preprocessing).

## Size
**12 participants, 717 trials (one per story) of 240.0-406.4 s, 60.48 h in total; 5.04 h per participant (range
4.83-5.06 h).** Every participant has all 60 stories (5.06 h) except sub-06 (57; runs 58-60 are not on OpenNeuro,
see Caveats). Pilot standardised: sub-01..05, 300 trials, 25.30 h.

## What is provided
- **MEG:** Elekta-Neuromag TRIUX (Peking University), 102 magnetometers (`mag`, T) and 204 planar gradiometers
  (`grad`, T/m), recorded and stored at **1000 Hz** (resampled only for the drift correction), online 0.1-330 Hz.
  **tSSS already applied by the authors** in the files OpenNeuro ships as raw (MaxFilter 2.2.15, in/out order
  8/3, 30 s buffer, correlation 0.98; SSS rank 67-72); the truly raw recordings are not shared. No bad channels
  marked (reconstructed by MaxFilter). No reference sensors.
- **Other channels:** BIO001 (`misc`, V): a bio channel, probably one EOG lead (unverified). Head-shape
  digitisation (111-170 points), fiducials, HPI coils and the device-to-head transform are kept. Dropped: STI*,
  IAS*, SYS201. No audio copy exists in the recordings. `line_freq` set to 50 Hz (the shipped meg.json says 60).
- **Stimuli** (shared by all participants): `story_1` ... `story_60`.
  - `audio`: the wav as shipped (16 kHz mono int16);
  - `textgrid`: tiers `words` and `characters` from the authors' Kaldi forced alignment (10 ms resolution), on
    the wav time base (the shipped times carry a +10.65 s fMRI offset, removed). Zero-length punctuation tokens
    are dropped; punctuation with a duration (labelling a pause) is kept; punctuation marks sharing one interval
    are joined. No phone tier (not shared).
- **Condition:** `story`; trial = run = story id (1-60); session = MEG visit (1-6, 10 stories each, the same
  fixed order for all participants). Each trial starts at the sound onset and is as long as the wav (the
  recordings continue >= 11.7 s after every wav end).
- Trial metadata (`raw.info["description"]`, JSON): story, visit and position, Beg/End trigger samples, onset,
  sound delay, drift applied, MaxFilter settings and SSS rank, `validation_tier`.

## Alignment
- **Software triggers** (`alignment_method` `sw_trigger`): the presentation script sends TTL 1 (Beg) on the
  parallel port right after `PsychPortAudio('Start')` and TTL 2 (End) when playback stops; read from STI101.
- **Onset = Beg + 39.5 ms**, the delay to the participant measured by the authors with a sound sensor (paper;
  their own code does not apply it). The MEG envelope response then peaks at a normal M100 latency (110-140 ms),
  but this cannot pin the delay to better than ~10-20 ms. Beg is consistent between participants to < 1 ms and
  across stories to ~5 ms (MEG response); `jitter_ms` 1.
- **Clock drift +500 ppm** (MEG clock fast): no audio copy, so the drift is the dataset value from the MEG
  envelope response (503 ppm, 95% CI 495-510, in the four strongly responding pilot subjects; the triggers give
  482 ppm, CI 420-535). Without correction the response slides by ~150 ms over a story. Corrected in the same
  interpolation that cuts the trial (`drift_correction=500e-6` default, `None` disables); residual uncertainty
  ~+-10 ppm (+-4 ms at the end of the longest story). Checked on the standardised trials (sub-01, sub-02, 60
  trials each): the envelope response peak stays at 103-108 ms and 116-117 ms across 100 s blocks of the stories.
- The End trigger has a story-specific +-20 ms scatter (playback side, identical across participants) and is not
  used.
- sub-08 run-16 and sub-09 run-7 have no Beg trigger (README): Beg = End - median End-Beg of the same story in the
  other participants (`beg_reconstructed` true; ~1 ms uncertainty).

## Validation
Not yet validated (`validation_tier` null).

## Decisions taken (coordinator, 2026-11-22; to revisit)
- **Files standardised as shipped** (authors' tSSS); no further Maxwell filtering, no use of the ICA/0.1-40 Hz
  derivatives.
- **Drift +500 ppm for every run**, onset Beg + 39.5 ms (see Alignment).
- **sub-06 runs 58-60 skipped** (copies of sub-05's runs, see Caveats).
- **BIO001 kept as `misc`**; participant names, birthday, weight and height removed from the FIF `subject_info`
  (only `sub-XX`, sex and hand kept).

## Caveats
- tSSS (30 s, 0.98) is already in the data and cannot be undone; the data rank is 67-72 (`sss_rank`).
- Continuous HPI (293, 307, 314, 321 Hz) was on during recording; whether tSSS removed the lines is not checked.
- Two participants (sub-04, sub-06 in the pilot download) show 3-4x weaker envelope tracking than the others in
  every visit; not a trigger problem.
- Upstream: sub-05 and sub-06 runs 58-60 are the same files (sub-05's recordings by `meas_date` and head
  position); sub-06's own runs 58-60 are missing. Annotation files of stories 1, 2, 10-29 sit in neighbouring
  folders (the adaptor finds them by name). meg.json says 60 Hz line frequency; the recordings show 50 Hz.

Details: `notes.md`.
