# pkueeg2025: PKUEEG, 25 Mandarin listeners, 50 synthesised Three Kingdoms stories over 3 days (OpenNeuro ds008834)

Explorer notes, 2026-11-22. Scratch scripts, tables and figures are in `tmp/review/pkueeg2025/` on data storage
(`scripts/*.py`; `scratch/*.tsv`, `scratch/*.png`). Everything that explains a choice is recorded here because tmp
gets deleted.

## 1. Source
- OpenNeuro ds008834 v1.0.4 "PKUEEG", doi:10.18112/openneuro.ds008834.v1.0.4, **CC0** (`dataset_description.json`,
  `LICENSE`). Authors: Xiao B, Xu X, Yan Y, Li S, Zhang Z, Zheng L, Liang J, Wu X, Cheng H, Chen J (Peking University,
  SHRC). Companion code: https://github.com/boda-xiao/PKUEEG (a copy is shipped in `code/`).
- Papers that use the data (neither one describes the acquisition in detail):
  - Zhang A, Wang B, Wu X, Cheng H, Chen J. Cross-subject generalization in decoding perceived speech from
    non-invasive brain recordings. arXiv:2608.22420 (IEEE/ACM TASLP submission). Table I: "PKUEEG 2025", 64-ch
    NeuroScan, 1000 Hz, 25 subjects, 68.1 h. 68.1 h matches days 1-2 only (25 x 33 stories); the paper mentions
    NeuroScan only.
  - Xu X, Yan Y, Li S, Zheng L, ... Chen J. SHINE: sequential hierarchical integration network for EEG and MEG.
    Section 4.1: 50 chapters over three days, ~4 h of speech per listener, NeuroScan on days 1-2 and Neuracle on day 3,
    1,250 recordings, 57 common scalp channels.
- **Not documented anywhere** (README, sidecars, papers): sound delivery (headphones/loudspeaker, level),
  presentation software, how markers were generated, online reference and ground, hardware filters, exclusions.
  The README states: "Acquisition reference and ground remain unavailable, and hardware filter settings are not
  documented".
- Shared code (`code/`) contains preprocessing (`preprocessing/preprocess_pkueeg.py`: notch, 250 Hz, 1-40 Hz, average
  reference, ICA; segments with `events.tsv` onset/duration, no latency shift) and the release builders
  (`provenance/legacy_layout/build_pkueeg_release.py`: events.tsv derivation, Day-3 x1e-6 scaling). There is no
  presentation code.
- Registry exclusions (not downloaded): `derivatives/preproc_*` (1-40 Hz/250 Hz and 1-8 Hz/128 Hz NPZ) and
  `derivatives/stimulus_features` (100 Hz envelope, Mel, wav2vec2, BERT). We do not need them because the audio is shipped.

## 2. Layout
- `sub-XX/ses-day{1,2,3}/eeg/sub-XX_ses-dayN_task-audio_eeg.{vhdr,vmrk,eeg}`: one continuous BrainVision file per
  session (written by pybv 0.7.5, IEEE float32, 64 channels), plus `_channels.tsv`, `_eeg.json` and `_events.tsv`.
  There are 75 files, 4.95-6.00 h of recording per participant (135.5 h in total, including rest, questions and
  breaks).
- `sub-XX/sub-XX_sessions.tsv`: day, story range, system, vendor format (CNT on days 1-2, BDF on day 3).
- `stimuli/audio/story-NN.mp3` (50 files), `stimuli/transcripts/story-NN.txt` (UTF-8 Hanzi, no punctuation),
  `stimuli/stimuli.tsv` (story -> session, voice, `duration_sec_from_analysis_envelope`, sha256).
- `derivatives/stimulus_annotations/`: `textgrid/story-NN_alignment.TextGrid` (MFA; tiers `words` = Pinyin
  syllables, `phones`), `pinyin/boundaries/story-NN_pinyin.tsv` (syllable onset/offset + Hanzi),
  `pinyin/inputs/*.txt`, `word_boundaries/legacy/story-NN_words.tsv` (word, POS, onset/offset) and `legacy_mat/`,
  `annotation_index.tsv`, `mfa_alignment_quality.tsv`.
- `participants.tsv`: age, sex, handedness (all right-handed; 13 M / 12 F, 19-29 y).

## 3. Stimulus <-> trial mapping
- Every participant heard all 50 stories: day 1 stories 1-17, day 2 stories 18-33, day 3 stories 34-50. Each
  session also has a 300 s eyes-open rest. The same stimuli are used across subjects.
- `events.tsv` has one row per story (`trial_type=speech`, `story_id`, `stim_file`) and one `rest` row. Onset is the
  start marker, duration = end marker minus start marker (1 ms resolution). All 1,250 speech and 75 rest intervals
  start and end on a marker in the `.vmrk`, and none runs past the end of the recording.
- **Raw marker codes are not story IDs.** In the `.vmrk` the codes are `S 1`..`S 18`. They are MNE's
  `events_from_annotations` enumeration of the *string-sorted* original codes (story IDs and 255 = rest), e.g. day 1
  `'1','10','11',...,'17','2','255','3',...` -> 1..18, so `S 11` = rest, `S 1` = story 1, `S 10` = story 2,
  `S 12` = story 3 ... `S 9` = story 17. On day 2 rest is `S 9` (`S 10` if an accidental extra code is present:
  sub-09, sub-13, sub-19, sub-24). On day 3 rest is `S 1` and `S 2`..`S 18` = stories 34..50. The release builder
  took the story IDs from the authors' intermediate `trigger_info_dayN.csv` (not shipped). **Use `events.tsv`,
  not the raw codes.** Decoding the raw codes this way reproduces `events.tsv` in every file.
- **Verified independently by duration** (`scripts/markers.py`, `drift_fit.py`; `scratch/trials_err.tsv`). For each
  trial I subtracted the system-level fit (section 7) from the marker interval and compared the result with the
  exact length of all 50 mp3s. The labelled story is the unique best match in 1250/1250 trials. The nearest other
  story in the same session is >= 185 ms away, while the residual is <= 8.6 ms.
- Presentation order is story-ID order within a session, except:
  - sub-02 day 2: 22..33, rest, 18..21.
  - sub-03 day 1: story 13 played last.
  - sub-20 day 3: story 47 played last.
- Repeated or aborted presentations. The authors' rule is "last adjacent same-code marker pair >= 150 s", and the
  release uses the last play.
  - Complete first plays that were then repeated (the first pair spans the full story):
    - sub-09 day 3 stories 39 and 50
    - sub-13 day 2 story 25
    - sub-16 day 1 story 3
    - sub-19 day 2 story 33
    - sub-20 day 3 story 47

    These participants heard the story twice, and the selected trial is the second hearing.
  - Partial plays: sub-03 day 1 story 14 (restarted after 171 s). Single unmatched start markers: sub-04 d1 s6,
    sub-20 d1 s2 and s7, sub-21 d1 s6. Stray single markers: e.g. sub-21 d1 (a burst of rest codes), sub-21 d3
    (several rest markers; the selected rest pair is the 300.004 s one).

## 4. Speech features available
- **Raw audio**: `story-NN.mp3`, MPEG-1 Layer III, CBR 320 kb/s, LAME 3.100, 48 kHz, stereo. **L and R are
  bit-identical** in every file (max |L-R| = 0), so the content is mono.
- Speech is TTS from the Guagua Audiobook platform. Stories 1-25 use the female preset "Dapiaoliang", stories 26-50
  the male preset "Huazai". Speech starts 0.96-1.02 s into every file (-50 dB re peak) and ends 0.8-1.0 s before the
  end. Peak is ~0.71 and RMS ~0.08 in all files (level-normalised).
- **Exact lengths (gapless decode, ffmpeg default, LAME header honoured)**: 193.310-325.610 s
  (`scratch/audio_info.tsv`, column `n` at 48 kHz). `stimuli.tsv` `duration_sec_from_analysis_envelope` is the same
  length rounded to 10 ms. The full-frame (non-gapless) decode is 1,152-2,302 samples longer: 1,105 leading samples
  (LAME encoder + decoder delay, 23.02 ms) plus trailing padding.
- The ID3 XMP block carries Adobe "CuePoint Markers" at sentence starts (48 kHz sample positions and the sentence
  text). These are unused, and their time base was not checked.
- **Annotations**:
  - MFA TextGrids: tier `words` holds Pinyin syllables with tones (e.g. `huang2`), tier `phones` holds initials and
    finals (122 labels). `xmax` equals the gapless mp3 length exactly (e.g. 300.289896 s for story 3), and the first
    syllable (0.98 s) matches the first sound (0.964 s). **The time base is the gapless decode, starting at its
    first sample.** The `words` tier equals `pinyin/boundaries/*.tsv` in all 50 stories, and that table adds the
    Hanzi per syllable.
  - **Legacy word boundaries are shifted.** `word_boundaries/legacy/*.tsv` onsets are later than the MFA syllable
    onsets of the same characters by a median of **+300 ms in stories 1-33 and +20 ms in stories 34-50** (5-95 %:
    270-350 ms and 0-40 ms; every word matched). Do not use their times (`scripts/annot_check.py`). The legacy word
    segmentation and POS tags are useful, but the times should come from the MFA syllables.
  - `mfa_alignment_quality.tsv`: per story log-likelihood and SNR. Values are uniform; no story stands out.
- Transcripts: UTF-8 Hanzi, 747-1,295 CJK characters per story.

## 5. Neural data
- **1000 Hz in all 75 files.** Native rate is kept (1000 Hz is a "nice" rate).
- **Days 1-2: NeuroScan SynAmps2** (source CNT). There are 62 scalp channels (`Fp1 Fpz Fp2 AF3 AF4 F7 ... I1 O1 Oz O2 I2`,
  10-10 mixed case) + `HEO`, `VEO` (bipolar EOG, typed EOG in channels.tsv).
- **Day 3: Neuracle NeuSen Wireless** (source BDF). There are 59 scalp channels in UPPER case (`FPZ FP1 FP2 ... OZ O1 O2`,
  including AF7/AF8; no CPz, P1, P2, I1, I2) + `ECG`, `HEOR`, `HEOL`, `VEOU`, `VEOL` (monopolar EOG).
- Channel lists are identical within each system across all 25 participants. There are 57 common scalp channels
  (case-insensitive): NeuroScan only has CPz, I1, I2, P1, P2; Neuracle only has AF7, AF8.
- No stimtrack, audio, Sound or aux channel; `TriggerChannelCount` is 0 and markers live only in the `.vmrk`.
  There is no digitisation (README: "no participant-specific electrode coordinates were collected"; MNE `dig`
  is empty), and `meas_date` is absent.
- **Units**: the header says µV with a resolution of 0.1. MNE reads correct volts. The 1-40 Hz robust SD is a median
  of 13.9 µV (day 1), 14.0 µV (day 2) and 7.0 µV (day 3) over files (`scripts/eeg_check.py`,
  `scratch/eeg_check.tsv`). No flat channels; single noisy channels are e.g. sub-02 d1 PO4 and sub-17/sub-22 d1 C3.
  The authors' `code/preprocessing/config/bad_channels.tsv` lists bad channels per session. Day 3 was rescaled by
  the authors (x1e-6, the BDF physical unit field was empty). Its amplitudes are plausible, and the factor-2 lower SD
  fits a nearby reference (below). Day-3 channels carry large DC offsets (median |DC| 4.5 mV), which is normal for
  a DC amplifier. Days 1-2 have |DC| < 20 µV.
- **Reference: undocumented.**
  - Day 3 (inferred): **CPz**. CPz is the missing channel, and the lowest-amplitude channels are CP1, CP2, Cz, Pz
    and C2 in all three subjects checked.
  - Days 1-2: unknown. Not average-referenced (the channel mean has the same SD as a channel). The lowest-amplitude
    channels are temporal (FT7/T7/TP7/T8/F8), which is consistent with a mastoid/ear-type reference, but this is
    unverified.
  - Keep as recorded and record "unknown (Day 3 inferred CPz)".
- **Anti-alias / online low-pass differs by system** (Welch PSD, median over channels, relative to 60 Hz): NeuroScan
  is -3 to -11 dB at 200 Hz, -8 to -13 dB at 250 Hz, -30 to -40 dB at 400 Hz and ~-45 dB at 450 Hz (steep roll-off
  above ~200 Hz). Neuracle is -15 to -21 dB at 400 Hz (gentle). This matters for high-frequency (brainstem) analyses
  on days 1-2.
- BrainVision checks: there are **no `New Segment` markers** in any file (pybv export, `Stimulus` markers only). Pauses
  in the original CNT/BDF, if any, are not visible. Within every story, the marker interval matches the audio to a
  few ms (section 7), so there is no gap inside any trial.

## 6. Alignment
- Markers: one start and one end marker per story (same code), one start/end pair per rest. Codes and their meaning
  are in section 3.
- Hardware/software:
  - README: "The original hardware marker stream remains in the BrainVision marker file" (documented as hardware
    markers).
  - The marker source (parallel port, USB box) and the presentation software are not documented. That the start
    marker is issued at playback start by the presentation software is inferred.
  - The inferred interval jitter (~3 ms SD per start-to-end interval, i.e. ~2 ms per marker) shows the markers are
    not sample-locked to the audio.
- **The presentation played the full mp3 frames (non-gapless decode).** The marker interval minus the *gapless*
  length varies by story (54-115 ms, SD 8-10 ms within a session). The marker interval minus the *full-frame*
  length (`ffmpeg -flags2 skip_manual`, i.e. frames x 1152 samples) is a near constant ~62 ms (days 1-2) or ~32 ms
  (day 3), with residual SD ~3 ms. So the player kept the encoder padding, and the leading encoder/decoder delay
  (1,105 samples = 23.02 ms, or 576 samples = 12.0 ms for decoders that strip the 529-sample decoder delay) was most
  likely played before the first gapless sample. The leading part cannot be measured without a stimtrack (section 8).
- Stimtrack: none.
- Proposed alignment:
  - Trial = each `events.tsv` speech row. EEG from onset = start marker (`sample` column) to start marker + gapless
    length.
  - Stimulus = gapless decode (ffmpeg default; matches the TextGrids and the authors' envelope), one channel
    (L == R), 48 kHz as shipped.
  - Default onset shift: **+1105/48000 s (23.02 ms)**, inferred from the non-gapless playback; see open question 1.
  - Drift correction per EEG system (section 7): NeuroScan days **+77 ppm** (EEG-clock duration = audio length x
    (1 + 77e-6)), Neuracle day not corrected (27 ppm, CI includes 0).
  - Rest intervals are not stimuli (continuous-stimuli default), so skip them.
- Provenance per trial:
  - `alignment_method: hw_trigger`
  - `trigger_type: hardware (README), issued by presentation software; marker-to-sound latency unknown`
  - `drift_ppm`: 76.8 (days 1-2), 27.1 (day 3, not applied)
  - `jitter_ms`: 2.1 (per marker; 3.0 per interval)

## 7. Cross-subject duration check (drift vs jitter)
All 25 subjects heard every story, so durations can be checked story by story (`scripts/drift_fit.py`;
`scratch/drift_fit.tsv`, `scratch/err_vs_length.png`, `scratch/drift_per_subject.png`).

- Model: (marker interval - full-frame mp3 length) = c + drift x length + noise. It is fitted per subject-session,
  and pooled with subject(-session) intercepts. Story lengths span 193-326 s, so the lever arm is small.

| session (system) | mean interval - full length | pooled drift (within-subject) | story-bootstrap 95 % CI | residual SD |
|---|---|---|---|---|
| day 1 (NeuroScan) | 62.9 ms (SD over subjects 0.7) | 70.1 ppm | - | 3.3 ms |
| day 2 (NeuroScan) | 62.0 ms (0.8) | 98.5 ppm | - | 2.8 ms |
| days 1+2 (NeuroScan) | | **76.8 ppm** | 68.7-107.3 | 3.1 ms |
| day 3 (Neuracle) | 32.2 ms (1.2) | **27.1 ppm** | -4.6-62.4 | 3.1 ms |

- Per-subject Theil-Sen estimates are noisy (95 % CIs about +-100 ppm; 16 or 17 trials per session). They scatter
  around the pooled value with no visible cluster: medians 64 (d1), 73 (d2) and 18 (d3) ppm (plot
  `drift_per_subject.png`). Story-level medians (common to all subjects) show the same slopes: d1 88 ppm, d2 122 ppm
  (confounded with voice: the short day-2 stories 26-33 are all male), d3 29 ppm. Story-level residual SD is
  1.5-1.8 ms.
- Independent support for a clock origin:
  - The drift differs by EEG amplifier with the same stimuli and (presumably) the same playback PC.
  - The 300 s rest intervals (timed by the presentation PC) exceed 300 s by 34.6 ms (days 1-2, SD 0.5) and 5.8 ms
    (day 3, SD 1.0). The 29 ms difference is ~96 ppm over 300 s, with the same sign as the speech drift difference
    (~50-70 ppm).
  - An alternative cause (a length-proportional playback overhead) cannot be excluded, but it would not depend on
    the EEG system.
- Size: 77 ppm x 300 s = 23 ms at the end of a NeuroScan story; 27 ppm x 300 s = 8 ms on day 3.
- Jitter: residual SD of the interval ~3 ms (1-ms marker quantisation contributes ~0.4 ms), i.e. ~2 ms per marker.
  Onset jitter relative to the sound is not measurable (no stimtrack).
- Constant c (interval minus full length at zero length): ~40 ms (NeuroScan) and ~25 ms (Neuracle). These are end-of-playback
  overheads (end marker after the buffer drains, etc.). They are not the start latency and should not be used
  to shift onsets.

## 8. Data size
- 25 participants x **4.00 h** of speech each (240.2 min; every participant has all 50 stories once in the selected
  trials). In total **100.1 h**, 1,250 trials.
- Per session: day 1 1.40 h (17 stories), day 2 1.32 h (16), day 3 1.28 h (17). Per voice: female (1-25) 2.09 h,
  male (26-50) 1.91 h. Per system: NeuroScan 2.72 h, Neuracle 1.28 h per participant.
- No stimulus is cut short: every marker interval is 24-115 ms longer than the gapless audio.
- Not yet added to `tmp/review/data_size.csv` (the standardiser runs `data_size.py` on the adaptor).

## 9. Proposed adaptor (for the standardiser)
- One TrialRecord per speech row of `events.tsv` (50 per participant). Condition: `story`, with session/day, EEG
  system and voice (female/male) in the trial metadata. There is no other experimental condition. The system,
  session and story set are confounded (README).
- EEG per session file, read lazily (files are 1.4-2.2 GB float32). Keep 1000 Hz and all channels.
  - Types: scalp `eeg`; HEO/VEO/HEOR/HEOL/VEOU/VEOL `eog`; ECG `ecg`.
  - Keep the raw labels (Day-3 upper case) or normalise case to the 10-10 convention (open question 5).
  - Use the standard_1005 montage only as a template, flagged as not measured.
- Stimulus `story-NN`: gapless ffmpeg decode, channel 0, 48 kHz float32. TextGrid from the MFA file.
  - Tiers renamed to the standard: `phones` = MFA phones; `words` = Chinese words with the legacy segmentation,
    timed by the MFA syllables (first syllable onset to last syllable offset).
  - Keep the Pinyin syllable tier as an extra tier `syllables`.
  - Transcript as UTF-8.
- Onset and drift as in section 6. `drift_ppm`/`jitter_ms` as in section 7.

## 10. Open questions (recommended default in brackets)
1. **Leading mp3 delay.** The playback kept the full mp3 frames (section 6). The first gapless sample was therefore
   probably heard 23.0 ms (1105 samples; or 12.0 ms with a decoder that strips 529) after playback start, plus an
   unknown output latency. The authors segment at the marker with no shift.
   [Onset = marker + 23.02 ms; note "inferred, not measured". Compare 0 / +12 / +23 ms with the validator's lag
   sweep on the pilot; the MLR/brainstem tier latency is the only check available.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): onset = start marker (events.tsv `sample`, never the raw
   codes) + adaptor option `onset_shift_s`, default 1105/48000 s (23.02 ms); 0 or 576/48000 s (12 ms) can be passed
   for the comparison.
2. **Drift correction.** Pooled per system: NeuroScan 77 ppm (clearly non-zero), Neuracle 27 ppm (not significant).
   Per-subject estimates are too noisy to correct per subject.
   [Apply 76.8 ppm to all day-1/2 trials. Apply no correction on day 3 and record 27.1 ppm as estimated-not-applied.
   Alternative: also apply 27 ppm on day 3; the difference is <= 8 ms at story end.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): adaptor option `drift_correction`, default `"system"` =
   76.8 ppm on days 1-2, none on day 3 (sidecar `drift_ppm` 27.1, `drift_corrected_ppm` 0); `None` disables it.
   Values: `DRIFT_PPM` / `DRIFT_APPLIED_PPM` in the adaptor (evidence: section 7). Applied with
   `standardise/clock.py:crop_on_audio_clock` (fractional onset + drift in one quintic-spline interpolation, 1000 Hz
   kept).
3. **Repeated stories** (six full first plays, section 3).
   [Use the authors' selection (the last play) only, and flag those six trials `repeated_presentation: true`. The
   first plays are not standardised.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): last play only. Sidecar `repeated_presentation` is
   `"complete"` for the six trials, `"partial (restarted after 171 s)"` for sub-03 day 1 story 14, null otherwise
   (adaptor `REPEATED`); events.tsv `candidate_pair_count` is copied too (it is also 2 for sub-04 d1 s6, a stray
   start marker, not a repeat).
4. Reference. Day 3 is inferred CPz; days 1-2 are unknown (possibly mastoid/ear).
   [Keep as recorded; metadata "unknown; day 3 inferred CPz from channel amplitudes".]
   Decided (coordinator, 2026-11-22, user asleep; revisit): kept as recorded; sidecar `reference` "unknown
   (undocumented; possibly mastoid/ear, unverified)" on days 1-2 and "unknown (undocumented; CPz inferred from
   channel amplitudes)" on day 3.
5. Channel naming across systems (Day-3 upper case, e.g. `FPZ`, `FCZ`).
   [Map Day-3 names to standard 10-10 case (`Fpz`, `FCz`, `Cz`, `Pz`, `POz`, `Oz`, `Fz`), and record the original
   labels in the metadata. Keep all channels; do not reduce to the 57 common ones.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): EEG labels mapped to the standard_1005 case
   (case-insensitive lookup; days 1-2 unchanged), original labels in the sidecar (`original_labels`). All channels
   kept, types from channels.tsv (EEG `eeg`; HEO/VEO/HEOR/HEOL/VEOU/VEOL `eog`; ECG `ecg`). Template standard_1005
   positions (not measured). The authors' bad channels (`code/preprocessing/config/bad_channels.tsv`, read as data)
   are set in `info["bads"]` (standardiser's choice, as in habersetzer2025).
6. Stereo mp3 with identical channels. [Store one channel, noting L == R bit-exact.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): left channel stored; every decode asserts L == R.
7. Legacy word times are shifted by +300 ms (stories 1-33) / +20 ms (34-50) relative to the MFA alignment and the
   audio. [Do not use their times. Build the words tier from legacy segmentation + MFA syllable times (section 9).]
   Decided (coordinator, 2026-11-22, user asleep; revisit): done (section 12).
8. Rest intervals (300 s, one per session). [Skip (continuous-stimuli default). They could be added later as
   `stimulus=[]` trials.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): skipped.
9. Day-1/2 online low-pass (steep roll-off above ~200 Hz) is undocumented.
   [Note it in the metadata; brainstem-tier validation is most meaningful on day 3.]
   Decided (coordinator, 2026-11-22, user asleep; revisit): sidecar `online_filters` per system.
10. Condition naming. Decided (coordinator, 2026-11-22, user asleep; revisit): condition = voice, `female`
    (stories 1-25, "Dapiaoliang") / `male` (26-50, "Huazai"); session = day (1-3); trial = presentation order
    within the day; story id, day and EEG system in the sidecar (`story_id`, `day`, `eeg_system`). Voice is
    confounded with story set and partly with day/system (day 1 female only, day 3 male only, day 2 both).
11. Alignment label. Decided (coordinator, 2026-11-22, user asleep; revisit): `alignment_method: sw_trigger`,
    `trigger_type: unknown` (README calls them hardware markers; source undocumented; ~2 ms per-marker jitter shows
    they are not sample-locked to the audio). `jitter_ms` 2.1.

## 11. Upstream issues (to report)
1. `word_boundaries/legacy` onsets are +300 ms (stories 1-33) / +20 ms (34-50) relative to the shipped MFA/Pinyin
   alignment and the audio.
2. Raw `.vmrk` codes are MNE's string-sorted enumeration of the original codes, not story IDs. This is undocumented;
   `events.tsv` is correct.
3. The presentation played the mp3 encoder padding (non-gapless). Marker intervals exceed the audio by 54-115 ms,
   and the leading delay (12-23 ms) is not accounted for in the authors' segmentation.
4. Reference, ground, hardware filters, sound delivery and the presentation software are undocumented (README
   acknowledges the first three).
5. `word_boundaries/legacy` omits numerals (e.g. the year in `公元190年`) that are in the transcripts and the
   MFA alignment.
6. sub-01 and sub-11 day 3: the EEG response precedes the markers by a constant 12.66 s / 10.44 s (section 14).
7. sub-25 day 3: recording failure from ~400 s (all channels carry the same common signal, no ECG; section 14).

## 12. Adaptor (standardiser, 2026-11-22)
- **mp3 decoding:** system `ffmpeg` (7.1.1 on the review machine; no Python mp3 decoder is installed in the venv),
  called by `subprocess` with the decoder pinned: `ffmpeg -nostdin -v error -c:a mp3float -i story-NN.mp3
  -map 0:a:0 -f f32le -c:a pcm_f32le -`. ffmpeg honours the LAME/Xing header by default (gapless: encoder delay and
  trailing padding removed). The adaptor asserts that the decoded length equals the MFA TextGrid `xmax` x 48000
  (exact for all 50 stories) and that L == R. Stored: left channel, float32, 48 kHz. The `textgrid` package rounds
  times to 4 digits by default; the adaptor reads with `round_digits=6`, which keeps the exact `xmax`.
- **TextGrid** (relative to the gapless audio start, `xmax` = audio length):
  - `words`: Chinese words of `word_boundaries/legacy/*.tsv` (segmentation only; their times are shifted, section
    4), each timed from the onset of its first to the offset of its last MFA syllable. Words are matched to
    syllables by Hanzi (one per syllable): the concatenated legacy words equal the concatenated Pinyin-table Hanzi in
    every story except for **numerals** (e.g. `190` in `公元190年`, 1-3 per story in 21 stories), which MFA aligns
    as one interval and the legacy table omits; they become their own word. The adaptor raises on any other
    mismatch. POS tags are not carried over.
  - `syllables`: MFA `words` tier (Pinyin with tone), checked equal to `pinyin/boundaries/*.tsv`.
  - `phones`: MFA `phones` tier (initials/finals).
  - Transcript `story-NN.txt` as shipped (UTF-8) as feature `transcript`.
- **Neural:** BrainVision read lazily (`lru_cache` of one header; trials read with `get_data(start, stop)`),
  `crop_on_audio_clock(raw, sample + shift_s * 1000, ceil(n_audio / 48), drift)`: the output has exactly the
  stimulus length at 1000 Hz. Raises if a recording ends before the stimulus (never happened in the pilot).
- **Pilot (2026-11-22, sub-01..sub-12, defaults):** 600/600 trials, no failures, 37.7 min, 46 GB (FlatSinkV1). All
  at 1000 Hz, 64 channels, every trial exactly ceil(audio/48) samples (193.3-325.6 s); 4.004 h per participant;
  day 1 1.402 h, day 2 1.321 h, day 3 1.280 h per participant; `female` 25.06 h, `male` 22.98 h in total. Order
  checks: sub-02 day 2 = 22..33, 18..21; sub-03 day 1 = ..., 12, 14..17, 13. Flags: sub-03 d1 story 14 (partial
  earlier play), sub-09 d3 stories 39 and 50 (complete earlier play). First trial per session, 1-40 Hz robust SD
  (median over channels): days 1-2 14.3 / 13.8 uV, day 3 7.5 uV (matches section 5); no flat or NaN channels.
  Scripts and logs: `tmp/review/pkueeg2025/scripts/{adaptor_test,pilot,pilot_check}.py`, `pilot.log`,
  `pilot_check.log`.

## 13. Timing check: match-mismatch DNN (2026-11-22; pilot sub-01..12; note only, no change)
`fs128_1020-64_broadband` classifier (trained on accou2023; `tmp/review/scripts/dnn_drift_check.py` on the pilot
output, which already has the +23.02 ms onset shift and the 76.8 ppm NeuroScan drift correction applied). 5 s windows,
+-500 ms lag scan; per subject pooled over trials; offsets relative to accou2023 (negative = neural response later).

| session (system) | all windows | first 60 s | last 60 s | late - early | residual drift |
|---|---|---|---|---|---|
| day 1 (NeuroScan) | -74.1 ms [-79.5, -64.4] | -77.2 | -70.9 | +6.4 ms (subj. median +6.7) | -27 ppm |
| day 2 (NeuroScan) | -79.0 ms [-83.1, -75.4] | -83.5 | -74.2 | +9.4 ms (+6.3) | -40 ppm |
| day 3 (Neuracle) | -41.8 ms [-44.6, -39.6] | -39.9 | -43.7 | -3.8 ms (-2.5) | +18 ppm (uncorrected) |

- **Constant offset:** even after +23 ms, responses are 74-79 ms (NeuroScan) and 42 ms (Neuracle) later than in
  accou2023, a ~35 ms difference between the two setups. Clean speech in other datasets scores within +-5 ms, and
  das2019 (-81 ms) / bentum2023 (-68 ms) are the precedents for unmeasured playback latencies of this size. Likely an
  undocumented trigger-to-sound latency that differs between the two recording setups (a synthetic Mandarin voice
  could add some latency difference, but not one that depends on the amplifier). **Not applied** (as for
  das2019/bentum2023); open question for the user: apply a per-system onset correction (~+75 ms days 1-2,
  ~+42 ms day 3 on top of +23 ms)?
- **Drift:** with 76.8 ppm applied, days 1-2 end ~6-9 ms *earlier* than they start relative to the stimulus, i.e. the
  correction overshoots by ~30-40 ppm (true drift ~40-50 ppm?); day 3 (uncorrected) drifts ~+18 ppm, consistent with
  the explorer's 27 ppm [-5, 62]. The early/late CIs overlap: suggestive, not conclusive. Default unchanged
  (76.8 ppm days 1-2); open question: use ~45 ppm instead? Residual error is < 10 ms per story either way.

## 14. Validation (pilot) and session-level checks (2026-11-22)
**Validation summary** (`validation.json`, pilot sub-01..12, average reference over the 57 common channels, run
before the session-offset fix below):
- Low tier passes on all three days. Backward median r 0.238 / 0.218 / 0.237 (days 1 / 2 / 3; 12/12 subjects
  significant); lag sweep peak +2 ms. Forward median r 0.059 / 0.061 / 0.056.
- MLR (30-60 Hz) passes only on day 2 (p 0.0099, 2/12 subjects). It is **treated as not established**: the ~75 ms
  constant offset (section 13) would put a genuine MLR outside the 18-45 ms test window. Brainstem (30-250 Hz)
  fails (day 1: p 0.0495 with 2/12 subjects and a GFP peak at 0 ms, not a response).
- TRF dominant peak 207 / 213 / 178 ms vs herrmann2025 152 ms (shape shift +47 / +63 / +31 ms). Days 1-2 are
  ~25-30 ms later than day 3, the same direction as the DNN offsets (section 13).
- Coherence (`tmp/review/coherence_batch/{128,native}/pkueeg2025_day{1,2,3}.json`, ratio to a circular-shift null):

  | band | day 1 | day 2 | day 3 |
  |---|---|---|---|
  | 0.2-1 Hz | 13.6 | 9.8 | 11.4 |
  | 1-4 Hz | 7.1 | 7.5 | 5.7 |
  | 4-8 Hz | 4.5 | 4.0 | 4.1 |
  | 8-15 Hz | 1.8 | 2.0 | 1.9 |
  | 15-30 Hz | 1.2 | 1.3 | 1.3 |
  | 30-60 Hz | 1.1 | 1.1 | 1.1 |

  Native rate: 60-500 Hz 1.02-1.07. The strongest low-frequency coherence of the batch.
- Decided (coordinator, 2026-11-22, user asleep; revisit): `validation_tier="low"` for **all** trials (provenance
  call). The pilot fifs written before this change carry `null`, except the re-standardised sub-01/sub-11 day 3.
- Data size: full dataset 25 x 4.00 h = 100.1 h (pilot 12 subjects, 48.0 h).
- **Open questions** (still open):
  1. The constant ~75 ms (days 1-2) / ~42 ms (day 3) response offset is not applied (section 13).
     Decided by the user (2026-11-22): document only, no onset correction for now.
  2. The 76.8 ppm drift correction on days 1-2 may overshoot by ~30-40 ppm (section 13).

**Suspect sessions** (validation: sub-11 day 3 backward r -0.001; sub-01 day 3 0.019; their days 1-2 fine).
Scripts: `tmp/review/pkueeg2025/scripts/{session_xcorr,decoder_scan,session_quality,verify_backward,restandardise}.py`;
logs `decoder_scan_*.log`, `verify_backward.log`; tables `scratch/decoder_scan_*.tsv`.
- **Markers and mapping are correct.**
  - events.tsv equals the `.vmrk` (sample = vmrk position - 1; day-3 codes S 2..S 18 = stories 34..50).
  - Order is the standard one, there are no extra markers, and the marker intervals match each story's length to
    the ms (as in every session, section 3).
  - Testing each trial against the neighbouring stories' envelopes (k = -2..+2 in presentation order) gives no
    peak for k != 0.
- **The EEG is offset from the markers by a constant.**
  - Method 1, envelope-EEG cross-correlation (1-8 Hz, GFP over channels, +-60 s; `session_xcorr.py`). For
    sub-11 day 3, the matched story peaks at -10.30 s (17x the off-peak level; good sessions peak at +0.16 to
    +0.20 s), at the same lag in 16/17 single trials.
  - Method 2, a subject-independent backward decoder (`decoder_scan.py`). It is trained on day 3 of the other
    pilot subjects at the marker alignment (59 ch, lags 0-406 ms, 64 Hz) and applied to whole sessions.
    - sub-11 day 3: pooled peak at **-10.443 s** (r 0.194 vs noise SD 0.010; r at 0: -0.003). All 17 trials peak
      at -10.42 to -10.47 s, as do the 40 s windows within trials, so the offset is constant.
    - sub-01 day 3: pooled peak at **-12.660 s** (r 0.071 vs 0.006). All 17 trials peak at -12.63 to -12.81 s
      (r 0.025-0.11).
  - Locating every one of the 50 stories anywhere in the sub-11 day-3 session (markers ignored) finds only the 17
    day-3 stories (z 7.6-12.3, all at marker - 10.44 s). The 33 other stories are at noise level (z ~4.0-4.8).
  - The cause is unknown. The marker intervals are on the same clock as the audio, so the shift is between the
    marker stream and the EEG samples (e.g. Neuracle's separate data/event files, or a cut at the start). It is
    probably introduced in the authors' BDF -> BrainVision conversion or the original recording.
  - **Fix:** `SESSION_OFFSET_S = {(1, 3): -12.660, (11, 3): -10.443}` is added to the onset. Sidecar fields:
    `session_offset_ms` and `quality: "corrected: ..."`.
  - Verified after re-standardising (`verify_backward.py`, LOTO backward model on the standardised trials):
    sub-11 day 3 mean r 0.240 (trials 0.153-0.282; was -0.001), sub-01 day 3 0.128 (0.042-0.166; its day 1 by
    the same method 0.121), control sub-09 day 3 0.225. The lag of the best r is the same as in the control.
- **sub-09 day 3 (DNN -152 ms):** the decoder scan peaks at 0 ms (16/17 trials; r 0.06-0.14). There is no offset;
  the DNN value is unexplained and not acted on.
- **Remaining subjects (13-25, not in the pilot), all three days** (`decoder_scan.py`, +-60 s): every session
  peaks within -21 to +34 ms of the marker alignment, **except sub-25 day 3**. That session shows no tracking at
  any lag within +-30 min, and no story is found anywhere in it (all at noise level).
  - Signal (`session_quality.py` and SD per 60 s window): ~200 uV in the first minutes. From ~400 s, every
    channel, including ECG and the four EOG channels, has the same 1-40 Hz SD (1.4-60 uV, varying with time).
    There is no ECG signal (other subjects: ECG SD 15-450 uV). This looks like a lost reference/ground or
    electrode contact; the data cannot be fixed.
  - Kept and flagged: `SUSPECT[(25, 3)]`, sidecar `quality: "suspect: recording failure ..."`. Its days 1-2 are
    normal.

## 14. Drift re-estimation (2026-11-22; pilot sub-01..12; note only, no change)
Two independent estimates from the EEG itself, compared with the marker estimate A (section 7). Both use uncorrected
trials (the adaptor with `DRIFT_APPLIED_PPM` set to 0 in memory, onset shift 23.02 ms). sub-01 and sub-11 day 3 are
excluded because they do not track (backward r ~0). Scripts, caches and figures:
`tmp/review/pkueeg2025/drift_reestimate/` (`scripts/run.py` per subject-day and drift, `estimate.py`, `analyse.py`,
`validate_candidates.py`, `refcheck.py`/`refanalyse.py`; results in `results/`).

- **B (DNN):** accou2023 `fs128_1020-64_broadband` lag scan (5 s windows, 1 s hop, +-500 ms). Windows are averaged
  into 30 s blocks, and the blocks are averaged over the subject-day's stories at the same time-in-story. Block
  lag = sub-sample peak. Drift = minus the Theil-Sen slope of the block lags.
- **C (backward decoder):** leave-one-story-out ridge decoder (57 common channels minus bads, average reference,
  0.5-8 Hz, 64 Hz, lags 0-250 ms). The held-out reconstruction is scored in 30 s (C30) or 60 s (C60) windows over
  shifts of +-150 ms (2 ms steps after 8x upsampling). Blocks are pooled over stories as for B. Drift = the Theil-Sen
  slope.
- **CIs:** pooled per system with subject-bootstrap 95 % CIs (NeuroScan: days 1+2 pooled per subject).
- **Per-story Theil-Sen** (one line per story) is far too noisy (IQR about +-300 ppm per story) and is not used.
- **Repo `align.scan.joint_fit` + `pooled_drift`** collapses to ~0 ppm here, with an implausibly small SE. At zero
  drift every window is read at an integer lag, so the estimate is biased towards 0 (likely mechanism, not tested).
  Not used.

| system | A markers (section 7) | B DNN | C30 decoder | C60 decoder |
|---|---|---|---|---|
| NeuroScan, days 1+2 (n=12) | 76.8 [68.7, 107.3] | **47.4 [36.6, 56.5]** | 23.9 [15.9, 29.3] | 21.8 [13.5, 27.7] |
| day 1 only | 70.1 | 51.8 [40.6, 67.7] | 24.1 [14.6, 32.9] | 22.6 [13.9, 30.0] |
| day 2 only | 98.5 | 34.9 [15.4, 50.8] | 19.8 [10.8, 31.6] | 20.0 [5.3, 31.8] |
| Neuracle, day 3 (n=10) | 27.1 [-4.6, 62.4] | **28.3 [13.2, 39.2]** | -5.7 [-13.5, 7.4] | 5.1 [-6.0, 14.3] |

- **Per-subject consistency** (`results/drift_per_subject_estimates.png`; `results/lag_vs_time_{B,C30,C60}.png`):
  - Medians of the per-subject values: NeuroScan B 49.8 [45.8, 57.2], C30 25.1 [14.2, 30.6]; Neuracle B 20.8
    [0.0, 37.1], C30 -1.2 [-20.7, 7.9].
  - NeuroScan B: 10 of 12 subjects lie in 44-66 ppm (outliers sub-12 111, sub-11 -54 on day 2).
  - sub-09 day 3 B is unusable (182 ppm, CI +-400; the DNN peak is unstable).
  - B > C in 11 of 12 subject-days on day 1 and 8 of 10 on day 3. B and C disagree by ~20-25 ppm in both systems.
- **Reference check of the estimators** (weissbart2019: stimtrack-measured drift 1.2 ppm, not corrected; 12 of 13
  subjects (sub-000 not run), 15 stories of ~160 s each; same pipeline; `results/refcheck_weissbart2019.json`):

  | estimator | as recorded (truth ~1 ppm) | with an injected correction of 50 ppm (truth ~-49) |
  |---|---|---|
  | B | **+1.3 [-21.9, 20.1]** | -48.8 [-71.7, -27.4] |
  | C30 | +20.3 [-12.3, 57.3] | -39.3 [-66.0, -2.7] |
  | C60 | +33.4 [1.7, 71.6] | -35.7 [-66.8, 3.1] |

  - B is unbiased there and recovers the injected change exactly (-50.1 ppm).
  - C reads high (+20/+33) and is less precise. On weissbart C > B, on pkueeg C < B, so the B-C gap is not a fixed
    bias of either method. The reference check supports B; C is the noisier estimator.
- **Validation of candidates:**
  - Each candidate is applied with the adaptor's own warp (`crop_on_audio_clock`) and scored per subject; NeuroScan
    days are averaged per subject. Wilcoxon tests are paired over subjects (n = 12 / 10). Figure:
    `results/validation_candidates.png`. Tables: `results/validation.json`, `results/validation_subject_day.tsv`.
  - The residual drift with B or C equals estimate minus applied value, as it should (sign and scale check of the
    in-memory warp). It is not an independent test.
  - 30-60 Hz TRF: half-wave-rectified audio, lags -150..250 ms, scored -100..200 ms. SNR = RMS in the window vs the
    -75..-20 ms noise window. "Offset window" = 18-45 ms + the constant DNN offset (+77 ms NeuroScan, +42 ms
    Neuracle, section 13).
  - The 30-60 Hz response is weak (SNR ~1.0-1.3; the grand GFP peaks at ~140 ms NeuroScan and ~90 ms Neuracle), so
    this test has little power.

  | NeuroScan candidate (ppm) | 0 | 24 (C) | 47 (B) | 76.8 (A, default) |
  |---|---|---|---|---|
  | residual B / C30, pooled | 47.4 / 23.9 | 22.9 / -0.1 | **-0.7** / -23.1 | -29.8 / -52.8 |
  | held-out decoder r, median | 0.2345 | 0.2347 | 0.2347 | 0.2344 |
  | TRF SNR, offset window: median (mean) | 1.09 (1.05) | 1.15 (1.13) | 1.20 (**1.28**) | **1.31** (1.17) |
  | TRF SNR, 18-45 ms: median (mean) | 0.96 (0.94) | 0.98 (0.99) | **1.14** (1.10) | 1.10 (**1.14**) |

  - Decoder r: every non-zero candidate beats 0 (24 vs 0 12/12 subjects, p = 0.0005; 47 vs 0 p = 0.002; 76.8 vs 0
    p = 0.016). 47 vs 24: p = 0.027 (8/12). 76.8 vs 47: p = 0.79. The differences are < 0.001 in r.
  - TRF SNR, offset window: 47 vs 0 p = 0.064 (9/12 subjects higher); 76.8 vs 0 p = 0.27; 76.8 vs 47 p = 0.18
    (4/12 higher at 76.8). 18-45 ms window: 47 vs 0 p = 0.052; 76.8 vs 47 p = 0.91.
  - Neuracle 27.1 vs 0: decoder r p = 0.13 (8/10 higher); TRF SNR, offset window, 1.15 -> 1.38 median, p = 0.084
    (8/10 higher); 18-45 ms p = 0.70. Residual B 4.2 [-12.9, 12.2] at 27.1.
- **Conclusion:**
  - Correcting a positive drift beats no correction on NeuroScan (decoder r significant, TRF SNR trend).
  - The data cannot separate 47 from 76.8 ppm (r and SNR are flat between them).
  - B, the estimator validated on weissbart2019, puts NeuroScan at 47 ppm, with a CI [37, 57] that excludes 76.8.
    This agrees with the section 13 residual of -27/-40 ppm against 76.8. A's CI lower bound (68.7) is above B's
    CI, so the two estimates are in tension. A is marker intervals vs mp3 length, with a small lever arm and a
    possible length-proportional playback overhead (section 7).
  - Neuracle: A (27.1) and B (28.3) agree; C (~0) does not. Correcting 27 ppm gives a non-significant SNR trend
    (p = 0.08).
- **Recommended alternative:**
  - NeuroScan days 1-2: **47 ppm** (B). Moderate confidence: B's CI excludes both 76.8 and C's 24, but the
    validation does not separate 47 from 76.8. Residual error with 76.8 instead of 47 is ~9 ms at the end of a
    300 s story.
  - Neuracle day 3: **27 ppm** (A = B). Low-to-moderate confidence: C disagrees and the validation trend is not
    significant.
- **Decided by the user (2026-11-22): keep 76.8 ppm; alternatives logged for the second pass.** Adaptor default
  unchanged: 76.8 ppm NeuroScan, none Neuracle.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**poor**: Markers (not sample-locked, ~2 ms jitter) + 23 ms inferred shift; 2 sessions get decoder-measured offsets; drift 76.8 ppm from markers kept (DNN says 47); DNN -74/-42 ms documented as timing error; low tier.

## Restructure 2026-11-25 (not yet re-validated on data)
- dataset.json: listening_hours 100.1 (was 68.1; 25 participants x 4.00 h, size section).
- TextGrid written by `iohelpers.textgrid` (was the `textgrid` library; the MFA TextGrid is still read with it):
  same intervals, long text format, gaps filled up to the MFA end time.
- Bad channels from `bad_channels.tsv` marked with `iohelpers.mark_bads` (strict: a name missing from the
  recording raises a ValueError, as the old lookup raised a KeyError). Audio unchanged (ffmpeg float32 decode).
