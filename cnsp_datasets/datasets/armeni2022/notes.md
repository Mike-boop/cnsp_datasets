# armeni2022: notes

Findings that explain `adaptor.py`. Review scripts and results: `tmp/review/armeni2022/`,
`tmp/review/scripts/meg/armeni_*.py` (2026-11-21).

## 1. Source
- Donders Repository DSC_3011085.05_995_v1, doi:10.34973/5rpw-rn92 (WebDAV `webdav.data.ru.nl/dccn/...`). Data use
  agreement: every file except `MANIFEST.txt`/`README.txt` needs the user's data.ru.nl WebDAV credentials
  (`RADBOUD_USERNAME`/`RADBOUD_PASSWORD`; registry entry `armeni2022`, anatomy excluded). Acknowledge "Data were
  provided (in part) by the Donders Institute for Brain, Cognition and Behaviour, Radboud University Nijmegen".
- Paper: Armeni, Güçlü, van Gerven & Schoffelen 2022, Sci Data 9:278, doi:10.1038/s41597-022-01382-7.
- Code: `code/pipeline` in the release (FieldTrip; `meg/dm_audiodelay.m`, `meg/dm_subjinfo.m`); also
  github.com/KristijanArmeni/Deep-MEG.

## 2. Layout
- BIDS: `sub-00{1,2,3}/ses-0{01..10}/meg/sub-*_ses-*_task-compr_meg.ds` (CTF) + `_events.tsv`; empty-room
  recordings (`task-emptyroom`); eye tracking (`eyelink/`); `stimuli/<ses>_<part>.wav` (22.05 kHz int16) and
  `.txt` transcripts; `noise_ceiling.wav` (29 s); `derivatives/fieldtrip-preprocessing/` (trial definitions and the
  authors' audio delays per part: `audiodelay.mat`).

## 3. Stimulus <-> trial mapping
- Ten sessions per participant, each 6-8 parts of The Adventures of Sherlock Holmes (7-10 min), same stimuli for
  all three participants. `wav_onset` event codes 10, 20, ... = part 1, 2, ... of the session
  (`stimuli/<ses>_<part>.wav`; `dm_subjinfo.m` task codes); codes 100/150 = the noise-ceiling passage
  (`noise_ceiling.wav`, played twice after each part; `noise_codes = [100 150]`).
- One trial per `wav_onset` event, numbered in recording order; conditions `story` and `repeat`.
- Word and phoneme onsets: events `word_onset_<part>` / `phoneme_onset_<part>` (value = label, with duration). The
  adaptor builds a part's TextGrid relative to the part's onset, from the first participant whose annotations of the
  part start at its own `wav_onset` (within 0.1 s); within a wav the timings are the same for every participant.
- **sub-003 ses-008 (crashed run 3; paper, "Repeated run")**: the script crashed in run 3 and was restarted at run 3.
  The recording holds the aborted playback (08_3 from 1211.8 s) and the complete restart (from 2022.9 s, ending at the
  run-3 offset marker 2549.05 s), but **no `wav_onset` for run 3** (codes 10, 20, 40-70; the authors' `trl.mat` also
  lacks run 3). The adaptor adds the restart with the onset measured on UADC003 (2022.901 s; 08_3.wav r = 0.98, other
  parts <= 0.13). The codes of the other parts match their audio (r 0.97-0.98). Its **word annotations are shifted
  by one part** after the crash: the words of part 3 start at part 4's onset (2685.85 s), part 4's at part 5's, ...,
  part 7 has none; hence the TextGrids from another participant (sub-001 for session 8).

## 4. Speech features
Audio as shipped, TextGrids (words, phones) for story parts, transcripts in `stimuli/*.txt` (not carried).

## 5. Neural data
- CTF-275: 269 axial gradiometers (MNE `mag`; 6 dead/removed), 29 reference sensors (`ref_meg`), 1200 Hz (analog
  anti-alias low-pass 300 Hz), head casts (continuous head localisation channels HLC* dropped).
- Kept extra channels (paper, Table 5): UADC003 (audio), UADC005-007 (EyeLink x, y, pupil diameter on the MEG
  clock). UADC004 (a second audio channel) is not kept.
- Known bad channels (paper): sub-003 ses-004 MRC23, MLO22, "MRP5", MLC23; "MRP5" is MRP55 (1-40 Hz SD 24x and 99.9th
  percentile jumps 38x the channel median, the other MRP5x ~1x; MLO22 24x, MLC23 2.5x, MRC23 0.9x in 300-900 s).
  Marked bad in that session's trials. Not marked (paper): MRP57 spikes in sub-003 ses-003; slow-drift artefacts in
  sub-002 ses-009 run 1, sub-003 ses-004 run 4, ses-005 run 1, ses-006 run 6, ses-008 run 4. UADC003 = audio copy (kept, `misc`). MNE names carry
  the system suffix (`UADC003-4302`).
- EEG057-064 (BIDS type `eeg`, use not documented) carry no physiological signal and are dropped (user's decision
  2026-11-21). Checked on sub-001 ses-001: EEG057 ~1.4 mV and EEG059 ~0.35 mV (0.5-40 Hz) of broadband noise with
  slow wandering and steps (floating inputs); EEG058 and EEG061-064 ~0.4 uV, mains-dominated and correlated 0.75 with
  each other (open inputs); EEG060 flat; no heartbeat periodicity in any. Against the session's EyeLink recording
  (1488 blinks, 7235 saccades; `scripts/meg/armeni_eog.py`, figure `tmp/review/armeni2022/eog_sub-001_ses-001.png`):
  |r| < 0.03 with the blink indicator at every lag, no blink- or saccade-locked deflection, so not EOG. The
  participants wore head casts and were eye-tracked; the EEG inputs were presumably not connected.
- Resampled 1200 -> 1000 Hz (anti-alias FIR + quintic spline, in the same interpolation as the drift
  correction; `sfreq=None` keeps 1200 Hz).

## 6. Alignment (verified)
- The authors measured each part's delay between trigger and sound from UADC003 (phase slope of the coherence at
  150-250 Hz, `dm_audiodelay.m`): 50-114 ms, varying from part to part. The released `wav_onset` events already
  include it: event onset = trigger (`derivatives/fieldtrip-preprocessing/.../trl.mat`, (begsample - 1 - offset) /
  1200) + `audiodelay.mat`, to 0.0 ms (checked: sub-001 ses-001, sub-002 ses-004, sub-003 ses-008). The paper
  describes `audiodelay.mat` as "the audio delay between the audio recording onset in each session and the MEG
  system trigger sending". Eye blinks were removed by the authors with ICA components of the MEG (`selcomp.mat`),
  not with EOG channels.
- Check (`armeni_audio_lag.py`, UADC003 vs wav, envelope cross-correlation and Theil-Sen through 10 s windows):
  sound within -1.8 to +1.4 ms of the shipped `wav_onset` in every story part checked (r = 0.90-0.97); the
  noise-ceiling repeats at -1.6 ms. The adaptor uses the shipped onsets.
- sub-003 ses-001: the recording started ~4-8.5 s after part 1 began (the authors' note in `dm_audiodelay.m`;
  `wav_onset` at -4.14 s). That part is skipped.

## 7. Drift
- +5.7 ppm (Theil-Sen, 10 s windows of the 70-250 Hz waveform; 5.4-6.0 in every part checked): the MEG clock runs
  fast relative to the audio, ~2.7 ms over an 8 min part. `drift_correction=True` (default).
- All 30 sessions, 196 story parts (`tmp/review/armeni2022/audio_lag.csv`): onset -0.1 +- 0.8 ms relative to the shipped
  `wav_onset` (largest +3.1 and +3.3 ms: session 8 part 7 in sub-001 and sub-003, the same wav, so probably the
  authors' delay estimate for that wav); drift +5.73 +- 0.14 ppm, participant medians 5.70-5.76.

## 8. Validation (sessions 1-3 of each participant, story parts, magnetometers (axial gradiometers), no re-referencing)
`validate_subset.py armeni2022 ... mag low,mlr,brainstem "r.condition == 'story' and r.session <= 3"` (adaptor
defaults: 1000 Hz, +5.7 ppm drift); results and figure `tmp/review/armeni2022/validation_ses1-3/`.
- low: mean r 0.061 (0.061 / 0.047 / 0.076), 3/3 above the nulls.
- mlr: SNR 2.57, 3/3 significant (peaks ~27, 40, 50 ms).
- brainstem tier (30-250 Hz, 28-45 ms): SNR 3.03, 3/3 significant. **Validation tier: brainstem.**
- **Stimulus artefact at lag 0:** the 30-250 Hz TRF has a narrow spike at -2.5 and +0.5 ms, ~10x the null, i.e. the
  sound picked up electromagnetically by the sensors.
- Sound delivery (paper): "a sound pressure transducer through two plastic tubes terminating in plastic insert
  earpieces"; tube length and acoustic delay not reported, not corrected. It confirms the audio-MEG alignment to ~1-2 ms; exclude lags
  around 0 in high-frequency analyses (the tier's noise and latency windows do not include it).

## 9. Data size
3 participants: story parts 8.76 h each (26.3 h), noise-ceiling repeats 1.06 h each (3.2 h); 29.5 h in total.

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**good**: Shipped wav_onset = trigger + authors' per-part UADC003 delay; re-check vs UADC003 -0.1 +- 0.8 ms (196 parts); drift +5.73 ppm from the audio copy corrected; brainstem tier (stimulus artefact near 0 ms).

## Restructure 2026-11-25 (not yet re-validated on data)
- Stimulus audio as float32 in [-1, 1) (`iohelpers.read_wav`; was the raw int16 samples).
- Channels the CTF header marks bad are kept and listed in `info["bads"]` (`pick_types` dropped them, and
  `info["bads"]` was then overwritten with the paper's list); a listed bad sensor missing from the recording raises.
- TextGrid written by `iohelpers.textgrid` (was `broderick2019_natural.utils.multi_tier_dict_to_textgrid`): long
  text format, xmin 0 (was the first onset), gaps filled with empty intervals, quotes escaped. Overlapping
  annotations within a tier now raise (the old writer wrote them as they were); not yet checked on the events.
