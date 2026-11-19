# das2019 notes

## Timing offset (not corrected by the adaptor)
A match-mismatch DNN trained on accou2023 (`fs128_1020-64_broadband`, 5 s windows over stimulus lags of +-500 ms)
finds the das2019 neural response **~81 ms later** than accou2023's (-81.5 ms, 95% CI -84.9 .. -78.3; every one of
the 16 subjects between -103 and -67 ms). Clean-speech datasets aligned by stimtrack (weissbart2019, fuglsang2018,
broderick2019 natural) sit within +-5 ms of accou2023, so this is most likely an alignment offset in the release
(the EEG is shipped preprocessed at 128 Hz: a causal filter delay or an onset convention would fit), not a real
latency difference. Unverified: the release has no stimtrack or triggers to check it against.

Users who need absolute timing can shift the EEG ~80 ms earlier relative to the stimulus. A future adaptor option
may estimate and apply such offsets (PLAN.md section 8). Evidence: `tmp/review/timing.md`, `tmp/review/dnn_offsets/`.
