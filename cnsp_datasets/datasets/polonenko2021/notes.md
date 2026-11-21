# polonenko2021: peaky speech, eLife 2021 (Dryad doi:10.5061/dryad.12jm63xwd)

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
- 15 stimulus zips (158 GB zipped, 249 GB unzipped): one expyfun hdf5 per 64 s chapter,
  `<Exp>_Stimuli_<Narrator>_Narrator_<NN-NN>/<Narrator>Narrator<NNN>_bands[_aud].hdf5` (Exp3: `_aud`), each
  ~1.7-2 GB of float64 synthesis intermediates (`phase`, `x_harm*`, `mixer`, `t0`, ...). Only `fs` (44100),
  `x` (unaltered), `x_play_single` (broadband peaky), `x_play_band` (multiband peaky; Exp3 stereo, one ear per
  channel), `pulse_inds/idx_k` and `fc_band` are needed. `compact_stimuli.py` (this folder) keeps just
  those keys in the same file names and layout (~30 GB); the adaptor reads either.
- The two `Pilot_Stimuli_Female_*` zips return HTTP 401 (embargoed/private on Dryad); the pilot is left out.
- README lists `Exp1_Stimuli_Female_*` and `Pilot_Stimuli_Male_*` zips that are not on Dryad; Exp1 used only the
  male narrator (dataset README), so the former were never needed. The pilot is left out (its male stimuli are not on Dryad).

## 3. Trials and triggers (from the READMEs and code; checked in 3b, 9)
- 64 s trials played back to back; S 1 at each start, then the trial number (0-119) as 4/8 bits. Stories advance
  through the session (alchemyst000_unaltered, alchemyst001_broadband, ...). Several subjects have two runs
  (battery died) and repeated trials after a restart; the authors keep one copy (`code/...:160-171`).
- **Tube delay:** Exp1-3 READMEs: "already corrected" in the triggers; Pilot README: NOT corrected. Checked in section 9.
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

## 4. Stimulus <-> trial mapping (authors' analysis code, checked against events.tsv)
Trial n = the 7-bit ID (0-119); file chapter and key:
- Exp1: chapter n; type n % 3 = unaltered (`x`), broadband (`x_play_single`), multiband (`x_play_band`).
- Exp2: narrator Male if n % 4 < 2 else Female; type n % 2 = broadband / multiband; chapter 2 * (n // 4) + n % 2.
- Exp3: narrator Male if n even else Female; multiband (`x_play_band`, 2 channels); chapter n // 2.
events.tsv `trial_type`/`stimulus_type`/`narrator` agree for all 5,306 events. Its `file` column agrees too, except
in **Exp2 run-2 files (sub-04, sub-10), where it restarts at 0** (BIDS-conversion counter): 21 events name the
wrong chapter. The trial ID is used.
- Pulse trains (`pulse_inds`, 44.1 kHz sample indices): unaltered and broadband use `idx_0` (authors:
  `[:1]`; unaltered speech's own glottal pulses); multiband uses the band trains (Exp1/2: `idx_0..3`, 0-1, 1-2,
  2-4, 4-8 kHz; Exp3: `idx_0..9`, row 2 * band + ear, 0.5-8 kHz) and 6 common-component trains after them
  (`[:n_bands + 6]`).
- Audio rms 0.01 in every file (README: 65 dB SPL); stored = played (no rescaling in the analysis code).

## 5. Neural data
- BrainVision, 10 kHz, channels `A1`, `A2` (earlobes; reference FCz, ground Fpz: `task-*_eeg.json`), µV.
  Amplitudes 9-11 µV at 1-1000 Hz: no gain problem (unlike polonenko2026). Kept as recorded.

## 6. Adaptor
One TrialRecord per trial; subject 100 * experiment + label (Exp1 102..124, Exp2 201..212, Exp3 301..311);
trial = ID + 1; conditions `exp1-<type>`, `exp2-<narrator>-<type>`, `exp3-<narrator>-multiband`. Stimulus
`<exp>_<narrator><NNN>_<type>` (the experiments' files are separate downloads, so the experiment is in the name):
`audio`, `pulses` (uint8), `pulses_fake` (multiband). All 44 subjects have all 120 trials after dropping
cut/repeated copies: 5,280 trials. Drift per recording from the start-to-start intervals (`start_drift`).

## 7. Data size
44 participants x 120 x 64 s = **93.9 h** (2.13 h each). Exp1 22 x 2.13 h (46.9 h; 15.6 h per type), Exp2 11 x
2.13 h (23.5 h; 5.9 h per narrator x type), Exp3 11 x 2.13 h (23.5 h; 11.7 h per narrator).

## 8. Upstream issues (to report)
1. Exp2 events.tsv `file` restarts at 0 in run-2 files (section 4).
2. Pilot female stimulus zips not downloadable (HTTP 401); pilot male stimuli not listed at all.

## 9. Tube delay (onset = S 1)
- Exp1-3 READMEs: markers "already corrected for the tubing delay"; the Exp1-3 analysis code adds nothing, the
  pilot's (uncorrected) adds 11 inch / 343 m/s. The adaptor uses S 1 as the onset.
- **Not confirmable from the ER-2 artefact here**: per-trial deconvolution (30-3000 Hz, as stoll2025) finds no
  artefact that replicates between the two halves of a trial (Exp1 sub-03, 10, 20; split-half z ~0), unlike
  ds005408/ds006434/ds008065. Peak-lag medians of -0.5..-0.7 ms are the centre of the -2..1 ms search window
  (noise). A cross-correlation (EEG and audio > 1.5 kHz) gives -0.5 ms in two subjects and +1.7 ms in a third,
  and the same method gives +0.5 ms on ds008065 (markers at the transducer): not a usable calibration.
  Per-trial audio polarity is therefore not checkable either (no sign of alternation in the code or READMEs).
- **Wave V latency check** (`tmp/review/scripts/wave_v_latency.py`: standardised 1 kHz data, channel mean,
  pulse train row 0, 30-450 Hz deconvolution, peak at 4-10 ms): Exp1 broadband 7.35 ms grand average (15
  subjects, per-subject median 7.31, IQR 7.07-7.74) vs polonenko2024 7.83 ms (15 subjects; markers + 0.81 ms,
  artefact-confirmed in ds005408). Uncorrected markers would put polonenko2021 ~0.8 ms *later* than the truth;
  it is 0.5 ms earlier, so onset = S 1 is consistent with the README (the remaining difference: different
  stimuli and f0s).

## 10. Validation (2026-11-21; A1, A2, 1000 Hz, no re-reference)
`tmp/review/polonenko2021/validation.{json,png}`, `by_condition/`.

| condition | low r (sig) | mlr SNR (sig) | brainstem SNR (sig) | tier |
|---|---|---|---|---|
| all (44 subjects) | 0.073 (1.00) | 2.88 (0.82) | 3.57 (0.86) | brainstem |
| exp1-unaltered / broadband / multiband | 0.065 / 0.066 / 0.066 | 2.18 / 1.63 / 1.79 | 2.82 / 3.62 / 2.20 | brainstem |
| exp2-male-broadband / multiband | 0.059 / 0.069 | 1.47 / 1.57 | 3.47 / 1.76 | brainstem |
| exp2-female-broadband / multiband | 0.065 / 0.068 | 1.78 / 2.42 | 3.11 / 1.91 | brainstem |
| exp3-male / female (multiband) | 0.090 / 0.091 | 2.11 / 3.10 | 1.51 / 2.80 | brainstem |

Broadband > multiband at the brainstem tier, as in the paper (multiband spreads the response over bands; the
validator uses the audio). Coherence (`tmp/review/coherence_peaky/polonenko2021_*`): f0-band peak for the male
narrator (80-150 Hz: 4.8x the null in exp1-broadband, 2.8x exp2-male-broadband), at 150-300 Hz for the female
(1.5x); 1-8 Hz 2.4-9x.
