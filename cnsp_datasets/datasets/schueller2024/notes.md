# schueller2024: notes

Findings that explain `adaptor.py`. Review results and scripts: `tmp/review/schueller2024/`,
`tmp/review/scripts/meg/schueller_*.py` (2026-11-21).

## 1. Source
- Zenodo 12793944 (Set1: participants 1-19 + `Audio/` + `Participants_Overview.pdf`), 12794769 (Set2: 20-38),
  12794808 (Set3: 39-58). CC BY 4.0, v1 (2024-07-22).
- Papers: Schüller et al. 2023, J Neurosci 43(44):7429, doi:10.1523/JNEUROSCI.1247-23.2023 (22 participants);
  preprints doi:10.1101/2024.07.25.605057 and 10.1101/2024.08.01.606154 (the full 58-participant set).
- Code: github.com/Al2606/MEG-Analysis-Pipeline (source reconstruction and a TRF demo; nothing on cutting or
  alignment).
- The raw recordings of the same experiment (BTi files with the `EXT 004` audio channel, EEG, empty room) are the
  non-public `schuller2022full` dataset on branch `internal`; they were used here to verify the release (section 6).
  The public release does not include empty-room recordings.

## 2. Layout
- `Set<n>/<participant>/{LP,HP}_speaker_attended/data_meg.fif`: one run per attended speaker.
- `Set1/Audio/attended_speech/audiobook{1,3}_{1..5}.wav` (int16 mono, 44.1 kHz) and
  `Set1/Audio/ignored_speech/audiobook{2,4}_{1..5}.wav` (float64, two identical channels, 44.1 kHz). Only Set1
  carries the audio; the adaptor reads it from there.

## 3. Stimulus <-> trial mapping
- Two German audiobooks played diotically at once, one per narrator: LP (low pitch) and HP (high pitch). Attention
  switched every chapter, starting with LP (paper). Each run is the authors' concatenation of the 5 chapters with
  that attended speaker.
- Pairing (attended, ignored): LP runs = audiobook1 + audiobook4, HP runs = audiobook3 + audiobook2. Verified:
  paired wavs have identical lengths, and the median f0 (autocorrelation, chapter 1, 30-90 s) is 88 Hz (book1),
  91 Hz (book2), 119 Hz (book3), 124 Hz (book4), so the ignored track is always the other narrator. The internal
  raw-data adaptor (`schuller2022full`) uses the same pairing.
- The ignored track's ~5 s delayed start ("the noise audiobook started ~5 s later") is inside its wav (first
  sound at 5.08-5.09 s); attended speech starts at 0.15 s (book1) and 2.06 s (book3).
- Run length = sum over chapters of ceil(n_audio * 1000 / 44100) samples, exactly: 959415 (HP) and 1247855 (LP)
  in every Set1 participant (959416 for HP in participants 18 and 19: one extra sample at the end). The adaptor
  cuts trials at these cumulative boundaries.
- Trial numbers follow presentation order (LP 1, HP 1, LP 2, ...: inferred from "starting with the LP speaker");
  conditions `lp-attended` / `hp-attended`. Same stimuli for all participants.

## 4. Speech features
Audio only (as shipped). No transcripts or word alignments in the release.

## 5. Neural data
- 4D Neuroimaging Magnes 3600 WH, 248 magnetometers (`A1`-`A248`), in T (cal 1.0). No reference sensors, EEG,
  EOG or audio channel in the release; head-shape points (~3900) and dev_head_t are kept in the FIF.
- Online analog band-pass 1.0-200 Hz (paper; confirmed by the user). The FIF header's 1-500 Hz is a default written
  when the authors resampled to 1000 Hz, not the recording filter. The authors notched 50 Hz harmonics
  (FIR, 0.5 Hz transition) and resampled 1017.25 -> 1000 Hz. Kept at 1000 Hz (no further resampling).

## 6. Alignment (verified against the raw recordings)
- Authors: cross-correlation of the stimulus with the analog audio channel recorded by the MEG logger (the sound-card
  output, before the 2 m tubes), "accuracy 1 ms". The Zenodo text gives the tube delay as 6 ms; the paper does not
  mention it.
- Check (`schueller_cut_check.py`, participant 1 = raw P2, matched by identical meas_date 2023-01-13 16:07:38): each
  Zenodo chapter was located in the raw MEG by cross-correlating its MEG (10 channels, 2-40 Hz, r > 0.995) and
  compared with the chapter onset in `EXT 004`. Over the 10 chapters the release starts 0.16-1.13 ms after the
  stimtrack onset (whole-sample stimtrack onsets at 1017.25 Hz, so within ~1 ms), and the release's time base
  matches the raw file to < 0.1 ppm. So the release is cut at the electrical onset: **the 6 ms acoustic delay is not
  compensated**. `tube_delay=True` (default) starts each trial 6 ms after its boundary and ends it at the next
  boundary (the last 6 ms of a chapter would belong to the next chapter's recording).
- Drift (sound card vs MEG clock): no audio channel in the release, so it cannot be estimated from the release
  itself; see section 7.

## 7. Drift (drift.py, drift.csv)
- Measured on the non-public raw recordings (`drift.py`: stimtrack `EXT 004` resampled to 1 kHz, chapter onset by
  cross-correlation, `jehn2025_base.drift.trial_drift`: 2-200 Hz, 10 s windows every 5 s, Theil-Sen). `drift.csv`:
  one row per raw recording x chapter (61 recordings, 610 chapters; `trial` as in the adaptor), with the recording's
  meas_date.
- Result: **+8.46 ppm** median (6.3-10.5 per chapter; participant medians 7.1-9.8, rising over the months of
  recording; LP and HP chapters agree), onset -0.27 +- 0.30 ms. Per-subject plot:
  `tmp/review/schueller2024/drift/drift_per_subject.png`. At 8.5 ppm a 5 min chapter ends 2.5 ms late.
- Matching to the release: a release run has the same meas_date as its raw recording (participant 1 = P2, ...;
  18 of the 19 Set1 participants; participant 15 (2023-04-05) has no raw recording: `P15-no data` is empty and there is
  no P17).
- `drift="subject"` (default): the participant's median over chapters with >= 10 valid windows, the dataset median
  for participants without raw data; `"dataset"`: +8.46 ppm for everyone; `None`: no correction. Applied by
  resampling each trial onto the audio clock (`standardise/clock.py`, quintic spline).

## 8. Validation (Set1, 19 participants, magnetometers, no re-referencing)
`python -m cnsp_datasets.validate schueller2024 --download-dir ... --picks mag --n-subjects 0`; results and figures
`tmp/review/schueller2024/validation_set1{,_drift}/`.

| drift | low r | mlr SNR (sig.) | 30-250 Hz SNR, 28-45 ms (sig.) |
|---|---|---|---|
| none | 0.0211 (19/19) | 1.04 (4/19) | 1.60 (16/19) |
| per subject (default) | 0.0211 (19/19) | 1.05 (4/19) | **1.68 (18/19)** |

All tiers pass (p <= 0.02); **validation tier: brainstem** (for MEG: the 30-250 Hz cortical response, sharp peak at
~38 ms). The drift correction leaves the low tier unchanged and raises the high-frequency SNR, as expected for
1-3 ms of drift per chapter.

## 9. Data size
58 participants x 0.61 h (10 chapters, 36.8 min) = 35.6 h; Set1: 19 participants, 11.6 h.

## 10. Open questions
- Set2/Set3: Zenodo returned HTTP 403 ("unusual traffic") to this server on 2026-11-21; only Set1 is checked. The
  user recalls no differences in Sets 2 and 3, so the adaptor assumes the same layout, run lengths and pairing; check
  run lengths and the meas_date matching (drift.csv) when they are downloaded.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**good**: Authors' cut by xcorr with the MEG audio channel; release onset within 0.2-1.1 ms of the raw stimtrack (participant 1); drift +8.46 ppm from the stimtrack, per participant; +6 ms tube delay (Zenodo text) applied; brainstem tier (Set1).
