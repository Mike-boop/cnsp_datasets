# hassan2026: MAESTRO, 32-ch ANT eego EEG, 4 talkers + 2 noise loudspeakers, 16 listeners

Explorer notes, 2026-11-23, written **before any data file could be downloaded**: the Hugging Face repo is gated
(see section 1). Everything below comes from the dataset card (`README.md`, public), the HF file tree (public API),
the paper (`data_campaign/papers/hassan2026.pdf`) and the authors' loader `maestro-loader` 0.1.2 (PyPI wheel, read,
not run). Items marked **(unverified)** need the data. Scratch: `/data_storage/gu08wuvu/datasets/tmp/review/hassan2026/`
(`authors_code/` = the wheel and its PyPI metadata).

**Headline.**
1. Hugging Face `aspire-osu/maestro-eeg-dataset`, **gated ("auto": accept the terms while logged in, approved
   automatically)**. Without a token the tree listing and README work, every data file returns HTTP 401. The
   downloader now sends `HF_TOKEN` as a bearer header (`download_helpers.id_to_downloadables_huggingface`).
2. **EEG ships epoched per trial** (one parquet per subject x trial, ~35 s), not as continuous recordings. 16
   subjects x (5 training + 100 evaluation) = 1,680 trials, all present (card).
3. **Raw audio per loudspeaker** (6 mono 16 kHz FLAC per trial, identical for all subjects): 4 attendable talkers
   (LibriSpeech) + 2 rear noise sources (CHiME-Home). Continuous speech: in scope.
4. **Timing is software only**: unix wall-clock anchors per trial (EEG first sample via LSL, `playback_start` per
   audio device, Tobii recording start), all on one host clock (paper II-D). The three playback devices start at
   different times (paper: median 80 and 160 ms after the earliest one). No triggers, no stimtrack on the EEG.
5. A possible **acoustic copy of the stimulus**: the Tobii scene video has a mono 24 kHz microphone track (paper
   II-D-3), on the Tobii clock. Excluded from the download for now (36.7 GB of video); see open question 3.

## 1. Source
- Data: https://huggingface.co/datasets/aspire-osu/maestro-eeg-dataset, pinned to commit
  `534710be3a1132a83774bb6a80b7bf3f69a6d511` (lastModified 2026-11-08). Licence CC BY-NC-SA 4.0 (card front matter
  and `LICENSE`). Registry entry `hassan2026` (source `huggingface`), with `media/video/*` excluded.
- Size (tree API, 2026-11-23): 9,055 files, 41.87 GB in total; without video 7,377 files, **5.15 GB**:
  `data/eeg` 1,680 parquet 4.23 GB, `data/gaze` 1,678 0.23 GB, `data/imu` 1,678 0.36 GB, `media/audio` 630 FLAC
  0.32 GB, `media/timing` 1,680 json 2 MB, `metadata/` 7 files, `splits/` 21 json, `media/video` 1,678 mp4 36.7 GB
  (excluded). LFS files carry sha256 in the tree; the small git files (json/csv) only a git blob id.
- Paper: Hassan KMN, Alavi A, Williamson DS (2026). MAESTRO: a Multimodal Auditory-attention Egocentric
  Speech-TRacking Open corpus. arXiv:2609.31898 (eess.AS). The Ohio State University.
- Code: `maestro-loader` 0.1.2 (PyPI, Apache-2.0; wheel sha256 47876ab2...). Its repository
  (github.com/sAliAlavi/maestro-loader) returns 404 (private or removed).
- Stimulus licences: LibriSpeech CC BY 4.0; CHiME-Home (noise) licence **to check**; the dataset as a whole is
  CC BY-NC-SA 4.0.

## 2. Layout (card and tree)
```
data/eeg/subject=S01/trial=eval_001.parquet     # 500 Hz; t_sec (internal) + sample_idx + 32 ch_* columns
data/gaze/subject=S01/trial=eval_001.parquet    # Tobii per-eye gaze + pupil, ~50 Hz, recording-relative t
data/imu/subject=S01/trial=eval_001.parquet     # Tobii accelerometer + gyroscope, ~100 Hz
media/audio/eval_001/speaker{1..6}_dev{d}_{L|R}_spkid{ID}.flac   # per trial, shared by all subjects
media/timing/subject=S01/trial=eval_001.json    # unix anchors (EEG first sample, playback_start per device, Tobii)
metadata/{trials,subjects,bad_channels,trials_per_subject}.csv, {eeg_channels,audio_layout,audio_manifest}.json
splits/loso/fold_00..15.json, splits/within/fold_0..4.json
```
`metadata/trials_per_subject.csv` (32 kB) holds the per-subject comprehension labels (loader). Gaze/IMU/video are
missing for S02 eval_077 and eval_078 only (tree: 1,678 of 1,680).

## 3. Stimulus <-> trial mapping
- Subjects S01-S16 (native English listeners). Trials `training_001..005` then `eval_001..100`, the evaluation
  trials in two 25-min sessions of 50 trials with a 10-min break (paper II-B). Session boundary is presumably
  eval_050/051 (unverified; the timing anchors will show the break).
- Per trial: 4 unique 30-s LibriSpeech excerpts on the front loudspeakers S1-S4 and 2 unique 30-s CHiME-Home noise
  excerpts on the rear ones; 630 files, 420 speakers, nothing repeated across trials. Every subject heard the same
  105 trials (card: "the 105 stimuli are shared across subjects"); whether in the same order is **unverified**
  (timing anchors give the order).
- Loudspeaker layout (card, `metadata/audio_layout.json`): device 1 L/R = speakers 1/2 (-22.5/+22.5 deg), device 2
  L/R = 3/4 (-67.5/+67.5 deg), device 3 L/R = 5/6 (-135/+135 deg, noise, never attended). The card's azimuth
  signs (1 = -22.5, 2 = +22.5, but 2 labelled "Left, inner") look inconsistent; check against `audio_layout.json`.
- Attended speaker per trial in `metadata/trials.csv` (balanced 25 x 4 over the 100 evaluation trials), with
  per-speaker power and the attended SNR (0-18 dB, mean ~12, SD 3.16). Comprehension correctness per subject and
  trial (multiple choice, with an "I could not pay attention" option).
- Paper II-C says the "naturally mixed audio recording" is released too; the tree has only the 6 per-speaker
  streams (unless that is the scene-video audio). Upstream issue candidate.
- Paper Sec. IV: SNR scaling clipped the **attended** stream's peaks (16-bit PCM), not the competitors' (crest
  factor 11.1 vs 20.5 dB). The FLACs are what was played, so this is a property of the stimulus, not an error to
  fix; mention it in the README (it biases attended-vs-ignored contrasts built on envelope statistics).
- Expected size: 16 x 100 x 30 s = 13.3 h of evaluation trials (+16 x 5 x 30 s = 0.67 h training).

## 4. Speech features available
Raw audio (16 kHz mono FLAC per loudspeaker, as played after SNR scaling, unverified). No transcripts or word/phone
alignments are shipped; LibriSpeech has transcripts per utterance, and `spkid` in the file names identifies the
LibriSpeech speaker, but the excerpt boundaries within LibriSpeech are not given (`audio_manifest.json` may say
more, unverified).

## 5. Neural data
- 32-ch ANT Neuro eego mylab, 500 Hz (native rate kept: <= 1024 Hz). Channel order (card,
  `metadata/eeg_channels.json`): Fp1 Fpz Fp2 F7 F3 Fz F4 F8 FC5 FC1 FC2 FC6 M1 T7 C3 Cz C4 T8 M2 CP5 CP1 CP2 CP6 P7
  P3 Pz P4 P8 POz O1 Oz O2. M1/M2 are mastoids (type `misc` in the standard format), so 30 scalp channels. No EOG,
  ECG or stimtrack on the amplifier.
- **Units: "raw ADC units (clipped +-0.0839)"** (card). The eego range is commonly given as +-1 V (and the ADC
  clips well inside); +-0.0839 could be volts (+-84 mV). To establish from the data: the 1/f spectrum and alpha
  amplitude give the scale (scalp EEG ~10-50 uV RMS after a high-pass). The card's figure shows uV-scale traces
  after a 1-45 Hz band-pass and average reference with 50 uV spacing.
- Reference: paper II-D-1 says "acquired ... using a linked-mastoid reference" (sentence split over a page in the
  PDF). The eego mylab records against a hardware reference (often CPz); with M1/M2 among the channels the shipped
  data are probably referenced to the amplifier reference, not linked mastoids (unverified).
- Bad channels per subject in `metadata/bad_channels.csv` (flat, saturated or outlier variance; paper). They go to
  `info['bads']`; the authors interpolated them.
- Paper: hardware sample counter checked, uniform 2.0 ms intervals, no dropped samples (`sample_idx` column).
- Shipped data are raw (not filtered or referenced): the card says preprocessing happens in the loader (unverified).
- Gaze, pupil and head IMU (Tobii Pro Glasses 3, uncalibrated) are on the Tobii clock at ~50/~100 Hz. They are a
  separate system and not EEG channels; open question 2.

## 6. Alignment
- No triggers or stimtrack. Per trial a json of unix anchors (host system clock): EEG first-sample time (LSL),
  `playback_start` per audio device (from the Python UI, PySide6), Tobii recording start (RTSP).
- Paper: "signals were aligned to the onset of audio playback by trimming each modality according to the offset
  between its first-sample timestamp and the earliest audio playback timestamp"; each device's waveform was then
  shifted by its own playback timestamp (median +80 / +160 ms for the later devices).
- The loader 0.1.2 does **not** read the timing json: it slices the EEG (from `t_sec`) and the FLACs from their own
  t = 0. Either the shipped EEG parquets are already trimmed to the earliest playback start (then `t_sec` 0 =
  earliest `playback_start`), or the loader ignores the per-device offsets. To establish from the data: compare
  `t_sec[0]`, the parquet length and the json anchors.
- Proposed (pending data): onset of each loudspeaker stream in the EEG = `playback_start[device] - eeg_first_sample`
  (or relative to `t_sec`), one onset per device, all three per trial. `alignment_method = sw_trigger`,
  `trigger_type = software` (paper). Expected error: LSL first-sample timestamps of the eego carry the amplifier
  and driver latency (tens of ms, constant-ish), and `playback_start` is the request time, not the sound (cf.
  chen2026 ~0.5 s, pkueeg2025/wang2025 ~0.2 s software leads). So the absolute onset is uncertain by tens to
  hundreds of ms; per-device differences may be more reliable than the absolute value.
- Drift: trials are ~35 s, so clock drift (100-500 ppm) contributes <= 18 ms within a trial. It cannot be measured
  without an audio copy; across the session the anchors are re-taken per trial, so it does not accumulate.
- Checks once data are in: lag sweep of the 0.5-8 Hz forward model per device and pooled; DNN offset scan vs
  accou2023 (per device stream); if the scene-video microphone is usable, acoustic onsets of each device relative
  to the Tobii start give the playback latency per trial.

## 7. Cross-subject duration check
Not possible yet. Planned: EEG trial length vs FLAC length (30 s) vs the anchor window, per subject and trial;
spread of `playback_start[d] - playback_start[1]` per device across subjects and trials (jitter of the software
start).

## 8. Open questions (recommended default in brackets)
1. **Access**: accept the dataset terms on Hugging Face with the user's account and put a read token in
   `secrets.json` (e.g. key `hf`), exported as `HF_TOKEN` for the download. [needed; nothing else unblocks it]
2. Gaze/pupil/IMU: standardise or not? They are on another clock and rate. [download them (0.6 GB), do not
   standardise in v2; mention in the README]
3. Scene video: download a subset (e.g. 2 subjects, ~4.6 GB) to test whether the 24 kHz microphone track gives
   acoustic onsets per device? [yes, after the EEG has been explored, if the lag sweep shows a non-zero offset]
4. Training trials (5 per subject): include as trials with condition `training`? [include, labelled]
5. Stimuli: store all 6 streams per trial (4 talkers + 2 noise) as separate stimuli, attended one flagged.
   [yes, per LESSONS "include everything that was played"]
