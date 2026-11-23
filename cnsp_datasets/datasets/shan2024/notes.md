# shan2024: ABRs to music and speech (NEMAR on004356 = OpenNeuro ds004356)

## 1. Source
- NEMAR on004356 v1.0.0 (doi:10.82901/nemar.on004356), mirror of OpenNeuro ds004356; EEG-BIDS.
- Shan T, Cappelloni MS, Maddox RK (2024). Subcortical responses to music and speech are alike while cortical
  responses diverge. *Sci Rep* 14:789. Code: https://github.com/maddoxlab/Music_vs_Speech_abr (read:
  `response_derive/derive_music_speech_ABR.py`, `stim_preproc/stim_preproc.py`, `regressor_gen/*`).
- Shared code: `datasets/maddox_base/common.py`.

## 2. Layout
- `sub-01`..`sub-24` (no 14, 21: withdrew / technical problems; 22 subjects). One recording each, except sub-03
  and sub-19: run-01 = clicks only, run-02 = the music/speech phase.
- `stimuli/<type>/<type><NNN>.wav`: 12 types x 40 clips, 12 s, 48 kHz mono float64 (rms ~0.0096-0.01), plus
  `click/` (60 s). 229 GB in total, nearly all EEG (34 channels at 10 kHz).

## 3. Stimulus <-> trial mapping (verified)
- Phase 1: 10 x 60 s clicks (skipped: ABR only). Phase 2: 480 x 12 s clips (6 music genres: acoustic, classical,
  hiphop, jazz, metal, pop; 6 speech types: chn_aud, eng_aud, interview, lecture, news, talk), 40 each, shuffled.
- The 10-bit ID after each start trigger decodes (MSB first) to [type (4 bits, index in events.json levels),
  clip number (6 bits)] and matches events.tsv (`trial_type`, `number_trial`, `sample`, `stim_file`) for every
  trial of all 24 recordings (README: "trial number ... 2 ** (b + 2)").
- **Undocumented extra trials:** 64-120 start triggers with 7-bit IDs follow the experiment in most recordings
  (from ~100 s after the last clip, ~1 s apart, no end markers). Not in events.tsv or the README; skipped.
- sub-19 run-01 has 15 click starts for 10 click events (clicks are skipped anyway).

## 4. Speech features
- Audio as played (`audio`, 48 kHz). No pulse trains (not peaky speech); the authors' regressors (half-wave
  rectified audio, IHC/ANM models) are generated from the audio by their code.

## 5. Neural data
- BrainVision actiCHamp, 10 kHz, µV. 32 scalp channels (active; original reference not documented; the authors'
  cortical analysis re-references to P7/P8) + `EP1`, `EP2` (EP-PreAmp: FCz minus each earlobe; "ABR reference
  placed on FCz"; ground Fpz). Amplitudes plausible (EP 8-13 µV, scalp 11-25 µV at 1-1000 Hz): no gain problem.
- All 34 channels kept as recorded, type `eeg`.

## 6. Alignment
- Sound-card triggers (expyfun, RME Babyface Pro, ER-2): S 1 start, S 2 20 ms before the end. events.tsv
  `sample` = S 1.
- Tube delay: the authors do not correct it. **No ER-2 artefact is visible in EP1/EP2** (pooled SNR ~3, per-trial
  signs at chance), so it cannot be checked from the EEG as in the other datasets. Same hardware, booth and
  months (Jun-Aug 2021) as ds005408, whose markers do not include it: the adaptor adds 0.81 ms (unverified here;
  wave V latency in validation is a soft check).
- Drift 24.8-31.4 ppm per recording from S 2 - S 1 (authors: fixed 10000.25 Hz = 25 ppm).
- No recording pauses.

## 7. Adaptor
One TrialRecord per clip; condition `music-<genre>` / `speech-<type>`; trial = start marker index across runs.
Onset = S 1 + tube delay; drift correction (default on); 1000 Hz by default. Stimulus `<type><NNN>` audio.

## 8. Data size
22 participants x 480 x 12 s = **1.60 h each, 35.2 h in total** (10,560 trials); each of the 12 conditions
22 x 0.13 h; music 22 x 0.80, speech 22 x 0.80.

## 9. Upstream issues (to report)
1. The 7-bit trials after the experiment are undocumented (section 3).

## 10. Validation (2026-11-20; EP1, EP2, 1000 Hz, no re-reference) — brainstem tier not reached by the validator
`tmp/review/shan2024/validation.{json,png}`, `by_condition/`.
- All 22 subjects pooled: low r 0.038 (22/22 significant, TRF peak 31 ms), MLR SNR 1.44 (6/22), **brainstem SNR
  0.92 (1/22)**: tier `mlr`. Per condition: low tier in 10 of 12 (classical and news: none), MLR in interview only.
- Coherence (`tmp/review/coherence_peaky/shan2024_*`, EP1/EP2): above the null at 1-8 Hz, but the f0 range
  (80-150 Hz) is ~1.1x the null median (polonenko2024/2025: 2.3-2.5x).
- Checks (sub-01, 05, 09; `tmp/review` session log 2026-11-20):
  - **Click ABR** (10 x 60 s, rectified click train, raw markers): wave V at 7.7-8.0 ms, 6-42x the noise SD on
    EP1/EP2. Channels, triggers and onsets are right.
  - Music/speech, the authors' way (EP mean, positive and negative half-wave rectified audio averaged, 10 kHz):
    no wave V (largest peak 1.5-5.9x noise at 6-15 ms).
  - Not a rate error (stimulus stretch -90000..+88435 ppm: no peak above 6x), not a constant offset (no sharp
    peak within ±1 s), not a clip-numbering offset (clip n-2..n+2: n is best, but only 2.6-3.9x noise).
- Interpretation (open): mapping and timing are right (clicks, low tier, clip-offset test); the half-wave
  rectified regressor gives little brainstem response to these natural, non-peaky clips. The paper derived its
  ABRs with IHC/ANM model regressors (`regressor_gen/IHC_ANM_regressor_gen.py`). To do: derive ANM regressors and
  re-check before calling the tier; alternatively the shared wavs differ in fine structure from those played
  (stimuli were added to the dataset later, 2024-01-18: "fix stim and event file").
- **Dataset version ruled out** (2026-11-21): the authors' README points to OpenNeuro ds004356 v2.2.1; the NEMAR
  v1.0.0 copy used here has the same CHANGES (up to 2.2.1), the same sizes for all 640 files, and SHA-256-identical
  content for all 24 events.tsv, every other .tsv/.json sidecar, CHANGES, README and 37 sampled wavs (clip 000 of
  every type + 25 random); only dataset_description.json differs (NEMAR's). The authors' derivation
  (`derive_music_speech_ABR.py`) maps clips by events.tsv row order and reads these wavs, as the adaptor does.

## 11. ANM regressors: the brainstem response is there (2026-11-21)
- Regressors as the authors' `regressor_gen/IHC_ANM_regressor_gen.py` `anm()` (Zilany 2014 via the `cochlea`
  package, HSR rates at 43 CFs 125 Hz - 16 kHz, 65 dB SPL re rms 0.01, summed, +1 ms, 10 kHz, both polarities):
  **`datasets/shan2024/anm_regressors.py`** (kept in the repo; run in a separate env with `cochlea`; cochlea 2
  needs a `np.fft.fftpack` stub on current numpy). ~15 CPU-h for 480 clips.
- Derivation the authors' way (`derive_music_speech_ABR.py`; `tmp/review/scripts/shan2024_anm_abr.py`) on the
  adaptor's EEG (10 kHz, drift-corrected, onset = S 1 + tube delay), EP1/EP2 mean, 150-2000 Hz for display:

  | regressor | wave V > 4x noise: all / music / speech | grand average |
  |---|---|---|
  | ANM (+2.75 ms, as the authors) | 22/22 / 21/22 / 22/22 | wave V 7.3 ms, 40x noise SD |
  | half-wave rectified audio | 12/22 / 0/22 / 13/22 | wave V 7.5 ms, 11x |

  (`tmp/review/shan2024/anm_vs_rect.png`.) As in the paper: the rectified regressor is weak for speech and fails
  for music; the ANM regressor gives clear ABRs for both. The validator's brainstem tier uses the audio, hence
  `mlr`. Mapping, timing and the added tube delay are right (wave V 7.3-7.4 ms, cf. clicks 7.7-8.0 ms,
  polonenko2024 7.8 ms).
- **Decision (2026-11-21): the adaptor ships audio only** (the ANM regressors are not in the dataset and need the
  external model). Users who want brainstem responses to these clips generate them with `anm_regressors.py`.
  Validation tier stays `mlr` for the audio feature; the response itself is confirmed above.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**medium**: Sound-card triggers (expyfun) + 0.81 ms tube delay; no ER-2 artefact visible, so only the brain check (ANM wave V 7.3 ms) confirms it; drift 25-31 ppm from triggers corrected; mlr tier.
