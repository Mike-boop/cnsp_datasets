# diliberto2020: monophonic Bach melodies, EEG (Dryad g1jwstqmh, CND)

20 listeners (1-10 non-musicians, 11-20 expert pianists) x 30 trials: 10 MIDI-synthesised piano pieces (~2.5 min),
each played 3 times. BioSemi ActiveTwo, 64 scalp channels + 2 mastoids, **raw at 512 Hz** (integer ADC counts, no
filter, no reference). Stimuli shipped only as 64 Hz features (envelope, note onsets, pitch-weighted note onsets)
plus the MIDI scores; no audio. Trials are cut by the authors, with 1 s of padding (512 samples before the
stimulus, ~1 s after). Presentation order not shipped.

## 1. Source
- Dryad doi:10.5061/dryad.g1jwstqmh (version 9, files from 2021-10-07), 3 files, 5.98 GB:
  `diliBach_4dryad_CND.zip` (5,984,510,089 B), `diliBach_midi_4dryad.zip`, `readme_DiliBach_EEG.txt` (v1.1,
  9 June 2021; the Dryad metadata copy says v1.2, 24 June 2021, and differs only in naming the stimulus fields
  `stim.data{f,k}`). All three matched Dryad's size and sha-256 (2026-11-23). Downloads need a Dryad token
  (`tmp/review/scripts/diliberto2020_download.sh` mints one from the client credentials in `secrets.json`).
- **Licence: CC0 1.0** (Dryad).
- Paper: Di Liberto GM, Pelofi C, Bianco R, Patel P, Mehta AD, Herrero JL, de Cheveigné A, Shamma S, Mesgarani N
  (2020). Cortical encoding of melodic expectations in human temporal cortex. *eLife* 9:e51784,
  https://doi.org/10.7554/eLife.51784 (`data_campaign/papers/diliberto2020.pdf`). The 3 ECoG patients of the paper
  are not in the release. Reanalysed by Kern et al. 2022 (kern2022).
- Shared code: none.

## 2. Layout
- `diliBach_4dryad_CND/dataStim.mat` (one file for all subjects), struct `stim`: `names` = 'Speech Envelope
  Vectors', 'Note Onsets', 'Note Pitch Vectors'; `data` {3 x 30} of column vectors; `stimIdxs` (piece 1-10),
  `repIdxs` (repetition 1-3), `condIdxs` (all 1), `condNames` 'Listening', `fs` 64.
- `diliBach_4dryad_CND/dataSub<N>.mat`, N = 1..20, struct `eeg`: `dataType` 'EEG', `deviceName` 'BioSemi', `fs`
  512, `data` {30} of [n x 64] (float), `chanlocs` (64 labels + EEGLAB coordinates), `extChan.description`
  'Mastoids', `extChan.data` {30} of [n x 2], `paddingStartSample` 512, `origTrialPosition` **empty** (all 20).
- `diliBach_midi_4dryad.zip`: `audio1.mid` .. `audio10.mid` (= piece 1-10; original jsbach.net names in the readme).
  The downloader extracts it into the download folder; the adaptor does not use it.

## 3. Stimulus <-> trial mapping (checked on all 20 subjects: `tmp/review/scripts/diliberto2020/explore2.py`)
- Shipped trial index i (0..29) = piece `stimIdxs[i]` = i % 10 + 1, repetition `repIdxs[i]` = i // 10 + 1, the same
  for every subject (readme: "the trial order is the same as in the 'stim' variable"). The three repetitions of a
  piece have bit-identical features: **10 unique stimuli**.
- EEG trial length = 8 x stimulus length + 1017..1024 samples in all 600 trials: 512 samples before the stimulus,
  505-512 after (rounding of the 64 Hz stimulus length).
- **Presentation order is not shipped** (`origTrialPosition` empty, although the readme says it is included).
  Trials were played in random order (paper). So the trial number is the shipped index + 1 and "repetition" is
  the authors' label (presumably the k-th time a piece was heard; unverifiable).
- No missing trials or subjects.

## 4. Speech (music) features available
- 64 Hz: 'Speech Envelope Vectors' (the acoustic envelope of the synthesised audio; non-negative, 0.007-6.4; the
  method is not documented in the paper or readme), 'Note Onsets' (binary pulses, e.g. 1022 notes in piece 1),
  'Note Pitch Vectors' (onset pulses weighted by absolute pitch). Score-derived, not model-derived.
- MIDI scores of all 10 pieces. The audio was synthesised from them with MuseScore 2 piano sounds at fixed tempi
  (47-140 bpm; paper), but the exact rendering (soundfont, version, gain) is unknown, so the audio cannot be rebuilt
  reliably. No audio shipped.
- IDyOM expectation features of the paper are not shipped.

## 5. Neural data
- BioSemi ActiveTwo, 512 Hz native (paper and `fs`). Output at 512 Hz (native <= 1024 Hz, kept).
- **Units: BioSemi ADC counts (LSB = 31.25 nV), scaled by 31.25e-9 to V.** Evidence (`explore3.py`): every value is
  an integer (smallest nonzero step exactly 1); per-channel DC offsets of 0.7-6e5 counts = 2-19 mV (normal for
  CMS/DRL; read as uV they would be 0.07-0.6 V, outside BioSemi's +-262 mV range); 1-8 Hz SD with a mastoid
  reference = 140-270 counts = 4.3-8.4 uV per subject (calderondepalma2023, also BioSemi CND: 3.5-9.9 uV).
- Raw: no reference applied (CMS/DRL; channel sum not zero), no high-pass (power at 0.25 Hz 40-1500x that at
  2 Hz), no low-pass beyond BioSemi's own; 50 Hz small (0.7-2.8x the 45 Hz power).
- Channels: 64 labels in MNE `biosemi64` order, four with aliases: 'T7 (T3)', 'T8 (T4)', 'Iz (inion)', 'Afz' ->
  renamed T7, T8, Iz, AFz (standard 10-20 names for the template montage). Mastoids: `extChan` columns 1/2 =
  left/right (readme: "electrodes 65 and 66 correspond to left and right mastoids") -> `M1`, `M2`, type `misc`.
  No EOG, no stimtrack, no trigger channel. Positions: `biosemi64` template (the shipped coordinates are EEGLAB
  template coordinates, not digitised).
- No NaNs, no flat channels. Bad-channel screen (`explore2.py`, `explore4.py`; 1-8 Hz, mastoid reference): blink-driven
  frontal channels > 3x the median SD in several subjects (physiological, not marked). Channels with a raised
  broadband floor (`explore/psd_suspect_all.png`) were judged by their 1-8 Hz correlation with the 4 nearest
  neighbours (r_nb):
  - **marked bad: sub8 C4** (r_nb -0.45, 3.6x SD; subject median r_nb 0.33) and **sub12 Fpz** (r_nb -0.18, 3.4x SD):
    noise without EEG.
  - not marked: sub4 F3 (r_nb 0.89), sub10 FC1/F8/FC2 (0.96-0.97), sub10 FCz (0.63), sub12 C5 (0.68), sub13 right
    temporal F8/FT8/FC6/T8 (EMG hump at 50-150 Hz; physiological).

## 6. Alignment
- Paper: Presentation software, 44.1 kHz, Sennheiser HD650 headphones (circumaural: no tube delay). No trigger
  information shared; the authors cut the trials. Trigger route unknown: `trigger_type` = `unknown (Presentation;
  trigger route not documented, triggers not shared)`.
- Readme: "the first sample of the stimulus corresponds to the EEG sample eeg.paddingStartSample+1 (=513)".
- Check (`explore3.py`, `explore/xcorr_per_subject.png`): RMS over channels of the cross-correlation of 1-8 Hz
  mastoid-referenced EEG (64 Hz) with the note-onset vector and the half-wave-rectified envelope derivative, with
  the stimulus at EEG sample 513. Sharp peak at +172..+219 ms in 13/20 subjects (P2-like music onset response),
  +62..+125 ms in sub4, 9, 16, 19; sub2 and sub7 have no clear peak (low SNR). Nothing points at a shift.
- Applied: **onset = EEG sample 513** (the leading 512 padding samples are dropped); the trailing ~1 s of EEG is
  kept (the longer signal is cut at the point of use). `alignment_method` = `onset_only` (onsets from the authors'
  epoching, no trigger information). No drift correction (cannot be estimated; see 7).
- Plausible tier: `low` only (64 Hz features; no audio for the 30-60 / 30-250 Hz tiers).

## 7. Cross-subject duration check
- Not possible: trial lengths were set by the authors (stimulus + fixed padding). Drift cannot be estimated. For
  scale: 50 ppm over 200 s is 10 ms, below one 15.6 ms stimulus sample.

## 8. Data size
- 20 participants x 30 trials = 600 trials. Pieces: 159-199 s (sum 1601.7 s = 26.7 min); each heard 3 times:
  **80.1 min per participant** (all identical), **26.7 h** in total (stimulus-based). Musicians (11-20) and
  non-musicians (1-10): 13.3 h each.
- Standardised size: ~0.65 GB per subject (66 channels, float32, 512 Hz), ~13 GB in total.

## 9. Upstream issues
- `origTrialPosition` is empty in all 20 EEG files, although the readme says the presentation order is included.
- EEG values are BioSemi ADC counts (31.25 nV), not uV; units are not stated in the readme.
- The envelope computation is not documented; familiarity ratings marked "(TODO)" in the readme are not shipped.

## 10. Open questions (recommended defaults in brackets)
1. Units: counts x 31.25 nV (evidence in section 5). [Accept.]
2. Onset at EEG sample 513 as documented; leading padding dropped, trailing ~1 s kept. [Accept.]
3. Trial number = shipped index + 1 (presentation order unavailable); piece, repetition and group (musician /
   non-musician) in the provenance; condition `listening`. [Accept.]
4. Stimuli: one stimulus per piece (`piece01`..`piece10`), feature `envelope` at 64 Hz. Note onsets and
   pitch-weighted note onsets (score-derived) could be added as extra features of the same stimulus. [Envelope
   only by default; option `note_features=True` adds `note_onsets` and `note_pitch`.]
5. Bads: sub8 C4, sub12 Fpz. [Accept.]

## 11. Validation (2026-11-23; all 20 subjects, 600 trials)
- `standardise_validate.sh diliberto2020 --tiers low` (average reference over the 64 scalp channels, bads
  excluded); output `tmp/review/diliberto2020/standardised/` (13 GB, 21 MB per trial), `validation.json` (copied
  here), figure `tmp/review/diliberto2020/validation.png`.
- **low (0.5-8 Hz, envelope): pass.** Mean r 0.046 (median 0.044; per subject 0.019-0.084), every subject above its
  circular-shift null (frac_subjects_sig 1.0); population p_circ 0.020, p_mismatch 0.048 (mismatched envelopes of
  other Bach pieces at fixed tempi correlate, so this null is conservative). TRF GFP: no response at negative
  lags; peaks at ~15, ~150 and ~234 ms (trf_peak_s 0.234). Weakest subjects sub2 (0.019) and sub7 (0.021), which
  also had no clear onset xcorr peak (section 6). Per-trial offset estimates are unreliable at this SNR (18 at
  the search edge, jitter SD 160 ms, MAD 14 ms); the drift estimate (-56 +- 184 ppm) is not informative.
- mlr / brainstem: not possible (no audio; 64 Hz features only).
