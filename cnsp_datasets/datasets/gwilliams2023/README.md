# gwilliams2023 (MEG-MASC): four synthesised stories, 27 listeners

MEG of 27 native English speakers listening to four fictional stories (synthesised speech, with inserted word
lists), in one or two ~1 h sessions.

- **Source:** OSF ag3kj (parts hqvm3, u5327, dr4wy), BIDS. Licence CC BY 4.0.
- **Paper:** Gwilliams L, Flick G, Marantz A, Pylkkänen L, Poeppel D, King JR (2023). Introducing MEG-MASC a
  high-quality magneto-encephalography dataset for evaluating natural speech processing. *Sci Data* 10:862.
  doi:10.1038/s41597-023-02752-5
- **Code (authors):** https://github.com/kingjr/meg-masc

## Size
27 participants (22 with two sessions), **51.4 h in total, 1.90 h per participant** on average. 1470 trials of
~3 min (one per sound file).

## What is provided
- **MEG:** KIT/Yokogawa, 208 axial gradiometers (MNE type `mag`, T) and 16 reference magnetometers (`ref_meg`),
  1000 Hz, 0.03-200 Hz online. Plus `MISC 009`, the recorded copy of the sound (`misc`).
- **Stimuli** (one per sound file, shared across participants, 22.05 kHz):
  - `audio`: the wav as shipped;
  - `textgrid`: word and phoneme tiers (the authors' forced alignment), relative to the start of the wav.
- **Conditions:** the story (`lw1`, `cable-spool-fort`, `easy-money`, `the-black-willow`). Trials are numbered in
  presentation order within a session.

## Alignment
- **The shipped events are ~44 ms early.** The `sound` events are the trigger; the sound itself, measured on the
  MEG's audio channel, starts 37-51 ms later (median 44 ms), varying from sound to sound (playback buffer jitter,
  SD 2.8 ms). The adaptor measures every sound's onset on `MISC 009` and starts the trial there (default;
  `onset="trigger"` uses the events as shipped). The absolute onset is known to ~3 ms.
- **Clock drift** of -46 ppm (every participant) is corrected by resampling onto the audio clock (default;
  `drift_correction=False` turns it off).
- Word and phoneme times inside a sound are relative to the wav, so they need no correction.

## Validation
**Brainstem tier** (20-participant pilot). Low-frequency r 0.050 (20/20 participants significant), middle-latency
SNR 2.09 (20/20), 30-250 Hz SNR 1.55 (19/20) with a sharp response at 35 ms.

## Caveats
- For MEG the "brainstem" tier tests the 30-250 Hz cortical response at 28-45 ms; it shows high-frequency timing
  accuracy, not a brainstem response.
- Word lists and a few pseudo-words are inserted in the stories (`stimuli/text_with_wordlists`); the TextGrids
  include them.
- Event files spell sound names inconsistently (`lw1_0.0.wav`, `The_Black_Willow_0.wav`); the adaptor normalises
  them.
- The repo's OSF downloader read only the first 10 files per folder before 2026-11-21; re-download if your copy
  has fewer than 1304 files.

Details: `notes.md`.
