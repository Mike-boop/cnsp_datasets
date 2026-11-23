# presacco2016: aging and speech in noise with an English or Dutch competing talker (MEG)

MEG of 46 participants: 17 younger (S01-S17), 15 older normal-hearing (S21-S35) and 14 older hearing-impaired
(S01-S08, S12-S17 HI). They attended a male talker (*The Legend of Sleepy Hollow*) in 60-s trials, under these
conditions:
- **Quiet:** two segments.
- **English competing talker:** a female talker (*A Christmas Carol*) at +3, 0, -3 and -6 dB SNR.
- **Dutch competing talker:** a female talker at the same four SNRs.

That makes 10 conditions x 3 repetitions = 30 trials per participant. Only the MEG part of the release is
standardised (user decision). The EEG (BioSemi FFR to /da/) is not.

- **Source:** DRUM (University of Maryland), item `79afc7aa-560d-442d-b201-ab63e7f1e69f`, doi:10.13016/M2599Z52H
  (registry entry `presacco2016`, `include` MEG zips + `Stimuli.zip`, 77 GB). A backup is on the NHR vault.
- **Licence: none stated** on the DRUM item (checked 2026-11-23). This is an **open question**: whether the data,
  or anything derived from them, may be redistributed is unknown. Ask the authors before sharing.
- **Papers:**
  - Presacco A, Simon JZ, Anderson S (2016a). Evidence of degraded representation of speech in noise, in the aging
    midbrain and cortex. *J Neurophysiol*. doi:10.1152/jn.00372.2016
  - Presacco A, Simon JZ, Anderson S (2016b). Effect of informational content of noise on speech representation in
    the aging midbrain and cortex. *J Neurophysiol* 116:2356. doi:10.1152/jn.00373.2016

  The hearing-impaired group is in neither paper (probably Presacco et al. 2019; not checked).
- **Code:** none shared.

## Size
**46 participants x 0.50 h = 23.0 h in total** (30 min each, the same for everyone). Durations are counted from the
60-s stimuli (`notes.md`, "Data size"). `data_size.py` was not run because the standardised data had been deleted.
- **Per group:** younger 8.5 h, older normal-hearing 7.5 h, older hearing-impaired 7.0 h.
- **Per condition and participant:**
  - `quiet`: 6 min (4.6 h in total);
  - each masker x SNR condition (`english_snr+3dB` ... `dutch_snr-6dB`): 3 min (2.3 h in total each);
  - English and Dutch: 12 min each (9.2 h in total each).
- The unique audio is 6 foreground minutes and 2 background minutes.
- A full standardisation would be about 53 GB. Only a 20-subject pilot was run.

## What is provided
- **MEG:** KIT 157-channel axial gradiometers (`mag`, KIT_GRAD) + 3 reference magnetometers (`ref_meg`), **1000 Hz
  native, stored at 1000 Hz**.
  - **Raw data, not denoised.** Only three 60-s epochs per condition were shipped, not the continuous recordings.
  - **Units:** shipped in fT (inferred from the ADC step and the 5 V MISC level), converted to T.
  - **Peripherals:** the MISC trigger lines are dropped. There is no audio copy, EOG or ECG.
  - **Geometry:** there are **no sensor positions, head shape or fiducials**, so channel positions are empty.
- **Bad channels:** the union of the authors' `bad_channels` (HI files, 0-based in the source) and all zeroed MEG
  channels. Every HI subject has MEG 056 zeroed; the full list is in `notes.md` section 7. They are listed in
  `info['bads']`. Exclude them yourself.
- **Subject numbers:** younger 1-17, older normal-hearing 21-35, older hearing-impaired 101-117. The original names
  are in the sidecar (`participant`).
- **Stimuli** (44.1 kHz): the **foreground** (attended) and **background** (unattended) wavs as shipped.
  - The played mixtures are **not shipped** and not rebuilt, because the authors' RMS convention is unknown.
    `snr_db` is in the sidecar.
  - The MEG tracks the background at lag ~0 in 30 of 32 checks, so each mixture starts both streams together.
  - There are no transcripts.
- **Trials:** 1-30 = conditions Q_H, Q_L, P3_H, Zero_H, M3_H, M6_H, P3_L, Zero_L, M3_L, M6_L x 3 repetitions. The
  presentation order is unknown.

## Alignment
- **Onset:** t = 0 at the onset-trigger edge, which is epoch index 1 (index 0 is dropped), so trials are 59,999
  samples long. The edge is on the line matching the file's condition in all 1380 trials.
- **Trigger type:** unknown. The tube delay (E-A-RTONE 3A, length not given) is not compensated.
- **Decoder check, all 46 subjects:** the assumed wav wins at lag 0 in 459 of 460 tests. The lag-sweep peak has a
  median of 0 ms (IQR -10..+10 ms).
- **Drift:** the offset trigger comes 2-3 ms before the end of the 60-s wav in every trial. This is -37 ppm if the
  trigger marks the sound end on the same timeline, or a constant early trigger otherwise. The two cannot be
  separated, so it is **documented, not applied** (`drift_ppm` null). It is at most 2.2 ms at the trial end.
- **Alignment grade: medium.** Onset-trigger edge (type unknown), no stimtrack. Decoder lag 0 ± 10 ms. The -37 ppm
  drift-or-end-trigger is documented, not applied. The 30-250 Hz tier passes, flat at negative lags.

## Download and adaptor options
- `download_dataset("presacco2016", <dir>)`. DRUM is slow and times out, so use `max_workers=1, read_timeout=120`.
  No credentials are needed. The registry's `include` fetches only the MEG zips and the stimuli.
- Extract the zips. The adaptor searches the root recursively for `S##_*_MEG` folders and `High Context`.
- `Presacco2016Adaptor(download_dir)`. It has no options.

## Validation
**Piloted on 20 of 46 subjects** (younger 1-10, older NH 21-26, older HI 101, 103-105; 600 trials), axial
gradiometers without bads, no denoising.
- **low:** mean r 0.035, 20/20 subjects significant.
- **mlr (30-60 Hz):** **fails** (SNR 0.97, p 0.28). The 30-60 Hz peak is at ~60 ms, outside the window.
- **30-250 Hz (MEG window 28-45 ms):** **passes**, SNR 1.75, p 0.0099, 19/20 subjects. There is a sharp peak at
  ~38-40 ms, flat at negative lags. This is a high-frequency cortical response; for MEG it says nothing about the
  brainstem.
- **Per condition group:**

  | group | low r | low sig. | 30-250 Hz SNR | 30-250 Hz sig. |
  |---|---|---|---|---|
  | quiet | 0.038 | 16/20 | 1.26 | 12/20 |
  | English | 0.029 | 14/20 | 1.39 | 16/20 |
  | Dutch | 0.032 | 18/20 | 1.37 | 14/20 |

- The validator records the tier as `low` because mlr fails, although the 30-250 Hz tier also passes.

**Suitable for** low-frequency tracking in noise, comparisons of age and hearing groups, and high-frequency
(~40 ms) cortical responses.
**Not suitable for** source analyses without borrowed sensor geometry, or for middle-latency (30-60 Hz) analyses.

## Caveats
- **Licence not stated** (see above).
- **Identical wavs (upstream):** `Minus_6_H.wav` is byte-identical to `Quiet_H.wav`, and `Minus_6_L` to `Quiet_L`.
  The MEG confirms that the -6 dB blocks used these foregrounds. They are stored under their own names
  (`identical_stimulus` in the sidecar).
- **HI file names:** three naming schemes are used. S04 HI ships `S04HL_M6L_II.mat` (used).
- S15 HI `S15_HL_M6H.mat` repetition 2 has no offset trigger inside the epoch.
- `bad_channels` is empty in the younger and older NH files, although channels are zeroed.

Details: `notes.md`.
