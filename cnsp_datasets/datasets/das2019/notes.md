# das2019 notes

## Data size
16 participants, ~1.3 h of EEG each (8 trials of ~6.5 min and 12 repeat trials of ~2 min per participant).

## Stimuli longer than the EEG (by convention)
The 12 `_rep` trials have ~124 s of EEG but carry the full ~6.5 min story track; trial 4 (fL dry) carries a 472 s
track against 399 s of EEG. Stimuli are not cut: the longer signal is cut where the data are used.

## Timing offset (not corrected by the adaptor)
A match-mismatch DNN trained on accou2023 (`fs128_1020-64_broadband`, 5 s windows over stimulus lags of +-500 ms)
finds the das2019 neural response **~81 ms later** than accou2023's (-81.5 ms, 95% CI -84.9 .. -78.3; every one of
the 16 subjects between -103 and -67 ms). Clean-speech datasets aligned by stimtrack (weissbart2019, fuglsang2018,
broderick2019 natural) sit within +-5 ms of accou2023, so this is most likely an alignment offset in the release
(the EEG is shipped preprocessed at 128 Hz: a causal filter delay or an onset convention would fit), not a real
latency difference. Unverified: the release has no stimtrack or triggers to check it against.

Users who need absolute timing can shift the EEG ~80 ms earlier relative to the stimulus. A future adaptor option
may estimate and apply such offsets (PLAN.md section 8). Evidence: `tmp/review/timing.md`, `tmp/review/dnn_offsets/`.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**poor**: Authors' 128 Hz preprocessed EEG, no triggers/stimtrack; DNN -81.5 ms in all 16 subj documented, not applied, read as an alignment offset in the release (timing error).
