# chen2026: ChineseEEG-2, two Mandarin novels heard as audiobooks (EEG)

128-channel EGI EEG of 8 listeners in the Passive Listening part of ChineseEEG-2. They heard one reader's
recordings of *The Little Prince* (27 chapters) and *Garnett Dream* (9 or 8 sections), one wav per chapter.
- Listeners 01-04 heard reader f1, and listeners 05-08 heard reader m1.
- Trial = one chapter: 281 trials.
- The Reading Aloud part (speech production) is not standardised (user decision, 2026-11-22).

- **Source:** Science Data Bank, doi:10.57760/sciencedb.CHNNeuro.00001, V5 (registry entry `chen2026`, source
  `scidb`). Derivatives, embeddings and ReadingAloud are excluded.
  - The **audio is not on Science Data Bank**. It is in the Hugging Face repo `moriartyJM/ChineseEEG-2_audio`
    (registry entry `chen2026_audio`).
- **Licence:** the data are **CC0** (scidb V5). The audio repo states only `license: cc`, with no variant, so its
  terms are **unverified** (treated as part of the CC0 record). The article is CC BY-NC-ND, which covers the
  article only.
- **Paper:** Chen S, Li B, He C, Li D, Wu M, Shen X, Wang S, Wei X, Wang X, Wu H, Liu Q (2026). An EEG dataset for
  multimodal semantic alignment and neural decoding during reading and listening. *Sci Data* 13:148.
  doi:10.1038/s41597-025-06466-8
- **Code (authors):** https://github.com/ncclab-sustech/ChineseEEG-2 (read, not run). The latency pipeline used
  here is in `alignment/` (see its README).

## Size
**8 participants, 24.72 h in total; 3.09 h per participant on average (2.92-3.26 h).**
- **Per story:** Garnett Dream 12.47 h and Little Prince 12.25 h. A complete listener has Little Prince 1.54 h and
  Garnett Dream 1.49 h (f1 group) or 1.71 h (m1 group).
- The figures come from the wav durations in `timing.csv` (`notes.md` section 8). `data_size.py` was not run
  because the standardised data were deleted.
- The 0.45 h of chapters missing from the release are excluded (see Caveats).
- Chapters last 38 s-20.4 min. A full standardisation is about 48 GB.

## What is provided
- **EEG:** EGI HydroCel GSN 128, **1000 Hz native, stored at 1000 Hz**, in V.
  - **Channels:** 129 channels, E1-E128 plus **VREF (Cz) added back as zeros**. The authors had dropped it, and the
    original reference is Cz (inferred). The data are not re-referenced.
  - **Peripherals:** there are no EOG, ECG, stimulus or trigger channels.
  - **Positions:** template HydroCel-129 positions.
  - **Line noise:** strong 50 Hz and harmonics. Notch or low-pass before any broadband analysis.
- **Bad channels:** a channel is listed per participant in `info['bads']` (`bads.json`, written by `bads.py`) when
  its 1-40 Hz SD is more than 5x or less than 1/5 of the median in at least 20% of the chapters.
  `raw.pick("eeg")` keeps bads; exclude them yourself.
- **Stimuli:** the 12 kHz wav of each chapter (left channel; L = R), named `<story>_<reader>_chNN`. Both reader
  groups share the Little Prince text and pace, but they are different recordings.
  - There are no transcripts aligned to the speech. The `*.xlsx` line timings are display timings, not spoken
    timings.
- **Trials and conditions:** `condition` = story. `session` = BIDS session (1 garnettdream, 2 littleprince); the
  listening order cannot be recovered from the files. Trial = chapter. Prefaces (practice) are excluded.

## Alignment
- **Triggers are software.** PsychoPy/sounddevice sends them over zmq/TCP to egi-pynetstation, although the paper
  says "hardware-level" (established from the authors' code).
  - The listening script replays the reader's ROWS/ROWE line timeline relative to the moment playback was
    *requested*.
  - Per chapter, t0 = the intercept of a fit of these events to the reader's json timeline (residual SD 1.9-4.4 ms;
    all 281 chapters matched; `alignment/trigger_fit.py` reproduces t0 from `events.tsv`).
  - CH markers are unreliable (some missing, some renumbered) and are not used.
- **The sound starts ~0.5 s after t0**, and the delay varies by chapter. It is the playback-side output latency of
  `sd.play()`, which the triggers cannot see.
  - **Listener medians:** 504-581 ms.
  - **Late chapters:** most chapters lie within ±30 ms of their listener's median, but a few start 0.1-1.0 s later.
  - **Estimation:** the latency was estimated from the EEG with a leave-one-chapter-out backward decoder, plus the
    accou2023 DNN where the decoder was weak (`alignment/`, `alignment/timing.csv`).
- **Default onset: t0 + option-B latency** (`latency="option_b"`, user decision 2026-11-23). This is the listener
  median, except for chapters whose own estimate deviates by more than max(40 ms, 3 SE). 39 of the 281 chapters use
  their own value.
  - Each trial's t0, latency, onset and source are in `onsets_optionB.csv`.
  - Why option B was chosen is in `notes.md` section 6e (held-out-halves test, r 0.113 vs 0.110 per-chapter and
    0.107 listener median).
- **Drift:** about +16 ppm from the EEG (pooled), **not applied**. Every listener's 95% CI includes 0 (`drift.csv`).
  The provenance records `drift_ppm` 16 and `drift_corrected_ppm` 0. The trigger fit cannot measure drift, because
  the triggers and their timestamps share one PC clock.
- **Jitter:** about 3.3 ms SD per trigger event. The sidecar's `jitter_ms` is the latency SE, or the listener's
  robust spread (14-33 ms) for trials that use the median.
- **Alignment grade: poor.** Software playback-request triggers plus a brain-derived latency per listener or per
  chapter (option B, decoder/DNN, ~0.5 s). The drift of +16 ppm is brain-based and not applied. Low tier.

## Download and adaptor options
- **EEG:** `download_dataset("chen2026", <dir>)`. Science Data Bank is slow; use 1 worker and a long read timeout.
  This needs no credentials.
- **Audio:** `download_dataset("chen2026_audio", <dir>/ChineseEEG-2_audio)`, from Hugging Face. Whether it needs
  a token (`HF_TOKEN`, `secrets.json` key `hf`) was not recorded.
- `Chen2026Adaptor(download_dir, latency="option_b", drift_ppm=0.0, audio_dir=None)`.
  - `latency` selects the column of `timing.csv`:
    - `"option_b"` (default);
    - `"chapter"` (each chapter's own EEG estimate where z >= 2);
    - `"listener_median"` (t0 + listener median, the closest to trigger-only timing).

    There is no trigger-only (t0) option. Without the ~0.5 s latency the data are unusable (held-out r -0.008).
  - `drift_ppm=16` applies the brain-based drift.
  - With `format_dataset`, pass these as `--adaptor-opt key=value`. The latency choice is still being settled; see
    `notes.md`.

## Validation
**Low tier, piloted on 3 of 8 listeners only** (sub-01, 02, 05; 105 trials, 9.2 h), with average reference. The
pilot ran before option B became the default and compared two other timings:

| timing | low r (mean) | subjects sig. | TRF peaks | mlr | brainstem |
|---|---|---|---|---|---|
| per-chapter (`chapter`) | 0.0156 | 3/3 | ~120, 234 ms | SNR 1.07, p 0.02 (artefact) | SNR 1.01, p 0.30 |
| listener median | 0.0116 | 2/3 | ~140, 250 ms | SNR 1.04, p 0.34 | SNR 1.03, p 0.34 |

- The mlr "pass" is a ~10 ms ripple at all lags (stimulus-locked hum, inferred), not a response.
- **DNN offset** vs accou2023: +13.6 ms pooled (per-chapter timing), so the absolute onset matches the accou2023
  convention to about 10 ms. Single subjects are unreliable.
- **Circularity:** the latencies come from the same EEG, so validation scores after applying them are optimistic.
  The held-out-halves test over all 8 listeners is the non-circular check.
- **Not run:** validation with the option-B default, and the full run of all 8 listeners.

**Suitable for** low-frequency envelope tracking and language-model analyses at the corrected onsets.
**Not suitable for** MLR, brainstem or absolute-latency analyses: the timing is software only, and the ~0.5 s
latency was estimated from the brain.

## Caveats
- **Missing EEG:** sub-05 Little Prince 14 and 27, and sub-06 Garnett Dream 4, are not in the release. The paper
  says triggers are missing for 10 min of ch 27.
- sub-02 tracks weakly: 26 of 36 chapters fall back to the listener median. sub-01 Garnett Dream 6 shows no
  envelope tracking. Both are kept (user, 2026-11-24). Filter on `chapter_rule` in `onsets_optionB.csv` if you
  want only tracked chapters.
- **Upstream:** `eeg.json` says "Brain Products" (it is EGI), and `EEGReference` is n/a. The ~0.5 s output latency
  is undocumented. The README says the audio is in `ReadingAloud/` (it is not).
- The replayed ROWS markers slide against the speech by up to ~0.1 s per chapter (they are on the reader's EEG
  clock). Do not use them as line timings.

Details: `notes.md`.
