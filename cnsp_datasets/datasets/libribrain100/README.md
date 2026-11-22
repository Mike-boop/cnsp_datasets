# libribrain100: 100 hours of MEG, mostly from one listener

MEG of one participant (sub-0) listening to the whole Sherlock Holmes canon, TIMIT and MOCHA-TIMIT sentences and
30 podcast stories from The Moth (~84 h), plus 32 participants who heard two chapters of *A Study in Scarlet*
(~16 h, partly embargoed).

- **Source:** Hugging Face `pnpl/LibriBrain` (2025 release, Sherlock 1-7) and `pnpl/LibriBrain2` (the rest);
  together "LibriBrain100". Licence CC BY-NC 4.0. Registry entries `libribrain100` (MEG, events, audio) and
  `libribrain100_moth` (The Moth audio from OpenNeuro ds003020, LeBel et al. 2023; download into
  `<libribrain100 download>/ds003020`).
- **Papers:** Özdogan M, Landau G, Elvers G, Jayalath D, Somaiya P, Mantegna F, Woolrich M, Parker Jones O (2025).
  LibriBrain: over 50 hours of within-subject MEG to improve speech decoding methods at scale. *NeurIPS Datasets &
  Benchmarks*, arXiv:2506.02098. Mantegna F et al. (2026). LibriBrain100: one hundred hours of broad and deep MEG
  data for neural speech decoding at scale. arXiv:2608.25204.
- **Code (authors):** https://github.com/neural-processing-lab/pnpl

## Size
- sub-0: **83.8 h** of raw MEG; ~65 h of it with audio. Sherlock books 1-9 (3.9-11.9 h each), The Moth 6.1 h,
  MOCHA-TIMIT 1.4 h, TIMIT 8.3 h.
- sub-1-32: Sherlock 1, chapters 11-12, **0.49 h per participant as released** (15.8 h; sub-13-22 have the first
  half, sub-23-32 the first quarter of each chapter until the competition embargo ends).

## What is provided
- **MEG:**
  - sub-0: raw MEGIN Triux Neo recordings, 102 magnetometers + 204 planar gradiometers, 1000 Hz, no Maxwell filter;
    with EOG (horizontal, vertical), ECG and the articulator EMG channels. The scanner's fine-calibration and
    cross-talk files are in `LibriBrain/metadata/neo/` of the download.
  - sub-1-32: the authors' preprocessed data (no raw data released): movement-corrected, SSS, 50/100 Hz notch,
    0.1-125 Hz, **250 Hz**. Sensor positions from the scanner; no head transform (the authors realigned all data to
    an undisclosed common head position).
- **Stimuli:** one per session (`<task>_sub-<n>_ses-<n>`):
  - `audio`: **the audio as played**, rebuilt (see Alignment), at the source rate (22.05/44.1/48 kHz);
  - `textgrid`: word and phone tiers from the authors' annotations, on the trial's time axis.
- **Conditions:** `sherlock1` ... `sherlock9`, `themoth`, `mochatimit`, `timit`.
- **Without audio** (MEG + TextGrid only): TIMIT (LDC licence), Sherlock8 (not released yet), Sherlock3 sessions
  10-12 and Sherlock4 session 8 (no matching wav in the release).

## Alignment
- The audio was played sentence by sentence (PsychoPy), with a trigger at each segment and gaps of 1-16 ms, so a
  chapter wav is not what was heard. The adaptor rebuilds the played audio: every segment is cut from the source
  wav and placed at its trigger-based time in the MEG.
- Where the release's wav does not follow the authors' chapter timeline (Sherlock 3; parts of Sherlock 4 and 6:
  pauses differ), each segment is located in the wav individually (`segalign.py`).
- The Moth stories are not redistributed by LibriBrain; they are taken from OpenNeuro ds003020 (same stories; word
  timings agree within ~10 ms).
- Checked by fitting a TRF from the authors' word and phoneme onsets to the envelope of the rebuilt audio: the same
  kernel in every 2-min window, for every session type tested.

## Validation
**Low tier.** 32 multi-subject participants: low-frequency r 0.054 (31/32 significant). sub-0: r 0.021 raw, 0.030
with Maxwell filtering (applied in the validation only). No convincing 30-60 Hz or 30-250 Hz response; the raw
sub-0 data show the stimulus artefact at 0 ms, which confirms the timing to ~1 ms.

## Caveats
- **Embargo:** parts of Sherlock 1 (sub-13-32, and all raw data of sub-1-32) and the Sherlock 8 audio are held back
  until after the 2026 competition; `notes.md` says what to do when they appear.
- High-frequency timing is not verified (software segment triggers, ~+-3 ms).
- Raw sub-0 data need Maxwell filtering (tSSS) for most analyses.
- Sound reached the ears through tube earphones; the acoustic delay is not reported and not corrected.
- 17 of the 33 participants are fluent second-language English speakers.

Details: `notes.md`.
