# straetmans2021: mobile EEG, attend one of two talkers while sitting or walking (OpenNeuro ds003801)

20 participants x 6 narratives (~4.5-6.7 min) of a German audiobook; two competing talkers (to-be-attended story
and to-be-ignored snippets of the same book) plus 60 spatialised environmental "salient events". Three narratives
were heard while sitting, three while walking a route indoors (alternating; starting condition alternates across
participants). Wireless 24-channel SMARTING amplifier at 250 Hz, recorded on an Android phone via LSL.
**No audio, no envelope, no attended side, no salient-event markers are shipped**: the release is EEG plus
narrative start/stop markers only. Neural data are raw (DC, unfiltered, original reference).

## 1. Source
- OpenNeuro ds003801 v1.0.0 (the only snapshot, 2021-11-09), DOI 10.18112/openneuro.ds003801.v1.0.0,
  "Neural Tracking to go". 165 files, 1.23 GB. **Licence CC0** (`dataset_description.json`).
- Paper: Straetmans L, Holtze B, Debener S, Jaeger M, Mirkovic B (2021). Neural tracking to go: auditory attention
  decoding and saliency detection with mobile EEG. *J Neural Eng* 18:066054
  (`data_campaign/papers/straetmans2021.pdf`). Data availability statement points to this DOI.
- Shared code: none.
- Registry: `straetmans2021` (source `openneuro`). Downloaded 2026-11-23 into `tmp/review/straetmans2021/download/`
  (52 s, 1 attempt). **Integrity**: all 166 listed files present, every size equal to the OpenNeuro listing (the API
  gives no checksums); all 20 `.set`/`.fdt` pairs read completely with MNE (no NaN).

## 2. Layout
- BIDS: `sub-0XX/eeg/sub-0XX_task-NeuralTrackingToGo_{eeg.set,eeg.fdt,eeg.json,channels.tsv,electrodes.tsv,
  coordsystem.json,events.tsv,events.json}`; `participants.tsv` (sex, age, handedness), README (3 lines),
  `CHANGES`.
- **No `stimuli/` folder.** No `scans.tsv`, no behavioural files, no motion channels.
- EEGLAB `.set` (2020.0), `setname` like `ad_list02`; `EEG.etc` keeps the XDF stream header: stream
  `Android_EEG_010037`, source `Smarting`, **`channel_count` 27** (24 EEG shipped; the other 3 are presumably the
  amplifier's motion sensors, not shipped), `nominal_srate` 250, `effective_srate` per subject (section 7).
- Each recording length is a whole number of seconds (2375-2630 s): the XDF EEG stream was probably trimmed on
  conversion.

## 3. Stimulus <-> trial mapping
- Events (`events.tsv` = EEGLAB events, identical in both): `start_exp`; `rest_sit`, `rest_stand` (1 min rest EEG
  each, before the first narrative); per narrative `start_sound<k>_<sit|walk>` and `stop_sound<k>_<sit|walk>`,
  k = 1..6; button presses `play` (start of each block; 20-52 ms before the start marker), `yes`/`no` (answers to
  comprehension questions between blocks). No salient-event or control-event markers.
- **Every subject has all 6 narratives exactly once**, 3 sit + 3 walk, alternating (checked in all 20,
  `explore/summary.json`). Narrative order and the sit/walk assignment of each narrative vary across subjects.
- The paper: six ~5 min to-be-attended stories (Kling 2009, *Die Känguru-Chroniken*, male narrator, 48 kHz),
  each paired with one fixed to-be-ignored stimulus (snippets of the same audiobook concatenated to 5 min) "saved
  into a stereo file"; attended stream spatialised to -45 or +45 deg azimuth (left/right side condition), ignored
  to the opposite side; salient events in a third stream (60 events, random azimuth in 5-deg steps, outside
  +-30..60 deg). The side condition per subject is **not shipped** (not in `participants.tsv`).
- Paper: 21 recruited, 2 excluded for technical difficulties, 19 analysed. The release has 20 (sub-001..020); which
  of them the paper excluded is not documented.
- Rest blocks (`rest_sit`, `rest_stand`) are not speech and are not standardised.

## 4. Speech features available
- **None.** No audio, envelope, transcript or word timing. Only snapshot 1.0.0 exists (checked via the GraphQL
  `snapshots` query, 2026-11-23), so no earlier version with audio (unlike holtze2021). The audiobook is commercial
  (Kling 2009); the Oldenburg datasets in the campaign (holtze2021, jaeger2025, mirkovic2016) use different
  narratives (fairy tales), so no other source in the campaign is known.
- Consequence: trials are standardised with `stimulus=[]` (PLAN 1, "datasets without speech are still
  standardised"), with the reason in the sidecar. The narrative id (1-6) is kept in the sidecar so that the audio
  can be attached if the authors ever share it.

## 5. Neural data
- SMARTING (mBrainTrain) wireless 24-channel DC amplifier, EasyCap 24 passive Ag/AgCl, 10-20 positions, 250 Hz,
  Bluetooth to a Sony Xperia (Android 5.1.1), LSL in the Smarting app, saved as XDF (paper). `eeg.json`:
  `EEGReference` "common", `SoftwareFilters` n/a, `PowerLineFrequency` 50.
- Channels (identical in all 20): Fp1 Fp2 Fz F7 F8 FC1 FC2 Cz C3 C4 T7 T8 CPz CP1 CP2 CP5 CP6 TP9 TP10 Pz P3 P4 O1
  O2, all `EEG`, `microV` (`channels.tsv`). No EOG, ECG, stimtrack, trigger or audio channel.
- Units: uV in the `.fdt`, MNE scales to V. 1-40 Hz RMS per channel 5-35 uV (median over subjects), frontal Fp1/Fp2
  highest (blinks): plausible. Raw DC offsets up to ~100 mV (DC amplifier, no high-pass): **raw, not
  preprocessed** (paper's ICA/ASR/filtering not applied).
- **Reference**: the paper says "Channel Fz was used as reference electrode", but Fz is a recorded channel with
  signal (median 8 uV RMS), so the data are not Fz-referenced; they are not average-referenced either (channel sum
  ~13x a channel's RMS). FC1/FC2/Cz have the lowest RMS in nearly every subject, which points to a reference near
  FCz (the usual SMARTING 24 cap layout: reference FCz, ground AFz; **inferred, not documented**). Kept as shipped,
  recorded as "common reference electrode not in the data (paper: Fz, contradicted by the data; probably FCz)".
- TP9/TP10 are 10-10 cap electrodes (the paper's "linked mastoid" re-reference used them). They are kept as `eeg`
  under their own names (not renamed M1/M2: they are cap positions, not mastoid electrodes; wang2025 precedent).
- Positions: template positions from the `.set` chanlocs (`smarting-24channels.locs`, EEGLAB spherical); MNE
  builds a head-frame montage from them. `electrodes.tsv` has unit-sphere coordinates labelled "mm"/"CTF" (upstream
  inconsistency). Template only, no digitisation.
- Bad channels (`explore/bad_channels_heatmap.png`, `explore/bad_channels_per_trial.png`; 1-40 Hz RMS per channel
  and narrative, and 50 Hz power):
  - **sub-018 P4**: 1200-2500 uV RMS in 4 of 6 narratives, ~35 uV (3.5x the subject median) in the other 2:
    intermittently broken electrode. **Marked bad** for the whole participant.
  - sub-016 TP9: 1119 uV RMS over the whole recording, but normal within all 6 narratives (artefact outside the
    trials): not marked.
  - sub-010: all channels 45-70 uV RMS and raised 50 Hz on every channel (common-mode noise, poor ground/reference
    contact); no single bad channel: not marked, noted in the README. sub-002 is also noisy overall (~22 uV).
  - sub-001 FC2 / sub-018 P4: strong 50 Hz; FC2 otherwise normal: not marked.
  - Walking narratives are noisier than sitting ones in several subjects (e.g. sub-008: 2x), as expected.
  - Fp1/Fp2 at 3-5x the median (blinks) in most subjects: physiological, not marked.
- Rate: 250 Hz kept (native <= 1024 Hz; never upsample). The 30-250 Hz brainstem tier is impossible at this rate,
  and without a stimulus no tier can be tested at all (section 12).

## 6. Alignment
- Audio, markers and behavioural responses all came from **Presentation for Android (1.2.1) on the same phone**
  that received the EEG via Bluetooth; markers via LSL into the Smarting app's XDF (paper). So markers are
  **software markers** (`trigger_type` = software, paper): the marker is a request time on the phone's clock, not
  the sound onset. Android audio output latency (typically tens of ms, variable) and Bluetooth/LSL timestamping of
  the EEG are both uncorrected and undocumented.
- Proposed (no alternative without audio): trial = narrative, **onset = `start_sound<k>` marker as shipped, end =
  `stop_sound<k>`** (the recorded span; trial lengths differ across subjects by the marker jitter, section 7);
  `alignment_method` = `sw_trigger`; no onset correction (none can be estimated without the audio or a stimtrack).
- Neural-only check (`scripts/straetmans2021/onset_erp.py`, `explore/onset_erp.png`, `explore/onset_erp_sit.png`):
  the grand-average ERP at the 120 start markers (average reference, 1-20 Hz) shows no clear auditory N1 near
  100 ms, only a broad GFP rise at 0.2-0.6 s (also in sitting blocks), confounded by the thumb press on the phone's
  `play` button 20-52 ms before each marker and by stories that may start with silence. **Inconclusive** about
  onset latency; not usable as a timing check.

## 7. Cross-subject duration check (`scripts/straetmans2021/drift_check.py`, `explore/drift_check.{png,json}`)
- Marker durations (stop - start) per narrative across the 20 subjects: SD 12-27 ms around the median; median
  |deviation| 6 ms; the errors are **one-sided** (up to +74 ms; never below -12 ms), i.e. occasionally a late stop
  or early start marker. Narrative lengths (median marker duration): 1: 301.33 s, 2: 294.57, 3: 368.42,
  4: 312.46, 5: 270.15, 6: 402.11 s (1949.0 s in total).
- LSL `effective_srate` (amplifier samples vs the phone's LSL clock): within +-3 ppm in 19 subjects (+-1.2 ms over
  400 s); **sub-001 +27.0 ppm** (11 ms over 400 s). sub-001 is also the subject with uniformly long marker durations
  (+6..+22 ms); scaling by `effective_srate` reduces them to ~+5..+11 ms. Overall the scaling barely changes the
  residuals (median |res| 6.0 -> 5.4 ms, SD 16.7 -> 16.6 ms): **jitter dominates, drift is at most a few ppm**.
- What this measures: amplifier vs phone clock, which is what places the markers on the EEG timeline. Whether the
  phone's audio clock drifts against its system clock cannot be checked without the audio. **Not corrected**
  (the rules apply drift corrections only from hardware triggers or an audio copy); the per-subject LSL value is
  stored in the sidecar as `drift_ppm` with `drift_corrected_ppm` = 0.
- Jitter estimate for the sidecar: ~15 ms (SD of duration residuals / sqrt(2) ~ 12 ms, with a one-sided tail to
  +74 ms); onset latency of the sound after the marker unknown (Android: likely tens of ms).

## 8. Data size
- 20 participants x 6 narratives: 32.5 min of attended speech per participant (all identical, marker-based:
  1949 s), **10.83 h** in total (sheet: 9.5 h for 19 participants x 30 min). Per condition 16.2 min per
  participant (16.1-16.4), 5.41 h each for sit and walk. The ignored stream is simultaneous and counted once.

## 9. Upstream issues
- No stimuli (audio or envelopes), no attended-side (left/right) per participant, no salient/control event markers,
  although the paper's analyses need all three. The README is three lines.
- Reference: paper says Fz, but Fz is a recorded channel with signal; `eeg.json` says "common".
- `electrodes.tsv` unit-sphere coordinates labelled mm / CTF.
- 20 participants shipped vs 19 analysed in the paper; which one was excluded is not stated.
- The 3 non-EEG channels of the 27-channel LSL stream (presumably motion) are not shipped, although the paper
  mentions gyroscope/accelerometer analyses.

## 10. Open questions (recommended defaults in brackets)
1. Include a dataset without any stimulus? [Yes, per PLAN 1 (`stimulus=[]`, reason in the sidecar); it is low
   value for speech tracking until the audio is shared. The user may want to ask the authors for the six stereo
   wavs, the side condition and the salient-event times; never contact them ourselves.]
2. Trial window: start -> stop marker as recorded. [Accept; alternative: start + the narrative's cross-subject
   median length, which makes all trials of a narrative the same length.]
3. Drift: not corrected; sidecar `drift_ppm` = LSL `effective_srate` ppm (sub-001 +27, others +-3). [Accept.]
4. Reference kept as shipped ("probably FCz"). [Accept.]
5. TP9/TP10 kept as `eeg` under their names (not M1/M2). [Accept.]
6. Bads: sub-018 P4 only. [Accept.]
7. Trial number = presentation order 1..6; condition = `sit`/`walk`; narrative id in the sidecar. [Accept.]
8. Rest EEG (1 min sit, 1 min stand) not standardised. [Accept.]

## 11. Adaptor (implemented with the defaults of section 10, 2026-11-23)
- Trial = narrative in presentation order (1-6), session 1, condition `sit`/`walk` (from the marker name),
  `stimulus=[]`. EEG cropped from the `start_sound<k>` sample to the `stop_sound<k>` sample (`round(t * 250)`),
  annotations dropped (no events inside a narrative), 250 Hz, uV -> V by MNE, 24 `eeg` channels with the
  template montage, original reference, no filtering. `info['bads']`: sub-018 P4.
- Parse checks: 6 start/stop pairs per subject, each 0-600 s long.
- Sidecar: `sw_trigger`, trigger type software (paper), `drift_ppm` = LSL `effective_srate` ppm (not applied,
  `drift_corrected_ppm` 0), `jitter_ms` 15, `validation_tier` null (untestable: no stimulus), `narrative`, `start_marker_s`,
  `stop_marker_s`, `stimulus_unavailable` (reason), sex, age, reference, positions.
- Pilot = all 20 subjects: 120 trials, 0.94 GB, ~1 min (`tmp/review/straetmans2021/standardised_v2/`, final
  adaptor after review; `standardised/` = first run, identical data, older sidecar wording; log
  `standardise_v2.log`). Read back with `FlatSourceV1` (file names without stimulus tokens parse).

## 12. Validation (2026-11-23, all 20 subjects; `validation.json`)
- **No model tier can be tested: no stimulus.** The validator (`--reference average --tiers low`) skips all 120
  trials ("no speech audio or envelope stimulus") -> tier `none` (sidecar `validation_tier` null = untestable). Independently of that, 250 Hz rules out the
  30-250 Hz brainstem tier (and leaves 30-60 Hz mlr only marginally possible).
- Sanity (`scripts/straetmans2021/sanity.py`, `tmp/review/straetmans2021/sanity_v2.json`): 120 trials, 6 per subject,
  250 Hz, 24 channels; no flat or NaN channels (bads excluded); median channel SD after a 1 Hz high-pass
  30-93 uV per trial (within the EEG unit range 1-200 uV; includes walking EMG and mains up to 125 Hz); trial length
  vs the narrative's cross-subject median length -12..+75 ms (median |d| 5.9 ms). No flags.
- Timing evidence: marker-duration jitter and LSL drift (section 7, `explore/drift_check.png`); narrative-onset ERP
  inconclusive (section 6, `explore/onset_erp.png`, `explore/onset_erp_sit.png`).
- Not run (need a stimulus): coherence, DNN offsets, per-condition validation, attention contrast.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**none**: No stimulus shipped (software LSL markers, Android latency uncorrected); sanity checks only.

## Restructure 2026-11-25 (not yet re-validated on data)
- Adaptor subclasses BaseAdaptor; bads via iohelpers.mark_bads (strict). No stimulus, no other change.
