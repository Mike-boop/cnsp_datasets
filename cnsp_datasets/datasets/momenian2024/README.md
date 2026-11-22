# momenian2024: Le Petit Prince Hong Kong, older Cantonese listeners (EEG)

EEG while older adults (65-77 y) listen to *Le Petit Prince* in Cantonese, in four ~5-min Parts, each followed by
five yes/no comprehension questions. The story was played **one sentence at a time** (535 sentence wavs, one
trigger per sentence). The fMRI part of the dataset is not used.

- **Source:** OpenNeuro ds004718 v1.1.2, doi:10.18112/openneuro.ds004718.v1.1.2 (registry entry `momenian2024`;
  the EEG files are identical to v1.1.1, v1.1.2 adds the sentence wavs). **Licence: CC0.**
- **Paper:** Momenian M, Ma Z, Wu S, Wang C, Brennan J, Hale J, Meyer L, Li J (2024). Le Petit Prince Hong Kong
  (LPPHK): naturalistic fMRI and EEG data from older Cantonese speakers. *Scientific Data* 11:992.
  doi:10.1038/s41597-024-03745-8
- **Code (authors):** https://github.com/jixing-li/lpp_data (fMRI and acoustic features only; no EEG code).

## Size
**51 participants, 194 trials (one per Part) of 176.7-302.6 s, 15.81 h in total, 0.33 h per complete
participant.** Five raw files are cut short upstream, so HK019 has Parts 1-3, HK030, HK042 and HK045 Parts 1-2 and
HK044 Part 1 only; HK005 Part 1 stops after sentence 1.065 (1.067-1.070 were never played). HK031 has no EEG.
One condition (`clear`).

## What is provided
- **EEG:** Neuroscan (Curry) at 1000 Hz, stored unchanged in V. 62 scalp channels (10-20 layout incl. F11/F12,
  FT11/FT12, CB1/CB2), M1/M2 (mastoids, `misc`), VEO/HEO (`eog`), EKG (`ecg`, HK015, HK040-042) and EMG (`emg`,
  HK015). **Original reference, not documented** (probably near CZ/CPZ, the Neuroscan default; the BIDS
  `EEGReference: Average` is wrong). Template positions (`standard_1005`; none for F11, F12, FT11, FT12, CB1, CB2).
  Large DC offsets (DC or very low high-pass recording, not documented).
- **Stimuli** per participant and Part, `HK<id>_part<p>`:
  - `audio` (44.1 kHz): the Part's sentence wavs, each **placed at its own trigger** on a silent track, as mono
    (L+R)/2 of the stereo files. The track is therefore specific to the participant: the ~8.5 ms gaps between
    sentences (and five pauses of 0.12-0.92 s) are silence; where a trigger came before the previous sentence had
    ended (about 7 % of sentences, usually by 1-10 ms), the earlier sentence is cut there.
  - `textgrid`: tiers `words` (upstream word times placed at their sentence's trigger) and `sentences` (the placed
    sentence wavs, labelled by sentence id). No phone tier.
- Trial metadata (`raw.info["description"]`, JSON): Part, first/last sentence, first trigger sample, number of cut
  sentences and the largest cut, pauses, age, sex, EEG quiz accuracy, flags (`weak_tracking`,
  `fdt_truncated_upstream`, `bad_channels`, `quality`).

## Alignment
- `sw_trigger`, software triggers (inferred: STIM2, one per sentence; ~16 ms timer steps). The EEG is the
  continuous recording from the Part's first sentence trigger to the end of its last sentence; no samples are
  removed or repeated. Each sentence starts in the stimulus at its trigger, so trigger timing errors do not
  accumulate over a Part.
- Not used: the continuous run wavs of v1.1.1, which omit the inter-sentence gaps and drift 0.8-1.9 s behind the
  EEG by the end of each Part.
- No drift correction (within sentences ~117 ppm, under 1 ms per sentence). Sentence-onset jitter ~7 ms SD.
  Trigger-to-sound latency is unknown and assumed constant.
- Envelope-EEG cross-correlation (1-8 Hz, 100-s windows, 5 participants): one ridge at +0.20 s throughout every
  Part with the placed stimulus; with the plain concatenation it moves by up to ~1 s.

## Validation
**Low tier for all 194 trials** (average reference, 62 scalp channels); mlr and brainstem fail, as expected with
~7 ms software-trigger jitter per sentence.
- Forward (envelope -> EEG): median r 0.034, 37/50 subjects above the circular-shift and mismatch nulls; TRF peak
  0.19 s. Backward (leave-one-Part-out decoder): **median r 0.216, 50/50 subjects** above both nulls.
- mlr: mean SNR 1.00 (4/51 subjects); brainstem 0.98 (2/51).
- **TRF P1/N1 at 57.5/115.3 ms**, +23/+26 ms later than herrmann2025 and weissbart2019 with the same code
  (~35/89 ms). That matches the match-mismatch DNN offset (-21.2 ms). An unmeasured trigger-to-sound latency and
  the longer latencies of older listeners cannot be told apart; nothing is corrected.
- Envelope-EEG coherence relative to a global-shift surrogate: 5.3 (0.2-1 Hz), 3.8 (1-4 Hz), 5.1 (4-8 Hz),
  2.3 (8-15 Hz), 1.3 (15-30 Hz), ~1.05 above 30 Hz.
- Suitable for low-frequency envelope and word/sentence-level analyses. Not suitable for middle-latency or
  brainstem responses, or for absolute latency comparisons at the ~20 ms level.

## Caveats
- **Word timings are mostly interpolated** upstream: in most sentences all words but the last have equal
  durations, and words tile each sentence without pauses. Use them as approximate word positions, not as
  forced alignment. Five words with offset < onset are dropped; sentence ids 2.023/2.024 are mislabelled
  upstream (the words are placed by time, not by id).
- Sentence ids before the dot are story sections, not Parts (1.117-1.144 are in Part 2, 2.118-2.127 in Part 3).
- HK037 and HK042 show no clear speech tracking (flagged, kept).
- **HK050: T8 is faulty** (marked in `info["bads"]` in all four trials): ~3.4 mV of artefact for the first 85 s of
  Part 1, nearly flat afterwards. Exclude it before average-referencing; with it, Part 1 looks misaligned
  (spurious -0.44 s peak). Part 1 has `quality: "suspect: ..."` in its metadata; the alignment itself is fine.
- Five truncated raw files (missing Parts, see Size); the authors' 250 Hz derivatives are complete but are not
  used.

Details: `notes.md`.
