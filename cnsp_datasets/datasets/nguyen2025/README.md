# nguyen2025: scalp + in-ear EEG while attending one of two Danish TTS talkers

Twenty-four Danish listeners heard two competing synthesized (Google TTS) story snippets from loudspeakers at
-60/+60 deg and attended one of them. Scalp EEG and in-ear EEG were recorded simultaneously with two amplifiers.
Two paradigms of the release are included: `focus` (paradigm 3: 20 trials of ~21 s, the listener also attended to
target words of one category, e.g. animal names) and `attend` (paradigm 4: 40 trials of ~32 s of stories and
radio news, no targets).

- **Source:** Zenodo 8082867, doi:10.5281/zenodo.8082867. **Licence: CC BY 4.0.**
- **Paper:** Nguyen NDT, Mikkelsen K, Kidmose P (2025). Cognitive component of auditory attention to natural speech
  events. *Front Hum Neurosci* 18:1460139, doi:10.3389/fnhum.2024.1460139. Cite the paper and the Zenodo record.
  Paradigm 4 is described in the paper but not analysed there.
- **Not included:** paradigms 1-2 (isolated words about 1 s apart: not continuous speech) and the spontaneous EEG.

## Size
24 participants (sub-001..025 without 013), 60 trials each: **28 min of attended speech per participant (all
equal; focus 6.9 min, attend 21.2 min), 11.3 h in total**; recorded blocks 30 min per participant. Attended side
balanced (left/right).

## What is provided
- **Two files per trial, one per montage (= per amplifier)** (TMSi Mobita, 1000 Hz, kept at 1000 Hz):
  - `eeg/` (scalp amplifier): 30 scalp 10-20 channels (`eeg`; T7/T8/P7/P8 are named `T7-T3` etc. as shipped;
    template positions from the release), mastoids `M1`/`M2` (`misc`), and `Fpz`, the reference (all zeros).
  - `ear-eeg/` (ear amplifier): 12 in-ear electrodes `EL{A,B,C,E,I,T}` / `ER{A,B,C,E,I,T}` (individual earpieces,
    IrO2), `EOG` (`eog`; placement undocumented) and `cRef`, the reference (all zeros). No positions.
  - Each amplifier was re-referenced by the authors to its half of one combined Ag/AgCl + IrO2 electrode at Fpz, so
    both files share the same reference site. `Fpz` and `cRef` are kept as zero channels and listed in `bads`.
    Re-reference before use (the authors: average of the scalp channels, and of each ear's channels).
  - Raw data, DC-coupled and unfiltered: high-pass before use.
- **Audio:** both streams of each trial as shipped (24 kHz mono): `synth-<n>-<category>` (focus) and
  `real-<n>-target` (attend). The first stimulus in a file name is the attended one. In `focus` every snippet is
  played twice, once attended and once ignored.
- **Word timings** from the TTS tool, as a TextGrid per stimulus: tier `words`, plus tier `targets` (focus: the
  target words labelled by category).
- **Conditions:** `focus-<left|right>` and `attend-<left|right>` (attended loudspeaker). Sidecar fields: attended
  and ignored stimulus, attended side, focus target category, source epoch and block start sample, sex, age,
  handedness.
- **Bad channels** (`info['bads']`, per participant and amplifier): flat, railing or much noisier than the rest of
  the group (`bads.json`, notes section 5). **sub-007: every ear channel is bad** (the ear amplifier recorded
  zeros in `attend` and noise in `focus`). The scalp files of sub-007 are fine.

## Alignment
- Each trial is the authors' block: EEG sample 0 = the onset of both wavs (start of a hardware audio trigger that
  ships with every stimulus; inferred, the trigger channel is not in the release), up to the attended wav's end
  + 2 s (`alignment_method` `onset_only`).
- The trial-end events are computed from the design (identical in every participant), so clock drift and lost
  samples cannot be measured. Nothing is corrected.
- **The two amplifiers agree to within +-2 ms** in 98% of 10 s windows (in-ear vs mastoid on the same side). In
  8 trials one of them lost ~10-16 ms mid-trial, and 11 more show single-window jumps. They are listed in the
  sidecar (`amplifier_steps`); which amplifier lost the samples is unknown, so they are not corrected. Sync could
  not be checked for sub-007, sub-008, sub-015, sub-017 and sub-025 (`amplifier_sync_assessable: false`).
- **Alignment grade: medium** (proposed). The trigger is hardware (inferred) but could not be verified (no trigger
  channel, no audio copy). The low tier passes on scalp EEG with a TRF peak at ~190 ms and nothing above the null
  at negative lags. Backward-decoder lag sweeps peak at 0 ms on both amplifiers. No correction is applied.

## Validation (all 24 participants, average reference per amplifier, attended talker)
| | low tier (0.5-8 Hz) | 30-60 Hz | 30-250 Hz |
|---|---|---|---|
| scalp | pass: mean r 0.022, 19/24 subjects significant, TRF peak 188 ms | no (SNR 1.08; a ~10 ms ripple at all lags, inside the null) | fail (SNR 1.04) |
| in-ear | pass: mean r 0.018, 13/23 significant, TRF peak 94 ms | fail (SNR 1.03) | fail (SNR 1.09) |

- Per paradigm (low tier): scalp focus r 0.018 (9/24 significant), attend 0.019 (18/24); in-ear attend 0.014
  (9/23) passes, **in-ear focus fails** (r 0.011, 4/23; only 7 min per participant).
- The in-ear TRF is broad and already above the null at negative lags (unlike the scalp TRF). The amplifiers are
  in sync with the scalp one, so this is probably not a timing error but low SNR smeared by the envelope's
  autocorrelation.
- Attention (backward decoder, seconds 2-60 of each trial, 30 s windows): attended > ignored in 24/24
  participants on scalp EEG (median accuracy 75%); in-ear 14/23 (not significant, 50%). Decoder lag sweeps peak
  at 0 ms on both. Include the first 2 s and the shared sound-onset response hides the contrast.
- Suitable for cortical envelope tracking and attention decoding (scalp; in-ear with low SNR). Not suitable for
  high-frequency (brainstem/MLR) analyses.

## Known issues
- `channels.tsv` says V; the `.set` data are uV (read correctly into V here).
- sub-008's ear channels carry a +52.5 V DC offset as shipped (the signal itself is normal).
- `electrodes.tsv` is one spherical template for all participants; the ear electrodes copy the mastoid
  positions there (dropped here).
- Paradigm order within the session is not recorded; trial numbers assume the paper's order (focus 1-20, then
  attend 21-60).

Details: `notes.md`.
