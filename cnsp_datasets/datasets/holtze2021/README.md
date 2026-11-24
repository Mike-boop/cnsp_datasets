# holtze2021: two competing talkers, own name in the ignored stream (scalp + cEEGrid)

EEG while attending one of two audiobook narratives (two male talkers, left and right) for five blocks of ~10 min,
German. Two studies of the Oldenburg lab with the same stories, combined:
- **Holtze et al. (2021)**, 25 participants: earphones, talkers HRIR-spatialised at +-30 deg. In blocks 2-5 the
  participant's own first name replaces a word 10 times in the ignored narrative; the ignored talker is either at
  equal level (`omni`) or attenuated by a beamformer (`beam`). **Scalp EEG** (47 channels) for all 25, and the
  concurrent **cEEGrid** (around-ear, 18 channels) for the 21 the authors included.
- **Jaeger et al. (2020)**, 15 participants: free-field loudspeakers at +-45 deg, both talkers at equal level, no
  names. **cEEGrid only** (their scalp cap was never shared). These are the recordings behind the results-only
  jaeger2025 entry.

Each montage is stored in its own file per trial (`ns_type` `eeg` = scalp, `around-ear-eeg` = cEEGrid), both on
the same stimulus timeline.

- **Sources:**
  - Scalp: OpenNeuro ds003516 v1.1.3, doi:10.18112/openneuro.ds003516.v1.1.3. **Licence: CC0.**
  - cEEGrid: OpenNeuro ds004015 v1.0.2, doi:10.18112/openneuro.ds004015.v1.0.2. **Licence: CC0.** Download it into
    `<download>/ds004015` (registry `holtze2021_ceegrid`) or pass `--adaptor-opt ceegrid_dir=<path>`; without it the
    adaptor writes the scalp files only.
  - Audio: the older snapshot **v1.1.1** of ds003516 (registry `holtze2021_audio`): the authors removed it in later
    versions (reason not stated; ds004015 v1.0.0/1.0.1 shipped the identical audio and removed it too). We download
    it for local use and **never redistribute it**.
- **Papers:**
  - Holtze B, Jaeger M, Debener S, Adiloglu K, Mirkovic B (2021). Are they calling my name? Attention capture is
    reflected in the neural tracking of attended and ignored speech. *Front. Neurosci.* 15:643705.
    doi:10.3389/fnins.2021.643705
  - Holtze B, Rosenkranz M, Jaeger M, Debener S, Mirkovic B (2022). Ear-EEG measures of auditory attention to
    continuous speech. *Front. Neurosci.* 16:869426. doi:10.3389/fnins.2022.869426
  - Jaeger M, Mirkovic B, Bleichner MG, Debener S (2020). Decoding the attended speaker from EEG using adaptive
    evaluation intervals captures fluctuations in attentional listening. *Front. Neurosci.* 14:603.
    doi:10.3389/fnins.2020.00603
- **Code (authors):** https://github.com/BjoernHoltze/EEGCompetingSpeakerNameDistraction (doi:10.5281/zenodo.4541039),
  https://github.com/BjoernHoltze/EarEEGAuditoryAttentionMeasures (doi:10.5281/zenodo.6379903)

## Size
Stimulus time; simultaneous talkers and the two concurrent montages are counted once.
- **Scalp:** 25 participants x 5 blocks = 125 trials of 600.5-622.6 s, **21.2 h**, 0.85 h per participant
  (17.8 h for the 21 the authors included).
- **cEEGrid:** 175 trials, **29.7 h**: Holtze 21 participants x 5 blocks, 17.8 h (concurrent with their scalp files);
  Jaeger 15 participants, 70 blocks, **11.9 h** (0.79 h per participant, 0.51-0.85 h: three sessions are
  incomplete, see Caveats).
- Distinct recording time 33.1 h, 40 participants.
- Conditions: `attend-<side>-omni-noname` (Holtze block 1), `-omni` and `-beam` (Holtze blocks 2-5, 0.34 h each
  per participant), `-freefield` (Jaeger blocks 1-5).

## Participants
Holtze participants keep their ds003516 ids; Jaeger participants are 100 + their original number. Every file's
metadata has the original id (`bjh_sNN` / `maj_sNN`) and the ids in both OpenNeuro datasets.

| subject | original id | ds003516 | ds004015 | files |
|---|---|---|---|---|
| 1, 2, 3, 5, 6, 8, 9, 11-15, 17-25 | bjh_sNN | sub-0NN | sub-016 .. sub-036 (same order) | scalp + cEEGrid |
| 4, 7, 10, 16 | bjh_sNN | sub-0NN | - | scalp only (excluded by the authors) |
| 107, 108, 109, 110, 112, 114, 115, 118, 120, 122, 123, 124, 125, 126, 127 | maj_sNN | - | sub-001 .. sub-015 | cEEGrid only |

## What is provided
- **Scalp EEG** (`eeg`, unchanged from the first release of this entry): BrainAmp at 500 Hz, 47 scalp channels of
  an equidistant 64-channel layout (`E01`-`E60` subset, template positions) and `E19`/`E20` (below the eyes) as
  `eog`. Original **nose reference**.
- **cEEGrid** (`around-ear-eeg`): two C-shaped grids around the ears, 18 channels `L01`-`L08`, `L04a`, `L04b`,
  `R01`-`R08` (template positions), SMARTING (mBrainTrain) Bluetooth amplifier at 500 Hz (stored unchanged).
  Original **reference R04b** (ground R04a). The amplifier is DC-coupled: channels carry offsets of several mV, so
  high-pass before use. Flat or very noisy channels are listed per trial in `info["bads"]` (9 participants).
- **Stimuli** per block b, both talkers, `story1_block<b>` = left, `story2_block<b>` = right (`is_attended` from
  the participant's side), shared by both montages and both studies:
  - `audio`: the matching channel of `Block_<b>_32k.wav` (32 kHz). These are the **dry narratives** (one talker per
    channel): no HRIR, no beamformer, no room or loudspeaker, and **no names** (the ignored story still contains
    the word the name replaced; the name audio is not shared);
  - `onset_envelope_authors`: the authors' envelope (500 Hz), the half-wave-rectified derivative of the low-passed
    Hilbert envelope of the same audio. A plain Hilbert envelope of `audio` tracks better.
- **Annotations** `own_name` (Holtze blocks 2-5, both montages): the 10 name onsets per block, duration = the
  participant's name length.
- Trial metadata (`raw.info["description"]`, JSON): block, attended side, condition order (Holtze), `incl` (the
  authors' inclusion, Holtze), sex, age, the trigger time and the onset shift applied, the ids, the presentation
  setup and, for the cEEGrid, the three blocks the 2022 paper analysed.
- Not included: calibration and beep periods, Jaeger block 6 (no stimulus shared), the authors' ICA derivatives.

## Alignment
- **Scalp:** trial onset = the block's `StartTrigger` (LSL marker stream, software; the authors already corrected
  the constant 102 ms marker delay). Block-onset jitter ~7 ms SD (from the EEG). Drift not corrected (pooled
  -5.6 ppm from the EEG, ~3 ms per block). DNN offset vs accou2023 -7.9 ms (not corrected).
- **cEEGrid, Holtze half:** the cEEGrid ran on its own amplifier and clock. Its trial onset is carried over from the
  scalp: cross-correlating the two concurrent recordings (shared blinks, muscle and movement artefacts) gives each
  block's lag, median **-37 ms** relative to ds004015's `StartTrigger` (range -30 to -69 ms), measured to ~1 ms.
  ds004015's markers contain the authors' shift that matched the cEEGrid's beep N1 to the cap's; the around-ear N1
  peaks later, so that shift was ~37 ms too large. Relative drift cEEGrid vs scalp +4 ppm (<= 1.3 ms within a
  block), not corrected.
- **cEEGrid, Jaeger half:** no scalp data, so onset = `StartTrigger` - 35.0 ms: the Holtze half's median lag plus
  2 ms for the two studies' different stated delays (same amplifiers and recorder). Expected error ~ +-6 ms per
  session (the Holtze lags vary by 5.5 ms SD between sessions; one Holtze session stepped by 20 ms between XDF
  files). `--adaptor-opt ceegrid_onset=shipped` keeps ds004015's markers instead (both halves).
- The cEEGrid onsets above are the default (approved 2026-11-24); hardware-style alignment of the two recordings,
  not fitted to the stimulus response.
- Attended side as in the participants files; confirmed by backward decoders for every participant (scalp 25/25;
  cEEGrid 35/36, the exception, subject 13, is confirmed by its scalp file).
- **Alignment grade: medium** (both montages). Scalp: software markers with the authors' 102 ms delay, validated
  (low tier, DNN -7.9 ms, no correction); cEEGrid: carried onto the scalp timeline by cross-correlating the
  concurrent recordings (-37 ms, IQR 4 ms), Jaeger half by the same lag plus the papers' stated constants.

## Validation
Low tier (forward model, 0.5-8 Hz envelope; significant against circular-shift and mismatched-stimulus nulls),
backward decoders (leave one block out) and auditory attention decoding (AAD):

| | scalp (25) | cEEGrid, Holtze (21) | cEEGrid, Jaeger (15) |
|---|---|---|---|
| low tier, attended | passed (first release) | passed, 21/21 participants, median r 0.025 | passed, 14/15, median r 0.029 |
| low tier, ignored | - | passed, 7/21, r 0.006 | passed, 8/15, r 0.009 |
| backward r attended / ignored (median) | 0.153 / 0.072 | 0.047 / 0.024 | 0.051 / 0.022 |
| attended > ignored | 25/25 | 20/21 | 15/15 |
| AAD accuracy, 30 s windows (median) | 0.94 | 0.73 | 0.68 |

The 30-60 Hz and 30-250 Hz tiers do not pass for the scalp (software markers, 500 Hz, dry audio) and were not run
for the cEEGrid. Decoder lag sweeps peak within 2 ms of zero in every group, which only shows that the blocks agree
with each other; the absolute cEEGrid onset rests on the scalp comparison (Alignment).

## Caveats
- The audio was removed upstream (reason not stated). Do not redistribute it or the stimulus features derived from
  it.
- The stimuli are the dry narratives, not what was played: no HRIR spatialisation, no beamformer attenuation (Holtze
  `beam`), no loudspeaker or room (Jaeger).
- During the ~0.4-0.6 s of each name the ignored-stream audio and envelope describe the original word, not what was
  played.
- The authors excluded sub-004, 007, 010 and 016 (`incl` in the metadata); all 25 are standardised (scalp only).
- Incomplete Jaeger sessions (the later blocks' EEG was not saved): 108 (maj_s08) blocks 1-4, 112 and 114
  (maj_s12, maj_s14) blocks 1-3.
- The ds004015 sidecars name a BrainAmp for the cEEGrid; it was a SMARTING (paper; XDF stream header).
- The cEEGrid's Jaeger-half onsets rest on a constant transferred from the Holtze half (see Alignment).

Details: `notes.md`.
