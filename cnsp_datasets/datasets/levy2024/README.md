# levy2024: attending a virtual teacher in a VR classroom, with and without distractor sounds (Hebrew, EEG)

EEG while adults with AD(H)D (24) and controls (25) attend 30 mini-lessons (30.6-52.0 s each, one male Hebrew
talker, from informational podcasts) given by a virtual teacher in a virtual-reality classroom (Unity, in-ear
phones). In 22 lessons (`events`) 3-5 distractor sounds of 300 ms (artificial noises or coughs, from a virtual
student to the left or right) are played; 8 lessons have none (`quiet`). Lesson order differs per participant.

> **No audio.** Only the authors' 100 Hz speech envelope is shared, so only the `low` tier (0.5-8 Hz envelope
> tracking) can be validated. The envelope is **speech only**: the distractor sounds that participants also heard
> in `events` lessons are not in it (their onsets and types are given as annotations). **Licence unknown.**

- **Source:** OSF project svjqg, https://osf.io/svjqg/ (49 `dataSub<N>.mat` files, ~30.4 GB). Dataset citation:
  Levy O, Zion Golumbic E (2025), OSF svjqg. **Licence: none stated.** The OSF node has no licence and the wiki
  says nothing about reuse, so redistributing derived data is **not confirmed to be allowed**. A request to the
  authors (licence, audio, trigger latency, subjects 13/22) is drafted in `notes.md`. It has **not been sent**.
  The paper itself is CC BY 4.0, but that covers the article only.
- **Paper:** Levy O, Libman Hackmon S, Zvilichovsky Y, Korisky A, Bidet-Caulet A, Schweitzer JB, Zion Golumbic E
  (2024). Selective attention and sensitivity to auditory disturbances in a virtually real classroom. *eLife*
  13:RP103235. doi:10.7554/eLife.103235 (reviewed preprint 2024, Version of Record 12 May 2025).
- **Code (authors):** none shared.

## Size
**49 participants, 1466 trials, 17.42 h in total, 0.356 h (21.3 min) per participant (range 0.332-0.357 h).**
- `events`: 1075 trials, 12.68 h, 0.259 h per participant (0.248-0.268);
- `quiet`: 391 trials, 4.74 h, 0.097 h per participant (0.085-0.097).

The same 30 lessons are used for every participant, and lessons 1-22 are always `events` and 23-30 always `quiet`
(the paper says the allocation was randomised, but in the shared data it is fixed per lesson). Missing upstream,
not documented: subject 9 lacks lesson 3, subject 17 lessons 1 and 30, subject 34 lesson 1. All other subjects
have 30 trials.

## What is provided
- **EEG:** BioSemi ActiveTwo, 64 scalp channels (BioSemi 64 layout) and 3 EOG (`EXG1`, `EXG3`, `EXG4`, type `eog`;
  above the right eye and at both outer canthi, but which channel is which is unknown). 1024 Hz, stored at
  **1024 Hz**, in V (shipped in µV). **As shipped by the authors: unfiltered (DC-coupled; BioSemi 208 Hz
  anti-alias filter only), with DC offsets of up to ~27 mV, and re-referenced to the average of the mastoids**
  (`EXG5`/`EXG6`). The mastoid channels are dropped because they carry no information after this re-referencing.
  The original CMS-referenced data cannot be recovered. **High-pass or detrend before use.** The paper's
  preprocessing (0.5-40 Hz, ICA, interpolation) has not been applied. **Template positions** (`biosemi64`); no
  digitisation.
- Dropped: `EXG5`/`EXG6` (the reference) and `GSR1`/`GSR2`. The authors' re-referencing also subtracted the mastoid
  mean (µV) from the skin conductance (nS), so the GSR is unusable as shipped. `EXG2`, `EXG7-8`, the auxiliary
  channels and the Status channel are not shared.
- **Stimulus** per trial: `lesson<NN>` (NN = 01-30), feature `envelope`, the authors' broadband speech envelope at
  **100 Hz** (narrow-band cochlear filterbank, |Hilbert| per band, averaged; not z-scored, no high-pass). It is
  bit-identical across subjects for each lesson. No audio, no event-sound files, no transcripts, no word or phoneme
  timings.
- **Annotations:** `distractor_artificial` / `distractor_cough` (onset, 0.3 s duration) in `events` trials. These
  are the authors' event onsets. They are computed from a schedule (whole seconds apart), not recorded, and their
  reference is ~15 ms (SD 1.9 ms) before the speech-onset marker. Their timing relative to the sound output is
  unknown. The side and identity of each event sound are not shared.
- Trial = position in recording order (1-30). Participant group (`ADHD` / `Control`) is in the sidecar. Age, sex
  and symptom scores are not shared. The OSF wiki gives the groups as 25 ADHD / 24 control. The files and the paper
  have **24 ADHD / 25 control**, and the files are followed here.
- Trial metadata (`raw.info["description"]`, JSON): `group`, `lesson`, `missing_lessons`, `events_unreliable`,
  `trigger_code`, `trigger_code_conflict`, `subject_trigger_codes_inconsistent`, `bdf_sample_start` (trial start in
  the original BDF), `n_samples_shipped`, `n_samples`, `n_events_cropped`, `reference`, `eog`, `dropped`,
  `units_as_shipped`, `positions`.

## Alignment
- **Onset only (`onset_only`).** The authors cut each trial from their speech-onset marker ("onset of the
  teacher's speech"; code 100 + lesson) to marker + lesson length, and cut the envelope to the same length.
  Envelope sample 0 = EEG sample 0, as the authors aligned them. There is no end trigger, no stimtrack and no
  continuous recording, so trial lengths are lesson lengths and not measurements.
- Trigger type: **unknown**. How Unity sent markers to the BioSemi, and the audio output latency, are not
  documented.
- Drift and jitter: **not estimable.** Trial lengths are identical across subjects by construction. At 30 ppm the
  drift over a 52 s lesson would be 1.6 ms (an estimate, not measured). The only visible timing spread is
  between the speech-onset marker and the reference of the distractor schedule: ~15 ms apart, SD 1.9 ms. This is
  not a measure of audio-onset jitter.
- **Constant offset (documented, not applied):** the match-mismatch DNN trained on accou2023 places the responses
  **7-9 ms later than accou2023** (`events` -9.2 ms, 95% CI -12.0 to -6.4; `quiet` -7.1 ms, -9.0 to -4.9). With the
  same method, weissbart2019 (stimtrack-aligned) gives +3.4 ms, so levy2024 is ~10-12 ms later than weissbart2019.
  The forward TRF agrees: P1/N1 are 14-16 ms later than weissbart2019 with the same code. A plausible cause is a
  small constant audio output latency of the Unity/VR setup, but this is unverified. A population difference cannot
  be ruled out. No shift is applied, following the project-wide rule that constant DNN offsets are documented, not
  corrected.

## Validation
**Low tier** in both conditions (`events`, `quiet`; all 1466 trials). The `mlr` and `brainstem` tiers cannot be
run: the 100 Hz envelope has nothing usable at 30-60 Hz (-28 dB at 40 Hz), and the brainstem tier needs the audio.
The EEG itself (1024 Hz, unfiltered) would not limit them.
- **Backward** (review script; ridge decoder, 64 channels, average reference, demeaned and linearly detrended per
  trial, 0.5-8 Hz, 64 Hz, lags 0-250 ms, leave-one-trial-out; circular-shift and mismatched-lesson nulls):
  decoder over all 30 trials, mean r **0.119** (median 0.123), all **49/49** subjects above both nulls. Split by
  condition: `events` 0.117 and `quiet` 0.125, 49/49 each. A decoder trained only on the 8 `quiet` trials is weaker
  (mean r 0.088) and fails in 9/49 subjects (3, 4, 5, 9, 22, 35, 46, 47, 48). A decoder trained only on `events`
  reaches 0.109 (49/49).
- **Lag sweep:** the fixed-decoder peak is at -0.7 ms (95% CI -1.7 to +0.3), and every subject is within one
  sample (15.6 ms). The refit sweep is flat-topped (within 10% of peak over ±94 ms), so it only bounds a constant
  offset. Compared with weissbart2019 run through the same code, levy2024 minus weissbart2019 is **+29 ms (95% CI
  -13 to +58)**, which is no significant offset.
- **Forward TRF** (envelope, 1-15 Hz, 128 Hz, frontocentral mean, average reference): **P1 46 ms, N1 102 ms, P2
  165 ms**. With the same code: weissbart2019 P1 30 / N1 88 ms, momenian2024 57 / 115 ms. P1/N1 in `events`
  and `quiet` agree within 1 ms.
- **Subjects 13 and 22** are the weakest (r 0.072 and 0.049, ranks 44 and 49 of 49) but significant. Excluding them
  changes nothing (mean r 0.122, 47/47).
- **Group:** ADHD vs control, mean r 0.111 vs 0.127 (median 0.115 vs 0.133), Mann-Whitney p = 0.15. This is
  descriptive only. The paper reports a similar trend for its decoder (p = 0.057).
- **Repo validator** (forward model): mean r 0.028 (median 0.026), 71% of subjects significant (`events` 65%,
  `quiet` 33%), tier `low`. Its jitter and drift estimates are not meaningful here, because trial lengths are
  fixed by construction.
- **Coherence** (EEG-envelope, at 100 Hz, ratio to a circular-shift surrogate):

  | condition (trials) | 0.2-1 Hz | 1-4 Hz | 4-8 Hz | 8-15 Hz |
  |---|---|---|---|---|
  | `events` (1075) | 5.6 | 3.1 | 3.2 | 1.7 |
  | `quiet` (391) | 2.6 | 2.1 | 2.1 | 1.2 |

  `quiet` has about a third as many trials, so a lower ratio is expected.
- **Suitable for:** low-frequency (≤ 8 Hz) envelope tracking and decoding, attention and distraction effects in a
  naturalistic setting, ADHD vs control comparisons, and ERPs to the distractor sounds (with the caveats below).
- **Not suitable for:** middle-latency or brainstem responses (no audio; trigger type and latency unknown),
  absolute latency comparisons at the ~10 ms level (unexplained ~7-9 ms offset), models of the full acoustic input
  in `events` trials (the distractor sounds are not in the envelope), analyses that need measured electrode
  positions, and GSR.

## Caveats
- **Licence unknown** (see above): check with the authors before redistributing anything derived from this
  dataset.
- **Unfiltered, DC-coupled, mastoid-referenced EEG**: high-pass or detrend each trial before analysis. The
  validation re-references to the average of the 64 scalp channels.
- **Subjects 13 and 22: contradictory trial labels.** In these two subjects the trigger codes (`trialinfo`)
  disagree with the authors' lesson index (`stimIdxs`) in 29 and 30 of 30 trials. The envelope, condition label and
  decoding agree with `stimIdxs`, so each trial is paired with the `stimIdxs` lesson. The authors cut the EEG with
  the length of the trigger-code lesson, so these trials are up to 16.9 s too short or too long. Trials that are
  too long are cropped to the lesson length. Trials that are too short are kept, and the envelope is longer than
  the EEG: **cut the envelope to the EEG at use** (29 trials differ by more than 1 s). The sidecar flags these
  trials (`subject_trigger_codes_inconsistent`, `trigger_code_conflict`, `n_samples_shipped` vs `n_samples`).
  Exclude both subjects if this matters.
- **Subject 13, trials 1-19: do not trust the distractor annotations** (`events_unreliable` = true). Their event
  schedule matches neither the `stimIdxs` lesson nor the trigger-code lesson. Speech tracking in these trials is
  as good as in trials 20-30 (median r 0.094 vs 0.074, p = 0.76), but which lesson was played there is not proven.
  Distractor events that fall after a crop are dropped (`n_events_cropped`).
- Missing lessons in subjects 9, 17 and 34 (see Size), listed in `missing_lessons`.
- **Template electrode positions** only. The EOG channel assignment is inferred.
- The ~7-9 ms DNN offset is documented but not applied (see Alignment).
- Upstream issues: `stim.condNames` labels condition 1 as "Without Events" (it is "with events"). The OSF wiki
  swaps the group sizes. The paper says Events/Quiet allocation was randomised, but it is fixed per lesson in the
  data. Subjects 13/22 have inconsistent labels. The GSR was re-referenced together with the EEG.
- Not shared upstream: audio and event sounds, the continuous recording (question periods, training trials), 5
  participants excluded by the authors (54 recorded), the eye-tracking data.

Details: `notes.md`.
