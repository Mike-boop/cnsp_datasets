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
| Sherlock1-7, 9 | LibriVox chapters, `stimuli/audio/*.wav` (Sherlock1: 22.05 kHz int16) | rebuilt as played (section 4) |
| Sherlock8 | none | MEG only, `stimulus=[]` (TODO above) |
| MOCHA-TIMIT | 921 sentence wavs | placed at their onsets |
| TIMIT | not redistributed (LDC licence) | MEG only, `stimulus=[]` |
| TheMoth | not redistributed (copyright) | rebuilt from OpenNeuro ds003020 (section 5) |

- Session k of Sherlock1 is chapter k (session events end ~8 s before the chapter wav; checked for ses-1-10 and 12).
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

## 5. TheMoth audio from OpenNeuro ds003020
- The 30 stories are among the 84 stories of LeBel et al. 2023 (OpenNeuro ds003020 v4.0.0, `stimuli/<story>.wav`,
  44.1 kHz; `derivatives/TextGrids/<story>.TextGrid`), same story ids.
- Check (`moth_match.py`, results `tmp/review/libribrain100/moth_match.csv`): LibriBrain `timepodcast` word onsets vs
  the ds003020 TextGrid word onsets, per story: almost all words matched (e.g. 1387/1388), median offset -25 to
  +8 ms (mostly within +-12 ms), scale -47 to +21 ppm, per-word scatter (median |residual|) 12-21 ms, as expected
  between two forced aligners. Story lengths agree (wav 0.2-17 s longer than the last LibriBrain word). So
  `timepodcast` is ds003020 wav time to within ~10 ms; the presented audio is rebuilt from these wavs as in
  section 4. Residual constant offsets of a few ms per story cannot be excluded by word alignment.

## 6. Neural data
- MEGIN (Elekta) 306 channels (102 magnetometers, 204 planar gradiometers), 1000 Hz, 0.03-330 Hz online; EOG001-002,
  ECG003, EMG004, STI101, 11 IAS (internal active shielding) channels and SYS201. Continuous HPI. Head shape
  digitised. Raw data: no SSS/MaxFilter applied; the calibration files are in `LibriBrain/metadata/neo/`.
- h5 (sub-1-32): float32 (306, n) in T and T/m at 250 Hz after the authors' bads + head position + SSS + notch +
  0.1-125 Hz band-pass; `times` starts at 0 = recording start, so `timemeg` applies directly. No sensor geometry in
  the file: channel positions and coil types are taken from a sub-0 raw FIF (same scanner); the device-to-head
  transform is not available.

## 7. Upstream issues
- Sherlock1 sub-0 ses-11: the BIDS `*_events.tsv`, `*_channels.tsv` and `*_meg.json` are 0-byte files on Hugging Face,
  and the folder holds `sub-0_ses-1_coordsystem.json` (session 1's name). The events exist in
  `derivatives/events/` as `run-2`, while the raw FIF is `run-1`.
- Sherlock8 has no stimuli.
