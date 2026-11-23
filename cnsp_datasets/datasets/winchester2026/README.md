# winchester2026: uninstructed listening to two-voice polyphonic piano music (EEG)

EEG of 31 participants listening to 32 MIDI-synthesised classical piano pieces (50.6-166.4 s; mostly J.S. Bach).
Each piece was heard once, in one of these variants:
- **`Original`:** the two-voice piece.
- **`Inverted`:** the pitch-inverted piece.
- **Single voice:** one of the two voices alone (`<Original|Inverted>_Mono_<Left|Right>`).

Of the 40 participants recruited, 9 were excluded upstream for trigger problems. There are 991 trials (31 x 32 - 1).

- **Source:** OSF bjdh6 (https://osf.io/bjdh6/), CND files (registry entry `winchester2026`), 5.69 GB.
- **Licence: not stated** on OSF. The paper is CC BY 4.0, which covers the article only. This is an **open
  question**: whether the data, or anything derived from them, may be redistributed is unknown. Ask the authors
  before sharing.
- **Paper:** Winchester MM, Reynolds R, Nebo M, Scott IC, Di Liberto GM (2025/2026). eLife reviewed preprint
  RP108767 (v2). doi:10.7554/eLife.108767.2
- **Code (authors):** 8 MATLAB scripts on OSF (read, not run). The shared EEG is not preprocessed: their
  `preProcessCND.m` is not applied.

## Size
**31 participants, 26.15 h in total, 0.84 h per participant (0.79-0.85 h).** The EEG epochs total 31.2 h.
- **Per condition:**
  - `Original`: 8.44 h (0.27 h per participant, 0.14-0.42);
  - `Inverted`: 8.82 h (0.28, 0.14-0.44);
  - single voice (`Mono`, four variants): 8.89 h (0.29, 0.14-0.43).
- Durations are counted from the stimuli (`notes.md` section 9). `data_size.py` was not run because the standardised
  data had been deleted.
- The standardised output is 4.4 GB.

## What is provided
- **EEG:** mBrainTrain Smarting (wireless), 24 channels, raw (no filter, no re-reference). Units µV, scaled to V.
  - **Rates:** **native 250 Hz for subjects 1-5 and 16-19, 500 Hz for the other 22**, stored at the native rate.
    The paper says 250 Hz.
  - **Channels:** 22 scalp channels plus **M1/M2** (mastoids, `misc`). There are no EOG, ECG, stimulus or trigger
    channels.
  - **Reference:** not documented (the Smarting default is FCz; unverified).
  - **Positions:** template `standard_1020` positions.
  - **Line noise:** 50 Hz mains and, at 250 Hz, a 62.5 Hz line.
- **Bad channels:** sub4 C4, P3 and O2 (flat in every trial) are listed in `info['bads']`. Exclude them yourself.
- **Stimuli: no audio and no MIDI were shared.** Only the authors' 125 Hz features are available.
  - **Stored:** the Hilbert envelope of what was played (`is_attended`). For polyphonic trials the two voices'
    envelopes are stored too, as extra stimuli with the single-voice names. The envelopes are identical across
    subjects.
  - **"Left"/"Right" are the two voices, not ears.** Which one is the high voice is **unverified** (presumably Left
    = left hand = low voice in `Original`).
  - **Not stored:** note onsets, and the model-derived surprisal/entropy.
- **Trials:** epochs run from the stimulus onset to the next piece's onset (self-paced), and the last one to the end
  of the recording. They are kept as shipped, and the stimuli are not cut. `trial` = presentation position.

## Alignment
- **Software trigger** (Presentation to the wireless Smarting; the route is not stated). The authors cut the epochs
  at the onset trigger, and the triggers were not shared. Onset = epoch start, kept as shipped (`sw_trigger`).
- **Headphones:** Sennheiser HD 280 Pro, so there is no tube delay.
- **Drift and jitter:** cannot be measured (no end triggers, no audio copy). Not corrected (`drift_ppm` null).
- **Check:** the pooled per-trial best lag has a median of +1 ms, with nothing above the null at negative lags.
- **Alignment grade: medium.** The authors' epochs start at a software trigger (Presentation to Smarting), and there
  is no audio. The per-trial best lag is +1 ms, with nothing at negative lags. Low tier.

## Download and adaptor options
- `download_dataset("winchester2026", <dir>)` (OSF, no credentials).
- `Winchester2026Adaptor(download_dir)`. It has no options.

## Validation
**Low tier, all 31 subjects** (991 trials), average reference over 22 channels without bads.
- **Pooled:** mean r 0.023, 21/31 subjects significant. TRF peaks at ~70, 190 and 300 ms.
- **Per condition:** `Original` r 0.020 (10/31), `Inverted` 0.019 (11/31), `Mono` 0.020 (13/31). All pass at
  population level.
- **mlr and brainstem tiers cannot run**, because the stimuli are 125 Hz envelopes and 9 subjects are at 250 Hz.
- **Not run:** DNN timing check (the model is trained on speech).

**Suitable for** low-frequency envelope tracking of music, and polyphony or voice comparisons at the envelope level.
**Not suitable for** high-frequency or brainstem analyses, or any analysis that needs the audio or the note onsets.

## Caveats
- **Licence not stated** (see above).
- **sub5:** every channel is about 30-80x larger than in other subjects, with a ~5 Hz harmonic comb (r 0.007, not
  significant). It is probably a broken recording, and it is kept as shipped with nothing marked. Drop it if in
  doubt.
- **sub25:** an empty 33rd trial is skipped.
- **sub16:** the recording ends 3.4 s into position 31 (kept), and position 32 holds a single sample (skipped).
- **Sidecars:** the validated output (since deleted) was written before the adaptor's review edits. Its sidecars
  lacked `validation_tier` and had an extra `reference` field; the EEG and stimuli were identical. The current
  adaptor has not been re-run on the data.

Details: `notes.md`.
