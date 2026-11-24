# gao2024: echoic speech (MEGIN TRIUX neo MEG, 100 Hz)

MEG of 48 native Chinese speakers (19-33 years, right-handed; paper) listening to a Chinese story ("Thatched
Memories" by Cao Wenxuan, ~39 min, three ~13 min segments in story order), each segment presented anechoic or with
an echo, in three experiments:
- **Experiment 1** (15 participants): anechoic, 0.125-s echo, 0.25-s echo (echo as loud as the direct sound);
- **Experiment 2** (12): the same delays with the echo 6 dB above the direct sound (direct sound at half amplitude);
- **Experiment 3** (21 of 24; the authors excluded 3 whose onset trigger was missing): an echo whose delay varies
  between 0.125 and 0.25 s at every pause > 500 ms, once attended (story questions) and, in a second block during
  a silent subtitled movie, once as is and once noise-vocoded (1 channel).

- **Source:** Zenodo 10472483, doi:10.5281/zenodo.10472483. **Licence CC BY 4.0.** Registry entry `gao2024`
  (the figure results `Fig*_data.mat`, figure scripts and `tools.zip` are not downloaded).
- **Paper:** Gao J, Chen H, Fang M, Ding N (2024). Original speech and its echo are segregated and separately
  processed in the human brain. *PLoS Biol* 22(2):e3002498. doi:10.1371/journal.pbio.3002498

## Size
**48 participants, 3888 trials (27 story chunks of 11-34 s per segment, 81 per participant), 31.3 h in total;
0.652 h per participant** (all complete). Each condition is one segment, ~13 min (0.216-0.220 h) per participant:
exp1 3 x 15, exp2 3 x 12, exp3 3 x 21 participants.

## What is provided
- **MEG:** the authors' preprocessed data, the only MEG shipped: MEGIN TRIUX neo, 102 magnetometers (`mag`, T) and
  204 planar gradiometers (`grad`, T/m), **tSSS-cleaned and downsampled to 100 Hz by the authors**; not
  band-passed (the paper's 0.8-10 Hz filter is not applied to the shipped data). Channel names are assigned in
  Neuromag order (`MEG0111` mag, `MEG0112`/`MEG0113` grad, ...), as the authors' code indexes them; **no sensor
  positions** (no fif, no digitisation), and the order of the two gradiometers within a pair is assumed.
- **EOG:** one channel (`EOG`, direction unknown), cut from the authors' continuous EOG trace; missing for exp1
  sub13-15 and exp3 sub14, sub16.
- **Trials:** one per story chunk, cut by the authors from the chunk's start trigger for the length of the wav;
  the 0.2-5 s gaps between chunks are not in the data. Trial number = presentation order (1-81).
- **Subjects:** `100 x experiment + subject number` (exp2 sub3 = 203); the original numbers are in the sidecar
  (`experiment`, `participant`). Different experiments had different participants.
- **Conditions:** `exp1-anechoic`, `exp1-echo125`, `exp1-echo250`, `exp2-anechoic`, `exp2-echo125-6dB`,
  `exp2-echo250-6dB`, `exp3-echo-attend`, `exp3-echo-movie`, `exp3-vocoded-echo-movie`.
- **Stimuli** (`audio`, 48 kHz mono, shared across participants, uncut): the played sound first (`is_attended`,
  also in the movie conditions, where attention was on the movie: sidecar `task`), then its two components, the
  direct sound (`clean_<chunk>`, or `vocoded-clean_<chunk>`) and the echo (`delay125_`, `delay250_`, `vardelay_`,
  `vocoded-vardelay_`).
  The played sound is `clean_*` (anechoic), `echo125_*`/`echo250_*` (exp1), `echo125-6dB_*`/`echo250-6dB_*`
  (exp2: 0.5 x direct + echo; the `clean_*` component is stored at full amplitude, sidecar `direct_gain` 0.5),
  `varecho_*` or `vocoded-varecho_*` (exp3). Delays per pause-delimited stretch of exp3 are in the release
  (`echolist-*.mat`), not stored.
- Trial metadata (`raw.info["description"]`, JSON): `experiment`, `participant`, `segment`, `chunk`,
  `chunk_index`, `direct_gain`, `task` (listen / movie), `drift_ppm`, `drift_corrected`,
  `units_as_shipped`, `reference`, `validation_tier`.

## Alignment
**Grade: medium.** Onsets are the authors' start triggers (source not documented; the trigger durations agree with
the wavs to 1 ms), drift from the trigger durations, no correction from the neural data; validated at the low tier
with a plausible TRF and no response at negative lags.
- One start and one end trigger per chunk at 1 kHz; trial sample 0 = start trigger, as cut by the authors.
- **Clock drift +490 ppm**, from the triggers: over all 3888 chunks, (end - start trigger) - wav length =
  2.5 ms + 490 ppm x length, residual SD 1 ms. The MEG is resampled onto the audio clock (one interpolation; at
  most 17 ms, < 2 samples, at the end of a 34 s chunk). On by default; `drift_correction=False` keeps the samples
  as shipped. The same rate as other TRIUX systems (habersetzer2025: +485 ppm, measured on an audio copy).
- Headphone/tube delay unknown (not reported).
- Five first chunks of a session have a start trigger ~20-25 ms off (exp1 sub4 and exp3 sub16 ~25 ms early; exp3
  sub2, 7, 8 ~20 ms late); not corrected.

## Validation
**Low tier** (`validation_tier: low` in every trial; 100 Hz data, no higher tier possible). Forward model 0.5-8 Hz
on the played sound, 102 magnetometers, no re-referencing, all 48 participants: **median r 0.049 (mean 0.050),
48/48 participants significant**, p 0.02 (circular shift) and 0.048 (mismatch); `validation.json` (pooled).

| condition | n | median r | significant |
|---|---|---|---|
| exp1-anechoic | 15 | 0.045 | 15/15 |
| exp1-echo125 | 15 | 0.062 | 15/15 |
| exp1-echo250 | 15 | 0.063 | 15/15 |
| exp2-anechoic | 12 | 0.054 | 12/12 |
| exp2-echo125-6dB | 12 | 0.055 | 12/12 |
| exp2-echo250-6dB | 12 | 0.054 | 11/12 |
| exp3-echo-attend | 21 | 0.055 | 20/21 |
| exp3-echo-movie | 21 | 0.058 | 21/21 |
| exp3-vocoded-echo-movie | 21 | 0.033 | 19/21 |

- TRF (GFP) peaks at 172 ms in both anechoic conditions; the vocoded condition peaks at ~60 and ~270 ms.
- In the echo conditions, TRFs on the **played mixture** shift by about minus the echo delay; in exp2-echo250-6dB
  (echo louder than the direct sound) they peak at -110 to -180 ms. This is the echo, not a timing error: on the
  **direct-sound component** (`clean_*`) the TRF is flat at negative lags and rises from 0 ms (exp2, 12
  participants, notes.md section 10). Use the direct sound and the echo as separate regressors for latency work.
- The validator's per-trial jitter and drift estimates (11-34 s trials at 100 Hz) are at their noise floor and
  not informative.
- **Suitable for** low-frequency envelope tracking of echoic speech (direct vs echo streams), attention (attended
  vs movie) and vocoded speech. Not for latencies below ~10 ms or anything above 50 Hz (100 Hz data).

## Condition labels
The release does not document `order_sub`. It is read as "condition of segment s", which the design requires in
exp3 (the two movie conditions share one block, so they occupy adjacent segments). Checked against the authors'
own per-subject results: phase coherence recomputed per segment matches the authors' per-condition coherence
(Fig 2 and 3 data) for the assigned condition in 27/27 exp1/2 participants; in exp3 the vocoded envelope fits best
in the segment labelled vocoded in 21/21. Attended vs movie echoic speech in exp3 rests on the design only.

## Caveats
- Authors' preprocessing only: no raw MEG, no sensor positions, no head digitisation, 100 Hz (low-frequency
  analyses only).
- Gradiometer pair order within a triplet is assumed.
- The chunk gaps are missing, so continuous-segment analyses must concatenate trials.
- In exp2 the played sound has the direct part at half amplitude; build regressors from the played sound or scale
  `clean_*` by `direct_gain`.

Details: `notes.md`.
