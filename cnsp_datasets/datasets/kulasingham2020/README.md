# kulasingham2020: younger and older listeners, two audiobook segments in quiet (MEG)

MEG of 40 adults with clinically normal hearing, 17 younger (18-27 y) and 23 older (61-78 y). They listened to two
60-s segments of *The Legend of Sleepy Hollow* (male talker) in quiet, each repeated three times: **6 trials of
60 s per participant**, condition `quiet`. The release was made for Kulasingham et al. (2020) on high-gamma
(70-200 Hz) cortical responses.

- **Source:** DRUM (University of Maryland), item `da9293b8-cc3c-4965-8b4f-dd1bc91daca5`, doi:10.13016/33pk-ltqh
  (registry entry `kulasingham2020`, 12.1 GB; the two forward-model zips are excluded). A backup is on the NHR vault.
- **Licence: none stated** on the DRUM item (checked 2026-11-24). Whether the data, or anything derived from them,
  may be redistributed is unknown. Ask the authors before sharing.
- **Paper:** Kulasingham JP, Brodbeck C, Presacco A, Kuchinsky SE, Anderson S, Simon JZ (2020). High gamma cortical
  processing of continuous speech in younger and older listeners. *NeuroImage* 222:117291.
  doi:10.1016/j.neuroimage.2020.117291
- **Code:** github.com/jpkulasingham/highfreqTRF (analysis; not needed here).

## Overlap with presacco2016
**32 of the 40 participants are presacco2016's younger and older normal-hearing participants, and these are the
same recordings** as presacco2016's two quiet conditions (Q_H, Q_L), here as continuous files instead of 60-s
epochs, and denoised (below). The 8 older participants R2338, R2342, R2354, R2363, R2396, R2408, R2409 and R2428 are
not in presacco2016.
- The map is in `subject_map.tsv` (R-number, age group, presacco2016 subject, evidence) and in each trial's sidecar
  (`overlaps_with`, e.g. `presacco2016 S12 Younger`; empty for the 8). Four ambiguous pairs were settled by
  correlating the two releases (r 0.98-1.00 for the right pair, ~0 for the swap); the rest by block lengths.
- `Trial1.wav` and `Trial2.wav` are byte-identical to presacco2016's `Quiet_H.wav` and `Quiet_L.wav`
  (`identical_stimulus` in the sidecar).
- **When pooling with presacco2016, count these participants once**, e.g. with `subjects="unique"` here.

## Size
**40 participants x 6 min = 4.0 h** (all identical: 6 trials x 60 s). Younger 1.7 h, older 2.3 h; the 8 unique
participants 0.8 h. Continuous recordings: 5.6 h. Standardised: 9.4 GB.

## What is provided
- **MEG:** KIT 157-channel axial gradiometers (`mag`, KIT_GRAD) + 3 reference magnetometers (`ref_meg`), **1000 Hz
  native, stored at 1000 Hz**, in T.
  - **Denoised by the authors, not raw.** Saturating channels were zeroed, then TSPCA (reference-channel
    regression) and SNS (sensor noise suppression) were applied before upload (readme, paper section 2.2). Against
    presacco2016's raw epochs of the same participants the difference is 15-24 dB below the signal in every band,
    with no time shift. The sidecar says so (`preprocessing`).
  - **Peripherals:** the MISC trigger lines and STI 014 are dropped. There is no audio copy, EOG or ECG.
  - **Geometry:** sensor positions and orientations in KIT device coordinates (two calibrations, 2014 and
    2015-2017); `dev_head_t` is identity; no head shape, fiducials or MRI here (the release's forward models were
    not downloaded).
- **Bad channels** (`info['bads']`, kept in the data; exclude them yourself):
  - the authors' `bad_channels.txt` (MEG 056 in 13 participants, R1801 MEG 105, R2084 MEG 111 and 146);
  - flat or all-zero gradiometers (rms below the median / 20), e.g. R2281 MEG 056, R2084 MEG 099 in Trial1;
  - channels that are dead in presacco2016's raw recordings but were refilled from their neighbours by SNS here
    (R2185, R2079, R2230, R2210 MEG 062; R2201 MEG 062 and 157; R2254 MEG 001 and 002; R2084 MEG 099).
- **Subject numbers:** the full R-number (R2201 -> 2201); `participant` and `age_group` are in the sidecar.
- **Stimuli:** `Trial1` and `Trial2` (44.1 kHz mono, 60.000 s), as shipped. No transcripts. The release's auditory
  spectrograms (`Trial*-audspec-1000.mat`) are not used.
- **Trials:** 1-3 = `Trial1` repetitions 1-3, 4-6 = `Trial2` repetitions 1-3 (the same numbering as presacco2016's
  quiet trials). Block start times are in the sidecar (`block_recorded`).

## Alignment
- **Onset:** t = 0 at the onset-trigger edge (STI 014 code 166 for Trial1, 171 for Trial2; TTL lines MISC 007 /
  MISC 012). Three onsets in every one of the 80 blocks. Trials are 60,000 samples.
- **Trigger type:** unknown. The tube delay (E-A-RTONE 3A, length not given) is not compensated.
- **Drift:** the offset trigger (code 163) comes 59,997 or 59,998 samples after the onset in all 240 repetitions
  (mean -2.25 ms per 60 s). That is -37.5 ppm if it marks the sound end on the same clock, or a constant early pulse.
  The two cannot be separated with one stimulus length, so it is **documented, not applied** (`drift_ppm` null); at
  most 2.3 ms at the end of a trial.
- **Alignment grade: medium.** Onset-trigger edges of unknown type, no stimtrack; validation confirms the timing
  (30-250 Hz TRF peak at ~40 ms, flat at negative lags, also in the 8 new participants alone); the -37.5 ppm
  drift-or-early-end is documented, not applied.

## Download and adaptor options
- `download_dataset("kulasingham2020", <dir>, max_workers=1, read_timeout=300)`. DRUM is slow; no credentials.
  The MEG comes as two split zips (`younger_meg.z01`-`.z03` + `.zip`, `older.*`). The default
  `extract_archives=True` joins and extracts them (needs `bsdtar`); `extract_archives(dir, keep=True)` keeps the
  zips.
- The adaptor searches the root recursively for `*_MEG/<Group>_R####_Trial{1,2}-raw.fif`, `Trial1.wav` and
  `bad_channels.txt`.
- `Kulasingham2020Adaptor(download_dir, subjects="all")`:
  - `subjects="all"` (default): all 40 participants;
  - `subjects="unique"`: only the 8 participants not in presacco2016.

## Validation
All 40 participants (240 trials), axial gradiometers without bads, no re-referencing (MEG).
- **low (0.5-8 Hz forward):** passes. Mean r 0.038, **35/40 participants** above the circular-shift null, p_circ
  0.020, p_mismatch 0.048. TRF peaks at ~60 and ~190 ms.
- **mlr (30-60 Hz, 18-45 ms):** fails (SNR 0.97, p 0.23, 3/40); the 30-60 Hz TRF peaks at ~62 ms, outside the
  window (as in presacco2016).
- **30-250 Hz (MEG window 28-45 ms):** passes. SNR 1.34, p 0.0099, **29/40 participants**; a sharp peak at ~40 ms
  and nothing at negative lags. For MEG this is the high-gamma cortical response the paper reports, not a brainstem
  response.
- **The 8 participants not in presacco2016, alone** (48 trials): low passes (mean r 0.042, 7/8; R2342 not
  significant), mlr fails (SNR 1.01, p 0.16), **30-250 Hz passes (SNR 1.33, p 0.0099, 7/8)** with the peak at
  ~41 ms and nothing at negative lags. So the timing holds for the new participants too.
- The validator records the tier as `low` because mlr fails, although the 30-250 Hz tier also passes.

**Suitable for** low-frequency speech tracking, age-group comparisons and high-gamma (~40 ms) cortical responses.
**Not suitable for** source analyses without head registration, middle-latency (30-60 Hz) analyses, or pooling
with presacco2016 without the subject map.

## Caveats
- **Licence not stated.**
- **Duplicated recordings:** 32 participants are also in presacco2016 (raw there, denoised here).
- **Denoised data:** TSPCA/SNS cannot be undone; dead channels can look alive after SNS (listed as bads above).
- R2254 Trial1 is about twice as noisy as the cohort (median gradiometer SD 473 fT).
- The release's zips store the authors' absolute path (`Volumes/JOSHUA/Drum/...`); the adaptor searches recursively.

Details: `notes.md`.
