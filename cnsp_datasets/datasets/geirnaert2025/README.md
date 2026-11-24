# geirnaert2025: Ear-SAAD, scalp + around-ear + in-ear EEG while attending one of two Danish talkers

Fifteen native Danish listeners attended one of two competing male talkers (educational talks, HRTF-spatialised
to -60/+60 deg, insert earphones in custom earpieces) for six 10-min trials. In half of the trials the video of
the attended talker was shown, otherwise a fixation cross. Scalp EEG and ear-EEG were recorded simultaneously
with two amplifiers.

- **Source:** Zenodo 16536441 (Ear-SAAD dataset), doi:10.5281/zenodo.16536441. **Licence: CC BY-NC-SA 4.0**:
  non-commercial use only, and derived data (including this standardisation) must be shared under the same
  licence.
- **Paper:** Geirnaert S, Kappel SL, Kidmose P (2025). A direct comparison of simultaneously recorded scalp,
  around-ear and in-ear EEG for neural selective auditory attention decoding to speech. *Sci Rep* 15:41655,
  doi:10.1038/s41598-025-25576-2. Cite the paper and the Zenodo record.
- **Code (authors):** `preprocessFromBIDS.m` in the record (MATLAB; not used here).

## Size
15 participants (sub-01..15), 6 trials of 600 s each: **60 min per participant (all equal), 15 h in total**;
30 min per participant with video and 30 min without; 30 min attending left, 30 min attending right.

## What is provided
- **Two files per trial, one per amplifier** (TMSi Mobita, 1000 Hz, kept at 1000 Hz), in two ns_type folders:
  - `eeg/` (scalp amplifier): 27 scalp 10-20 channels (`eeg`, template standard_1020 positions), mastoids `M1`/`M2`
    (`misc`), `EOG2`/`EOG3`/`EOG4` (`eog`; placement undocumented: EOG2 behaves like an infraorbital vertical
    channel, EOG3/EOG4 like a horizontal pair, inferred from the data only).
  - `ear-eeg/` (ear amplifier): 12 dry in-ear electrodes `EL{A,B,C,E,I,T}` / `ER{A,B,C,E,I,T}` (A/B/C concha,
    E/I canal, T tragus) and 19 wet around-ear electrodes `cEL1-9` / `cER1-10` (C-shaped arrays like cEEGrids,
    1 = top), all `eeg`; `Fp1-cr` (`misc`), a frontal scalp electrode at the same site as the scalp amplifier's
    Fp1 (sub-04: Fp2). No positions.
  - Each amplifier keeps its own common reference (not a recorded channel); shared ground at CPz. Re-reference
    before use (e.g. average of the scalp channels; for ear-EEG the authors used the average of the ear channels
    without Fp1-cr). The shared electrode lets you put both systems on one reference.
  - The data are raw (DC-coupled, unfiltered); high-pass before use.
- **Audio:** the two talkers of each trial as shipped (`Speaker<k>Part<p>`, 48 kHz, stereo with identical channels,
  i.e. before the HRTF), from wav time 5 s on: the first 5 s of each wav were a prelisten before the trial and
  are not in the EEG. `Part1` is always the attended talker. The first stimulus in a file name is the attended one.
- **Conditions:** `attend-<left|right>-<video|novideo>`. Sidecar fields include the left/right files, attended side,
  video flag, age, sex.
- **Bad channels** (`info['bads']`, per participant and amplifier): flat, railing or far noisier than the rest of
  the group (list in `notes.md`, section 11). Ear-EEG is affected much more than scalp EEG (e.g. dry in-ear
  electrodes without contact). **sub-05 trials 5 and 6: the whole ear amplifier was saturated**; those two ear files
  have every channel in `bads` and `amplifier_saturated: true`. Their scalp files are fine.

## Alignment
- The trials are the authors' 600 s epochs, cut at a hardware audio trigger (a separate sound-card channel into the
  EEG trigger input) played 5 s into each stimulus. The trigger channel itself is not shipped, so the onsets cannot
  be re-measured here (`alignment_method` `onset_only`, `trigger_type` hardware). Drift cannot be estimated (fixed
  600 s epochs) and is not corrected. Insert-earphone tube delay unknown.
- Both streams start at wav 5.000 s at EEG sample 0. This matches the authors' code and shipped envelopes, and it
  is confirmed from the EEG for the attended and the unattended stream (backward decoders peak at 5 s; none
  near 0 s).
- **The two amplifiers are not perfectly synchronous.** From the shared frontal electrode, the ear amplifier lags
  the scalp amplifier by 0-2 ms with a relative drift of about +2 ppm (~1 ms per trial). In a few trials the lag
  steps by ~15 ms mid-trial (probably samples lost by one amplifier; which one is unknown): sub-04 trial 2, sub-07
  trials 1, 4, 6, possibly sub-12 trial 5. They are listed in the sidecar (`amplifier_steps`), not corrected.
  Combine the two files sample by sample only with this in mind. The check was impossible where the shared
  electrode was too noisy (`amplifier_sync_assessable: false`).
- **Alignment grade: medium.** The trigger is hardware (documented) but could not be verified here. The low tier
  passes, the TRF peaks at ~190 ms with nothing at negative lags, and the DNN offset of -10 ms is typical for two
  talkers. No correction was applied.

## Validation (all 15 participants, average reference per amplifier, attended talker)
| | low tier (0.5-8 Hz) | 30-60 Hz | 30-250 Hz |
|---|---|---|---|
| scalp | pass: mean r 0.023, 13/15 subjects significant, TRF peak 188 ms | fail (SNR 1.02) | fail (SNR 1.06) |
| ear | pass: mean r 0.012, 8/15 significant, TRF peak 203 ms | fail | fail |

- Per condition (low tier): scalp video r 0.016 (8/15), no video 0.024 (12/15); ear video 0.009 (5/15; the
  TRF does not rise above the null, so this pass is marginal), ear no video 0.010 (5/15).
- DNN match-mismatch offset vs accou2023 (scalp): -10.2 ms (95% CI -13.8 to -6.6).
- Attention (backward decoder, 30 s windows): attended > ignored in 15/15 participants on scalp EEG
  (median accuracy 69%) and 14/15 on ear-EEG (57.5%); lag sweeps peak at 0 ms.
- Suitable for cortical envelope tracking and attention decoding (scalp; ear-EEG with low SNR). Not validated for
  high-frequency (brainstem/MLR) analyses.

## Known issues
- No trigger channel, inter-trial data, training trial or ASSR run are in the release.
- The paper describes the prelisten as target-only, the manual as both talkers (irrelevant here: it precedes the
  EEG).
- Participant notes from the authors' manual (e.g. sub-08 excessive blinking, sub-12 eyes closed in trials 1-2)
  are listed in `notes.md`, section 5.

Details: `notes.md`.
