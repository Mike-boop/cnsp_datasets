# harshaiyahav2025: selective attention to an audiovisual lecture with a competing talker

EEG while attending a video lecture (front loudspeaker) and ignoring a competing audio-only lecture (left); the
roles of the two lectures swap at half-time. Hebrew.

- **Source:** OSF bzean (https://osf.io/bzean/), CND files. **Licence: unknown** (none on OSF; the article is CC BY
  4.0). Ask the authors before redistributing the data or anything derived from them.
- **Paper:** Har-shai Yahav P, Rabinovitch E, Korisky A, Vaknin Harel R, Bleichner M, Zion Golumbic E (2025).
  Neural speech tracking during selective attention: a spatially realistic audiovisual study. *eNeuro* 12(6).
  doi:10.1523/ENEURO.0132-24.2025
- **Code (authors):** none shared.

## Size
23 participants, 939 trials of 18-30 s (19 x 41, 4 x 40), **6.62 h in total, 17.3 min per participant
(16.9-17.4)**. Conditions `first_half` (457 trials, ~8.5 min per participant) and `second_half` (482, ~8.9 min).
The two talkers play simultaneously and are counted once. These are the shared durations: the authors cut the
first ~5 s of every trial and dropped the first trial.

## What is provided
- **EEG:** 64 scalp channels (BioSemi, recorded at 2048 Hz), **already preprocessed by the authors**:
  linked-mastoid reference, ICA, interpolated channels, 1-20 Hz, 100 Hz. Stored at 100 Hz (not upsampled).
  Mastoids, EOG, the microphone channel and triggers are not shared. Positions are `standard_1005` templates.
- **Stimuli:** only the authors' broadband envelopes at 100 Hz (feature `envelope`), cut to each trial:
  `L<l>s<k>` = target (attended) segment k of lecture l, `L<other>e<k>` = its non-target. Which lecture is the male
  or female talker is unknown. No audio, raw EEG, video, triggers or transcripts are public, so this dataset
  offers the envelopes only.
- Trial 22 (first trial after the switch) is kept, although the paper excluded it.

## Alignment
- No triggers or audio shipped; the authors' alignment is used as is (`alignment_method` `none`; trigger type
  unknown). EEG and envelopes start at the same sample, about 5 s after the target onset (inferred, not
  documented). Drift and jitter cannot be estimated.
- Trials are mapped to segments by envelope content (positions and `condIdxs` are unreliable, see notes).
- **Match-mismatch DNN offset** (classifier trained on accou2023): -15.6 ms pooled (-20.7 / -18.5 ms in the first
  / second half), i.e. responses later than in accou2023. Offsets of this size are typical of competing speech, so
  it is recorded as a note and not corrected. A constant cut error of a few tens of ms cannot be ruled out.

## Validation
**Low tier**, the highest reachable (100 Hz, 1-20 Hz, envelopes only; mlr and brainstem not applicable).
Average reference.
- **Forward** (envelope -> EEG, repo validator): attended median r 0.014, 12/23 subjects above both nulls
  (circular shift, mismatched trial); ignored 0.009, 8/23. Attended > ignored in 15/23 (p = 0.045). Other
  datasets' median low-tier r: 0.022-0.032.
- **Backward** (decoder, review script): attended median r 0.049 (23/23 > 0), ignored 0.031; **attended > ignored
  in 20/23 (p = 2.4e-4)**; attention decoding accuracy 0.70 per ~25 s trial (0.55-0.85, all 23 above 0.5). There
  is no null distribution for the backward model.
- **Lag sweep** (backward, 31 ms steps): peak at 0 s for both streams, overall and in both halves; 21/23 subjects
  peak within one step for the attended stream.
- The validator's per-trial jitter and drift estimates (SD ~280 ms; 730 +- 1320 ppm) are dominated by noise at
  these r values and say nothing about timing.
- Suitable for low-frequency envelope tracking and attention decoding. Not suitable for middle-latency or
  brainstem analyses, comparisons of absolute response latency with other datasets at the ~20 ms level, or speech
  features other than the envelope.

## Caveats
- Licence unknown (see above).
- Talker sex per lecture unknown.
- Undocumented trial counts: subjects 13, 14, 22 and 24 have 40 trials, each missing a different one. `condIdxs`
  is one entry short in 13, 14 and 24; halves and segments are taken from the envelope content instead.
- Trial 22 (post-switch) is in the data but excluded in the paper; drop it to match the paper's 40 trials.
- Weak subjects: 3, 4, 15, 16 and 23 fail both forward nulls (attended); 3, 7 and 12 have ignored >= attended in
  the backward model.

Details: `notes.md`.
