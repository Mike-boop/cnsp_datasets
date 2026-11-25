# miran2020: notes

At-will attention switching experiment of Miran et al. (2020): one subject (R2082), raw KIT MEG, 3 x 90 s. Sibling
dataset: `miran2020b` (instructed switching, 7 subjects, DSS-denoised). Scratch: `tmp/review/miran2020/`, scripts
`tmp/review/scripts/miran2020/`.

## 1. Source
- DRUM hdl 1903/26351, item 36f86b13-fefe-41b2-b6e6-236f87b170e3 ("at-will attention switching"). Files:
  `R2082_Cocktail_171.mat` (490,665,554 B), `Seg_V_885_5_Sec_filt.wav_Short_Norm.wav` and
  `Seg_IV_Female_Sleepy_1413.2_Sec_filt.wav_Short_Norm.wav` (3,969,044 B each). No licence stated (open access).
- Paper: Miran et al. (2020), PLoS Comput Biol 16(8):e1008172, doi:10.1371/journal.pcbi.1008172
  (`data_campaign/papers/miran2020.pdf`). The recording is from Presacco A, Miran S, Babadi B, Simon JZ (2019),
  "Real-time tracking of magnetoencephalographic neuromarkers during a dynamic attention-switching task", IEEE EMBC
  2019, 4148-4151 (their ref. 51). No code shipped.
- Download 2026-11-24 (registry `miran2020`, DRUM, 1 worker): sizes and md5 = DRUM listing (`integrity.tsv`).
- **Vault backup** (2026-11-24, `scripts/miran2020/backup.sh`; the first rsync attempt was refused by the vault node,
  the second succeeded): the 3 files + `download_log.tsv`, `integrity.tsv`, `drum_listing.json`,
  `backup_manifest.tsv` in `csnhr:/home/vault/iwpm/iwpm104h/miran2020/`; every file checked with `stat`, 0
  mismatches (`backup_verify.txt`).

## 2. Layout
- `R2082_Cocktail_171.mat`: MATLAB v7.3 (HDF5, h5py), struct `data_exported` in the same export format as
  presacco2016 (Presacco curated both): `eeg_data_aligned` float64 (3 repetitions, 192 channels, 180000 samples) as
  h5py reads it; `labels` '1'..'192'; `sampling_frequency` 2000; `samples` 4104000 and `trial_duration` 2052 s
  (the continuous recording the epochs were cut from, not shipped); `bad_channels` [39, 55]; `chanlocs`,
  `eeg_data`, `events_trigger`, `events_type` empty (`inspect.txt`, `inspect2.txt`).
- Wavs: mono int16, 22,050 Hz, 90.000 s (1,984,500 samples), speech from ~0.2 s.

## 3. Stimulus <-> trial mapping
- Paper (Methods): 5 young native English speakers in the original study; this is the only one with a meaningful
  auditory DSS response and a reliable behavioural report. Two segments of *The Legend of Sleepy Hollow* (Irving),
  male and female narrators, presented **diotically** as one 90 s mixture, 3 trials of the same mixture. Start on
  the male talker, then switch at will 1-3 times per trial, pressing a button at every switch. A single-speaker pilot
  (three 60 s trials) preceded it; not shipped.
- Talkers (F0, `stim_check.py`): `Seg_V_885_5...` male (114 Hz), `Seg_IV_Female_Sleepy...` female (220 Hz).
- **Switch times are not shipped.** No events, and none of the 32 MISC lines carries a button press in any epoch
  (`misc_a.py`, `explore/misc_a.txt`: only the onset pulse on channel 171; the other lines are constant or
  low-level noise with no excursion > 15 MAD). The paper's Fig 6 shows the reported switches for two trials only.
  So attention is labelled only at t = 0 by a zero-length `attend_start/<male>` annotation (the instructed start;
  not named `attend/...`, so code pairing `attend/*` spans with stimuli cannot misread it as a span); is_attended is
  False for both talkers.
- Overlap: the participant R2082 appears in no other dataset of the campaign (repo search). The wavs do not match
  presacco2016's / kulasingham2020's Sleepy Hollow quiet segments (`stim_overlap_a.py`, `stim_overlap.txt`:
  chance-level envelope matches, r 0.29-0.51 at random lags).

## 4. Speech features available
- Raw audio of both talkers (22.05 kHz, "filt", "Short_Norm": filtered and level-normalised by the authors, RMS
  1131.8 in both). No mixture, transcripts or annotations.

## 5. Neural data
- KIT 157-channel axial-gradiometer MEG (UMD): channels 1-157 = MEG 001-157 (`mag`), 158-160 = reference
  magnetometers (`ref_meg`), 161-192 = MISC 001-032 (dropped). Recorded at 2 kHz (paper and file).
- **Raw**: every MEG and reference value is an integer multiple of a per-channel step of ~0.45 (`raw_or_not_a.py`,
  `explore/raw_or_not.txt`), the ADC quantisation, as in presacco2016. PSD: online 60 Hz notch (-18 dB re 30-55 Hz),
  120 Hz harmonic not notched (+6 dB), no ~200 Hz low-pass (power to 900 Hz).
- **Units: fT** (as presacco2016: step 0.45 fT/count, idle MISC lines at 15067 = full scale; MEG SD median ~100 fT
  broadband at 2 kHz). Adaptor x 1e-15 (T).
- Bad channels: `bad_channels` [39, 55] are **0-based** (MEG 040 and MEG 056 are all zero; same convention as
  presacco2016). Adaptor: listed + zero-variance channels in `info['bads']`.
- No positions, head shape or `meas_date`.

## 6. Alignment
- Trigger: channel 171 (MISC 011) is idle high (15067) except a 10-sample (5 ms) active-low pulse at epoch indices
  1-10 in all 3 epochs; no offset pulse (`misc_a.txt`). So the authors cut each epoch one sample before the onset
  trigger, as in presacco2016. Trigger hardware/software: unknown.
- **Adaptor: t = 0 at the trigger edge** (epoch index 1), 90 s (90000 samples at 1 kHz) via `crop_on_audio_clock`
  (anti-alias FIR + one quintic-spline resample from 2 kHz; integer ratio). `onset_only`, `drift_ppm` null.
- Drift: not estimable (one onset per epoch, same stimulus length).
- Decoder check on the shipped data (`scan_a.py`, `explore/scan_a.txt`; 157 sensors, 30 PCs, 1-8 Hz, lags 0-400 ms,
  leave-one-trial-out): the female talker peaks at 0 shift in all 3 trials (whole trial r 0.11-0.12); the male
  talker is weak.

## 7. Cross-subject duration check
- One subject; epochs 90 s = wav length. Nothing more to check.

## 8. Standardisation and validation (2026-11-24)
- Full run: 3 trials, 0 errors, 181 MB (`tmp/review/miran2020/standardised/`); one trial = 58 MB. Validated as below.
- **Final run** (after the code review, `scripts/miran2020/standardise_v4.sh`, `standardised_v4/`; comparison
  `compare_v4.txt`): identical to the validated run except the first 10 samples (10 ms) of each trial, where the
  reviewed loader passes the whole epoch to the resampler instead of pre-cropping at the trigger edge (removes the
  anti-alias filter's edge transient); sidecar now carries `validation_tier` and the `attend_start/` marker.
  Superseded runs `standardised/`, `standardised_v2/`, `standardised_v3/` can go.
- **Validator** (`scripts/miran2020/validate.sh`; `--picks mag`, no re-reference; `validation.json`, figure
  `tmp/review/miran2020/validation/validation.png`): scores the first stimulus (the female talker, by name order).
  - low (0.5-8 Hz): **fail**, r 0.025, p_circ 0.078 (one subject, 4.5 min of raw unde-noised MEG; TRF at the null
    level).
  - mlr (30-60 Hz, 18-45 ms): pass, SNR 1.42, p 0.020. MEG 30-250 Hz (28-45 ms): pass, SNR 1.24, p 0.030. The
    30-250 Hz TRF is spiky everywhere (one subject); the 30-60 Hz TRF peaks at ~37, 48 and 62 ms and
    stays at the null level at negative lags.
- **Low tier with reference regression** (validation only, `scripts/miran2020/lowtier_a.py`;
  `validation/lowtier_refreg.{json,png,txt}`): the 3 reference sensors regressed out per trial,
  0.5-8 Hz, forward TRF lags -100..500 ms, leave-one-trial-out, 20 best sensors from training trials, 50 circular
  shifts: male r 0.080 (null 95th pct 0.030), female 0.051 (0.024), both 0.077 (0.029), all p = 0.020 (minimum).
  One broad sweep peak from -0.3 to +0.2 s around 0 (male +0.1 s, female plateau -0.3..0 s, 100 ms steps), null
  level beyond +-0.7 s: consistent with the shipped onset.
- **validation_tier = `mlr`** in the sidecar: the low tier passes only with validation-only reference regression
  (the KIT analogue of tSSS for MEGIN data) and the 30-60 Hz tier passes on the standard validator with a plausible
  TRF (peaks ~34, 48, 62 ms; flat at negative lags). The 30-250 Hz pass is not credited (TRF spiky at all lags). The
  validator's strict cumulative rule gives `none` (open question 4).
- **Alignment grade: medium** (weak evidence). Shipped trigger edge, source unknown; the standard low tier fails
  for lack of signal, but the reference-regressed low tier and the 30-60 Hz tier confirm the timing, with nothing at
  negative lags; no correction. A single subject.
- Data size: 1 participant x 0.075 h (3 x 90 s).
- No attention contrast: the switch times are not shipped.

## 9. Open questions (defaults applied)
1. Keep as its own dataset (1 subject, 4.5 min), or fold into miran2020b / drop? [own entry; the task's default]
2. Switch times: none shipped; read them off the paper's Fig 6 (two trials, approximate)? [no]
3. Grade medium on the reference-regressed check while the standard low tier fails? [medium, flagged weak]
4. validation_tier `mlr` (reference-regressed low + standard mlr) or `none` (validator's cumulative rule)? [mlr]

## 10. Upstream issues
- No switch times or button-press events are shipped, although the paper's analysis uses them; the MISC lines carry
  no presses either. Worth asking the authors for the button-press times (`R/upstream_issues.md`).

## Restructure 2026-11-25
- Restructure 2026-11-25 (not yet re-validated on data): adaptor on `BaseAdaptor`; bads set with `iohelpers.mark_bads`
  (same list); stimulus wavs read with soundfile through `simon_base.read_wav` (`iohelpers.read_wav`): float32 in [-1,
  1), any PCM width; the same values as before for the shipped int16 wavs; dataset.json: paper DOI.
