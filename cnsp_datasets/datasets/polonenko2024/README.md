# polonenko2024: peaky speech at three voice pitches

Subcortical EEG to 10 s clips of peaky speech, each read by a male or female narrator and pitch-shifted to a low,
mid or high fundamental frequency (f0). Recorded for auditory brainstem responses (ABRs) to continuous speech.

- **Source:** OpenNeuro ds005340 v1.0.4 (doi:10.18112/openneuro.ds005340.v1.0.4). Licence CC0.
- **Paper:** Polonenko MJ, Maddox RK (2024). Fundamental frequency predominantly drives talker differences in
  auditory brainstem responses to continuous speech. *JASA Express Lett.* 4(11):114401. doi:10.1121/10.0034329
- **Code (authors):** https://github.com/polonenkolab/peaky_pitchshift

## Size
15 participants, 720 speech trials each (10 s): **30.0 h in total, 2.00 h per participant**. Six conditions
(`male-f0low`, `male-f0mid`, `male-f0high`, `female-f0low`, `female-f0mid`, `female-f0high`; f0 123/150/183 Hz),
0.33 h per participant each. The 90 click trials per participant are left out.

## What is provided
- **EEG:** 2 channels, `A1` and `A2` = FCz minus the left / right earlobe (EP-PreAmp, bipolar). Recorded at
  10 kHz; stored at **1000 Hz** by default (`sfreq=None` keeps 10 kHz). Channels as recorded; do not
  average-reference them (that would cancel the common FCz signal).
- **Stimuli** (48 kHz, one per file, shared across participants):
  - `audio`: the waveform as played (diotic);
  - `pulses`: the glottal pulse train (uint8), the authors' regressor;
  - `anm` (optional, `save_anm=True`): the authors' auditory-nerve-model regressor, two polarities.
- No transcripts or word alignments.

## Alignment
- Sound-card triggers (expyfun): sample-locked to the audio, no software jitter.
- Onset = start marker + 0.81 ms (ER-2 tube delay), so time 0 is sound at the eardrum.
- Clock drift of 25 ppm (all subjects) is measured from the start/end markers of every trial and corrected
  (default on).
- The stimulus mapping was checked against the trial IDs stamped in the triggers: 0 mismatches in 12,150 trials.

## Validation
**Brainstem tier**, overall and in every condition. Overall: brainstem SNR 5.57 (15/15 subjects significant),
middle-latency SNR 3.83, low-frequency r 0.064. Brainstem SNR falls with f0, as in the paper.

## Caveats
- The 30-250 Hz response contains the earphone's electrical artefact at about -0.8 ms (the sound leaves the
  transducer before reaching the eardrum). No polarity alternation was used, so it cannot be averaged out;
  exclude lags around 0 ms or use the pulse-train regressor.
- Every participant hears all 720 files once, in random order.

Details: `notes.md`.
