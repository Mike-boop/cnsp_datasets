# broderick2019_cocktail: attention labels

**The attention labels come from this repository, not from the download.** The dataset's EEG Readme says subjects
1-17 attended "20000 Leagues Under the Sea" and 18-33 attended "Journey to the Centre of the Earth". That is wrong
for 16 of the 33 subjects. The correct labels are in the dataset's `Cocktail_Party_Read_Me_-_Correction.rtf`.
Older copies of the dataset may not include that file, so the adaptor hard-codes the corrected labels
(`ATTENDED_20000` / `ATTENDED_JOURNEY` in `adaptor.py`):

| attended story | ear | subjects |
|---|---|---|
| 20000 Leagues | left (`competing-fL`) | 3 6 7 8 9 10 13 15 17 18 19 21 24 25 27 31 32 |
| Journey | right (`competing-fR`) | 1 2 4 5 11 12 14 16 20 22 23 26 28 29 30 33 |

Relabelled subjects (Readme rule -> correction): 1 2 4 5 11 12 14 16 (Readme: 20000) and 18 19 21 24 25 27 31 32
(Readme: Journey).

**Data standardised before commit 2d21508 (2026-11-18) carries the Readme labels.** Re-standardise it, or swap the
attended and ignored story for the subjects listed above.

The EEG confirms the correction (0.5-8 Hz forward TRFs, all 33 subjects):
- With the corrected labels, the attended story is predicted better than the ignored one in 27 of 33 subjects.
  With the Readme labels this holds for only 21 of 33.
- Of the 16 relabelled subjects, 11 favour the correction.
- 1-8 Hz coherence is higher for the attended story in 24 of 33 subjects.

Other changes in the same commit:
- EEG and mastoids are converted from microvolts to volts.
- Envelopes are named `envelope`.

## Timing offset (not corrected by the adaptor)
A match-mismatch DNN trained on accou2023 finds the attended-story response **~45 ms later** than accou2023's
(-45.2 ms, 95% CI -57.2 .. -39.9; most subjects -70 .. -23 ms). broderick2019 natural speech (same lab, same
pipeline) is within +5 ms of accou2023, so this may be a real latency effect of attending in a competing-speaker
scene rather than an alignment error; the other competing-speaker datasets are smaller (etard2019 -8 / +1 ms,
jehn2025 normal-hearing -6 / -9 ms). Unresolved; not corrected. A future adaptor option may estimate and apply such
offsets (PLAN.md section 8). Evidence: `tmp/review/timing.md`, `tmp/review/dnn_offsets/`.

## Data size
33 participants, 0.33 h each (competing-fL 17, competing-fR 16 participants), 11 h in total. Estimated from the stimuli (tmp/review/data_size.md).

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**poor**: Same CND pipeline as natural; DNN -45 ms (CI -57..-40) documented, not applied; notes: maybe attention latency, 'unresolved'; low tier.

## Restructure 2026-11-25 (not yet re-validated on data)
- BaseAdaptor. EEG through the shared `broderick2019_natural/cnd.read_eeg` (same values; mastoids M1/M2 when the
  file has `mastoids`, orientation decided by the channel count; see broderick2019_natural/notes.md).
- Word TextGrids through `iohelpers.textgrid` (long format, xmin 0, gaps filled, quotes escaped; overlapping words
  now raise).
