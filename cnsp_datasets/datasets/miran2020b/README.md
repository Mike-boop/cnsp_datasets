# miran2020b: instructed attention switching between two talkers (MEG, DSS-denoised)

MEG of 7 young normal-hearing adults (S8, S9, S10, S11, S14, S15, S16) listening to a male talker (Sp1) and a female
talker (Sp2), both reading *A Child's History of England* (Dickens), at the same time (diotic, per the paper). In
each 60-s trial they attended one talker for 0-28 s and switched to the other after a 2-s pause cue (28-30 s):
- **`sp1_then_sp2`** (file 5): Sp1 attended 0-28 s, Sp2 30-60 s;
- **`sp2_then_sp1`** (file 6): Sp2 first, then Sp1.

2 conditions x 3 repetitions of the same mixture = 6 trials per participant. These data are from Akram et al.
(2016) and were reanalysed by Miran et al. (2020). The sibling dataset `miran2020` is the paper's at-will switching
experiment (one subject, raw MEG).

- **Source:** DRUM (University of Maryland), hdl 1903/26352, item `d935265d-895c-4fc7-aec2-36dc7682d87d`
  (registry entry `miran2020b`; one uncompressed zip, 0.66 GB). A backup is on the NHR vault.
- **Licence: none stated** on the DRUM item. Whether the data may be redistributed is unknown; ask the authors
  before sharing.
- **Papers:**
  - Miran S, Presacco A, Simon JZ, Fu MC, Marcus SI, Babadi B (2020). Dynamic estimation of auditory temporal
    response functions via state-space models with Gaussian mixture process noise. *PLoS Comput Biol*
    16(8):e1008172. doi:10.1371/journal.pcbi.1008172
  - Akram S, Presacco A, Simon JZ, Shamma SA, Babadi B (2016). Robust decoding of selective auditory attention from
    MEG in a competing-speaker environment via state-space modeling. *NeuroImage* 124:906-917.
    doi:10.1016/j.neuroimage.2015.09.048
- **Code:** none shared.

## Size
**7 participants x 0.10 h = 0.70 h in total** (6 x 60 s each), 0.05 h per condition and participant. The
standardised data are 0.32 GB.

## What is provided
- **MEG:** KIT 157-channel axial gradiometers (`mag`, KIT_GRAD), **200 Hz as shipped** (recorded at 1-2 kHz and
  downsampled by the authors).
  - **Denoised by the authors, not raw:** the 10 first DSS components projected back to the sensors, so every
    trial has **rank 10**. The data are not band-pass filtered.
  - **Units unknown.** The shipped values (~1e5) are neither fT nor T. They are multiplied by a **nominal 1e-18**
    so that amplitudes fall in the usual KIT range. Treat absolute amplitudes as arbitrary; correlations and TRF
    shapes are unaffected.
  - **Channel labels were not shipped:** 156 channels (S9: 155) for 157 sensors. They are stored as MEG 001-157 in
    file order, with the missing sensor taken to be **MEG 056** (S9: MEG 056 and MEG 144). That sensor is
    zero-filled and listed in `info['bads']`; the sidecar's `missing_sensors` names it. The assignment is inferred
    from neighbour correlations and the system's known dead channel. If it is wrong, at most two channels near
    MEG 054-058 (S9 also 142-145) carry a neighbour's label.
  - No reference sensors, trigger lines, sensor positions or head shape.
- **Stimuli** (44.1 kHz): **Sp1** (male) and **Sp2** (female) as shipped. The mixture is not shipped; both talkers
  start together at t = 0. `is_attended` is False for both, because attention switches within every trial.
- **Attention annotations** in each MEG file: `attend/Sp1` and `attend/Sp2` spans (0-28 s and 30-60 s, in the
  condition's order) and `switch_cue` at 28-30 s. The pause cue is not in the wavs; how it was played is unknown.
- **Trials:** 1-3 = `sp1_then_sp2`, 4-6 = `sp2_then_sp1`. The presentation order is unknown.

## Alignment
- **Onset:** t = 0 is the start of the authors' 60-s epochs, cut at stimulus onset. No triggers were shipped, and
  the trigger type is unknown. No drift correction (it cannot be estimated, and is irrelevant at 200 Hz).
- **Checks:** decoder and forward-model lag sweeps peak at 0 shift (50-100 ms steps) for both talkers, in both
  halves and in both conditions. So there is no inserted 2-s pause in the timeline.
- **Alignment grade: medium.** Shipped epoch onsets, confirmed by the low tier (TRF peak 47 ms, nothing at negative
  lags) and the lag sweeps; no correction.

## Download and adaptor options
- `download_dataset("miran2020b", <dir>, extract_archives=True)`. DRUM is slow, so use `max_workers=1` and a long
  `read_timeout`. No credentials are needed.
- `Miran2020bAdaptor(download_dir)` searches the tree for `Speech/Sp1.wav` and `ssbj*_epochData*_DSSed.mat`. It
  has no options.

## Validation
All 7 subjects, axial gradiometers without bads.
- **low (0.5-8 Hz forward, Sp1 envelope):** **pass**. Mean r 0.091, 6/7 subjects above the circular-shift null
  (S8 is not). TRF peak at 47 ms with a second component at ~375 ms. Per condition: `sp1_then_sp2` r 0.082,
  `sp2_then_sp1` r 0.096, 6/7 each.
- **Attended vs ignored, switch respected** (0.5-8 Hz forward model per attention span): attended > ignored in
  6/7 subjects (mean r 0.171 vs 0.132, Wilcoxon p = 0.11).
- Higher tiers: not applicable (200 Hz, rank 10). **Validation tier (sidecar): `low`.**

**Suitable for** attention decoding and switching analyses at low frequencies, and dynamic TRF methods (the purpose
of the paper).
**Not suitable for** high-frequency analyses, source analyses, absolute amplitude comparisons, or anything that
needs the raw sensor data.

## Caveats
- **Units and channel labels are inferred** (see above).
- **README vs paper:** the shipped README says the talkers were presented "monaurally" and that the recording was
  at 1 kHz; the paper says diotic and 2 kHz. It also says "two different 60-s mixtures", but the MEG shows that both
  conditions used the same Sp1 + Sp2.
- **Shared audio with brodbeck2018:** the same LibriVox readings of the book, in a different edit (Sp1 overlaps
  brodbeck2018 `male_1`, part of Sp2 overlaps `female_2`). The files are not identical. Participant overlap is
  unknown: the original R-numbers were not shipped.

Details: `notes.md`.
