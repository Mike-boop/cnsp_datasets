# Lessons: a checklist for every dataset

Each item caught a real error in at least one dataset; the dataset is named in brackets. Run through the list
before closing a dataset. Add new lessons here, not in the handover.

## Timing and drift
- **Look for an audio copy in every recording**: stimtrack, aux, `Sound`, or MEG MISC/UADC/EXT channels. Measure
  onsets and drift on it.
  - Convenience releases may have dropped it: look for the original record (weissbart2019, etard2019: Zenodo
    7086168, 7086209).
  - Shipped onsets can be wrong: gwilliams2023 events were 44 ms early, with jitter.
- **Drift fit.** Use a Theil-Sen or linear fit through positive-peak lags in ~10 s windows
  (`yang2026_base/drift.py:window_fit`).
  - Two endpoint windows are fragile: periodic side peaks give ms-sized jumps.
  - `jehn2025_base/drift.py:trial_drift` takes the |xcorr| peak and can lock onto an inverted side lobe (yang2026:
    41/222 presentations ~2.4 samples off). Don't reuse it.
- **Authors rarely correct drift.** Examples: jehn2025 26.7 ppm, bentum2023 33.6 ppm, habersetzer2025 +485 ppm,
  yang2026 TRIUX +538 ppm. Plot drift per subject: clusters differ (jehn2025 ~18 ppm for a run of subjects).
- **Markers can be late, missing or off by a whole amount** (guilleminot2021: one marker 2.39 s late;
  pkueeg2025 day 3: +10-13 s, found with a decoder scan over ±60 s). Check every session's events against its
  audio, not just one (armeni2022: a crash session with a missing onset).
- **Software markers lead the sound** by 40-500 ms, and the lead can vary per playback call:
  - pkueeg2025, wang2025 ~0.2 s;
  - chen2026 ~0.5 s, varying per chapter.

  A fit of the markers to the presentation timeline gives only the request time, and its slope says nothing about
  sound-card drift when both run on the same clock (chen2026).
- **Recordings and files.**
  - BrainVision `New Segment` annotations mark recording pauses, and MNE joins segments without a gap.
  - Check for trials that run past the end of the recording.
  - File durations rounded to ms add up over concatenated stimuli (bentum2023).
- **Frame rates.** Never use an integer hop `fs // FS` for envelopes: 220 for 22.05 kHz is a 0.227% stretch.
- **`np.allclose` has a relative tolerance.** At sample positions ~1e5 it treats ppm drifts as zero (`clock.py`
  once silently skipped drift correction).

## Mapping, labels and files
- **Verify trial → stimulus with an independent signal**: duration vs wav (exact to the ms in varano2022),
  recording order (`first_samp`, `meas_date`), stimtrack correlation, logs.
- **Verify condition labels against the authors' code and the stimuli**, not the readme:
  - varano2022 cartoon/edge swapped;
  - etard2019 SNR labels;
  - jehn2025 three subjects with swapped sides (stimtrack).
- **Readmes and helper files can be wrong**: varano2022 `trial_index`, the jehn2025 code table, etard2019
  `align_data.py` copying onsets between conditions. Upstream errors also include:
  - ds008065 events off by one and a 100× EEG gain;
  - ds006434 truncated files.
- **Check every file, not one**: channel lists, lengths, annotations, zip integrity (truncated uploads in
  momenian2024 and wang2025).
- **Check for literally identical data** across datasets with content-hash fingerprints
  (`tmp/review/newbatch/dupcheck/`).
- **Check whether shipped data are raw or preprocessed**: karunathilake2023_aging shipped DSS components only.

## Stimuli
- **Include everything that was played**, as separate stimuli: noise/babble, distractors, tactile signals
  (guilleminot2021 mismatched trials rolled the tactile buffer by a quarter), embedded sentences.
- **Sentence-wise playback with gaps**: rebuild the stimulus per participant from the sentence wavs at their
  triggers (momenian2024).
- **Validate a stimulus rebuild at the scale that matters.** A coarse word-mask match passed a rebuild that drifted
  1.4 s per 10 min. The annotation-onset TRF (`scripts/annot_trf.py`) exposed it.
- **A stimulus `data_fn` must depend only on (modality, name, feature).** The sink writes one file per name and the
  first trial written wins, so anything trial-specific needs its own name (varano2022 audio cut).
- **Test polarity both ways** when trials alternate polarity.

## Channels and units
- **Dead or broken channels can mimic misalignment** under an average reference (momenian2024 HK050 T8). Mark
  them in `info['bads']`.
- **Bads are kept by MNE picks.** `raw.pick("eeg")` / `pick("mag")` keep channels in `info['bads']`
  (`exclude=()`). A dead bad channel then gives NaN coherence or poisons the average reference.
  - `validate.load.load_neural` excludes bads since 75b48d4.
  - `--picks mag` in the validator CLI still keeps them.
- **Raw MEGIN data without SSS fail the high-frequency tiers.** Use tSSS in the validation only.

## Validation and interpretation
- **Validate with an average reference** (32+ EEG channels; mastoids for fewer). Without re-referencing the numbers change a lot (weissbart2019 30-250 Hz
  SNR 2.46 vs 1.54). Record the reference with every result.
- **Look at the TRF plots, not only the p-values.**
  - A stimulus-locked ripple at all lags can pass the MLR test (guilleminot2021).
  - A spike at -21 ms meant a wrong onset delay (wang2022).
- **`validate.load.stimulus_feature(..., 'hf')`** returns None for envelope-only stimuli, so `--tiers low,mlr`
  silently skips mlr. `--tiers` is comma-separated.
- **The validator holds a subject in memory.** Keep a validation subject to ~2-3 h of 300-channel 1 kHz data.
- **DNN offsets vs accou2023 are not absolute.** pkueeg2025 (Mandarin) gave -42 to -79 ms after a known correction,
  cause unknown. Cross-check with TRF latencies against a reference dataset in the same code (herrmann2025,
  weissbart2019).
- **Speech in noise** gives ~-15 ms DNN offsets even with measured onsets: that is response latency, not a timing
  error.

## Data size
- Count each trial's longest stimulus (simultaneous streams once), summed per participant. Where stimuli are longer
  than the recording, report the recorded duration (das2019: 2.3 h estimated vs ~1.3 h recorded).

## Running the work
- **Long jobs.**
  - Detach them and make them resumable: a server reboot and a Claude Code restart have each killed everything.
  - After relabelling conditions or changing an adaptor, move the caches aside: caches keyed by subject, trial or
    condition silently return old results (etard2019 DNN offsets).
- **scipy.fft caches a plan per transform length**, ~5 GB each for long awkward lengths. Pad to `next_fast_len`.
- **`multiprocessing.Pool` with fork hung** in a numpy-threaded parent. Use `get_context("spawn")`.
- **Downloads.**
  - They can stop silently or time out (DRUM 15 s read timeout): check the final sizes.
  - ePrints serves an Anubis proof-of-work gate (HTTP 401). Don't circumvent it; ask for a manual download.
- **The downloader's `extract_archives=True` deletes the zips** after extraction (chen2026 backup).
- **A shared git index in a worktree** lets another session's staged files slip into your commit (ea493e7). Commit
  with explicit paths.
