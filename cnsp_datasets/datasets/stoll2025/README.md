# stoll2025: selective attention to two talkers, subcortical and cortical EEG

EEG while listening to two simultaneous audiobooks (one female, one male talker) and attending one, played
diotically (exp1) or one to each ear (exp2); plus passive listening (exp3). Subcortical montage for ABRs and,
in exp1 and exp2, 32 scalp channels from the same recordings.

- **Source:** OpenNeuro ds006434 v1.2.0 (doi:10.18112/openneuro.ds006434.v1.2.0). Licence CC0.
- **Paper:** Stoll TJ et al. (2025). The auditory brainstem response to natural speech is not affected by
  selective attention.
- **Code (authors):** in the dataset (`code/*.ipynb`) and https://github.com/maddoxlab/stoll_et_al_selective_attention
- Two adaptors: `stoll2025` (subcortical) and `stoll2025_cortex` (32 channels, exp1 and exp2).

## Size
Subcortical: 66 participants, 5234 trials, about 106 h (99 h of audio; exp3 trials are padded).
- exp1 diotic (28 participants, 2.13 h each): `diotic-attend-female`, `diotic-attend-male`, 120 x 64 s, every
  chapter pair heard twice (once attending each talker).
- exp2 dichotic (24, 1.06 h each; one 0.82 h): `dichotic-attend-{female,male}-side{0,1}` (side of the attended
  talker).
- exp3 passive (14, 1.52 h each, padded): `passive-fM`, `passive-fW`.

Cortical: 52 participants (exp1, exp2), 4786 trials.

## What is provided
- **Subcortical EEG:** stored at 1000 Hz by default. Do not average-reference.
  - exp1: `A1`, `A2` = FCz minus each earlobe (plus `TM`, eardrum, in some subjects), recorded at 10 kHz.
  - exp2: `FCz` (minus one earlobe), 10 kHz.
  - exp3: `A1`, `A2` at 25 kHz.
- **Cortical EEG:** 32 channels at their native rates: 1 kHz (exp1) and 500 Hz (exp2; the README says 1 kHz).
- **Stimuli:**
  - exp1: `wrinkle_chNN` (female) and `alchemyst_chNN` (male), 48 kHz audio as played, plus `pulses`; `anm`
    with `save_anm=True`. The attended one is marked.
  - exp2: `<talker>_dichotic_chNN`, 24414.0625 Hz.
  - exp3: `exp3_<fM|fW>_<story|distractor>K[_inv]`; none attended; `_inv` = played inverted, audio negated.

## Alignment
- Sound-card / hardware triggers; the markers already include the tube delay, as confirmed from the ER-2
  artefact.
- Drift is corrected by default. It falls in two clusters in exp1 (24-25 and 11-12 ppm: a hardware change); exp2
  uses -5 ppm, from the artefact.
- Mapping verified from the trigger IDs. Ear routing in exp2 was confirmed from the artefact.

## Validation
- **Subcortical:** brainstem tier overall (SNR 2.55, 77% of 66 subjects) and in all conditions except
  `passive-fW` (low tier).
- **Cortical:** middle-latency tier (low r 0.038, 52/52 subjects; MLR SNR 1.52).

## Caveats
- **Polarity:**
  - exp1's stored audio alternates polarity in segments within each trial. That is how it was played (confirmed
    from the EEG), so `audio` is right as is.
  - The file that would undo the alternation (`flip_signs`) is truncated on OpenNeuro.
  - exp3 alternates polarity across repetitions (the `_inv` stimuli). sub-passive20's starting polarity is
    assumed, not verified.
- Not included:
  - exp1's silent intervals, which the authors zero in the EEG;
  - exp2's ANM regressors (36 entries for 30 chapters, unclear);
  - exp3's EMD features (truncated file).
- **Open observation:** in the diotic conditions, envelope coherence with the *ignored* talker exceeds the
  attended one at 1-3 Hz (but not at 4-10 Hz). See `notes.md` section 14.

Details: `notes.md`.
