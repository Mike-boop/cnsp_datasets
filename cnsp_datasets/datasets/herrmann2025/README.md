# herrmann2025: younger and older adults, stories in clear and in 12-talker babble

EEG while younger (18-34 years) and older adults (57-78) listen to short stories (~1.7 min), each either clear
or masked by 12-talker babble at one of 16 SNRs (57 to -6 dB). English.

- **Source:** OSF p8nxq (https://osf.io/p8nxq). No DOI. **Licence: unknown** (none set on OSF; the lab's
  read_me says "a Creative Commons license" without a version). Cite the paper; ask the author before
  redistributing the data or anything derived from them.
- **Paper:** Herrmann B (2025). Age-related differences in the impact of background noise on neural speech
  tracking. *Neurobiology of Aging* 153:10-20. doi:10.1016/j.neurobiolaging.2025.06.001
- **Code (authors):** none shared.

## Size
**34 participants (16 younger, 18 older), 584 trials of 91-136 s, 16.9 h in total, 0.50 h per participant**
(0.12-0.58 h; 22 participants have all 20 stories).
- `clear`: 124 trials, 3.6 h; 6.4 min per participant (1.7-7.8).
- `babble`: 460 trials, 13.3 h; 23.4 min per participant (1.8-28.2); 27-33 trials per SNR. The SNR (dB) is in
  the trial metadata (`snr_db`).

The OSF project has EEG for 52 participants (30 h), but only 146 of the 260 blocks have a log saying which story
was played at which SNR. Unlogged blocks (114) are left out: 18 participants have no log at all, among them na17
and na60, which are also missing from the demographics. Asking the author for the logs would add ~13 h.

## What is provided
- **EEG:** BioSemi ActiveTwo at 1024 Hz (stored unchanged), 16 scalp channels (10-20 names, `standard_1020`
  template positions) and `EXG1`/`EXG2` (left/right mastoid by BioSemi convention, unverified) as `misc`.
  Reference as recorded (CMS/DRL); the authors re-reference to the mastoid mean. No EOG, no stimtrack.
- **Stimuli** (`audio`, 44.1 kHz mono, as shipped, all at the same RMS):
  - `<Title>`: the clean story, marked as attended (every trial);
  - `<Title>_L<SNR>` (babble trials): the speech-babble mixture as played;
  - `<Title>_L<SNR>_babble` (babble trials): **derived**, mixture minus the least-squares scaled clean speech. The
    babble is not shipped; each wav has its own babble segment. It starts at wav sample 0, the speech after
    0.3-0.4 s of silence.
- Transcripts and comprehension questions exist on OSF but are not included (no word timings).
- Trial metadata (`raw.info["description"]`, JSON): story, wav, SNR, block, age group, age, sex, pure-tone
  average (0.5-4 kHz, both ears), `weak_tracking` flag and `validation_tier` (see below).

## Alignment
- One Status marker per story (rising edge 254 -> 255); onset = marker (`sw_trigger`). Whether the marker is
  hardware- or software-timed is not documented; inferred software (MATLAB/Psychtoolbox).
- No end markers and no stimtrack: drift and jitter cannot be measured and are not corrected. At a typical
  25-35 ppm clock drift, the error would be <= 5 ms over the longest story (an estimate, not measured).
- **The marker is the sound onset to within a few ms** (indirect evidence, no correction applied):
  - Clear-speech TRF (fronto-central, 1-15 Hz): P1 34.7 ms, N1 88.6 ms. Stimtrack-aligned weissbart2019 in the
    same code and on the same 16 channels: P1 34.8 ms, N1 88.9 ms.
  - Match-mismatch DNN offset vs accou2023 (positive = responses earlier than in accou2023): clear +4.9 ms
    (95% CI 2.1 to 7.9), babble 23-57 dB +5.0 ms (1.5 to 8.6), babble 2-19 dB +2.8 ms (-0.4 to 5.6). At -6 and
    -1.8 dB the lag scan has two peaks (near 0 and ~+125 ms), so no offset can be read there.
  - Backward-model lag sweep: best lag +0.6 ms overall (95% CI -0.7 to 2.0); 33/34 subjects within one sample
    (15.6 ms).
- Story and SNR per trial come from the authors' logs (timestamps tie each log to its recording). A
  leave-one-subject-out TRF confirms the logged story well above chance.

## Validation
**Middle-latency tier** overall, average reference over the 16 scalp channels, clean speech as the regressor.
The tier is set per trial in the metadata: `mlr` for clear and babble >= 15 dB (444 trials), `low` for babble
<= 10.8 dB (140 trials). The brainstem tier fails in every condition.
- **Forward, low tier** (0.5-8 Hz): median r 0.036, 27/34 subjects above the circular-shift null (26/34 above
  mismatched stories); clear 0.046, babble 0.032 (>= 40 dB 0.045, 15-36 dB 0.030, <= 10.8 dB 0.015). Other
  datasets in the same code: 0.024-0.035.
- **Backward** (decoder, review script, 0.5-8 Hz, 0-250 ms): median r 0.123, **34/34 subjects above both nulls**;
  clear 0.148, babble 0.113 (>= 40 dB 0.147, 15-36 dB 0.128, <= 10.8 dB 0.071). The mixture as regressor gives
  the same as the clean speech (babble 0.112 vs 0.109, babble-only decoders).
- **MLR** (30-60 Hz): SNR 1.31 (p 0.01), 11/34 subjects individually; TRF peaks at ~18, 28 and 39 ms, nothing
  at negative lags. By condition: clear 1.08 (p 0.04, 2/34), babble >= 40 dB 1.10 (p 0.01), 15-36 dB 1.17
  (p 0.02), <= 10.8 dB 0.94 (p 0.71, fails).
- **Low SNR (<= 10.8 dB):** the backward lag sweep peaks at +11.8 ms (95% CI 8.2 to 15.3) and the TRF N1 at
  98.3 ms (clear 88.6 ms). A later response in noise and a timing error cannot be told apart.
- **Coherence** (EEG vs clean-speech envelope, average reference, 5 s windows): above the surrogate up to
  ~10-12 Hz, largest at delta/theta. Ratio to the surrogate below 8 Hz: clear 2.3-4.6, babble 2.6-4.1, falling
  to 1.3-1.7 at -6/-1.8 dB; 8-15 Hz 1.2-2.0. Nothing above the surrogate above 30 Hz in the channel mean.
- The validator's per-trial jitter and drift estimates (SD 241 ms; 94 +- 404 ppm) are dominated by noise and
  say nothing about timing.
- Suitable for low-frequency envelope tracking, effects of SNR and age, and middle-latency responses at
  SNR >= 15 dB. Not suitable for brainstem analyses (no stimtrack, software marker, 16 channels), and absolute
  latencies are only trustworthy to a few ms.

## Caveats
- Licence unknown (see above).
- `weak_tracking`: na10, na21, na55, na61, na64 and na65 showed no clear tracking in a leave-one-subject-out
  forward TRF before validation (cause unknown: weak responses or wrong logs). In the validation they track like
  the others: backward median r 0.116 vs 0.125 (all above both nulls; lower only at <= 10.8 dB), forward 5/6
  above the null. The flag is kept for transparency; there is no reason to exclude them.
- Unlogged blocks are not included (see Size). na17 and na60 (raw data on OSF, but not in the demographics; possibly
  participants who declined sharing) are not singled out; they have no logs and are left out for that reason.
- The EEG lasts as long as the story. The babble can mask the clean-speech envelope at low SNRs; use `<Title>`
  for speech tracking, as the paper does.
- Upstream issues (to report): missing logs for 114 blocks; no licence on OSF; story durations are 91-136 s, not
  1.5-2.5 min as in the paper.

Details: `notes.md`.
