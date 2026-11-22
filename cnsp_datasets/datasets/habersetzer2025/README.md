# habersetzer2025: two German audiobooks (MEG-SCANS)

MEG of 24 native German speakers (16 female, mean age 25, normal hearing; paper) listening to two Edgar Allan Poe
stories in German ("Das schwatzende Herz", "Die Maske des roten Todes"), each read by a different male narrator
and played continuously in two ~9 min runs.

- **Source:** OpenNeuro ds006468 v1.1.2, doi:10.18112/openneuro.ds006468.v1.1.2 ("MEG-SCANS: Stories, Chirps And
  Noisy Sentences"). **Licence CC0** (no restriction on redistributing derived data). Registry entry
  `habersetzer2025` (anatomy and the authors' derivatives are not downloaded).
- **Paper:** Habersetzer T, Steuer A, Radeloff A, Meyer BT (2025). MEG-SCANS. *Sci Data* 12:1938.
  doi:10.1038/s41597-025-06397-4 (cite as asked in the dataset's `HowToAcknowledge`).
- **Code (authors):** https://github.com/tillhabersetzer/MEG-SCANS (doi:10.5281/zenodo.17397581)

## Size
**24 participants, 94 trials (one per run) of 494-562 s, 13.82 h in total; per participant mean 0.576 h (range
0.301-0.588 h).** sub-02 to sub-24 have 4 runs (0.588 h); sub-01 (pilot) has 2 runs (0.301 h).
- `audiobook1`: 48 trials, 7.24 h (24 participants; 0.302 h each, sub-01 0.301 h);
- `audiobook2`: 46 trials, 6.58 h (23 participants, not sub-01; 0.286 h each).

## What is provided
- **MEG:** MEGIN TRIUX, 102 magnetometers (`mag`, T) and 204 planar gradiometers (`grad`, T/m), recorded and
  stored at **1000 Hz** (resampled only for the drift correction, see Alignment), online 0.1-330 Hz. **Raw, as
  shipped: no SSS/MaxFilter**, no reference sensors (MEGIN relies on SSS). MEG2143 and MEG1112 are marked bad (the
  authors mark them in every participant). The scanner's fine-calibration and cross-talk files are in the download
  (`sub-XX/meg/sub-XX_acq-{calibration,crosstalk}_meg.*`), so tSSS can be applied (see Validation).
- **Other channels:** EOG001/EOG002 (vertical/horizontal, bipolar), ECG003, and MISC001/MISC002 (`misc`: recorded
  copy of the sound, left/right, identical: diotic). Head-shape digitisation, fiducials, HPI coils and the
  device-to-head transform are kept. Dropped: MISC007 (experimenter's microphone), STI*, IAS*, SYS201.
- **Stimuli** (44.1 kHz, shared across participants): `audiobook<n>_run-0<r>`; sub-01 heard preliminary versions,
  `pilot_audiobook1_run-0<r>` (0.8-2.0 s shorter).
  - `audio`: the wav as shipped;
  - `textgrid`: the shipped word and phone tiers (Montreal Forced Aligner), relative to the wav start.
- **Conditions:** `audiobook1`, `audiobook2`; trial = run in presentation order (1-2: audiobook1 runs 1-2, 3-4:
  audiobook2 runs 1-2). Each trial starts at the audio onset and is as long as the wav.
- Trial metadata (`raw.info["description"]`, JSON): story, run, wav, first trigger sample, audio-copy onset,
  acoustic delay, drift measured and applied, bads, cHPI frequencies, `validation_tier` and `validation_note`.

## Alignment
- Triggers are **hardware** (documented in the paper): an extra sound-card channel drives a TTL input of the MEG
  via an FPGA box clocked by the sound card, one trigger per second of audio. Audio and triggers share one clock
  (residual -0.01 +- 0.03 ppm between them).
- Per run, the onset is measured on the audio copy (MISC001 vs the wav, 10 s windows; `alignment_method`
  `stimtrack_xcorr`): 2.61 +- 0.32 ms (1.75-3.13 ms) after the first trigger, window-lag SD ~0.004 ms
  (`jitter_ms` 0.01). A further **0.4 ms acoustic delay** is assumed (the authors shift by 3 ms after the trigger,
  from undescribed measurements), < 1 sample; not verified.
- **Clock drift: +485 ppm** (the MEG counts 1000.485 samples per audio second; 484.99-485.15 ppm in all 94 runs,
  confirmed by the triggers): without correction the end of a run is ~270 ms late. Corrected per run in the same
  interpolation that cuts the trial (`drift.py` -> `drift.csv`; `drift_correction="run"` default, `"dataset"`
  uses the median +485.07 ppm, `None` turns it off).
- Checked on the standardised data: MISC001 matches the wav at lag -0.4 ms (the assumed acoustic delay) at the
  start and the end of the runs, constant to < 0.03 ms over 9 min (4 trials checked, notes.md section 10).

## Validation
**Brainstem tier with tSSS** (`validation_tier: brainstem` in every trial); the raw data as stored reach **mlr**.
Magnetometers (102), no re-referencing, all 24 participants. For MEG the "brainstem" tier tests the 30-250 Hz
cortical response at 28-45 ms; it shows high-frequency timing accuracy, not a brainstem response.

tSSS was applied in the validation only (the standardised data stay raw): bads MEG2143, MEG1112 +
`mne.preprocessing.find_bad_channels_maxwell` on the first 120 s of each trial (e.g. MEG1023 in several
participants), `maxwell_filter` with the participant's shipped fine-calibration and cross-talk files, tSSS
`st_duration` 10 s, origin fitted to the head shape, head frame, no movement compensation.

| | tSSS | raw |
|---|---|---|
| Forward, low (0.5-8 Hz), median r | 0.060 (24/24) | 0.030 (23/24) |
| Backward (decoder, 0-250 ms), median r | 0.346 (24/24) | 0.260 (24/24) |
| mlr (30-60 Hz, 18-45 ms), SNR median / mean | 1.35 / 1.40 (18/24, p 0.01) | 1.21 / 1.26 (7/24, p 0.01) |
| brainstem (30-250 Hz, 28-45 ms), SNR median / mean | 1.24 / 1.25 (14/24, p 0.01) | 0.99 / 1.01 (1/24, p 0.0495) |

- **Raw brainstem is not counted:** the formal p 0.0495 rests on 1/24 participants, and the raw 30-250 Hz TRF
  peaks at 0 ms (stimulus artefact: the sound picked up by the sensors) with nothing in the 28-45 ms window above
  the noise. Raw per condition: mlr in both (audiobook1 SNR 1.08, p 0.03, 1/24; audiobook2 1.20, p 0.01, 7/23).
- **tSSS per condition** (mean SNR): audiobook1 mlr 1.20 (8/24), brainstem 1.21 (12/24); audiobook2 mlr 1.21
  (9/23), brainstem 1.10 (8/23); all p 0.01. The brainstem tier is reached weakly: the largest 30-250 Hz peaks
  are at ~20-25 ms, just before the window, plus a smaller artefact spike at 0 ms.
- **Latencies (tSSS):** 30-60 Hz TRF peaks at ~27 and 38 ms. Low-frequency TRF (1-15 Hz, GFP): M50 ~46-53 ms
  (subject medians; grand-average peak 46 ms in audiobook2, none in audiobook1), M100 94 / 109 ms (grand average,
  audiobook1 / audiobook2; subject medians 108 / 112 ms).
- **Backward lag sweep** (64 Hz, +-1 s): peak at **+0.7 ms (95% CI -0.0 to +1.3)**, every participant within one
  sample (15.6 ms; subject peaks -1.9 to +4.5 ms). Without drift correction the stimulus would slide by up to
  272 ms over a run, so this confirms the per-run drift correction and the MISC-based onsets end to end. The
  validator's residual drift estimate is -8 +- 14 ppm (consistent with 0).
- **Comparison with other MEG datasets** (same code, magnetometers; mean SNR, participants significant):

  | dataset | n | low median r | mlr SNR | brainstem SNR | tier |
  |---|---|---|---|---|---|
  | habersetzer2025, tSSS | 24 | 0.060 (24/24) | 1.40 (18/24) | 1.25 (14/24) | brainstem |
  | habersetzer2025, raw | 24 | 0.030 (23/24) | 1.26 (7/24) | 1.01 (1/24) | mlr |
  | gwilliams2023 | 20 | 0.046 (20/20) | 2.09 (20/20) | 1.55 (19/20) | brainstem |
  | armeni2022 | 3 | 0.061 (3/3) | 2.57 (3/3) | 3.03 (3/3) | brainstem |
  | schueller2024 | 19 | 0.020 (19/19) | 1.05 (4/19) | 1.68 (18/19) | brainstem |
  | libribrain100 sub-0, tSSS (all MEG) | 1 | 0.030 | 0.95 (n.s.) | 1.10 | low |

- **Coherence** (MEG vs the envelope, 102 magnetometers, raw data, no re-reference; 5 s Hann windows, 4 s
  overlap; ratio to one global-shift surrogate; bands up to 60 Hz at 128 Hz, above at the native 1000 Hz):

  | condition | 0.2-1 Hz | 1-4 Hz | 4-8 Hz | 8-15 Hz | 15-30 Hz | 30-60 Hz | 60-120 Hz | 120-250 Hz | 250-500 Hz |
  |---|---|---|---|---|---|---|---|---|---|
  | audiobook1 | 3.84 | 2.86 | 1.74 | 1.17 | 1.06 | 1.09 | 1.71 | 1.75 | 1.20 |
  | audiobook2 | 4.13 | 2.56 | 1.70 | 1.15 | 1.12 | 1.15 | 1.42 | 1.69 | 1.22 |

  The native-rate run agrees within 0.03 below 30 Hz (30-60 Hz: 1.18 / 1.15). The ratios of 1.4-1.75 at
  60-250 Hz are on raw data, whose 30-250 Hz TRF shows only the 0 ms stimulus artefact; they most likely reflect
  that artefact rather than a neural response (not verified).
- **DNN offset:** not applicable (the match-mismatch classifier is trained on EEG).
- **Suitable for** low-frequency envelope tracking and decoding, word- and phone-level analyses (forced-aligned
  TextGrids), and, **after tSSS as validated above**, middle-latency and 30-250 Hz cortical responses (timing to
  ~1 ms: hardware triggers plus a measured audio copy). Apply tSSS (or use the authors' tSSS derivatives) for any
  high-frequency analysis; the raw data reach mlr only. Exclude lags around 0 ms in high-frequency analyses
  (stimulus artefact). Subcortical (ABR/FFR-type) responses were not tested.

## Decisions taken (coordinator, 2026-11-22; to revisit)
- **Raw data standardised** (least processed); the authors' tSSS + movement-compensated files are not used (see
  Caveats). Maxwell filtering is up to the user.
- **Drift corrected per run** from `drift.csv` (default `drift_correction="run"`).
- **Onset = first audiobook trigger + the run's MISC001 onset + 0.4 ms assumed acoustic delay.**
- **Skipped:** the OLSA sentences-in-noise block (sentence and noise audio not shared; only 64 Hz envelopes), the
  chirp blocks before each audiobook run (transient stimuli) and the empty-room recordings.
- **sub-01 (pilot)** is included with the pilot wavs as stimuli `pilot_audiobook1_run-0N`; its 32 pilot EEG
  channels are dropped (reference undocumented).
- **Channels kept:** MEG, EOG, ECG, MISC001/002 (audio copy); cHPI lines left in.

## Caveats
- **No SSS:** most analyses need Maxwell filtering first (see Validation for settings). The authors' tSSS +
  movement-compensated files (head position of audiobook1 run-01) are on OpenNeuro
  (`derivatives/sub-XX/maxfilter/*_proc-tsss-mc_meg.fif`, same time base as the raw files, verified on one file;
  ~85 GB for the audiobook runs).
- Only MEG2143 and MEG1112 are marked bad; `find_bad_channels_maxwell` flags further channels in some runs (e.g.
  MEG1023), which are not marked in the stored data.
- Continuous HPI lines at 261, 278, 295, 311 and 328 Hz are in the data (not removed).
- Sound came through insert earphones (Tip-300); the acoustic delay is not reported (0.4 ms assumed, see above).
- sub-01 is the pilot: preliminary audiobook1 recordings, no audiobook2.
- The STI101 trigger channel has glitches in 8 runs (e.g. sub-03 audiobook1 run-01); events.tsv is clean and is
  what the adaptor uses.
- Upstream: CHANGES 1.1.0 says sub-02 audiobook2 run-01 was removed, but it is present and correct; the missing
  runs are sub-01's audiobook2 (probably a typo for sub-01).

Details: `notes.md`.
