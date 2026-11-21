# polonenko2026: multiband peaky speech, three experiments

Subcortical EEG to 10 s clips of dichotic multiband peaky speech, comparing stimulus phase and voice pitch
(f0) for measuring frequency-specific ABRs. Three experiments with different participants.

- **Source:** OpenNeuro ds008065 v1.0.1 (doi:10.18112/openneuro.ds008065.v1.0.1). Licence CC0.
- **Paper:** Polonenko MJ, Eisenreich BR (2026). Optimal parameters for measuring multiband auditory brainstem
  responses to continuous speech. *Trends in Hearing*. doi:10.1177/23312165261465722
- **Code (authors):** in the dataset (`code/`) and https://github.com/polonenkolab/multibandABR_optimal_params

## Size
62 participants, 46,604 trials (10 s): **129.5 h in total, 2.09 h per participant** (1.33-2.33).
- `phases` (17 participants, 1.96 h each): `phases-zero`, `phases-chirp`.
- `f0s` (30, 2.33 h): `f0s-{toto,wizardofoz}-{original,shifted}`.
- `f0s2` (15, 1.75 h): `f0s2-wizard`, `f0s2-wonderland`, `f0s2-drdolittle`.

Subjects are numbered 101-117, 201-230, 301-315.

## What is provided
- **EEG:** `FCzA1` (FCz minus the left earlobe, bipolar), `FCz`, `A2`, as recorded. The authors use `FCzA1` and
  `FCz - A2`. Recorded at 10 kHz, stored at **1000 Hz** by default. Scaled to µV: the shipped files are 100x too
  large (EP-PreAmp gain), and the adaptor divides by 100.
- **Stimuli** (48 kHz, 2 channels = left/right ear):
  - `audio` as played (exp2/exp3 rescaled to std 0.01, as at playback);
  - `pulses`: 10 pulse trains, row `2 * band + ear`, 5 bands (uint8);
  - `pulses_fake`: 5 trains for the common component.
- No transcripts or nerve-model regressors.

## Alignment
- Sound-card triggers (sample-locked); onset = start marker + 0.81 ms tube delay.
- Drift is 8.5-10.2 ppm per run, corrected by default.
- Trials crossing a recording pause are skipped, as are 24 trials with garbled trigger IDs.
- **events.tsv is off by one in exp2 and exp3:** it names the file before the one played. The adaptor uses the
  played file, as confirmed from the EEG.

## Validation
**Brainstem tier**, overall (SNR 3.27, 84% of subjects significant) and in all 9 conditions. Chirp > zero phase
and shifted (lower f0) > original, as in the paper.

## Caveats
- The authors excluded some participants and data, all kept here; filter them if you want to match the paper:
  - sub-101 (no responses);
  - sub-113 (last hour not saved);
  - sub-223 and 230 (recording problems);
  - sub-206, 208 and 217 (noisy);
  - the first 40 min of sub-222.

Details: `notes.md`.
