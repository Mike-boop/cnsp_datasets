# miran2020: at-will attention switching between two talkers (MEG, one subject)

Raw MEG of one young adult (R2082) listening three times to the same 90-s mixture of a male and a female talker
reading *The Legend of Sleepy Hollow* (diotic). The listener started on the male talker and then switched attention
at will 1-3 times per trial, pressing a button at each switch. This is the at-will experiment of Miran et al.
(2020), recorded for Presacco et al. (2019). The sibling dataset `miran2020b` is the paper's instructed switching
experiment (7 subjects).

- **Source:** DRUM (University of Maryland), hdl 1903/26351, item `36f86b13-fefe-41b2-b6e6-236f87b170e3`
  (registry entry `miran2020`; 0.50 GB). A backup is on the NHR vault.
- **Licence: none stated** on the DRUM item. Ask the authors before sharing.
- **Papers:**
  - Miran S, Presacco A, Simon JZ, Fu MC, Marcus SI, Babadi B (2020). *PLoS Comput Biol* 16(8):e1008172.
    doi:10.1371/journal.pcbi.1008172
  - Presacco A, Miran S, Babadi B, Simon JZ (2019). Real-time tracking of magnetoencephalographic neuromarkers
    during a dynamic attention-switching task. *IEEE EMBC 2019*, 4148-4151.
- **Code:** none shared.

## Size
**1 participant x 0.075 h** (3 x 90 s). The standardised data are 0.18 GB.

## What is provided
- **MEG:** KIT 157-channel axial gradiometers (`mag`, KIT_GRAD) + 3 reference magnetometers (`ref_meg`). **Recorded
  at 2 kHz and stored at 1000 Hz** (anti-alias filter and one resample).
  - **Raw data, not denoised** (the ADC quantisation is intact). The authors shipped only the three 90-s epochs.
  - **Units:** shipped in fT (same export and calibration as presacco2016), converted to T.
  - **Bad channels:** MEG 040 and MEG 056 (the authors' list, 0-based in the source, both all zero), in
    `info['bads']`. Exclude them yourself.
  - MISC trigger lines are dropped. There are no sensor positions, head shape, EOG or audio copy.
- **Subject number:** 2082 (from the R-number; `participant` in the sidecar).
- **Stimuli** (22.05 kHz, filtered and level-normalised by the authors): the male
  (`Seg_V_885_5_Sec_filt.wav_Short_Norm`) and the female talker
  (`Seg_IV_Female_Sleepy_1413.2_Sec_filt.wav_Short_Norm`) as shipped. The mixture is not shipped; both start at
  t = 0.
- **Attention:** **the switch times are not in the release**: no events, and the button presses are on none of the
  recorded lines. Each MEG file has only a zero-length `attend_start/<male talker>` annotation at t = 0, which is
  the instructed start (deliberately not an `attend/...` span). `is_attended` is False for both talkers. The
  paper's Fig 6 shows the reported switches for two of the trials.

## Alignment
- **Onset:** t = 0 at the onset-trigger edge (a 5-ms active-low pulse on MISC 011, epoch sample 1), as in
  presacco2016. The trigger type is unknown. No drift correction (it cannot be estimated).
- **Alignment grade: medium**, on weak evidence (one subject). The lag sweep of a reference-regressed forward model
  has a single broad peak around 0 shift, and the 30-60 Hz TRF is flat at negative lags. No correction.

## Download and adaptor options
- `download_dataset("miran2020", <dir>)`. DRUM is slow, so use `max_workers=1` and a long `read_timeout`.
- `Miran2020Adaptor(download_dir)` searches the tree for `R2082_Cocktail_*.mat` and the two wavs. It has no options.

## Validation
Raw gradiometers without bads, both talkers.
- **Standard low tier (female talker, all sensors):** **fails** (r 0.025, p 0.078). With 4.5 min of raw, undenoised
  MEG there is too little signal.
- **Low tier with the reference sensors regressed out** (validation only): male r 0.080, female 0.051, both above
  the circular-shift null (p = 0.02, the minimum with 50 shifts). The lag sweep peaks near 0.
- **30-60 Hz (18-45 ms):** pass, SNR 1.42, p 0.02. **30-250 Hz (MEG window 28-45 ms):** pass, SNR 1.24, p 0.03,
  but spiky everywhere.
- No attention contrast is possible without the switch times.
- **Validation tier (sidecar): `mlr`**, counting the reference-regressed low tier. By the validator's strict rule
  (every lower tier passed as run) it would be `none`.

**Suitable for** demonstrations and method tests on raw single-subject MEG with a two-talker stimulus.
**Not suitable for** attention decoding against behaviour (no switch times), or for group analyses.

## Caveats
- A single subject: in the paper, the only one of five with a usable response and behavioural report.
- The licence is not stated.
- The Sleepy Hollow segments differ from presacco2016's / kulasingham2020's.

Details: `notes.md`.
