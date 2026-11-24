# rogachev2024: neural tracking of stories in children aged 3-8

EEG of 52 Russian-speaking children (3-8 years) listening to short stories told by one female speaker, while
watching muted, story-related videos.

- **Source:** OSF c3agw (https://osf.io/c3agw/, DOI 10.17605/OSF.IO/C3AGW), CND files. **Licence: none stated**
  on the OSF project.
- **Paper:** Rogachev A, Sysoeva O (2024). Neural tracking of natural speech in children in relation to their
  receptive speech abilities. *Cognitive Systems Research* 86, 101236. https://doi.org/10.1016/j.cogsys.2024.101236
- **Code (authors):** none shared. The release also holds each child's age, sex, PLS-5 receptive-speech score and
  the authors' TRF prediction accuracies (`TRF_*.csv`; not stored here).

## Size
52 children (`sub-<digits of the ID>`, e.g. `NP012301` -> `sub-12301`; the ID is in the provenance), 148 trials,
**10.9 h in total, 12.6 min per child** (7.9-13.5). One condition (`story`):
- 37 children heard the hedgehog story (`HG_audio`, 292 s), "Brick and Wax" (`BW_audio`, 182 s) and "The Golden
  Duck" (`GD_audio`, 338 s);
- 7 children (the first recruits) heard the wombat story (`WB_audio`, 301 s) instead of "The Golden Duck" (the
  paper says six);
- 8 children heard only `HG_audio` and `BW_audio`.

Presentation order is unknown; the trial number is the order in the release (HG, BW, GD/WB).

## What is provided
- **EEG: preprocessed by the authors, not raw.** 31 channels of a 32-channel actiCHamp at 500 Hz (as recorded;
  stored at 500 Hz). Preprocessing (MNE 1.5): zero-phase 1-15 Hz band-pass (-6 dB at 0.5 and 16.9 Hz),
  interpolation of bad channels (0-5 per child; which ones is not shared), removal of 1-3 ocular ICA components,
  **average reference** (FCz, the online reference, is not restored). Units scaled from µV to V. No EOG,
  mastoids, triggers or audio channel. `standard_1020` template positions; the channel order was checked against
  the correlation structure.
- **Stimuli:** the four story wavs as presented (44.1 kHz, stereo, silences > 500 ms removed by the authors),
  feature `audio`. The release also has the authors' 500 Hz envelope, manually labelled word onsets and word2vec
  semantic dissimilarity per story; they are not stored (the onsets carry no word labels, and semantic
  dissimilarity is model-derived), and the transcripts (`*_text.txt`) are in the download only.

## Alignment
- The authors cut each trial at a Presentation event marker sent at the start of each story, to the story's
  length (EEG sample 0 = wav sample 0). The markers are not shared and their path (software port code) was not
  verified against the sound (`alignment_method` `onset_only`, trigger `software`). Headphones: Panasonic
  RP-HS46E-K (no tube delay).
- Drift cannot be measured (no end marker; trials are cut to the stimulus length). A typical 20-50 ppm would be
  7-17 ms at the end of the longest story.
- **Alignment grade: medium.** The shipped timing is kept; the low tier passes with a TRF peak at 125 ms, nothing
  at negative lags, and per-trial lag-sweep offsets centred on 0 (median +2 ms) in children with significant
  tracking.

## Validation
**Low tier** (the highest testable: the data are low-passed at 15 Hz). Average reference, all 52 children.
- Forward model (envelope -> EEG, 0.5-8 Hz): mean r 0.038, median 0.043; 42/52 children above their
  circular-shift null; the population passes both nulls. The per-child scores reproduce the authors' published
  accuracies (Spearman 0.93).
- TRF peaks at ~125 and ~290 ms. Lag-sweep offsets per story (significant children): HG +9, BW +2, GD -3 ms.
- Suitable for delta/theta envelope tracking in children, e.g. in relation to age or language scores. Not suitable
  for anything above ~15 Hz, or for analyses that need the original reference or the raw signal.

## Caveats
- Preprocessed release: filtering, interpolation, ICA and the average reference cannot be undone.
- The seven wombat-story children track weakly in every story (also in the authors' results); they are among the
  youngest, and tracking grows with age in this sample.
- No licence stated.

Details: `notes.md`.
