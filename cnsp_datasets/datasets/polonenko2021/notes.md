# polonenko2021: peaky speech, eLife 2021 (Dryad doi:10.5061/dryad.12jm63xwd) — in progress

## 1. Source
- Dryad doi:10.5061/dryad.12jm63xwd (CC0). Polonenko MJ & Maddox RK (2021). Exposing distinct subcortical
  components of the auditory brainstem response evoked by continuous naturalistic speech. *eLife* 10:e62329.
- Dryad needs an API token for file downloads (`DRYAD_TOKEN`); the registry entry is `polonenko2021`.
- Analysis code inside each dataset zip (`code/peakyspeech_*_eeg_analysis.py`); peaky-speech generation:
  https://github.com/maddoxlab/peaky-speech. Shared code: `datasets/maddox_base/common.py`.

## 2. Layout
- 4 EEG-BIDS zips (19.6 GB): `Exp1_Peaky-vs-Unaltered_Speech_Dataset` (22 subjects: sub-02..24 without 15;
  unaltered vs broadband vs multiband peaky speech, male narrator, 40 x 64 s each, interleaved),
  `Exp2_Peaky_Speech_Narrators_Dataset` (11: male/female x broadband/multiband, 30 x 64 s each),
  `Exp3_Peaky_Speech_Audiological_Dataset` (11: dichotic multiband, male/female, 60 x 64 s each),
  `Pilot_Dynamic_Random_f0_Shifts_Dataset` (1 subject).
- 16 stimulus zips (158 GB): hdf5 per narrator and chunk (`<narrator>Narrator<NNN>_bands[_aud].hdf5`: audio and
  pulse indices). **Not downloaded yet** (storage decision pending).
- README lists `Exp1_Stimuli_Female_*` and `Pilot_Stimuli_Male_*` zips that are not on Dryad; Exp1 used only the
  male narrator (dataset README), so the former were never needed. Pilot male stimuli: to check.

## 3. Trials and triggers (from the READMEs and code; to verify against the data)
- 64 s trials played back to back; S 1 at each start, then the trial number (0-119) as 4/8 bits. Stories advance
  through the session (alchemyst000_unaltered, alchemyst001_broadband, ...). Several subjects have two runs
  (battery died) and repeated trials after a restart; the authors keep one copy (`code/...:160-171`).
- **Tube delay:** Exp1-3 READMEs: "already corrected" in the triggers; Pilot README: NOT corrected. To verify from
  the ER-2 artefact as for stoll2025.
- **Drift:** no end markers; the authors derive the clock ratio from start-to-start intervals (nominal 64 s) per
  run (`clock_adjust = 64 / (64 + median diff)`; pilot: fixed 64 / 64.001967 from exp3 = 30.7 ppm).

## 3b. Markers checked against the data (2026-11-20)
- Exp1-3: the 7-bit ID after each S 1 = events.tsv `trial` (0-119) in every recording, and events.tsv `sample` =
  S 1. Exception: Exp3 sub-06 starts with a stray S 1 carrying 1 bit (skip trials whose ID is not 7 bits).
- Repeated trials after restarts (keep the later copy, as the authors do): Exp1 sub-07 (94-97), sub-21 (68),
  sub-23 (48-50); Exp3 sub-01 (90-91). Runs split by a dead battery (Exp1 sub-02, 04; Exp2 sub-04, 10; Exp3
  sub-08): the last trial of run-1 is cut (recording ends inside it), run-2 continues/repeats.
- Trials are back to back (start-to-start 64 s except at pauses). **Drift from a line through the start times**
  per back-to-back segment: **-7.5 ppm** (-7.0..-8.1) for Exp1 and Exp2 sub-01..11, **+30.5 ppm** (30.3..30.9)
  for Exp2 sub-12 and Exp3: a hardware change between Exp2 sub-11 and sub-12 (the pilot's hard-coded
  64 / 64.001967 = 30.7 ppm matches the second cluster). No end markers.
- Pilot: 8-bit IDs ([story 1, type 1, trial 6]), trials not back to back; the male stimuli are not on Dryad.

## 4. Open
- Download and inspect the stimuli; verify mapping (trial bits vs events.tsv), tube delay and drift; adaptor.
