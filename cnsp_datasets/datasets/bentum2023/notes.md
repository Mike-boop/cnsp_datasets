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

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**poor**: Software onset/end markers (~17 ms grid); marker-based drift 33 ppm corrected (hardware-like, logs confirm); DNN offset -68 ms in all conditions documented, not applied, read as playback latency (timing error).

## Restructure 2026-11-25 (not yet re-validated on data)
- Corpus audio directories: `ifadv_dir` / `sdc_dir` arguments, else the paths `CNSP_IFADV_DIR` / `CNSP_CGN_DIR`
  (environment variable or `paths.json`, `cnsp_datasets.config.get_path`); the local `config.json` is no longer read.
  Skipped blocks are logged (were printed).
- TextGrid written by `iohelpers.textgrid` (was `broderick2019_natural.utils.multi_tier_dict_to_textgrid`): long
  text format, xmin 0 (was the earliest onset), gaps filled with empty intervals, quotes escaped. An interval that
  overlaps the previous one in its tier starts at the previous one's end (dropped if nothing is left; logged, as a
  warning above 20 ms); the old writer wrote overlaps as they were. Whether the XML has overlaps is not yet checked.
- Audio via `iohelpers.read_wav`: integers scaled by 32768 (was 32767); dialogue channels still mixed by the mean.
- Bad channels from `rejected_channels` are renamed like the channels (e.g. `FT10` -> `HEOG_right`) before being
  marked (an unknown name is logged); before, a renamed channel's bad flag was silently lost.
- `wav_index` raises if a corpus directory holds two wavs with the same name (was: the last one found won).
