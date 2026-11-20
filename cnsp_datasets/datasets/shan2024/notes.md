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
