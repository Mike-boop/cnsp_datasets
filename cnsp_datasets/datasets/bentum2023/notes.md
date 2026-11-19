# bentum2023 notes

Full review notes: `tmp/review/bentum2023/notes.md` (download, block construction, triggers, drift).

## Drift (corrected by the adaptor)
The EEG clock drifts ~33 ppm relative to the stimulus PC (per recording, IQR 28-37 ppm, from onset/end markers;
`drift.py`). The adaptor resamples each block to the audio clock.

## Timing offset (not corrected by the adaptor)
A match-mismatch DNN trained on accou2023 finds the bentum2023 neural response **~68 ms later** than accou2023's in
all three conditions (dialogue -68.8, news -65.4, story -70.9 ms; 95% CIs +-2-3 ms; subjects -83 .. -53 ms).
Clean-speech datasets aligned by stimtrack sit within +-5 ms of accou2023, and the offset is the same for every
condition, so a constant playback latency of the setup (sound card or audio buffer after the onset marker) is the
likely cause. There is no stimtrack to confirm it.

Users who need absolute timing can shift the EEG ~68 ms earlier relative to the stimulus. A future adaptor option
may estimate and apply such offsets (PLAN.md section 8). Evidence: `tmp/review/timing.md`, `tmp/review/dnn_offsets/`.

## Blocks rated "bad" or "doubtfull"
Included by default (from 2026-11-19). The authors excluded them from their analyses; pass
`exclude_usability=("doubtfull", "bad")` to skip them (103 bad, 198 doubtful blocks).

## Data size
48 participants, 4.33 h each (3.63-4.38), 207.8 h in total, 1617 blocks (all blocks incl. bad/doubtful; EEG from onset to end marker = the played audio). Per task per participant: news 1.49 h, story 1.37 h, dialogue 1.47 h. Three blocks end after their recording (pp002 and pp006 block 7, pp035 dialogue block 2) and are not counted.
