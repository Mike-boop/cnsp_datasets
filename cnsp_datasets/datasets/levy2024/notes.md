# levy2024: attention to a virtual teacher with distractor sound-events in a VR classroom (OSF svjqg)

49 adults (24 AD(H)D, 25 control) x 30 mini-lessons (30.6-52.0 s, one male Hebrew talker), BioSemi 64-ch EEG +
3 EOG + 2 mastoids + GSR at 1024 Hz. Shared as FieldTrip structures per subject: **EEG unfiltered (DC, BioSemi
208 Hz anti-alias only), re-referenced to the mastoid average, cut into 30 lesson trials**, plus the authors'
**speech envelope at 100 Hz** per trial and the onsets/types of the distractor sound-events. **No audio, no
event-sound files, no Status/trigger channel, no continuous recording.** Two subjects (13, 22) have trial labels
that contradict each other (section 3).

Scripts used for these notes (not in the repo; `tmp/` is deleted later):
`/data_storage/gu08wuvu/datasets/tmp/review/levy2024/scripts/` (`inspect*.py`, `summarise.py` -> `work/summary.json`
+ `work/envelopes.npz`, `analyse*.py`, `check_events.py`, `envelope_props.py`, `decode_check.py`,
`decode_idx_sweep.py`, `chanlocs.py`).

## 1. Source
- OSF project svjqg (https://osf.io/svjqg/), category "data", created 2025-02-11, modified 2025-04-03.
  Description: "EEG and GSR data from the paper: https://doi.org/10.7554/eLife.103235.1". 49 files
  `dataSub1.mat` .. `dataSub49.mat` (579-661 MB each, ~30.4 GB) in osfstorage, nothing else. One child component
  py43u "Visualization of the VR classroom" with `VR Classroom Video.mp4` (27 MB; not downloaded). No linked
  nodes, no add-ons (checked via the OSF API, 2026-11-22).
- OSF wiki (home): overview only (title, authors, contact elana.zion-golumbic@biu.ac.il, 22/8 trials, "Data
  Format: .mat files (MATLAB)"). It says "participants with (25) and without (24) ADHD"; the files and the paper
  say 24 AD(H)D and 25 control (section 5). No description of the data structure.
- **Licence: unknown.** The OSF node has no licence (`node_license: null`). The paper is CC BY 4.0 (article only).
- Paper: Levy O, Libman Hackmon S, Zvilichovsky Y, Korisky A, Bidet-Caulet A, Schweitzer JB, Zion Golumbic E.
  Selective attention and sensitivity to auditory disturbances in a virtually real classroom. *eLife* 13:RP103235
  (2024/2025), doi:10.7554/eLife.103235. Data availability: "Video examples of the VR classroom and the entire
  dataset are publicly available on OSF: https://osf.io/svjqg. Please contact authors for additional information
  on data structure." Dataset citation: Levy O, Zion Golumbic E (2025), OSF svjqg.
- Related: Levy, Korisky, Zvilichovsky, Zion Golumbic (2025) J Cogn Neurosci 37:300-316 (same VR platform,
  different study).
- **No shared code** (no GitHub link in the paper or on OSF). Original BDFs were
  `EEGdata_s_classroom_<N>.bdf` (`hdr.orig.FILE`), recorded 2022-05-09 .. 2022-07-xx (`hdr.orig.T0`).

## 2. Layout
`dataSub<N>.mat` (MATLAB 5.0, `scipy.io.loadmat` works; ~1.5 GB RAM per subject as float64), top-level structs:
- `eeg.data`: FieldTrip raw structure (`ft_preprocessing` output with `cfg.trl`):
  - `trial` {1 x 30} of [71 x n] float64, `time` {1 x 30} (each starts at 0.0), `fsample` = 1024, `label` (71),
    `sampleinfo` [30 x 2] (1-based samples in the original BDF), `trialinfo` [30] = trigger code 101-130.
  - `hdr`: full BDF header of the original 88-channel file (`hdr.orig`: PhysDim, PreFilt, Transducer, T0, ...).
  - `cfg`: `reref = 'yes'`, `refchannel = {EXG5, EXG6}`, `refmethod = 'avg'`; `hpfilter`, `lpfilter`, `bpfilter`,
    `dftfilter`, `detrend`, `demean` all `'no'`; `cfg.trl` = [sampleinfo, offset 0, code]; `cfg.previous` empty.
    Identical in all 49 files.
- `eeg.fs` = 1024; `eeg.chanlocs` (64, EEGLAB struct, template positions on a unit sphere, identical in all
  subjects; labels 'T7 (T3)', 'Iz (inion)', 'Afz', 'T8 (T4)' differ in spelling from `eeg.data.label`, same order).
- `eeg.trlEvents` {104 x 4} cell = FieldTrip trl of the sound-event ERP epochs: [begin, end, offset = -103,
  type], 615 samples each (-100..+500 ms), type 'Artificial' or 'Cough' (52 each). Event onset = begin + 103.
- `stim`: `data` {1 x 30} envelope vectors, `fs` = 100, `names` = 'Envelope', `stimIdxs` [30] (lesson id
  1-30), `condIdxs` [30] (0/1), `condNames` = {'0 - Without Events', '1 - Without Events'} (**typo: 1 = with
  events**; 1 <=> the trial has sound-events in every subject, 1075 trials, 0 <=> none, 391 trials).
- `participant.group`: 'ADHD' or 'Control'.
- Trials are in recording order (`sampleinfo` increasing). The recording itself (incl. the ~30-90 s question
  periods between lessons and the training trials before the first lesson) is not shared.

## 3. Stimulus <-> trial mapping
- 30 lessons, same audio for all subjects. Lesson identity = `stimIdxs` (= `trialinfo` - 100 in 47 subjects).
  Lesson order differs per subject (43 distinct orders over 49 subjects).
- Verified: per lesson the shipped envelope is bit-identical across all subjects (MD5 of the vector, one hash per
  lesson), and in the 47 consistent subjects the EEG trial length is the same to the sample for each lesson
  (30 distinct lengths, so length identifies the lesson).
- **Condition is fixed per lesson in the shipped data**: lessons 1-22 = Events, 23-30 = Quiet, in every subject;
  the event schedule (onset times and types) is also identical across subjects per lesson. The paper says "The
  order of mini-lecture presentation and their allocation to the Events or Quiet condition was randomized across
  participants"; the order is randomised, the allocation is not (as shipped).
- Events per Events-lesson: 5 in 18 lessons, 4 in lessons 2 and 21, 3 in lessons 7 and 10 (104 per subject; the
  paper says "5 ... per trial" and 104 in total, which is the same count). Event onsets 0.98-35.99 s after trial
  start. Side (left/right) and identity of each event sound (110 sounds) are **not** in the files.
- Missing trials (undocumented): sub 9 lacks lesson 3; sub 17 lacks lessons 1 and 30; sub 34 lacks lesson 1
  (their event tables lack the matching events: 99 events). 1466 trials in total.
- **Subjects 13 and 22: trigger code and trial length disagree with stimIdx, envelope, condition and event
  schedule.** In both, `trialinfo` - 100 != `stimIdxs` in 28-30 of 30 trials. The EEG trial length always matches
  the lesson given by the code (e.g. sub 13 trial 0: code 115, n = 45796 = lesson 15), while the envelope
  (`stim.data`, lesson by `stimIdxs`), `condIdxs` and the event schedule in `trlEvents` all match `stimIdxs`:
  for every trial of subs 13 and 22 the event schedule (onset seconds and types) equals that of the **stimIdx**
  lesson in the other 47 subjects, and the quiet trials are exactly stimIdx 23-30 (`analyse3.py`). The event
  table is not independent evidence, though (event onsets are computed from a schedule, section 6), so the
  decisive check is the EEG itself. Backward model (as in section 6) with the envelope chosen by stimIdx vs by
  code (both zero-padded/cut to the EEG trial): sub 13 mean r = 0.032 (stimIdx) vs -0.003 (code), stimIdx better
  in 24/30 trials (Wilcoxon p = 0.0007); sub 22 0.036 vs 0.011, 19/30 trials (p = 0.04); mismatched-lesson
  nulls -0.014..+0.008; for comparison subs 1-4 reach 0.026-0.057 (`decode_check.py`, `decode_idx_sweep.py`).
  So **stimIdx is the lesson that was played**, and the codes (and the trial lengths the authors derived from
  them) are wrong in these two subjects. The trial *start* seems right (the stimIdx-envelope sweep in sub 13 is
  flat around 0, r = 0.032 at 0 vs 0.034 at its peak), but this is weak evidence.
  Consequence: in subs 13/22 the EEG trial is cut with the length of the wrong lesson, so it is too short
  (speech truncated) or too long (post-lesson silence/questions included) by up to 16.9 s. Recommended: use
  `stimIdxs` as the lesson id and the shipped envelope, keep the EEG as cut, and let the shorter signal set the
  usable length; flag both subjects (open question 1).

## 4. Speech features available
- Only the authors' speech envelope at 100 Hz (`stim.data`): broadband envelope from a narrow-band cochlear
  filterbank, |Hilbert| per band, averaged, downsampled to 100 Hz (paper, "Speech tracking response"); the paper
  then z-scores it (shipped values are not z-scored: 0..2.02, mean 0.43, 0.4 % small negative values from
  resampling). Spectrum (lesson-pooled Welch, re 4 Hz): +4 dB at 1 Hz, -6 dB at 8 Hz, -17 dB at 20 Hz, -28 dB at
  40 Hz, -35 dB at 49 Hz; no high-pass.
- Envelope length = EEG trial length at 100 Hz (`nenv` = floor or round of n/10.24), i.e. cut to the trial.
  Speech energy starts within 0.01-0.22 s of the envelope start and ends 0.07-0.47 s before its end, so the
  envelope (and the trial) starts at speech onset, consistent with the paper ("segmented into trials from the
  onset of the teacher's speech").
- **Speech only**: the event-locked average of the envelope around the 104 event onsets of sub 1 shows no bump
  (z ~1.0-1.2 throughout, same as random times), so the distractor sounds are not in it. The paper's TRF used a
  second regressor (envelope of the sound-events), which is not shipped. The participant heard the mixture
  (speech spatialised to the teacher's lips by Unity 3D audio, events from a student to the left or right at
  "50 % ... (-3 dB SPL)" of the speech level, Etymotic ER1-14 in-ear phones).
- **No raw audio** of the lessons or the event sounds, no transcripts, no word/phoneme annotations, anywhere
  public (OSF has only the 49 .mat files and the video; the paper has no further availability statement and no
  code). The lessons come from "existing informational podcast[s]"; event sounds from freesfx.co.uk,
  findsounds.com, freesound.org and IADS-E (Audacity-normalised to -5 dB peak, trimmed to 300 ms).

## 5. Neural data
- BioSemi ActiveTwo, 64 scalp channels (10-20 BioSemi 64 layout) + EXG1-8 + GSR1-2 + aux, 1024 Hz, BDF
  PreFilt "HP: DC; LP: 208 Hz" (scalp/EXG). Shipped 71 channels: 64 scalp, EXG1, EXG3, EXG4, EXG5, EXG6, GSR1,
  GSR2 (EXG2, EXG7, EXG8, Erg, Resp, Plet, Temp, Ana1-8 and Status dropped). Same list in all 49 files; no NaN or
  flat channels.
- Paper: three EOG electrodes "above the right eye and on the external side of both eyes"; linked mastoids.
  Inferred mapping: EXG5/EXG6 = mastoids (`cfg.refchannel`), EXG1/EXG3/EXG4 = EOG (which is which: unknown;
  EXG1 has the largest variance). EXG2's role is unknown.
- **Units as shipped: µV** (BDF PhysDim 'uV', FieldTrip default scaling). DC offsets of up to ~27 mV remain (no
  high-pass); per-trial SD 25-100 µV in sub 1.
- **Reference as shipped: average of EXG5 and EXG6** (EXG5 + EXG6 = 0 to 4e-12 after re-referencing). Raw
  (CMS) data are not recoverable. FieldTrip applied the reference to all 71 channels, so **GSR1/GSR2 (BDF unit
  nS) also had the mastoid mean (µV) subtracted** (inferred from FieldTrip behaviour; sub 30 GSR1 is
  negative, -1888..-1251, impossible for a conductance). GSR is not needed here, but should not be passed on as
  nS without that caveat.
- Preprocessing in the paper (0.5-40 Hz, ICA, interpolation) is **not** applied to the shipped data.
- Head-shape digitisation: none; `chanlocs` are template positions.
- Participants: 49 (paper: 54 recorded, 5 excluded). `participant.group`: ADHD = 13, 18-20, 22, 24-27, 29, 30,
  32-38, 40, 41, 44, 47-49 (24); Control = 1-12, 14-17, 21, 23, 28, 31, 39, 42, 43, 45, 46 (25). Age, sex, ASRS
  not shipped.
- Data size (recorded = stimulus, since trials are cut to the lesson length): 1466 trials, **17.42 h total;
  0.356 h per participant (mean; min 0.332, max 0.357)**; full set of 30 lessons = 1283.4 s (mean 42.78 s,
  SD 5.10 s; paper 42.7 +- 5.1). Events condition 12.68 h (0.259 h/participant, 0.248-0.268), Quiet 4.74 h
  (0.097, 0.085-0.097). Subs 13/22 counted with their shipped EEG lengths.

## 6. Alignment
- **Triggers:** only what the authors derived from the Status channel survives: trial start sample
  (`sampleinfo[:,0]`, "onset of the teacher's speech") with code 100 + lesson, and the event onsets. No end
  trigger: the trial end is start + lesson length (same sample count in every subject), so the trial length is
  not a measurement.
- Hardware vs software: **unknown**. The paper says only that GSR was "sampled by the BioSemi system, and thus
  synchronized to EEG data"; nothing on how Unity sent markers (parallel port, LSL, serial) or on audio-output
  latency. Unity audio output usually lags a script-side marker by tens of ms (buffering); not measured here.
- **Event onsets are computed, not recorded** (inferred): within each trial the event onsets are exact multiples
  of 1024 samples apart (all 82 within-trial gaps in subs 1 and 13), i.e. integer seconds from a common
  reference. That reference sits -17.6 .. +5.9 ms from the trial start (per trial; median -16.6 ms, 92 % between
  -17 and -14 ms, a few near 0/+5 ms). So the speech-onset marker and the event-schedule reference are two
  different time bases that differ by ~15 ms with ~2 ms SD; which one (if either) is the audio onset is unknown.
- **Stimtrack:** none (no audio channel was recorded or it was dropped; `Ana1-8` not shipped).
- **Proposed alignment:** take the trial start as the speech onset (as the authors did), envelope sample 0 = EEG
  sample 0, no drift correction. Verify a global offset with the low-tier lag sweep; preliminary
  (`decode_check.py`, backward model 1-8 Hz, 64 ch average reference, lags 0-250 ms, leave-one-trial-out,
  shifts +-600 ms in 20 ms steps, no artefact rejection, no ICA): subs 1-4 give mean r = 0.055, 0.057, 0.048,
  0.026 at zero shift (mismatched-lesson nulls -0.028..+0.036, i.e. weak and noisy on raw data), sweep peaks at
  0, +40, +20, -80 ms (positive = envelope delayed vs the trial start). The curves are flat-topped (~-80..+80 ms
  within 10 % of the peak), so the pooled peak (+20 ms) only bounds a constant offset to roughly +-50 ms; it is
  consistent with zero or with a few tens of ms of audio-output latency. The validator's pooled lag sweep over
  all subjects (forward TRF, finer steps) should decide whether a global shift is needed; nothing is applied
  until then.
- Drift: not measurable (no end trigger, no stimtrack, no audio). Over <= 52 s trials, 30 ppm would be 1.6 ms,
  irrelevant for the low tier.
- **Validation tiers possible:** the EEG bandwidth is not the limit (unfiltered, 1024 Hz, 208 Hz anti-alias),
  the stimulus is. With the shipped 100 Hz envelope only `low` (0.5-8 Hz) can be tested; `mlr` (30-60 Hz) is
  beyond its 50 Hz Nyquist and its content is -28 dB at 40 Hz; `brainstem` needs the audio. With the audio,
  `mlr` would become testable; `brainstem` would also depend on the unknown audio-onset jitter of Unity playback.
- Per condition: Events and Quiet trials come from the same Unity scene and trial code; no reason to expect a
  condition-specific offset, but the Quiet condition (8 trials, ~5 min per subject) is too short for a
  per-subject estimate; pool across subjects.

## 7. Cross-subject duration check
- Trial lengths per lesson are identical to the sample across the 47 consistent subjects (they are lesson
  lengths, not measured intervals), so the drift + jitter fit cannot be done: residuals are exactly zero by
  construction. Subs 13/22 deviate by -16.2 .. +16.9 s (wrong lesson, section 3).
- The only timing spread visible is the per-trial offset between the trial-start marker and the event-schedule
  reference (section 6): SD 1.9 ms, range 23.5 ms over 1075 Events trials. Not an estimate of audio-onset jitter.

| quantity | value |
|---|---|
| lessons | 30 (lessons 1-22 Events, 23-30 Quiet) |
| lesson length | 30.58-52.01 s, identical across subjects |
| trigger-derived duration - stimulus duration | 0 by construction (47 subjects) |
| drift (ppm) | not estimable |
| jitter | not estimable (marker-to-schedule offset SD 1.9 ms) |

## 8. Open questions
1. **Subjects 13 and 22** (codes/lengths vs stimIdx/envelope/events disagree). Recommended default: trust
   `stimIdxs` (envelope, condition and event schedule agree, decoding agrees with p = 0.0007 / 0.04,
   section 3), keep the EEG as cut,
   use the shorter of EEG and envelope, flag in `notes`. Alternative: exclude both subjects. Ask the authors.
2. **Stimuli**: without the lesson audio only the authors' 100 Hz speech envelope can be offered, and only the
   `low` tier can be validated (mlr needs 30-60 Hz content, brainstem needs audio). Adapt now with the envelope
   as the only feature (licence permitting), or wait for the audio? Recommended: ask the authors first (draft
   below), decide after the reply.
3. **Licence** unknown (none on OSF). Needs the authors' confirmation before redistribution.
4. Mixture vs speech: the distractor sounds (300 ms, 3-5 per Events trial) are not in the envelope and cannot be
   reconstructed (sound identity and side not shipped). Recommended: speech envelope as the stimulus, event
   onsets/types as annotations; mark Events trials as "speech + distractors".
5. Reference: shipped mastoid reference vs average reference for the standard format (PLAN: validate with
   average). Recommended: ship as recorded-reference data (mastoid average, documented) and let the validator
   re-reference.
6. Channels: keep EXG1/3/4 (EOG) and EXG5/6 (mastoids, now antisymmetric and redundant) and GSR? Recommended:
   keep EOG as `eog`, drop EXG5/6 (carry no information after re-referencing) or keep one, drop GSR or keep it
   as `misc` with the unit caveat.
7. Offset of audio vs trial-start marker (Unity latency) unknown; the preliminary low-tier lag sweep bounds it
   only to roughly +-50 ms (peak +20 ms pooled over 4 subjects). Recommended default: no shift; apply one only if
   the validator's pooled sweep over all subjects shows a clear non-zero peak. Ask the authors whether audio
   latency was measured.
8. Missing trials (subs 9, 17, 34) are undocumented; recommended: keep the remaining trials, list them in the
   README.

### Draft request to the authors (not sent)
> Dear Dr Zion Golumbic, dear Orel Levy,
>
> We would like to include your VR-classroom EEG dataset (OSF svjqg, eLife 2024 RP103235) in an open collection
> of standardised speech-EEG datasets (with full citation). Could you help with a few points?
> 1. Could you share the audio of the 30 mini-lessons as presented (and, if possible, the 110 event sounds with the
>    per-trial sound identity and side)? The OSF files contain the 100 Hz speech envelopes only.
> 2. Under which licence may the OSF data be redistributed (e.g. CC BY 4.0)?
> 3. How were triggers sent from Unity to the BioSemi (parallel port, LSL, ...), and was the delay between the
>    speech-onset trigger and the actual sound output measured?
> 4. In dataSub13 and dataSub22, `eeg.data.trialinfo` (trigger code) and the trial lengths do not match
>    `stim.stimIdxs` / `stim.data` / the event schedule (they do in all other subjects). Which lesson was played in
>    each trial? Would the raw BDF (with the Status channel) for these two subjects be available?
> 5. (minor) `stim.condNames` reads '1 - Without Events' for condition 1; and the OSF wiki gives 25 ADHD / 24
>    controls, while the files and the paper have 24 / 25.
>
> Many thanks and best regards,

## Upstream issues
- `stim.condNames{2}` = '1 - Without Events' (should be "With Events").
- OSF wiki: "with (25) and without (24) ADHD" vs files/paper 24 AD(H)D, 25 control.
- Subs 13 and 22: `trialinfo` and trial lengths inconsistent with `stimIdxs`/envelopes/events (section 3).
- GSR channels re-referenced together with the EEG (inferred).
- Paper says the Events/Quiet allocation was randomised across participants; in the shipped data it is fixed per
  lesson.

## User decisions (2026-11-22)
- Adapt now with the shipped 100 Hz speech envelope only (low tier only); licence unknown, flagged in the README;
  update if the authors provide audio later (the drafted request is not sent by us).
- Subjects 13 and 22: keep them; pair each EEG trial with the lesson from `stimIdxs` (which the EEG matches), use the
  shorter of EEG/envelope, flag the trigger-code/trial-length contradiction in the sidecar.
- Other open questions follow the recommended defaults in this file.

## Standardiser findings (2026-11-22)
- **Correction to section 3 (sub 13 event schedule).** Re-running `analyse3.py` on `work/summary.json`: in sub 22
  every Events trial's event schedule matches its stimIdx lesson, but in **sub 13 only positions 20-30 do**. In
  positions 1-19 the 14 Events trials carry the schedule of another Events lesson (by position: 15, 14, -, 16, 13,
  17, -, 18, 12, -, 19, 11|20, 20|11, -, 10, 21, -, 9, 22), which matches neither the stimIdx nor the trigger-code
  lesson (except positions 1-2, where it equals the code lesson). Quiet trials (stimIdx 23-30) have no events in
  both subjects. The stimIdx pairing rests on the envelope, `condIdxs` and the decoding (stimIdx beats code, 24/30
  trials); the decoding did not test the event-schedule lesson for positions 1-19, so it is open which lesson was
  played there. The adaptor keeps the shipped event annotations and flags positions 1-19 of sub 13 as unreliable
  (`EVENTS_UNRELIABLE`).
- Subs 13/22: EEG trials longer than the stimIdx lesson (`LESSON_SAMPLES`, the exact sample count of the lesson in
  the 47 consistent subjects) are cropped to it; shorter ones are kept (the envelope is never cut). Events that
  fall after the crop are dropped from the annotations (`n_events_cropped` in the sidecar; sub 13 position 2).
- GSR1/GSR2 are dropped (mastoid mean in µV subtracted from a conductance in nS; not usable as shipped).

## Subject 13 trials 1-19: third labelling check (2026-11-22)
The trlEvents schedule of sub 13 trials 1-19 matches neither stimIdx nor the trigger code (see "Standardiser
findings"). A label-independent cross-subject backward decoder (trained on subjects 1-8) ranks the stimIdx envelope
12.9/30 (r 0.019), trigger code 15.2 (r 0.006), events lesson 17.6 (r -0.005, chance); stimIdx > events in 11/14
trials (p = 0.057). Per-trial decoding cannot identify lessons (control sub 9: top-1 in 1/29). Decision unchanged:
pair by stimIdx; sub 13 trials 1-19 distractor annotations flagged "do not trust". The earlier "24/30, p = 0.0007"
used a decoder trained on the subject's own stimIdx labels and is not confirmed for trials 1-19. Trigger code ==
stimIdx: sub 13 1/30 (trial 6), sub 22 0/30. Details: tmp/review/levy2024/work/decide13.{json,log}.

## 9. Adaptor (implemented with the user decisions above)
- Reads `dataSub<N>.mat` (`scipy.io.loadmat`): `stim` + `participant` for the trial list (small), `eeg` only on load
  (~1.5 GB per subject, cached for one subject at a time).
- Trials: one per shipped trial, `trial` = position in recording order (1-30, or fewer for subs 9, 17, 34; missing
  lessons kept missing and listed per trial in `missing_lessons`). Lesson = `stimIdxs` (section 3, user decision);
  condition `events` if `condIdxs` = 1 else `quiet`. Checked per trial: condition must equal "lesson <= 22" and the
  envelope length must match the lesson length (`LESSON_SAMPLES`, the exact EEG sample count per lesson in the 47
  consistent subjects) to within 1 sample at 100 Hz; otherwise the adaptor raises. In consistent subjects the EEG
  length must equal `LESSON_SAMPLES` exactly.
- Stimulus: `audio` record `lesson<NN>`, feature `envelope`, the shipped 100 Hz envelope as is (not z-scored, never
  cut), attended.
- EEG: 64 scalp (`eeg`) + `EXG1`, `EXG3`, `EXG4` (`eog`) at 1024 Hz, µV -> V, `biosemi64` template montage, reference
  as shipped (mastoid average). Dropped: `EXG5`/`EXG6` (the reference, antisymmetric after re-referencing) and
  `GSR1`/`GSR2` (re-referenced conductance, section 5). No filtering, no detrending (DC offsets remain).
- Subs 13/22 (`subject_trigger_codes_inconsistent`): EEG longer than the `stimIdxs` lesson is cropped to
  `LESSON_SAMPLES`; shorter EEG is kept (envelope longer; cut at use, stimulus-length convention).
- Annotations: `distractor_artificial` / `distractor_cough`, onset = `trlEvents` begin + 103 - trial start, duration
  0.3 s; events outside the shipped trial are ignored, events after a crop dropped (`n_events_cropped`).
- Sidecar (`provenance`): alignment_method `onset_only`, trigger_type "unknown (not documented; Unity to BioSemi
  marker at speech onset, trials cut by the authors)", notes (+ conflict note for subs 13/22, + "do not trust" note
  for sub 13 trials 1-19 with events), and `group`, `lesson`, `missing_lessons`, `events_unreliable`, `trigger_code`
  (shipped `trialinfo`), `trigger_code_conflict` (per trial: code - 100 != lesson), `subject_trigger_codes_inconsistent`,
  `bdf_sample_start`, `n_samples_shipped`, `n_samples`, `n_events_cropped`, `reference`, `eog`, `dropped`,
  `units_as_shipped` ("uV"), `positions` ("template (biosemi64)").
- No drift correction (not estimable, section 7), no offset applied (sections 10, 12).

## 10. Validation (2026-11-22; `/data_storage/gu08wuvu/datasets/tmp/review/levy2024/validation/`, copy in `validation.json`)
- Tier **`low`** in `events` and `quiet`, all 1466 trials. `mlr`/`brainstem` not run: only the 100 Hz envelope
  (Nyquist 50 Hz, -28 dB at 40 Hz), no audio.
- Backward decoder (review script; 64 ch, average reference, EOG excluded; per trial demean + linear detrend before
  resampling, needed because of the DC offsets; 0.5-8 Hz, 64 Hz, lags 0-250 ms, ridge 0.1 x mean eigenvalue,
  leave-one-trial-out; nulls: 50 circular shifts >= 5 s and the 29 other lessons; pass = population p_circ and
  p_mismatch < 0.05 and |fixed sweep peak| <= 15.6 ms):

  | decoder (training set) | mean r | median r | subjects above both nulls | fixed sweep peak |
  |---|---|---|---|---|
  | pooled (30 trials) | 0.119 | 0.123 | 49/49 | -0.7 ms [-1.7, +0.3] |
  | pooled, `events` trials | 0.117 | 0.120 | 49/49 | -0.3 ms |
  | pooled, `quiet` trials | 0.125 | 0.123 | 49/49 | -1.6 ms |
  | `events` only (22) | 0.109 | 0.112 | 49/49 | -0.9 ms |
  | `quiet` only (8) | 0.088 | 0.089 | 40/49 | -1.2 ms |

  `quiet`-only failures (8 training trials): 3, 4, 5, 9, 22, 35, 46, 47, 48. Excluding subs 13/22: pooled 0.122,
  47/47.
- Refit lag sweep (pooled): peak -18.9 ms [-31.5, +2.0], plateau within 10% over ±94 ms. Same code on weissbart2019
  (stimtrack-aligned, 13 subjects, mean r 0.200): -48.3 ms. Difference levy - weissbart = **+29 ms [-13, +58]**
  (`global_offset_estimate`): no significant constant offset; channel count, feature (authors' envelope vs Hilbert
  envelope) and population differ, so this is an estimate, not a calibration. No shift applied.
- Forward TRF (128 Hz, 1-15 Hz, lags -200..600 ms, FC mean Fz Cz F3 F4 C3 C4, average reference): grand P1 46.5 ms,
  N1 102.4 ms, P2 164.9 ms (GFP peak 165 ms); `events` 46.6/102.6, `quiet` 46.3/101.9 ms. Same code: weissbart2019
  P1 30.4 / N1 87.6 ms, momenian2024 57.5 / 115.3 ms, herrmann2025 34.7 / 88.6 ms. levy2024 is +14-16 ms later than
  weissbart2019 (compare section 12).
- Subs 13/22: r 0.072 / 0.049 (ranks 44 and 49 of 49), both p_circ = p_mismatch = floor; fixed sweep peaks -11.3 /
  -0.1 ms. Sub 13 positions 1-19 vs 20-30: median r 0.094 vs 0.074 (Mann-Whitney p = 0.76): no sign of worse
  tracking in the trials with the unexplained event schedule.
- ADHD (24) vs Control (25), pooled decoder: mean r 0.111 vs 0.127, median 0.115 vs 0.133, Mann-Whitney p = 0.15
  (descriptive; paper's decoder p = 0.057, Events condition).
- Repo validator (forward model, `repo/`): all mean r 0.028 (median 0.026), 71% of subjects significant, tier `low`;
  `events` 0.026 (65%), `quiet` 0.025 (33%). TRF peak 172 ms. Its jitter/drift numbers (jitter SD 428 ms, drift
  -161 ppm, SE 848) are meaningless here (trial lengths fixed by construction). Sanity: 0 errors, no flat/NaN
  channels, 29 trials (subs 13/22) with |EEG - envelope duration| > 1 s (EEG shorter, up to 16.2 s).
- Figures: `figs/levy2024_backward.png`, `figs/levy2024_trf.png`, `figs/levy2024_groups.png`,
  `repo/{all,events,quiet}/validation.png`.

## 11. Coherence (2026-11-22; `/data_storage/gu08wuvu/datasets/tmp/review/levy2024/coherence/native/`)
Script `tmp/review/scripts/coherence_batch2.py` (Welch, 5 s Hann windows, 4 s overlap, 1 global circular-shift
surrogate; average reference; complex coherency averaged over each subject's trials, complex mean over subjects,
then |.| and channel mean). Run at 100 Hz, the envelope rate, so the 128 Hz and native runs coincide. Ratio to
surrogate:

| condition (trials) | 0.2-1 Hz | 1-4 Hz | 4-8 Hz | 8-15 Hz | 15-30 Hz |
|---|---|---|---|---|---|
| events (1075) | 5.65 | 3.15 | 3.18 | 1.68 | 1.17 |
| quiet (391) | 2.62 | 2.13 | 2.13 | 1.24 | 1.15 |

`quiet` has ~3x fewer trials, so its noise floor is higher and a lower ratio is expected; not evidence of weaker
tracking (the backward model gives the same r in both, section 10).

## 12. DNN offset (2026-11-22; `/data_storage/gu08wuvu/datasets/tmp/review/levy2024/dnn_offsets/`)
Match-mismatch classifier `fs128_1020-64_broadband` (trained on accou2023), lag scan ±500 ms, 5 s windows (1 s hop),
100 random trials per condition (45 subjects each), CI by subject bootstrap; script
`tmp/review/scripts/dnn_offsets_batch2.py`. Negative = neural data late relative to accou2023.

| data | offset | 95% CI |
|---|---|---|
| levy2024 `events` | -9.2 ms | -12.0 .. -6.4 |
| levy2024 `quiet` | -7.1 ms | -9.0 .. -4.9 |
| weissbart2019 (stimtrack) | +3.4 ms | +0.2 .. +8.3 |
| accou2023 (self-check) | +0.6 ms | -1.9 .. +2.9 |

levy2024 responses are ~10-12 ms later than weissbart2019, consistent with the TRF (P1/N1 +14-16 ms, section 10)
and within the refit-sweep bound (+29 ms [-13, +58]). Plausibly a small constant audio output latency of the
Unity/VR setup (Unity audio buffering; not measured, unverified); a population difference cannot be excluded.
Per-subject offsets are noisy (2-3 trials per subject). **User decision (2026-11-22, project-wide): constant DNN
offsets are documented, not applied**; the adaptor is unchanged and the README states the offset.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**medium**: Authors' trials at the Unity speech-onset marker, no stimtrack; DNN -9.2/-7.1 ms (vs weissbart +3.4) documented, possibly Unity output latency, unverified; low tier.

## Restructure 2026-11-25 (not yet re-validated on data)
- BaseAdaptor; sorted glob, and two files of one subject number now raise. Envelopes are float32 (were float64,
  same values up to float32 precision).
