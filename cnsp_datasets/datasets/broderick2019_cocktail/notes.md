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
