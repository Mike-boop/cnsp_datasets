# kern2022: notes

Findings that explain `adaptor.py` and `drift.py`. Review scripts and results: `tmp/review/kern2022/`,
`tmp/review/scripts/kern2022_*.py` (2026-11-23).

## 1. Source
- Donders Repository DSC_3018045.02_116_v1, doi:10.34973/5qxw-nn97, licence CC-BY-4.0 plus the Radboud data use
  agreement (`LICENSE.txt`). Every file except `MANIFEST.txt`/`README.txt`/`LICENSE.txt` needs the user's data.ru.nl
  WebDAV credentials (`RADBOUD_USERNAME`/`RADBOUD_PASSWORD`, from `secrets.json` keys `ru-rdr-usr`/`ru-rdr-pwd`);
  access worked with them, no manual agreement step. Acknowledge "Data were provided (in part) by the Radboud
  University, Nijmegen, The Netherlands".
- Paper: Kern, Heilbron, de Lange & Spaak 2022, eLife 11:e80935, doi:10.7554/eLife.80935
  (`data_campaign/papers/kern2022.pdf`). The paper's EEG replication uses Di Liberto et al. 2020; its 10 wavs are
  in this release too (`MusicData/MusicEEG/wav/audio01-10.wav`; useful for diliberto2020, whose Dryad record may
  lack audio).
- Code in the release: `Code/MEGExperiment` (Psychtoolbox presentation), `Code/MEEGPreprocessing` (FieldTrip),
  `Code/MEEGAnalysis`, `Code/MusicAnalysis`. Read, not run.

## 2. Layout and download
- 3736 files, 358 GB. Registry entry `kern2022` keeps 1162 files, 207 GB: the raw CTF recordings
  `MEGData/sub0NN/ses-meg01/meg/sub0NNses01_3018045.02_<date>_01.ds` (5.1-7.3 GB each, one per participant, plus a
  `hz.ds` head-localisation run), `MEGData/logfiles/sub0NN.mat` (Psychtoolbox timing), questionnaires, code, the
  stimuli and their MIDI/score files. Excluded: `MEGData/sub*/mri` (empty after the authors' privacy move:
  `MEGData/README_PRIVACY`; no Polhemus head shapes are shipped), `MEGSource` (41 GB), `preproc` (103 GB, the
  authors' 400 Hz FieldTrip data), `eyetracker` (6 GB EDF), the MCCC training corpus and the trained music models.
- Downloaded 2026-11-23 (3 workers, ~55 MB/s, 54 min); every file has the listed size; sha256 vs `MANIFEST.txt`:
  see section 10.

## 3. Stimulus <-> trial mapping
- 35 participants (sub001-sub035), one session each. 19 monophonic Western classical pieces (codes 101-119;
  `MusicData/MusicMEG/OverviewMusicMEG.csv`: composer, piece, instrument piano/oboe/flute, tempo), 78.8-275.9 s,
  43.3 min in total, each played once per participant in a pre-randomised order (`WavMain/SoundOrder.csv` column =
  participant; equals the `stimulus` order in the logfiles).
- Before the pieces: three test snippets (`WavTest/1-3.wav`, 15.9/12.1/11.9 s) to set the volume (paper, Procedure).
  Kept as condition `test` (everything played is kept); the volume may have changed during them.
- `Code/MEGExperiment/WavMain/<code>.wav` is byte-identical to `MusicData/MusicMEG/wav/<Filename>.wav`; stimuli are
  named by `Filename` (e.g. `JSBach_FlutePartitaBWV1013-4`), test snippets `test1-3`.
- One trial per piece trigger in recording order (trial 1-3 test, 4-22 music).

## 4. Stimulus features
- Wavs: 44.1 kHz int16 **stereo with different left and right channels**. `RunSingleTrial.m` plays
  `y(1,:)` (channel 0, left) on both ears; the paper says "the right audio channel ... was duplicated". The audio
  copy settles it: it matches channel 0 (r = -0.84 to -0.90 on well-covered pieces in sub001) and not channel 1
  (|r| 0.24-0.36). The adaptor stores channel 0 as a mono stimulus.
- Note-level MIDI annotations (`MidiDataMEG.csv`: onset/offset s, pitch, instrument) are not carried (open question
  4). Their times match the wavs within the instruments' attack (onset-train lag 10-40 ms) for 17/19 pieces; 111 and
  112 gave 270 and 510 ms (probably periodicity in the onset-train correlation, not checked further).
- Almost all energy is above 300 Hz (instrument fundamentals ~500-1600 Hz): the share of power in 30-290 Hz is
  0.9-1.5% for pieces 107, 109, 113, 114, 116, 118, 0.6% for test snippets 1 and 3, and <= 0.4% for the rest.

## 5. Neural data
- CTF-275 (VSM/CTF) at the DCCN, 1200 Hz, online low-pass 300 Hz (paper). 269 axial gradiometers (MNE `mag`; 6 of
  275 missing), 29 reference sensors (`ref_meg`). Stored without synthetic gradiometer compensation (grade 0, as
  recorded; the authors applied G3BR in FieldTrip). SI units (T) as read by MNE; 1-40 Hz median SD ~157 fT
  (sub001). `BadChannels` files are empty; no bads marked (section 9).
- Analog channels (sub001-sub035): UADC001/UADC002 = audio copy (the played channel, inverted; section 6);
  UADC003/UADC004 = the same audio, 30x stronger, in **sub001 only** (noise in the others); UADC005-007 = EyeLink x,
  y, pupil (0.3-1 Hz dominated; UADC007 clips at -5 V in blinks), as in armeni2022 (same lab); UADC008-013 constant
  offsets with noise. EEG057-064: same pattern as armeni2022 (EEG060 flat, the others DC offsets with uV-mV noise;
  the paper mentions no EEG/EOG), so unconnected inputs.
- Kept: MEG, reference sensors, UADC002 (audio copy, `misc`), UADC005-007 (EyeLink, `misc`). Dropped: UADC001 (same
  audio), UADC003/004, UADC008-013, EEG057-064, HLC (continuous head localisation), HADC/HDAC, SCLK, UPPT001/002
  (triggers), UDIO001 - the armeni2022 choices.
- Fiducials (nasion, LPA, RPA) and dev_head_t are in the .ds; no head shapes.
- Resampled 1200 -> 1000 Hz (anti-alias FIR + quintic spline in `crop_on_audio_clock`, the same interpolation as
  any drift correction; `sfreq=None` keeps 1200 Hz). As armeni2022.

## 6. Alignment
- Triggers on UPPT001 (BITSI box, parallel port): 128 then 1/2/3 for the test snippets, 250 at the fixation dot
  then the piece code 101-119 at the piece; UPPT002 = button presses. 19 piece codes and 3 test codes in every
  recording (section 10).
- Presentation (`RunSingleTrial.m`): the wav is preloaded, `PsychPortAudio('Start', h, 1, 0, 1)` waits until
  playback has started, then the trigger is sent: a software trigger after the sound start. Test snippets
  (`RunTestTrials.m`) send the trigger *before* a non-blocking `Start`, so their delay differs.
- The authors epoched on the trigger without any delay correction (`preproc_before_ica.m`, `cfg.trialdef.eventvalue
  = comp_id`), and analysed at 60 Hz.
- **Audio copy.** UADC001/UADC002 carry the played wav channel in all 35 recordings (sub001 also on UADC003/004;
  those are noise in the others, which is why a first fit on UADC003 found nothing after sub001), **inverted**: the
  30-290 Hz cross-correlation has its main peak at r = -0.84 to -0.90 and positive side lobes of ~0.5 half a carrier
  period later (figure `xcorr_shape_sub001.png`; taking the |xcorr| or the positive peak would put the onset ~2.5 ms
  late, LESSONS "inverted side lobe"). The copy is low-passed at 300 Hz by the MEG's anti-alias filter, and most
  pieces have almost no energy there (section 4), so only six pieces (107, 109, 113, 114, 116, 118, `band_frac` >=
  0.005, `reliable` in `audio_fit.csv`) give usable windowed fits; the others lock onto side lobes (values in the
  CSV, not used).
- `drift.py` (run on all 35 recordings; `audio_fit.csv`, 773 rows, one per trigger): on the 210 reliable piece fits
  (6 per participant, 8-43 windows each) the sound starts **4.08 ms after the trigger** (median; IQR 3.83-4.42,
  range 3.04-5.37 ms; participant medians 3.74-4.59 ms; within-participant SD 0.14-0.62 ms, not consistent per
  piece, i.e. jitter plus fit noise). Test snippets (trigger before a non-blocking `Start`; one whole-snippet
  cross-correlation, sub-sample peak): snippet 1 7.6-18.3 ms (median 11.7, SD 2.5), snippets 2 and 3 22.3-30.6 ms
  (medians 26.6/26.4, SD 2.1/2.2). Snippet 2 has no energy below 290 Hz (r ~0.14), but its delays match snippet 3's;
  the adaptor uses each test trial's own delay, snippet 2 included. sub008 heard the three snippets twice.
- Provenance: pieces `sw_trigger` (with or without the constant delay), test snippets `stimtrack_xcorr` when
  `audio_delay=True`; `jitter_ms` 0.4 (pieces: median within-participant SD of the piece delays) and 2.5 (test).
- Trigger jitter relative to the Psychtoolbox audio start: residual SD 0.20-0.39 ms per participant (section 8).
- Sound delivery: Etymotic ER3A with tubes and Doc's Promolds; tube length not reported, acoustic delay (~1 ms per
  ~34 cm of tube) not corrected.
- **Onset (approved, user 2026-11-23):** trigger + 4.1 ms for the pieces, trigger + the trial's own measured delay
  for the test snippets (`audio_delay=True`, default). `audio_delay=False` starts trials at the trigger.

## 7. Drift
- Audio copy (reliable pieces): **+6.47 ppm** (median of 210 fits; IQR 6.21-6.85; participant medians 6.21-6.78;
  MEG clock fast). Per-piece values have a small consistent piece bias (113 ~7.3, 118 ~5.5 ppm in every participant;
  <= 0.2 ms over a piece). Independent check from the logs (section 8): MEG vs sound card median +6.0 ppm (3.9-8.6).
  Same lab as armeni2022 (+5.7 ppm).
- At 6.5 ppm the longest piece (276 s) drifts 1.8 ms. **Approved (user, 2026-11-23: "hardware-derived values
  should be corrected for, unless validation gives reason to doubt them"):** `drift_correction=True` (default) with
  one dataset constant of +6.5 ppm (hardware-derived from the audio copy), folded into the 1200 -> 1000 Hz resample.
- Evidence figure (per participant: delay per reliable piece, drift per piece, log-based drift):
  `tmp/review/kern2022/evidence_delay_drift.png`; tables `audio_fit_subject_summary.csv`, `log_drift.csv`,
  `test_snippet_delay.csv` there.

## 8. Cross-check from the Psychtoolbox logs
- `logfiles/sub0NN.mat`: `start_times_audio`, `actual_start_times_audio`, `end_times_audio` (PC clock, GetSecs) and
  `stimulus`; the trigger time itself is not stored.
- Logged playback durations match the wavs to ~1 ms (median -1.2 ms, range -4.8 to +0.3 ms); slope vs duration
  (PC vs sound card clock) -4 to -18 ppm, different per session.
- MEG trigger samples vs `start_times_audio` (straight line over the 19 pieces): MEG vs PC clock +9.5 to +24 ppm,
  residual SD 0.20-0.39 ms, i.e. the trigger follows the PTB audio start with sub-ms jitter. MEG vs sound card =
  (MEG vs PC) + (PC vs sound card): median +6.0 ppm, range +3.9 to +8.6 over the 35 sessions (`log_drift.csv`).

## 9. Validation (2026-11-23, pilot: sub001, sub010, sub020, sub030; first 10 pieces each, music only; axial
gradiometers (`mag`), no re-referencing)
`validate_subset.py kern2022 ... mag low,mlr,brainstem "r.subject in (1, 10, 20, 30) and r.condition == 'music' and
r.trial <= 13" 1` (10 pieces keep a subject at ~5-6 GB in the validator). Run twice: without corrections (trials at
the trigger, no drift; `tmp/review/kern2022/validation_uncorrected/`) and with the adaptor defaults (+4.1 ms onset,
+6.5 ppm drift; `tmp/review/kern2022/validation/`, `validation.json` here).

| tier | uncorrected | corrected (defaults) |
|---|---|---|
| low 0.5-8 Hz | r 0.020 (0.022/0.011/0.029/0.017), p_circ 0.020, p_mismatch 0.048, 3/4, peak 0 ms | r 0.020 (0.022/0.011/0.030/0.017), p_circ 0.020, p_mismatch 0.048, 3/4, peak 78 ms |
| mlr 30-60 Hz | SNR 1.08, p 0.030, 1/4; peak ~45 ms | SNR 1.19, p 0.010, 2/4; peak ~42 ms |
| 30-250 Hz (28-45 ms) | SNR 1.33, p 0.010, 2/4; peak ~37 ms | SNR 1.32, p 0.010, 3/4; peak ~33 ms |

- Per participant (corrected vs uncorrected): mlr SNR up in 3/4 (sub030 0.92 -> 0.91); 30-250 Hz SNR up in 3/4,
  sub030 1.01 -> 0.92 (not significant either way). The high-frequency peaks move ~4 ms earlier, as the onset
  shift predicts, and get slightly higher; no tier is worse, so validation gives no reason to doubt the
  hardware-derived values.
- The 0.5-8 Hz TRF is periodic (peaks at 0, ~80, ~230, ~400 ms, above the null at -100 ms too), presumably the
  regular note rate (median inter-onset 200 ms) smearing the response; its two first peaks are nearly equal, so the
  reported peak flips between 0 and 78 ms.
- 30-250 Hz: a clear peak in the window, no spike at 0 or negative lags (no visible stimulus pickup).
  **Validation tier (pilot): brainstem** (for MEG: a high-frequency cortical response). Weak per participant: most
  energy of the music is above the MEG's 300 Hz low-pass, the data are uncompensated (no synthetic 3rd-order
  gradiometers) and only ~23 min per participant were used.
- Not yet run: all 35 participants, the test condition.

## 10. Checks
- Download: 1162 files, sizes as listed by WebDAV and **sha256 equal to `MANIFEST.txt` for all 1162** (2026-11-23).
- Triggers: 19 distinct piece codes and 3 test codes in every recording, 6 test codes in sub008 (snippets repeated);
  773 trials (665 music, 108 test). Every piece's trigger order equals the logfile's `stimulus` order.
- Pilot standardisation (sub001, sub010, sub020, sub030; uncorrected, then again with the corrected defaults): 88
  trials, 13 GB (~3.3 GB per participant; ~115 GB for all 35); trial length = wav length; 269 mag + 29 ref_meg + 4 misc at 1000 Hz.

## 11. Data size
- 35 participants x 0.722 h of music (the 19 pieces, 43.3 min) = 25.27 h, identical for everyone (each piece once),
  plus 0.40 h of test snippets (40 s per participant, 80 s in sub008). Recordings 50-71 min.

## Open questions (with recommended defaults)
1. ~~Onset~~: approved (user, 2026-11-23); `audio_delay=True` is the default.
2. ~~Drift~~: approved (user, 2026-11-23); `drift_correction=True` (+6.5 ppm) is the default.
3. Keep the test snippets (condition `test`; the volume was adjusted during them)? Recommended: keep (everything
   played is kept; easy to filter).
4. Carry the MIDI note annotations (`MidiDataMEG.csv`) as a TextGrid `notes` tier? Recommended: later, after
   checking pieces 111/112.
5. Drop EEG057-064 and UADC001/003/004/008-013 (armeni2022 decision)? Recommended: yes.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**good**: Software trigger + 4.1 ms measured on audio copy UADC002 (6/19 pieces fit, 210 fits; others get the constant); test snippets measured per trial; drift +6.5 ppm from the audio copy (logs +6.0) corrected; brainstem (pilot 4).
