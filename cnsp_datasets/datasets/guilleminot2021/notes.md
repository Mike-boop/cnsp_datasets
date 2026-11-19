# guilleminot2021 notes

Audio-tactile speech in noise: 18 participants x 2 sessions x 16 story parts (576 trials), BrainVision EEG at 1 kHz
(63 scalp channels + misc `Sound`, `Diode`, `Button`). Each session's csv lists File, Type (audio / tactile /
audio-tactile), Delay (tactile relative to speech, ms) and Correlated.

## What was played (from the EEG `Sound` channel, which records speech and tactile)
- Each trial plays one 39062.5 Hz buffer: 1 s silence, the story part (`Odin_X.wav`), 1 s silence.
  `Stimuli/Odin_X_audio.npy` is the speech buffer, `Stimuli/Odin_X_phone_.npy` the zero-delay vibrotactile buffer
  (~100 Hz carrier).
- Audio-tactile: the tactile buffer starts `Delay` ms after the speech buffer (Sound-channel lags equal the csv
  within +-1 ms).
- **Mismatched trials (Correlated = 0, 71 trials): the trial's own tactile buffer circularly shifted by a quarter of
  its length** (`np.roll(x, len(x) // 4)`; the wrapped part matches too, r 0.95-0.99). This answers the earlier
  question about the incongruent tactile stimulus.

## Timing (`timing.py` -> `trial_timing.csv`)
- Buffer onset is 1-3 ms (mostly 2 ms) after the `R3` marker, except zartan session 2 row 0 (marker 2.39 s late).
- `timing.py` measures every onset from the Sound channel near its marker (567 trials), falls back to the marker
  + 2 ms where Sound is saturated (6), and flags trials it cannot use:
  - naga session 1 row 0: missing (recording started late);
  - naga session 1 row 13 and **session 2 row 8**: started during a recording pause (`New Segment` inside the trial,
    no marker), so the EEG before the pause belongs to a different time. This is why session 2 trial 8 looked
    missing;
  - yr session 1 row 12, elios session 1 row 14: run past the end of the recording.
  571 trials are standardised. The previous adaptor's hard-coded lists also dropped naga session 1 rows 14-15,
  which are fine, and cut zartan session 2 row 0 2.4 s early.
- Standardised check: Sound channel vs the standardised speech and tactile stimuli peaks at 0 ms lag.

## Standardised format
- Conditions: `A`, `T`, `AT_<delay>` (`m` = negative), `AT_mismatched`. Subjects 1-18 in `PARTICIPANTS` order.
- Stimuli: speech (`audio`: wav + TextGrid) and the vibrotactile signal as played (`tactile`, features `audio` and
  `textgrid`, on the wav's time axis and rate), named `Odin_X_delay_<d>` or `Odin_X_rolled_quarter`. The tactile
  TextGrid is the speech TextGrid moved to where its words fall in the tactile signal: shifted by the delay, or rolled
  by a quarter of the tactile buffer for mismatched trials (wrapping words split). Check: 97-98% of the mismatched
  tactile signal's energy falls inside the moved word intervals (~82% with the unmoved ones, i.e. chance).

## Open
- There is behavioural data associated with this dataset that is not included yet.
