# geirnaert2025: Ear-SAAD, simultaneous scalp, around-ear and in-ear EEG, two competing Danish talkers

Notes from exploration, standardisation and validation (worker agent, 2026-11-24). Evidence scripts, logs and
figures: `/data_storage/gu08wuvu/datasets/tmp/review/geirnaert2025/` (`scripts/`, `agent_log.md`); that folder is
temporary, so the numbers that matter are copied here.

## 1. Source
- Zenodo record 16536441 ("Ear-SAAD dataset"), doi:10.5281/zenodo.16536441. Files: `bids_dataset.zip`
  (12.2 GB), `preprocessedData.zip` (0.4 GB, the authors' 20 Hz preprocessed trials), `experiment-manual.pdf`,
  `preprocessFromBIDS.m`. **Licence: CC BY-NC-SA 4.0** (`dataset_description.json`): non-commercial, and derived
  data must be shared under the same licence.
- Paper: Geirnaert S, Kappel SL, Kidmose P (2025). A direct comparison of simultaneously recorded scalp,
  around-ear and in-ear EEG for neural selective auditory attention decoding to speech. *Sci Rep* 15:41655,
  doi:10.1038/s41598-025-25576-2 (`data_campaign/papers/geirnaert2025.pdf`).
- Code: `preprocessFromBIDS.m` (read, not run): band-pass 1-9 Hz, EOG regression, ASR, 20 Hz; envelope from the
  wav **after dropping its first 5 s** (`y = y(5*fsAudio+1:end)`), both streams; EEG trial = `events.tsv`
  onset + 600 s.
- Obtained from the user's archive copy on woody (`/home/woody/iwpm/iwpm104h/zenodo/geirnaert2025/16536441/`,
  md5 verified against Zenodo's `MD5SUMS` on both ends; `unzip -t` clean). This server never contacted Zenodo.
  The zips are kept in `download/`, extracted to `extracted/` (same layout as the repo downloader's in-place
  extraction: `<download>/bids_dataset/...`).

## 2. Layout
- `bids_dataset/sub-XX/ses-01/eeg/sub-XX_ses-01_task-selectiveAttention_eeg.{set,fdt}`: EEGLAB, continuous,
  64 channels, 1000 Hz, **3600 s = the six 600 s trials back to back** ("RecordingType": "epoched"); the breaks,
  the 5 s prelisten, the training trial and the ASSR run are not included. **No trigger channel.** Steps of up to
  80 mV (DC level) at the trial boundaries: the trials were cut from different parts of the recording.
- `_events.tsv`: per trial `onset` (0, 600, ..., 3000 s), `duration` 600, `trial_type` trial1-6,
  `stim_file` (`<left>.wav;<right>.wav`), `attended_speaker`, `attended_ear`, `video_condition`.
- `_channels.tsv`: names and groups (scalp-EEG, EOG, left/right in-ear, left/right around-ear; `Fp1-cr` has no
  description). Units "NA"; no positions (`chanlocs` X/Y/Z empty).
- `bids_dataset/stimuli/Speaker{1..6}Part{1,2}.wav`: **the audio is shipped**. 48 kHz, int16, stereo with L = R
  (r = 0.998-1.000; Speaker3/6 differ in level only), i.e. before the HRTF; 605.000 s each, starting with 120 ms of
  zeros (Speaker5: 20 ms; see 6).
- `preprocessedData/dataSubject<N>.mat`: the authors' output at 20 Hz (61 channels, envelopes, acoustic edges,
  labels). Not used by the adaptor; used here to confirm the stimulus convention (3).

## 3. Stimulus <-> trial mapping (verified)
- 15 subjects x 6 trials. Talks by six male Danish professors; per talk two 10 min + 5 s excerpts: `Part1` =
  attended set, `Part2` = unattended set. Each subject attends each speaker once (always its Part1) against
  another speaker's Part2 (manual rules 1-6). Attended direction and video/no-video are balanced (45/45 each).
- **`stim_file` order = left; right** in all 90 trials: the attended file is first exactly when `attended_ear`
  is left (`scripts/inspect.py`), consistent with the authors' code (`attSpeaker` 1/2 = `attendedEar` 1/2).
- **EEG sample 0 = wav time 5.000 s**, for both streams: the authors' shipped 20 Hz envelopes match envelopes of
  the wavs best at a wav offset of exactly 5.00 s (12/12 streams of sub-01, r = 0.92-0.94;
  `scripts/check_preproc.py`), as in their code. The manual: "Only after 5 seconds, the actual trial (trigger)
  starts". The stimulus is therefore stored from 5 s on (600.000 s, = the EEG length); the prelisten is not in
  the EEG.
- Prelisten: the paper says the first 5 s present the target only ("a 5 s head start with only the target
  stream"); the manual says the first 5 s let the participant get used to the competing speakers. Either way the
  EEG starts after it. Whether the unattended stream played from its wav sample 0 or 5 s (i.e. muted during the
  prelisten) is not documented; the authors' code assumes 5 s. **Checked from the EEG** (`scripts/unatt_offset.py`,
  `unattended_offset_check.png`): leave-one-trial-out backward decoders (scalp, average reference, 0.5-8 Hz,
  64 Hz, lags 0-500 ms) trained on each stream read from wav offsets 0-1 s and 4-6 s: unattended mean r 0.031 at
  5.0 s vs <= 0.008 anywhere in 0-1 s (r@5 s above every 0-1 s value in 14/15 subjects); attended control 0.060 vs
  0.010 (15/15). Both streams are aligned as stored (wav from 5 s).

## 4. Speech features available
- Raw audio (as above). Stored as shipped (both channels, float32 / 32768), cut at 5 s. No transcripts,
  word/phoneme alignments or envelopes beyond the authors' 20 Hz derivatives.

## 5. Neural data
- Two TMSi Mobita amplifiers (32 channels each, 1000 Hz), one for the scalp, one for the ear-EEG; common ground
  at CPz; the shared electrode at Fp1 (sub-04: Fp2, manual) is recorded by both, so the two systems can be brought
  to one reference (paper, Dataset). `eeg.json`: `"EEGReference": "common"`. The data are not re-referenced:
  each amplifier's channels share a large common-mode signal (e.g. sub-01 ear channels all ~149 uV SD at 1-40 Hz,
  scalp channels sum far from 0), i.e. the amplifier's own common reference, which is not a recorded channel.
- Channels 1-32 (scalp amplifier, manual table): 27 scalp 10-20 electrodes, `M1`/`M2` (mastoid stickers),
  `EOG2`, `EOG3`, `EOG4`. Channels 33-64 (ear amplifier): `Fp1-cr` (the shared frontal electrode), in-ear
  `EL{A,B,C,E,I,T}`/`ER{A,B,C,E,I,T}` (dry; A/B/C concha, E/I canal, T tragus), around-ear `cEL1-9` and
  `cER1-10` (3D-printed C-shaped arrays like cEEGrids, wet; 1 = top). **Not a 10-channel cEEGrid**: 19
  around-ear + 12 in-ear electrodes.
- Units: volts after MNE's EEGLAB reader (shipped in uV). Plausible: median 1-40 Hz SD after re-referencing
  within the system 3-8 uV per subject and group (`scripts/chan_stats.py`, `chan_stats.csv`).
- EOG directions are not documented. From sub-01 (0.5-8 Hz, median-referenced): `EOG2` r = -0.94 with Fp1
  (blinks inverted: below the eye, vertical), `EOG3` vs `EOG4` r = -0.44 (probably the outer canthi,
  horizontal). Inferred only, so the original names are kept (type `eog`).
- Channel types in the output: scalp file `eeg` x 27, `misc` M1/M2, `eog` EOG2-4, standard_1020 template
  positions (none shipped); ear file `eeg` x 31 (in-ear + around-ear), `misc` Fp1-cr (sub-04: located at Fp2),
  no positions.
- Bad channels (`info['bads']`, **per subject and amplifier**, hard-coded `BADS` in the adaptor): a channel is bad
  if, in any of the subject's trials (1-40 Hz), it is flat (SD < 0.5 uV), railing (SD > 1 mV as shipped), or, after
  re-referencing to the median of the amplifier's other good channels, its SD exceeds 10x the median of its group
  (scalp incl. mastoids / in-ear / around-ear; EOG and Fp1-cr only flat/railing). Blink-dominated Fp1/Fp2 stay
  below 8.1x, so the threshold separates them. Per subject because the validator needs the same channels in every
  trial (per-trial bads crashed it: sub-04 F8 bad in trial 6 only). Rule applied by `tmp/.../scripts/bads_rule.py`
  (output `bads_rule.json`); figure `bads_matrix.png` shows the earlier per-trial version.
  The flagged channels agree with the manual's notes (sub-01 no right tragus electrode -> ERT flat; sub-02 "2 in
  ear electrodes no contact at both sides" -> ELB saturated, ELE/ERC/ERE flat, ERA noisy; sub-04 M2 flat; sub-05
  "flatlining and artefacts in trial 5 and 6 in ear channels" -> **all 32 ear-amplifier channels railing (1-40 Hz SD
  ~3.6 V) in trials 5 and 6**: these two ear files have every channel in bads and `amplifier_saturated: true`
  (`SATURATED`); the scalp files of those trials are fine; sub-08
  "3 electrodes had no contact" left -> ELC/ELE/cEL4 flat). Full list: section 11.
- Manual's participant notes worth knowing: sub-02 restless; sub-08 excessive blinking; sub-09 focused on part of
  the fixation cross; sub-12 closed his eyes in trials 1-2; sub-03 and sub-10 had no working video trigger (does
  not affect the audio); sub-04 shared electrode Fp2.

## 6. Alignment
- **Triggers (hardware, documented, not shipped):** "Audio triggers were generated from a separate audio trigger
  channel" (paper). Manual: audio and the silent video were played by PsychoPy in separate threads; "only a start
  and end trigger are given. After 5 s, the 2-bit (to distinguish start and end) audio trigger is played"; the
  video trigger (photodiode) follows 500 ms later on the same, single EEG trigger channel. The shipped epochs start
  at the audio start trigger (sample 0 = wav 5 s, section 3). Whether the trigger sound is in the same output
  stream as the speech (sample-locked) or a separate playback call is not stated.
- **Leading zeros:** to compensate a ~120 ms (+-20 ms) audio-before-video latency measured with an oscilloscope,
  the wavs start with 120 ms of zeros (Speaker 5: 20 ms; manual). These are part of the played file, so they are
  already accounted for when the trigger is locked to the wav timeline; they would matter only if the trigger
  were tied to the video.
- **Drift:** not estimable: the epochs are fixed 600.000 s cuts from the start trigger; the end triggers and the
  trigger channel are not shipped. No correction.
- **Inter-amplifier timing (hardware-derived, from the shared frontal electrode;** `scripts/amp_sync.py`,
  `scripts/amp_jumps.py`, `amp_sync_shared_fp1.png`): cross-correlating scalp Fp1 (sub-04 Fp2) with the ear
  amplifier's Fp1-cr (1-15 Hz, 10 s windows):
  - start offset within +-2 ms in all assessable trials; relative drift +2.0 ppm (IQR 1.3-3.0, 71 trials
    without jumps; ~1.2 ms over a trial): the ear amplifier's clock runs slightly behind.
  - **step jumps of 13-16 ms inside four trials**: sub-04 trial 2 (-15 ms at ~95 s, again at ~485 s), sub-07
    trial 1 (-16 ms at ~385 s), trial 4 (+13 ms at ~275 s), trial 6 (-15 ms at ~125-195 s); sub-12 trial 5
    possibly (+7.5 ms at ~325 s, noisy). Probably samples dropped by one of the two amplifiers. Which one is not
    knowable from the release, so nothing is corrected; the stimulus alignment of one of the two systems is off
    by ~15 ms after the step in these trials.
  - unassessable (shared electrode too noisy on one side, median r < 0.6): sub-02 trials 4-6, sub-09, sub-12
    trials 1-4 and 6.
- **Proposed method:** `onset_only` (the authors' epochs cut at the hardware audio trigger), no drift correction,
  no inter-amplifier correction. Insert-earphone tube latency unknown.

## 7. Cross-subject duration check
Not possible: every epoch is exactly 600.000 s by construction.

## 8. Data size
15 participants x 6 trials x 600 s = **60 min per participant (no range), 15 h in total**; per condition 30 min
per participant (video / no video; attend left / right). Both amplifiers cover the same time (counted once).
Standardised: 77 MB per trial and amplifier (fif, float32), 13.8 GB EEG + 2.8 GB audio (12 x 230 MB) = 16.6 GB.

## 9. Upstream issues
- The README's paper reference is truncated ("can be found in the paper: '").
- `channels.tsv` units "NA" (the data are uV); `Fp1-cr` has no description; no electrode positions.
- The trigger channel and the inter-trial data are not shipped, so the onsets cannot be re-measured and drift
  cannot be estimated; inter-amplifier sample losses of ~15 ms exist in at least four trials (section 6).
- The paper describes the prelisten as target-only, the manual as both talkers.

## 10. Open questions (defaults taken, worker run 2026-11-24)
1. Two amplifiers -> two files per trial with ns_type `eeg` (scalp) and `ear-eeg` (in-ear + around-ear + Fp1-cr)
   in one standardised directory [taken]. Alternative: two datasets (`geirnaert2025_scalp`, `_ear`).
2. In-ear and around-ear stay in one file: they share one amplifier and reference [taken].
3. EOG names kept (`EOG2-4`), directions only inferred [taken].
4. No correction of the inter-amplifier jumps; affected trials listed here and in the README [taken]. A
   per-segment correction of the ear file to the scalp time base would be hardware-derived, but it is unknown
   which amplifier lost samples.
5. Stimulus stored from wav 5 s on, both channels as shipped [taken].

## 11. Adaptor
`adaptor.py` (2026-11-24). Per trial two `TrialRecord`s (ns_type `eeg`, `ear-eeg`) with the same two stimuli
(`Speaker<k>Part<p>`, attended first), condition `attend-<left|right>-<video|novideo>`, session 1, trial = row of
`events.tsv`. EEG cropped to the event's 600 s; sidecar: `onset_only`, trigger `hardware`, `drift_ppm` null,
amplifier, epoch onset, `stimulus_start_in_wav_s` 5.0, left/right file, attended side, video flag, sex, age,
reference, shared electrode, `external_sensors`, `positions`, `units_as_shipped`, `amplifier_saturated`,
`amplifier_steps` (text, from section 6, or null) and `amplifier_sync_assessable`.

Bad channels (`BADS`; all other subject/amplifier pairs have none):
- scalp: sub-01 Fz; sub-04 M2, F8; sub-07 M2.
- ear: sub-01 ELC, cEL2, cEL3, ERC, ERT, cER2; sub-02 ELB, ELE, ERA, ERC, ERE; sub-04 cER8; sub-06 ELC, ERE;
  sub-07 ELB, cEL1, cEL2, ERB, cER2, cER8; sub-08 ELC, ELE, cEL4; sub-09 cER4; sub-11 ELB; sub-12 ERA, ERB, ERC;
  sub-14 ELE, ERE; sub-15 ELC, ERC.
- `SATURATED`: sub-05 ear trials 5 and 6 (all channels bad).

## 12. Validation (2026-11-24, all 15 subjects, from `standardised_v2`, data identical to the final run)
Average reference per amplifier (scalp: 27 scalp `eeg` channels minus bads; ear: in-ear + around-ear minus bads,
Fp1-cr excluded as `misc`), attended stream, `--first-attended`. Ear view without sub-05 trials 5-6 (saturated).
Figures in `tmp/review/geirnaert2025/`.
- **Scalp** (`validation.json`, `validation_scalp/validation.png`): low tier **pass**, mean r 0.023 (median
  0.023), p_circ 0.020, p_mismatch 0.048, 13/15 subjects significant, TRF peak 188 ms, nothing above the null at
  negative lags; 30-60 Hz fail (SNR 1.02, p 0.21), 30-250 Hz fail (SNR 1.06, p 0.12); both TRFs a ~12 ms ripple at
  all lags (noise). Tier: low.
- **Ear** (`validation_ear-eeg.json`, `validation_ear/validation.png`): low tier **pass**, mean r 0.012, 8/15
  significant, TRF peak 203 ms; 30-60 Hz fail (SNR 1.03), 30-250 Hz fail (SNR 0.96). Tier: low.
- Per condition (low tier, `validation_{scalp,ear}_{video,novideo}/`): scalp video r 0.016 (8/15), no video 0.024
  (12/15), TRF peaks 188/203 ms; ear video 0.009 (5/15; TRF entirely inside the null band, reported peak -16 ms is
  noise: marginal), ear no video 0.010 (5/15, peak 203 ms). All pass at population level.
- Attention contrast (`scripts/earEEG/aad_check.py`, backward decoder, 0.5-8 Hz, original reference;
  `aad_{scalp,ear}/r-attended-vs-r-ignored_env.png`): scalp r attended 0.052 vs ignored 0.014, attended > ignored
  in 15/15 (Wilcoxon p 6e-5), 30 s accuracy median 69%, lag-sweep peak -1 ms (CI 0..0); ear 0.019 vs 0.007, 14/15
  (p 9e-4), 57.5%, peak +1 ms. The paper reports 83% (scalp) / 67% (around-ear) / 61% (in-ear) on 60 s windows
  with ASR and 1-9 Hz; ours is unpreprocessed and 30 s, so lower, same ordering.
- DNN offset vs accou2023 (scalp; `dnn_offsets/`, `scripts/dnn_wrap.py`): **-10.2 ms** (95% CI -13.8..-6.6);
  video -10.4, no video -9.9 ms. In the range of other two-talker data (narayanan2021 -5/-9 ms); documented, not
  applied.
- Unattended-stream alignment: section 3 (confirmed at wav 5 s).

## Alignment grade
**medium** (proposed): hardware audio trigger documented but not verifiable (trigger channel not shipped, no audio
copy); shipped onsets kept, low tier passes on both amplifiers, TRF peak ~190 ms with nothing at negative lags, DNN
-10 ms, both streams confirmed at wav 5 s; no drift estimate; inter-amplifier steps of ~15 ms in 4 trials
documented, not corrected.
