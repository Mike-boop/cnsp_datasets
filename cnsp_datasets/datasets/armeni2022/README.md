# armeni2022: 10 hours of Sherlock Holmes per listener (MEG)

MEG of 3 native English speakers, each listening to *The Adventures of Sherlock Holmes* over 10 one-hour
sessions, with head casts to keep the head still.

- **Source:** Donders Repository, DSC_3011085.05_995_v1, doi:10.34973/5rpw-rn92. Access under the Donders data use
  agreement: you need a data.ru.nl account with the agreement accepted, and its WebDAV credentials in
  `RADBOUD_USERNAME` / `RADBOUD_PASSWORD` for the download (registry entry `armeni2022`; anatomy is not downloaded).
- **Paper:** Armeni K, Güçlü U, van Gerven M, Schoffelen JM (2022). A 10-hour within-participant
  magnetoencephalography narrative dataset to test models of language comprehension. *Sci Data* 9:278.
  doi:10.1038/s41597-022-01382-7
- **Acknowledge:** "Data were provided (in part) by the Donders Institute for Brain, Cognition and Behaviour,
  Radboud University Nijmegen".

## Size
3 participants: story parts **8.76 h per participant (26.3 h)**, plus the repeated 29 s "noise ceiling" passage
(1.06 h per participant, 3.2 h); 29.5 h in all, 593 trials.

## What is provided
- **MEG:** CTF-275, 269 axial gradiometers (MNE type `mag`, T) and 29 reference sensors (`ref_meg`); recorded at
  1200 Hz, stored at **1000 Hz** (`sfreq=None` keeps 1200 Hz). Plus `UADC003` (the recorded copy of the sound) and
  `UADC005`-`UADC007` (EyeLink gaze x, y and pupil diameter, on the MEG clock; `misc`). The eight EEG channels in the
  files carry no signal (floating or open inputs) and are dropped. Known unstable channels (sub-003 ses-004) are
  marked bad.
- **Stimuli** (22.05 kHz, shared across participants):
  - `audio`: the wav as shipped (`<session>_<part>` for story parts, `noise_ceiling` for the repeats);
  - `textgrid` (story parts): word and phone tiers from the authors' annotations, relative to the part's onset.
- **Conditions:** `story` (6-8 parts of 7-10 min per session) and `repeat` (the noise-ceiling passage, played twice
  after every part, for estimating the response reliability).

## Alignment
- The authors measured each part's playback delay on the audio channel (50-114 ms, varying) and corrected the onsets;
  checked here against `UADC003`: within +-1 ms (196 parts).
- **Clock drift** of +5.7 ppm (identical in all participants) is corrected in the same interpolation as the
  1200 -> 1000 Hz resampling (`drift_correction=False` turns it off).

## Validation
**Brainstem tier** (MEG: 30-250 Hz response at 28-45 ms), sessions 1-3 of each participant: low-frequency r 0.061
(3/3 significant), middle-latency SNR 2.57, 30-250 Hz SNR 3.03 (3/3).

## Caveats
- **Stimulus artefact at 0 ms:** the 30-250 Hz response contains a sharp spike at lag ~0 (the sound picked up by the
  sensors). It confirms the timing, but exclude lags around 0 in high-frequency analyses.
- sub-003 ses-001 part 1 is left out: the recording started after the audio.
- sub-003 ses-008: run 3 crashed and was restarted; the restart has no event in the release, so its onset was measured
  on the audio channel. That session's released word annotations are shifted by one part after the crash; the
  TextGrids here come from another participant (same wav, same timings).
- Short slow-drift artefacts in five runs (listed in the paper and `notes.md`); a high-pass at ~0.5 Hz removes them.
- Sound came through plastic tubes from a transducer; the acoustic delay is not reported and not corrected.
- The EyeLink's own files (`eyelink/*.asc`: blink and saccade events) are not carried; its gaze and pupil signals are,
  as the MEG channels `UADC005`-`UADC007`.

Details: `notes.md`.
