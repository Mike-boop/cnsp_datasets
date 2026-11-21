# libribrain100: notes

Findings that explain `adaptor.py`. Review scripts and results: `tmp/review/libribrain100/`,
`tmp/review/scripts/meg/` (2026-11-21).

## TODO
- **Sherlock8 stimuli**: the release has no `Sherlock8/stimuli/` (no audio, no README); its MEG is standardised
  without a stimulus. When the LibriBrain authors release the Sherlock8 audio (check the HF repo
  `pnpl/LibriBrain2` after the 2026 competition embargo ends), add it like Sherlock1-7/9 and re-standardise.
- **Sherlock1 sub-13 to sub-32**: only the first half (sub-13-22) or first quarter (sub-23-32) of each session is
  released (competition embargo; the BIDS raw data of sub-1-32 is embargoed too). Re-download when the rest is out;
  raw FIF for sub-1-32 would then replace the preprocessed h5.

## 1. Source
- Hugging Face `pnpl/LibriBrain` (Sherlock1-7, the 2025 competition release) and `pnpl/LibriBrain2` (Sherlock1
  multi-subject, Sherlock8, Sherlock9, TIMIT, MOCHA-TIMIT, TheMoth); together "LibriBrain100". CC BY-NC 4.0.
- Papers: Özdogan et al. 2025, LibriBrain (NeurIPS Datasets & Benchmarks, arXiv 2506.02098); LibriBrain100
  (2026, huggingface.co/papers/2608.25204). Code: github.com/neural-processing-lab/pnpl.
- Registry: one entry for both repos; files are stored as `LibriBrain/...` and `LibriBrain2/...`. Excluded: the
  serialised h5 and `derivatives/preproc` of everything that has raw FIF (duplicates of the raw data). Kept: the
  serialised h5 of LibriBrain2 Sherlock1 (sub-1 to sub-32), whose raw data is not released.

## 2. Layout and tasks
- BIDS per task folder: `<task>/sub-0/ses-<n>/meg/sub-0_ses-<n>_task-<task>_run-<r>[_split-<k>]_meg.fif`,
  `<task>/derivatives/events/*_events.tsv`, `<task>/stimuli/...`.
- Raw FIF only for **sub-0** (one participant): Sherlock1-9 (one chapter per session), TIMIT, MOCHA-TIMIT, TheMoth.
- LibriBrain2 Sherlock1: sub-1-32, sessions 11 and 12 (chapters 11 and 12) as preprocessed h5 only
  (`derivatives/serialised/` sub-1-12, `derivatives/serialised_competition/` sub-13-32 `desc-firsthalf` /
  `desc-firstquarter`). Standardised from the h5 (user's decision 2026-11-21: if only preprocessed data exists,
  standardise that).

## 3. Stimuli
| task | audio in the release | adaptor |
|---|---|---|
| Sherlock1-7, 9 | LibriVox chapters, `stimuli/audio/*.wav` (LibriBrain: 22.05 kHz int16; Sherlock9: 44.1 kHz) | rebuilt as played (sections 4-5) |
| Sherlock8 | none | MEG + words/phones TextGrid, no audio (TODO above) |
| MOCHA-TIMIT | 921 sentence wavs | placed at their onsets |
| TIMIT | not redistributed (LDC licence) | MEG + words/phones TextGrid, no audio |
| TheMoth | not redistributed (copyright) | rebuilt from OpenNeuro ds003020 (section 5) |

- Which wav a session played is established by content, not by number or duration (section 5): durations alone
  are ambiguous, and Sherlock3 has 9 wavs for 12 sessions.
- Events (`derivatives/events`): `kind` = word / phoneme / silence (/ nonspeech for TheMoth), `timemeg` (s from the
  start of the recording, i.e. after `first_samp`), `timeds` (same at 250 Hz, within 2 ms), `timechapter` /
  `timepodcast` / `timesentence` (time in the source audio). The BIDS `events.tsv` next to the FIF are copies.

## 4. How the audio was played (Sherlock, all tasks with segments)
- The chapters were split into sentence/phrase segments (voice activity detection + manual review, stimuli README)
  and played one after another. `timemeg - timechapter` is constant within a segment and steps up by 6-24 ms
  (median 12 ms) at each of the ~375 segments of Sherlock1 ses-1, so a session drifts 3.5-7 s behind the chapter
  timeline. The chapter wav is therefore **not** the stimulus as heard.
- Trigger `STI101` value 20 marks each segment start (within 3 ms of the events' segment boundaries; 188 x 20 and
  188 x 21 in ses-1, plus 10/30/40/50 once or twice). No audio channel is recorded, so timing rests on these
  (software) triggers as used by the authors' events.
- The adaptor rebuilds the played audio per session: each segment (source span from its first event to the next
  segment's first event) is placed at its `timemeg`, with zeros in the gaps. The stimulus is named per subject and
  session because the gaps differ between sessions.

## 5. Sherlock wavs vs the events: wavmap.py / wavmap.csv
- Content match (`wavmap.py`, run on the sub-0 events of every Sherlock session): the 100 Hz log-energy envelope of each
  candidate wav, read on the `timechapter` axis, against the events' word mask; then 60 s windows every 30 s and a
  Theil-Sen line through the window lags give wav_time = k * timechapter + c and the range where the match holds.
- **The LibriBrain (2025) wavs are not on the events' time axis.** Sherlock9 (LibriBrain2) matches its
  same-numbered wav at r ~ 0.75 with lag 0.00-0.02 s throughout. Sherlock1-7 match their wavs only after rescaling:
  Sherlock1, 2, 4-7 by k = 44100/44000 (the wav is 0.227% longer than the chapter time), Sherlock3 by k = 44000/44100
  (shorter); with that, r ~ 0.72-0.79 and the window lags scatter 4-9 ms around the line (c = 0-20 ms, resolution
  10 ms). A 44.1 vs 44 kHz mix-up when the wavs were made, presumably.
- Which clock the audio was played on: regressing the MEG interval between segment starts on the `timechapter`
  interval gives slopes of -400 to +400 ppm (not +2270 ppm) plus a constant 12-16 ms gap per segment (1-3 ms in
  Sherlock9), so the played audio followed `timechapter`; the adaptor resamples each wav by k (polyphase 440/441)
  before cutting the segments.
- Breaks: the match holds over the whole session in 89 of 106 sessions (incl. LibriBrain2 Sherlock1 ch 11-12). It
  breaks part-way in Sherlock4 ses-2 (at 930 s of 2617 s) and ses-9 (1350/2611), Sherlock6 ses-3 (2040/3645) and
  ses-10 (1620/2551): after the break the lag runs off at ~1% (Sherlock4 ses-2 loses the match entirely after
  ~1700 s). Sherlock3 matches its wav k for k = 1-9 (r ~ 0.6 over the first 300 s) but the lag wanders non-linearly
  (-0.05 to -3.8 s over 2500 s, ses-3), so only the first 90-210 s pass. No wav matches Sherlock3 ses-10-12
  (stories 10-12 are not in the release), Sherlock4 ses-8 and Sherlock6 ses-14.
- The adaptor splits a session at the break: trial 1 = the verified part with audio, trial 2 (`_part-2`) = the rest
  with MEG and TextGrid only; verified stretches under 60 s are not split off (Sherlock3: whole sessions without
  audio). Sessions without a match have no audio. A per-segment (piecewise) alignment could recover Sherlock3 and
  the post-break parts; not done.

## 6. TheMoth audio from OpenNeuro ds003020
- The 30 stories are among the 84 stories of LeBel et al. 2023 (OpenNeuro ds003020 v4.0.0, `stimuli/<story>.wav`,
  44.1 kHz; `derivatives/TextGrids/<story>.TextGrid`), same story ids.
- Check (`moth_match.py`, results `tmp/review/libribrain100/moth_match.csv`): LibriBrain `timepodcast` word onsets vs
  the ds003020 TextGrid word onsets, per story: almost all words matched (e.g. 1387/1388), median offset -25 to
  +8 ms (mostly within +-12 ms), scale -47 to +21 ppm, per-word scatter (median |residual|) 12-21 ms, as expected
  between two forced aligners. Story lengths agree (wav 0.2-17 s longer than the last LibriBrain word). So
  `timepodcast` is ds003020 wav time to within ~10 ms; the presented audio is rebuilt from these wavs as in
  section 4. Residual constant offsets of a few ms per story cannot be excluded by word alignment.
- Download: registry entry `libribrain100_moth` (the 30 wavs) into `<libribrain100 download>/ds003020`.

## 7. Neural data
- MEGIN (Elekta) 306 channels (102 magnetometers, 204 planar gradiometers), 1000 Hz, 0.03-330 Hz online; EOG001-002,
  ECG003, EMG004, STI101, 11 IAS (internal active shielding) channels and SYS201. Continuous HPI. Head shape
  digitised. Raw data: no SSS/MaxFilter applied; the calibration files are in `LibriBrain/metadata/neo/`.
- h5 (sub-1-32): float32 (306, n) in T and T/m at 250 Hz after the authors' bads + head position + SSS + notch +
  0.1-125 Hz band-pass; `times` starts at 0 = recording start, so `timemeg` applies directly. No sensor geometry in
  the file: channel positions and coil types are taken from a sub-0 raw FIF (same scanner); the device-to-head
  transform is not available.
- Raw FIF splits: many sessions are stored as BIDS splits (`_split-01`, `_split-02`, ...). MNE 1.9 fails to follow
  them ("'PosixPath' object has no attribute 'split'"), and a split read alone reports the whole recording (reading
  past its own buffers returns filler), so the adaptor reads each split, crops it to its own buffers and joins them
  (Sherlock3 ses-1: 28000-1684000, 1684000-3340000, 3340000-3448000 -> 3420 s). Some sessions also hold a plain
  `_meg.fif`: the first part of an MNE-style split whose continuation (`_meg-1.fif`) was not released (identical to
  split-01 where checked); it is used only when there are no splits.
- Kept channels: MEG, EOG, ECG, EMG (IAS shielding, SYS201 and STI101 dropped).

## 8. Checks
- The rebuilt audio against its own TextGrid (`libribrain_rebuild_check.py`, 60 s windows): lags within +-30 ms
  (10 ms resolution), r 0.63-0.83 (Sherlock1 sub-0 ses-1 and sub-1 ses-11, MOCHA-TIMIT ses-1).
- Word-onset evoked field (`libribrain_wordERF.py`, sub-0 Sherlock1 ses-1 raw, 2836 words, gradiometers 1-20 Hz): GFP
  peaks at 195 ms (and ~320 ms), about twice the random-onset maximum: `timemeg` is on the MEG clock.

## 9. Upstream issues
- Sherlock1 sub-0 ses-11: the BIDS `*_events.tsv`, `*_channels.tsv` and `*_meg.json` are 0-byte files on Hugging Face,
  and the folder holds `sub-0_ses-1_coordsystem.json` (session 1's name). The events exist in
  `derivatives/events/` as `run-2`, while the raw FIF is `run-1`.
- Sherlock8 has no stimuli.
- LibriBrain (2025) wavs are 44.1/44 kHz rescaled relative to the events (section 5); Sherlock3 does not match
  linearly; stories 10-12 of Sherlock3 and the wavs of Sherlock4 ses-8 and Sherlock6 ses-14 are missing.
- Raw FIF: plain `_meg.fif` files that are the first part of an MNE split without its continuation, next to the
  BIDS splits (section 7).
