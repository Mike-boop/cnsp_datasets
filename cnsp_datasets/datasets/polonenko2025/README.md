# polonenko2025: peaky speech with 1 to 5 simultaneous talkers

Subcortical EEG to 10 s clips of peaky speech from 1, 2, 3 or 5 male talkers at once (passive listening). Each
story is played at the same level, so the signal-to-noise ratio (SNR) of any one talker falls as talkers are added.

- **Source:** OpenNeuro ds005408 v1.0.1 (doi:10.18112/openneuro.ds005408.v1.0.1). Licence CC0.
- **Paper:** Polonenko MJ, Maddox RK (2025). The effect of speech masking on the human subcortical response to
  continuous speech. *eNeuro* 12(4). doi:10.1523/ENEURO.0561-24.2025
- **Code (authors):** https://github.com/polonenkolab/peaky_snr

## Size
25 participants, 17,998 speech trials (10 s): **50.0 h in total, 2.00 h per participant** (sub-19: 1.99 h).
Conditions `talkers1-clean`, `talkers2-snr0dB`, `talkers3-snr-3dB`, `talkers5-snr-6dB`, 0.50 h per participant
each. Click trials are left out.

## What is provided
- **EEG:** `A1`, `A2` = FCz minus the left / right earlobe, 10 kHz recorded, **1000 Hz** stored by default.
  Do not average-reference.
- **Stimuli:** every talker in a trial is its own stimulus (`<story>_NNN`; none attended), 48 kHz:
  - `audio`: the talker's waveform as played (the trial is their sum, diotic);
  - `pulses`: glottal pulse train (uint8);
  - `anm` (optional, `save_anm=True`): auditory-nerve-model regressor, two polarities.
- **Polarity:** from sub-07 on, half the trials were played inverted. These stimuli are named `<story>_NNN_inv`
  with the audio negated (and `anm` rows swapped), so `audio` is always the waveform as played. The polarity is
  decoded from the trigger IDs (not in events.tsv) and was confirmed from the EEG.
- No transcripts or word alignments. Story tokens are randomised, so the stories cannot be followed.

## Alignment
Sound-card triggers (sample-locked); onset = start marker + 0.81 ms tube delay (confirmed to one 10 kHz sample
from the earphone artefact); drift 24-26 ppm per run, corrected by default. Mapping verified against the trigger
IDs: 0 mismatches. One trial cut by the end of a recording (sub-19) is skipped.

## Validation
**Brainstem tier** overall (SNR 4.16, 23/25 subjects) and in the 1-, 2- and 3-talker conditions; the 5-talker
condition reaches the low tier. The validator scores one talker, whose response shrinks as talkers are added.

## Caveats
- The earphone's electrical artefact appears at about -0.8 ms; averaging normal and inverted trials (sub-07 on)
  cancels it.
- sub-01 to 06 have no inverted trials.

Details: `notes.md`.
