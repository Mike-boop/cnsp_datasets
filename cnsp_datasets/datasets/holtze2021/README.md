# holtze2021: two competing talkers, own name in the ignored stream

EEG while attending one of two audiobook narratives (male talkers, left and right at +-30 deg) for five blocks of
~10 min. In blocks 2-5 the participant's own first name replaces a word 10 times in the ignored narrative; the
ignored talker is either at equal level (`omni`) or attenuated by a beamformer (`beam`). German.

- **Source:** OpenNeuro ds003516 v1.1.3, doi:10.18112/openneuro.ds003516.v1.1.3. **Licence: CC0.**
  The audio is taken from the older snapshot **v1.1.1** (registry entry `holtze2021_audio`): the authors removed
  it in later versions (reason not stated). We download it for local use and **never redistribute it**.
- **Paper:** Holtze B, Jaeger M, Debener S, Adiloglu K, Mirkovic B (2021). Are they calling my name? Attention
  capture is reflected in the neural tracking of attended and ignored speech. *Front. Neurosci.* 15:643705.
  doi:10.3389/fnins.2021.643705
- **Code (authors):** https://github.com/BjoernHoltze/EEGCompetingSpeakerNameDistraction (doi:10.5281/zenodo.4541039)

## Size
**25 participants x 5 blocks = 125 trials of 600.5-622.6 s, 21.2 h in total, 0.85 h per participant** (identical
for everyone; 17.8 h for the 21 participants the authors included). The two talkers play simultaneously and are
counted once.
- `attend-<side>-omni-noname` (block 1, no names): 25 trials, 4.2 h, 0.17 h per participant.
- `attend-<side>-omni`: 50 trials, 8.5 h; `attend-<side>-beam`: 50 trials, 8.5 h; 0.34 h each per participant
  (0.339 or 0.343 h depending on the condition order).
- Attended side: 13 left, 12 right.

## What is provided
- **EEG:** BrainAmp at 500 Hz (stored unchanged), 47 scalp channels of an equidistant 64-channel layout (`E01`-`E60`
  subset, template positions from the EEGLAB chanlocs) and `E19`/`E20` (below the eyes) as `eog`. Original
  **nose reference** (the authors re-reference to the average). The concurrently recorded cEEGrid is not shared.
- **Stimuli** per block b, both talkers, `story1_block<b>` = left, `story2_block<b>` = right (`is_attended`
  from the participant's side):
  - `audio`: the matching channel of `Block_<b>_32k.wav` (32 kHz; v1.1.1, downloaded, never redistributed). These
    are the **dry narratives** (one talker per channel): no HRIR, no beamformer, and **no names** (the ignored
    story still contains the word the name replaced; the name audio is not shared);
  - `onset_envelope_authors`: the authors' envelope (500 Hz), the half-wave-rectified derivative of the low-passed
    Hilbert envelope of the same audio (`extract_envelope.m`). A plain Hilbert envelope of `audio` tracks better
    (backward attended r 0.153 vs 0.110; better in 20/25 subjects).
- **Annotations** `own_name`: the 10 name onsets per block (blocks 2-5), duration = the participant's name length.
  Onsets are relative to `raw.first_time`.
- Trial metadata (`raw.info["description"]`, JSON): block, attended side, condition order (OBOB/BOBO), `incl`
  (the authors' inclusion: sub-004, 007, 010 and 016 were excluded for hearing or movement), sex, age.
- Not included: the 60-s calibration and the beep period before block 1; the authors' ICA derivatives in
  `sourcedata/`.

## Alignment
- Trial onset = the block's `StartTrigger` (LSL marker stream, inferred software; the authors already corrected
  the constant 102 ms marker delay). `sw_trigger`. The EEG lasts as long as the stimulus.
- No end markers or stimtrack. Drift from EEG decoding: pooled -5.6 ppm (~3 ms per block, not resolvable per
  subject), **not corrected**; block-onset jitter ~7 ms SD.
- **Match-mismatch DNN offset** (classifier trained on accou2023; blocks 2-5, 100 trials): -7.9 ms [-10.4, -5.6]
  overall, omni -5.7 [-8.6, -3.0], beam -9.3 [-12.8, -6.7], i.e. responses up to ~10 ms later than in accou2023.
  Within ~10 ms of accou2023; not corrected.
- Attended side as in `participants.tsv`; confirmed by the backward decoder in 25/25 subjects (attended r >
  ignored r; smallest margins sub-006 and sub-014, attended better in 2 of 5 blocks each).

## Validation
**Low tier** (all 25 subjects and the 21 included). Average reference (47 scalp channels), `audio` feature
(Hilbert envelope for the low tier, half-wave rectified audio at 500 Hz for the high tiers).
- **Forward** (envelope -> EEG, repo validator): attended median r 0.033, 24/25 subjects above both nulls (circular
  shift, mismatched trial); ignored 0.018, 20/25. Comparable to fuglsang2018 on all tiers (low tier passed with
  mean r 0.033; middle-latency and brainstem not passed).
- **Backward** (decoder, leave-one-block-out): attended median r 0.153, ignored 0.073, **25/25 above both nulls**
  for each stream. Lag sweep peaks at 0 ms (attended +0.8 ms, ignored +0.6 ms; tolerance 15.6 ms).
- **Attention decoding** accuracy (median): 0.82 / 0.94 / 0.98 for 10 / 30 / 60 s windows, 25/25 subjects above
  chance in each.
- **TRF latency** (attended, central channels): P1 39 ms, N1 109 ms (GFP peaks 47 and 109 ms; 15.6 ms lag steps).
  The paper reports 50 / 156 ms GFP peaks with its onset envelope.
- The ignored stream in `beam` blocks peaks at +13 ms [9.8, 16.6] in the lag sweep vs -6 ms in `omni` (attended
  stream +2.5 vs -0.4 ms). The shift is specific to one stream within the same trials, so it reflects the
  beamformer's delay or a later response to the attenuated talker, not a marker error.
- **Middle-latency and brainstem tiers fail**: MLR SNR 1.03 (p 0.18; 3/25 subjects individually, about the
  false-positive rate), brainstem SNR 1.00 (p 0.32). The ignored stream of the 21 included subjects passes the
  MLR test marginally (p 0.050, 4/21), which is not taken as evidence. Reasons: ~7 ms software-marker jitter,
  500 Hz sampling (brainstem band capped at 225 Hz), and the dry audio (no HRIR or beamformer, names not inserted).
- **EEG-envelope coherence** (average reference, 5 s Hann windows, 4 s overlap, one global-shift surrogate, 500 Hz):
  above the surrogate up to ~10-12 Hz; attended > ignored at 0.2-1 Hz and 4-8 Hz. Ratio to surrogate, attended /
  ignored: 0.2-1 Hz 9.2 / 5.7, 1-4 Hz 3.3 / 3.6, 4-8 Hz 4.7 / 3.7, 8-15 Hz 2.2 / 1.6, 15-30 Hz 1.1 / 1.2, above
  30 Hz 1.0-1.1 (128 Hz analysis: same values within 0.05).
- The authors' 4 excluded subjects look normal (forward 4/4 significant, median r 0.037; backward and decoding in
  the same range as the others).
- The validator's per-trial jitter and drift estimates (SD ~66 ms; 12 +- 55 ppm) are dominated by noise and say
  nothing about timing.
- Suitable for low-frequency envelope tracking, attended/ignored comparisons and attention decoding. Not suitable for
  middle-latency or brainstem analyses, or latency comparisons with other datasets at the ~10 ms level.

## Caveats
- The audio was removed upstream after v1.1.1 (reason not stated). Do not redistribute it or the stimulus features
  derived from it.
- The stimuli are the dry narratives, not what was played: no HRIR spatialisation and, in `beam`, no attenuation of
  the ignored talker.
- During the ~0.4-0.6 s of each name the ignored-stream audio and envelope describe the original word, not what
  was played (the name).
- The authors excluded sub-004, 007, 010 and 016 (`incl` in the metadata); all 25 are standardised.
- sub-006 and sub-014 have the weakest attended-vs-ignored separation (decoding at 10 s: 0.75 and 0.65).

Details: `notes.md`.
