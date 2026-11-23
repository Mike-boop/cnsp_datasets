# hassan2026: MAESTRO, 32-ch ANT eego EEG, 4 talkers + 2 noise loudspeakers, 16 listeners

Explorer notes, 2026-11-23. Download complete and verified the same day (section 1). Sources: the dataset card
(`README.md`), the data, the paper (`data_campaign/papers/hassan2026.pdf`) and the authors' loader `maestro-loader`
0.1.2 (PyPI wheel, read, not run). Scratch: `/data_storage/gu08wuvu/datasets/tmp/review/hassan2026/`
(`explore/*.csv`, `figures/`, `authors_code/`, `video_subset/`); scripts in `tmp/review/scripts/hassan2026_*.py`.
That folder is temporary; every number that explains a choice is copied here.

**Headline.**
1. Hugging Face `aspire-osu/maestro-eeg-dataset`, gated (terms auto-approved; the user accepted them, the token is
   `hf` in `secrets.json`, exported as `HF_TOKEN`). 5.15 GB without the egocentric video.
2. **EEG ships per trial** (parquet, one per subject x trial, ~35 s) **in volts** despite the card's "raw ADC
   units" (section 5), against the amplifier reference (CPz, inferred). One continuous recording per subject.
3. **Raw audio per loudspeaker**: 6 mono 16 kHz FLACs per trial (identical for all subjects), 4 attendable
   LibriSpeech talkers and 2 rear CHiME-Home noise sources. Continuous speech: in scope.
4. **Timing is software only**: per trial, unix timestamps of the EEG first sample (LSL) and of each audio device's
   playback start. The EEG starts 1.7-5.7 s before the audio; **the authors' loader 0.1.2 ignores this** (it
   aligns EEG sample 0 with audio sample 0, ~4.4 s off; upstream issue).
5. **The per-device playback timestamps (0 / +80 / +160 ms) are not acoustic**: the scene-video microphone and the
   EEG both show devices 1 and 2 sounding together (section 6b, 6d).
6. **The sound reaches the EEG ~0.8 s after the earliest playback timestamp** (backward-model lag sweep, all 16
   subjects, median +797 ms, IQR 750-859 ms; section 6d). Brain-based, so documented, not applied (user decision).

## 1. Source
- Data: https://huggingface.co/datasets/aspire-osu/maestro-eeg-dataset, pinned to commit
  `534710be3a1132a83774bb6a80b7bf3f69a6d511` (lastModified 2026-11-08). Licence CC BY-NC-SA 4.0 (card front matter
  and `LICENSE`). Registry entry `hassan2026` (source `huggingface`, `media/video/*` excluded; the helper sends
  `HF_TOKEN` as a bearer header).
- Size (tree API): 9,055 files, 41.87 GB in total; without video 7,377 files, **5.15 GB**: `data/eeg` 1,680
  parquet 4.23 GB, `data/gaze` 1,678 0.23 GB, `data/imu` 1,678 0.36 GB, `media/audio` 630 FLAC 0.32 GB,
  `media/timing` 1,680 json, `metadata/` 7 files, `splits/` 21 json; `media/video` 1,678 mp4 36.7 GB (excluded).
- Download 2026-11-23, 28.6 min, 7,377/7,377 files, none failed (`R/hassan2026/download.log`). Integrity
  (`tmp/review/scripts/hassan2026_verify.py` against the raw tree `R/hassan2026/hf_tree_raw.json`): size of every
  file, sha256 of the 5,666 LFS files, git blob sha1 of the 1,711 small files: **0 problems**
  (`R/hassan2026/verify.txt`).
- 24 scene videos (S01 eval_001-006, S09 eval_051-056, S01/S05/S12 eval_023/027/079/100; sha256 checked) in
  `R/hassan2026/video_subset/` for the microphone check (section 6b).
- Paper: Hassan KMN, Alavi A, Williamson DS (2026). MAESTRO: a Multimodal Auditory-attention Egocentric
  Speech-TRacking Open corpus. arXiv:2609.31898 (eess.AS). The Ohio State University.
- Code: `maestro-loader` 0.1.2 (PyPI, Apache-2.0; wheel sha256 47876ab2...). Its repository
  (github.com/sAliAlavi/maestro-loader) returns 404.
- Stimulus licences: LibriSpeech CC BY 4.0; CHiME-Home (noise) licence **to check**; the dataset as a whole is
  CC BY-NC-SA 4.0.

## 2. Layout
```
data/eeg/subject=S01/trial=eval_001.parquet     # t_sec (amplifier clock, s) + sample_idx (from 0) + 32 ch_* (float32, V)
data/gaze/subject=S01/trial=eval_001.parquet    # Tobii per-eye gaze + pupil, ~50 Hz
data/imu/subject=S01/trial=eval_001.parquet     # Tobii accelerometer + gyroscope, ~100 Hz
media/audio/eval_001/speaker{1..6}_dev{d}_{L|R}_spkid{ID}.flac   # 16 kHz mono int16, exactly 30.000 s
media/timing/subject=S01/trial=eval_001.json    # unix timestamps (below)
metadata/trials.csv               # attended speaker, hemisphere, inner/outer, SNR, per-device-channel power
metadata/trials_per_subject.csv   # comprehension_correct per subject x trial (empty for training trials)
metadata/bad_channels.csv, subjects.csv (demographics empty), eeg_channels.json, audio_layout.json,
         audio_manifest.json (trial -> speaker -> FLAC name)
```
Timing json per trial: `eeg.{sfreq, n_samples, t0_internal_sec, first_sample_unix, end_unix}`,
`audio.devices[3].{device_id_raw, playback_start_unix, end_unix}`, `audio.{t0_unix, t1_unix, flac_dur_sec}`,
`tobii.recording_start_unix`, `align.{anchor_unix, end_unix, overlap_sec}`. In all 1,680 trials
`anchor = audio.t0 = tobii.recording_start = min(playback_start)` (so the Tobii field is not an independent
Tobii time), `overlap_sec = 30`, `n_samples` = parquet rows, `t0_internal_sec` = parquet `t_sec[0]`.
Gaze/IMU/video are missing for S02 eval_077 and eval_078 only.

## 3. Stimulus <-> trial mapping
- Subjects S01-S16. Every subject heard the same 105 trials **in the same order**: `training_001..005`, then
  `eval_001..100` (ordered by `eeg.first_sample_unix`). Trial number in the standard format = this position (1-105).
- Breaks: the longest gap between trials precedes eval_050 in 12 subjects (1.8-12.3 min; 11 min in S01-S04, ~2
  min in S06-S09, S11-S13, S16); in S05, S10, S14, S15 it precedes eval_045, eval_024, eval_075, eval_094. The
  adaptor labels block 1 = training + eval_001-049, block 2 = eval_050-100 (the paper's two sessions, nominal) in
  the trial metadata; `session` = 1 (one continuous EEG recording, same cap).
- Per trial: 4 unique 30-s LibriSpeech excerpts on speakers 1-4 and 2 unique 30-s CHiME-Home excerpts on speakers
  5-6; 630 files, nothing repeated.
- Loudspeaker layout (`metadata/audio_layout.json`, which **differs from the card's table**): device 1 L/R =
  speakers 1/2 at -67.5/-22.5 deg, device 2 L/R = speakers 3/4 at +22.5/+67.5 deg, device 3 L/R = speakers 5/6 at
  -135/+135 deg (noise). The json is self-consistent (hemisphere L for 1-2, R for 3-4; outer = 1 and 4); the card
  lists 1 = -22.5, 2 = +22.5, 3 = -67.5, 4 = +67.5. Upstream issue candidate. The adaptor uses the json.
- Attended speaker per trial in `metadata/trials.csv` (25 x 4 over the 100 evaluation trials), attended SNR 3-18 dB
  (mean 11.6, SD 3.1, 105 trials). `trials_per_subject.csv` has `comprehension_correct` = **False for all 1,600
  evaluation trials** (empty for the 80 training trials), which cannot be right (the paper reports behavioural
  accuracy); the adaptor stores it with a note (upstream issue).
- Paper II-C says the "naturally mixed audio recording" is released too; it is not in the repo (upstream issue
  candidate).
- Paper IV: SNR scaling clipped the attended stream's peaks (16-bit PCM). That the FLACs are exactly what was
  played is the paper's claim, not verified sample by sample; the scene microphone matches them (envelope r up to
  0.6 for the attended talker, section 6b) and the shipped `device*_power` columns carry the SNR scaling. The
  README should mention the clipping (it biases envelope statistics of attended vs ignored talkers).
- Size: 16 x 100 x 30 s = 13.3 h of evaluation trials, plus 16 x 5 x 30 s = 0.67 h training.

## 4. Speech features available
Raw audio (16 kHz mono int16 FLAC per loudspeaker). No transcripts or word/phone alignments; `spkid` in the file
name is the LibriSpeech (or CHiME) speaker id, but the excerpt boundaries within LibriSpeech are not given.

## 5. Neural data
- 32-ch ANT Neuro eego mylab, 500 Hz (kept). Channels (`eeg_channels.json`): Fp1 Fpz Fp2 F7 F3 Fz F4 F8 FC5 FC1
  FC2 FC6 M1 T7 C3 Cz C4 T8 M2 CP5 CP1 CP2 CP6 P7 P3 Pz P4 P8 POz O1 Oz O2. M1/M2 mastoids -> `misc`; 30 scalp
  channels. No EOG, ECG or stimtrack.
- **Units: volts.** The values are clipped at +-0.08388608 = +-2^23 x 1e-8 (24-bit ADC, 10 nV steps). Read as
  volts, the 1-40 Hz RMS is 5-19 uV per subject (median over channels), the spectrum 1-4 uV/sqrt(Hz) at 2-5 Hz with
  an alpha peak (S08 eval_010); DC offsets ~1-40 mV (DC-coupled). So the adaptor keeps the values unscaled. Some
  subjects carry strong 60/120 Hz line noise (S01: 370 uV/sqrt(Hz) at 60 Hz).
- **Reference**: CPz and AFz (the waveguard reference and ground) are not among the channels, and the shipped data
  are not re-referenced (the loader only references with `preprocess=True`); so the original amplifier reference,
  **CPz (inferred)**. The paper's "linked-mastoid reference" is the authors' preprocessing.
- `t_sec` is the amplifier clock (exact 2 ms steps; `sample_idx` restarts at 0 per trial). It increases
  monotonically over all 105 trials of a subject: one continuous recording per subject.
- **Bad channels** (`bads.json`, rule in `bads.py`): the authors' list plus channels at the clip in > 10% of
  samples plus flat channels (median 1-40 Hz SD < 0.1 x the subject's median). Scan over all trials
  (`explore/channel_scan.csv`): the rule adds S02 M1 (clipped) and S14 Pz (flat; probably bridged to the CPz
  reference). No upper variance threshold: the only channels with SD > 5 x the median (Fp1/Fpz/Fp2 in S10 and
  S16) carry blinks, which are physiological, not faulty; the authors' list already covers the noisy channels.
  Per subject:
  S01 M1 M2 | S02 F8 M1 M2 O2 | S03 Fpz Fz M1 M2 | S04 M2 | S05 F7 F8 FC5 FC6 O2 | S06 Fz | S07 FC6 T8 | S08 none |
  S09 F8 FC6 T7 T8 CP5 | S10 F4 F8 FC6 | S11 FC5 M1 T7 M2 P7 | S12 O1 Oz O2 | S13 M1 T8 M2 P7 |
  S14 F8 FC6 M1 M2 Pz | S15 T7 | S16 M1 T8. bads.json was written from the exploration scan (same rule, ba-form
  filter); `bads.py` (channel names from `eeg_channels.json`, sos filter) reproduces it from the download (not
  yet run: needs pyarrow in the project venv).
- With mastoids bad in 8 of 16 subjects, validate with an average reference (30 scalp channels).
- Gaze, pupil and head IMU (Tobii Pro Glasses 3): another system and clock, not standardised (default agreed
  2026-11-23).

## 6. Alignment
### 6a. Timestamps (`explore/timing.csv`, all 1,680 trials)
- `eeg.first_sample_unix` (LSL) to `align.anchor_unix`: 1.75-5.74 s (median 4.42 s). The EEG ends 0.27-0.48 s
  (median 0.34 s) after anchor + 30 s.
- Amplifier clock vs host clock: fit of `t0_internal_sec` against `first_sample_unix` over the 105 trials of each
  subject: +6.8 to +9.8 ppm (median 8.9 ppm), residual SD 1.6-1.8 ms (S10 2.3 ms, max 15 ms; S11 5.8 ms, max
  56 ms). The LSL first-sample timestamps are therefore consistent to ~2 ms; ~9 ppm is 0.27 ms over a trial, not
  corrected (there is no hardware estimate of the sound cards' clocks).
- Playback timestamps: the three devices' `playback_start_unix`, relative to the anchor, depend on
  `device_id_raw`, not on the list position: raw 6 at 0 (median), raw 5 at +81 ms (SD 24), raw 3 at +162 ms
  (SD 19), the same in all 16 subjects (the paper's "80 and 160 ms"). The list order varies from trial to trial,
  and nothing in the release says which raw id drives device 1/2/3 of the FLAC names, so the adaptor stores the
  offsets keyed by raw id (`playback_offsets_ms_by_raw_device`), unmapped.
  `end_unix - playback_start_unix` = 30.06-30.35 s (the 30 s FLAC + a call overhead).
- The loader 0.1.2 never reads the timing json; it slices EEG and audio from their own t = 0, i.e. ~4.4 s off.

### 6b. Scene-video microphone (`tmp/review/scripts/hassan2026_mic_lags.py`, `explore/mic_lags*.csv`)
The Tobii scene video carries a 24 kHz mono mp3 microphone track (34.3 s). For each of the 6 streams: envelope
xcorr (1 kHz) for a coarse lag, then GCC-PHAT on the waveforms within +-20 ms. Only the attended talker (the
loudest stream) is found reliably (envelope r 0.4-0.6); at low SNR (3-6 dB) a second talker is visible too. Taking
the strongest match per device, 12 trials have both device 1 and device 2 found within 0.3 s of each other (a window
that admits the 80 and 160 ms hypotheses): dev2 - dev1 = -20 to +26 ms (12 trials, S01/S05/S09/S12). Two talkers on
the same device differ by up to 13 ms, so the precision is about +-15 ms. **Devices 1 and 2 sound together**,
although their timestamps always differ by >= 80 ms. Device 3 (rear noise) is not detectable in the microphone.
The absolute latency of the sound cannot be read from the video (its start in unix time is not given:
`tobii.recording_start_unix` is the anchor). Figure: `R/hassan2026/figures/alignment_evidence.png` (right panel).

### 6c. Alignment implemented (default; user to confirm)
- Onset (all six streams) = `round((anchor_unix - eeg.first_sample_unix) x 500)` samples into the trial parquet;
  the adaptor crops the EEG there and keeps it to the end of the trial (~30.3 s after the onset).
- `alignment_method = sw_trigger`, `trigger_type = software (paper)`, `drift_ppm = 9.0` (amplifier vs host clock,
  measured, not corrected), `jitter_ms = null`; the per-device timestamp offsets go into the trial metadata
  (`playback_offsets_ms_by_raw_device`); `units_as_shipped` says raw ADC per the card, volts per section 5.
- Not applied: the authors' per-device shift by the playback timestamps (contradicted by 6b and 6d), and the
  ~0.8 s latency of 6d (brain-based; user decision).

### 6d. Lag sweep (exploration, `tmp/review/scripts/hassan2026_lag_sweep.py`, `explore/lag_sweep_wide.csv`)
Backward model per subject: EEG 0.5-8 Hz at 64 Hz, average reference without bads and mastoids, decoder lags
0-250 ms, attended-talker envelope (|hilbert| of the FLAC, 8 Hz low-pass), ridge, 5-fold CV over the 100
evaluation trials; the stimulus shifted globally from -1 to +2 s relative to the anchor onset (+ = sound later).
Results (grand average over 16 subjects): **peak at +797 ms** (r 0.042; r at 0 ms 0.006). Per subject: S01 1031,
S02 750, S03 766, S04 859, S05 750, S06 797, S07 891, S08 797, S09 938, S10 859, S11 828, S12 562, S13 734,
S14 781, S15 750, S16 859 ms (median 797, IQR 750-859). Trials attended on device 1 and on device 2 peak at the
same shift (+797 ms each; r 0.041 and 0.036), so device 2 is not 80 ms later than device 1 in the EEG either.
Interpretation: the sound starts ~0.8 s after the earliest playback request, or the LSL first-sample timestamp is
~0.8 s late (cannot be told apart; the sum is what matters). Cf. chen2026 ~0.5 s, pkueeg2025/wang2025 ~0.2 s.
Consequence: with the default onset, the last ~0.5 s of each stimulus has no EEG (the EEG ends 0.34 s after
anchor + 30 s), and a validation at lag 0 will look weak; the validator's lag sweep should show the same peak.
Figures: `R/hassan2026/figures/lag_sweep_per_subject.png`, `R/hassan2026/figures/alignment_evidence.png`.
Still to do: the accou2023 DNN offset scan per device stream (needs standardised data), and whether the latency
varies across trials or blocks.

## 7. Cross-subject duration check
FLACs are 30.000 s; the timestamps of the end of playback are 30.06-30.35 s after the start (call overhead, not
sound). No acoustic end marker exists, so durations cannot be checked against the EEG; drift within a 30-s trial
is below 1 ms for any plausible clock (section 6a).

## 8. Decisions and open questions
Defaults agreed for the user (coordinator, 2026-11-23): gaze/IMU downloaded but not standardised; scene video only
for timing checks; training trials included (condition `training`); all 6 streams stored as stimuli, the attended
one flagged.

Open:
1. Onset convention (6c): all streams at the anchor [implemented], vs the authors' per-device shift [rejected by
   6b/6d].
2. The ~0.8 s brain-based latency (6d): document only [default per the rules], or apply as a constant onset
   correction (+0.80 s, i.e. crop 400 samples later; the stimulus then extends ~0.46 s past the EEG).
3. Python dependencies: the adaptor reads parquet (pyarrow) and FLAC (soundfile); neither is in the project venv
   or pyproject, and the install (`uv pip install pyarrow==25.0.1 soundfile==0.14.0`, additions only) was denied
   by the permission system; the pilot, validation and DNN check wait on it.
4. CHiME-Home licence of the noise stimuli.

## 9. Upstream issues (for `R/upstream_issues.md`)
- Loader 0.1.2 ignores the timing json: EEG sample 0 is ~4.4 s before audio sample 0 (1.7-5.7 s per trial).
- The per-device playback timestamps (0/80/160 ms) do not reflect the sound (microphone: devices together); the
  paper's per-device shift adds 80-160 ms errors. The raw device id -> device 1/2/3 mapping is not documented.
- ~0.8 s between the playback timestamp and the EEG response (lag sweep), not mentioned in the paper.
- Card azimuth table disagrees with `metadata/audio_layout.json`.
- "Naturally mixed audio recording" announced in the paper, not in the release; `tobii.recording_start_unix` equals
  the audio anchor in every trial.
- Card: "raw ADC units"; the values are volts.
- `comprehension_correct` is False for all 1,600 evaluation trials.
- Demographics in `subjects.csv` are empty.
