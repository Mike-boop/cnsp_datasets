# polonenko2021: peaky speech, unaltered speech, two narrators, dichotic multiband

Subcortical EEG to 64 s audiobook segments: unaltered speech and broadband and multiband peaky speech. Three
experiments with different participants (the eLife peaky-speech paper).

- **Source:** Dryad doi:10.5061/dryad.12jm63xwd. Licence CC0 (data). Dryad needs an API token to download.
- **Paper:** Polonenko MJ, Maddox RK (2021). Exposing distinct subcortical components of the auditory brainstem
  response evoked by continuous naturalistic speech. *eLife* 10:e62329.
- **Code (authors):** in each dataset zip (`code/`); stimulus generation https://github.com/maddoxlab/peaky-speech

## Size
44 participants x 120 trials x 64 s = **93.9 h in total, 2.13 h per participant**.
- Exp1 (22 participants, subjects 102-124): `exp1-unaltered`, `exp1-broadband`, `exp1-multiband`, male narrator,
  0.71 h each per participant.
- Exp2 (11, subjects 201-212): `exp2-{male,female}-{broadband,multiband}`, 0.53 h each.
- Exp3 (11, subjects 301-311): `exp3-male-multiband`, `exp3-female-multiband` (dichotic, 5 bands per ear),
  1.07 h each.

The pilot experiment is left out: its stimuli are missing or not downloadable from Dryad.

## What is provided
- **EEG:** `A1`, `A2` (earlobes, referenced to FCz), 10 kHz recorded, **1000 Hz** stored by default.
  Do not average-reference.
- **Stimuli** (44.1 kHz, named `<exp>_<narrator><NNN>_<type>`):
  - `audio` as played (Exp3: 2 channels, one per ear);
  - `pulses`: glottal pulse trains, 1 for unaltered/broadband, one per band for multiband (uint8);
  - `pulses_fake` (multiband): 6 common-component trains.
- The stimulus files on Dryad hold about 2 GB of intermediate signals per segment (249 GB unzipped). The adaptor
  needs only the audio, pulse and rate entries. `compact_stimuli.py` (this folder) writes a ~30 GB copy with the
  same names and layout straight from the zips; the adaptor also reads a full unzip.

## Alignment
- Sound-card triggers (sample-locked). Onset = start marker: the README says the markers already include the
  tube delay. The earphone artefact is too weak here to confirm this. Broadband wave V latency (7.35 ms, against
  7.83 ms in polonenko2024) supports it, since uncorrected markers would make the latency longer.
- No end markers: drift is estimated from the start-to-start intervals of back-to-back trials, per recording, and
  corrected by default. It is -7.5 ppm (Exp1, Exp2 subjects 1-11) or +30.5 ppm (Exp2 subject 12, Exp3): a hardware
  change partway through.
- After restarts, the later complete copy of a repeated trial is kept; trials cut by a pause or the end of a
  recording are skipped. Every subject has all 120 trials.

## Validation
**Brainstem tier**, overall (SNR 3.57, 86% of 44 subjects) and in all 9 conditions; broadband > multiband, as in
the paper.

## Caveats
- events.tsv's `file` column restarts at 0 in Exp2 run-2 files (sub-04, sub-10). The adaptor uses the trial ID.
- Per-trial audio polarity cannot be checked from the EEG; nothing in the code or READMEs suggests inversion.

Details: `notes.md`.
