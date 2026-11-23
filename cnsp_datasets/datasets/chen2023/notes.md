# chen2023: Chen et al. (2023, NeuroImage), TRIUX MEG, audiobook at six noise-vocoding levels

First look, 2026-11-23 (download only; no adaptor yet). Scratch: `/data_storage/gu08wuvu/datasets/tmp/review/chen2023/`
(`download/`, `meta/` = API tree listing and LFS pointers, `download_stdout.log`, `verify_sha256.log`). That folder is
temporary; the numbers that matter are copied here.

## 1. Source and download
- Austrian NeuroCloud (ANC) BIDS server, a public GitLab with the data in Git LFS:
  `https://data.anc.plus.ac.at/bids-datasets/auditory/yc_audiobook_vocoding` (landing page
  `https://bids-datasets.data-pages.anc.plus.ac.at/auditory/yc_audiobook_vocoding/`, DOI 10.60817/v2fd-cq35).
- Registry entry `chen2023`, source `gitlab_lfs` (added for this dataset): pinned to commit
  `0a5a02a22a3c41e2eba6fff3e2a25fdc1ddda6bf` (2026-10-21, "Update HED and BIDS Version"). The source lists the tree
  through the GitLab API, reads the LFS pointer (sha256 + size) of each file matched by `.gitattributes`
  (`*.fif`, `*.wav`, ...), and downloads through `repository/files/<path>/raw?lfs=true`.
- 761 files, 108.6 GB (199 LFS files: 175 fif = 107.5 GB, 24 wav = 1.12 GB; the rest small json/tsv).
  Downloaded 2026-11-23 in 44 min with 3 workers, no failures. Integrity: every LFS file matched its pointer's size
  and sha256 (`verify_sha256.log`; script `tmp/review/scripts/chen2023_verify.py`).
- **Licence: ANC Data Use Agreement 1.0.2** (`LICENSE.md`). Use, modification and combination are allowed for
  scientific/educational purposes, but **2.2 forbids redistributing the dataset "in whole or in part, in any form"**,
  and citations must give the commit hash. This matters if standardised copies are ever to be shared.

## 2. Layout
BIDS 1.11.2, `DatasetType: raw`. `sub-<12 hex>/ses-1/meg/sub-*_ses-1_task-audiobook_run-0[1-8]_{meg.fif,meg.json,
channels.tsv,events.tsv}` + `sub-*_ses-1_coordsystem.json`; top level `participants.tsv` (age, sex, handedness,
acq_time), `ses-1_task-audiobook_events.json`, `stimuli/01.wav ... 24.wav`, README, CITATION.cff. No derivatives, no
MRI, no authors' code (the README points to https://gitlab.com/yapingchen/vocoded-speech-trf-meg, not fetched yet).

- 24 subjects (pseudonymised hex ids; 11 F, ages 18-45) as in the paper, one session, one run per block of 3 stimuli.
- **Runs are missing for 5 subjects**: `sub-400fb1b90f57` only run-08, `sub-520e215b49cf` only run-02 (3 stimuli each);
  `sub-2bf97e558a62` no run-02, `sub-2224b4d06ea2` no run-05, `sub-78f50f9a795e` no run-04. Some runs hold only 2
  stimuli (e.g. `sub-0c8a4f5c9ada` run-08, `sub-2bf97e558a62` run-05). In all, **520 of 24 x 24 = 576 presentations**
  are present (original 83, 7chan 88, 5chan 85, 3chan 89, 2chan 87, 1chan 88). The README says no one was excluded,
  so the gaps are probably upload/conversion losses: an upstream question.
- `sub-520e215b49cf`: run-02 `meas_date` 2019-04-26, while `participants.tsv` acq_time says 2019-04-10 (to check).
- Run lengths 155-650 s.

## 3. MEG files
- Elekta/MEGIN TRIUX, 1000 Hz, online 0.1-330 Hz. **MaxFilter 2.2.15 (SSS) already applied** (`proc_history`;
  README: SSS with movement compensation between blocks), so these are not raw MEGIN data: no tSSS needed for
  validation.
- Channels (`channels.tsv`, fif): 204 grad + 102 mag, EOG001/EOG002 (direction not stated: check which is vertical),
  ECG003, **EEG010** (a single EEG channel, purpose unknown; probably not an audio copy: only ~650 distinct values in
  521 s of run-01, to confirm against the wav envelope), 11 IAS channels, SYS201, STI001-STI008 + STI101. All marked
  `good`, `info['bads']` empty in the files checked. **No MISC/audio channel**, so likely no audio copy in the
  recording.
- Test-opened with mne (`read_raw_fif`) without errors: all of `sub-0c8a4f5c9ada`, `sub-2224b4d06ea2`,
  `sub-2bf97e558a62`, `sub-78f50f9a795e`, `sub-400fb1b90f57`, `sub-520e215b49cf` and the first file of
  `sub-27f7e83a28c9`.

## 4. Events and triggers
- `events.tsv` has onset (s from the start of the file, i.e. after `first_samp`), duration 0 and `trial_type`:
  condition `original/7chan/5chan/3chan/2chan/1chan` at stimulus onset, and `AnsCorrect/AnsWrong/NoResp` at the
  answer. **It does not say which wav was played.**
- Each stimulus onset in events.tsv matches an STI101 code (< 256) to the ms. The codes fall in one band per condition
  (16 runs checked): original 48-72, 7chan 81-101, 5chan 111-129, 3chan 144-164, 2chan 172-194, 1chan 204-222. So the
  code probably encodes condition + stimulus number (the bands are ~30 wide, wider than 24), which would give the
  trial -> wav mapping; decode it from the authors' code before relying on it. Other STI101 values: 16384 (a few s
  before each stimulus; trial start?), 8192 then 8214 (response). Hardware vs software triggering and the sound
  output latency are unknown.
- The same condition can appear twice in one run (e.g. `3chan`, `1chan`, `1chan`), so the block design is not a
  strict one-condition-per-slot Latin square.

## 5. Stimuli
- `stimuli/01.wav ... 24.wav`: **raw, clean audio** (the "original" condition), 44.1 kHz, 2 channels, float32;
  12 long files (01-12, 179.8-194.4 s) and 12 short ones (13-24, pairs of ~16, 29-30, 64-65, 92-93, 117-118,
  147-152 s). Total 3174.5 s (52.9 min), slightly more than the 3090 s from the paper's nominal lengths in the
  spreadsheet.
- **The vocoded versions (7/5/3/2/1 channels) are not shipped.** They would have to be rebuilt from the clean wavs
  with the authors' vocoder parameters (paper/code), or the clean envelope used as the regressor for all conditions.
  To decide in exploration.

## 6. Open points for the explorer
1. The trial -> wav mapping: decode the STI101 codes (authors' code), cross-check with the wav durations against the
   onset-to-answer intervals.
2. The vocoded stimuli: rebuild, or use the clean audio with a condition label (recommended default: clean audio as
   the stimulus, condition in the trial metadata, vocoding parameters documented).
3. EEG010 and EOG001/002 roles; is there any audio copy?
4. Onset latency and drift: there is no audio channel, so it must come from the trigger timing or a decoder scan.
5. The missing runs and the `sub-520e215b49cf` date: upstream questions.
6. The licence's redistribution ban.
