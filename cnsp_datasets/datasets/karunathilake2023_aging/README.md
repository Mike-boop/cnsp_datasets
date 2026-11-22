# karunathilake2023_aging: younger and older listeners, speech in quiet, with a competing talker and in babble

MEG while 18 younger (18-26 years) and 16 older (65-78) adults listen to 60 s passages of *The Legend of Sleepy
Hollow* (male and female LibriVox narrators) in quiet, with a competing talker of the other sex at 0 or -6 dB SNR
(attend one talker), and with three-talker babble. Diotic, insert earphones. English.

> **Not sensor MEG.** Only 6 DSS components per subject are shared, already band-passed 1-10 Hz and downsampled to
> 250 Hz by the authors, in arbitrary units. Usable for low-frequency (1-8 Hz) envelope tracking only (`low` tier).
> Stimulus onsets are inferred (no triggers); presentation order is unknown.

- **Source:** DRUM (University of Maryland), doi:10.13016/4goq-vs0z (hdl 1903/29748). **Licence: CC0 1.0** (no
  restriction on redistributing derived data).
- **Paper:** Karunathilake IMD, Dunlap JL, Perera J, Presacco A, Decruy L, Anderson S, Kuchinsky SE, Simon JZ
  (2023). Effects of aging on cortical representations of continuous speech. *J Neurophysiol* 129:1359-1377.
  doi:10.1152/jn.00356.2022
- **Code (authors):** in the DRUM item (`MEG Analysis.zip`, MATLAB: DSS, TRF, reconstruction).

## Size
34 participants (18 younger, 16 older), 23 trials of 58.5 s each: **12.7 h in total, 22.4 min per participant**
(identical for everyone).
- `quiet`: 8 trials, 7.8 min per participant, 4.4 h;
- `snr0dB`: 6 trials, 5.9 min, 3.3 h;
- `snr-6dB`: 6 trials, 5.9 min, 3.3 h;
- `babble`: 3 trials, 2.9 min, 1.7 h.

Each two-talker and babble mixture is played three times (same audio), so the unique audio is 8 single talkers,
4 two-talker mixtures and 1 babble mixture. Same stimuli for every subject.

## What is provided
- **MEG components, not sensors:** `dss1`-`dss6` (MNE type `misc`, unit `FIFF_UNIT_NONE`, arbitrary units), the
  first 6 DSS components ranked by trial-to-trial reproducibility. Recorded on a KIT system (157 axial
  gradiometers, 3 reference magnetometers, 2 kHz); the authors removed bad channels, applied TSPCA (with the
  reference channels) and SNS, a **causal 1-10 Hz FIR**, DSS, and downsampled to 250 Hz. Stored at **250 Hz**
  (as shared; not upsampled). The data contain nothing above ~12 Hz (-71 dB at 12-15 Hz) and little below 1 Hz.
  No sensors, reference channels, topographies, head shape, triggers or stimtrack are shared.
- **Auditory component:** `dss1`, except subject 594 (R2594), where it is `dss2` (paper, authors' code; sidecar
  field `auditory_component`). Components are stored as shared: **polarity is not aligned across subjects** and
  the order is not changed.
- **Subjects:** subject number = R-number - 2000 (R2509 -> 509); the R-number and age group (`younger`/`older`)
  are in the sidecar. Ages are not shared, only the group.
- **Stimuli** (`audio`, 22.05 kHz mono, as shipped; wavs are 60.0-69.0 s, longer than the 58.5 s of MEG: cut at
  use):
  - `quiet`: the single talker (`pass_single_<talker>`, attended);
  - `snr0dB` / `snr-6dB`: attended talker (`pass_single_*`, attended), the mixture as played (`pass_mix_*`) and the
    unattended talker (`pass_single_*`);
  - `babble`: attended stream **`babb_F08_foreground_derived`**, derived as
    `babb_mix_F08_BF08 - 0.714 * babb_singleQ_BF08` (the played foreground; the shipped `pass_single_F08` is the
    same passage but not sample-identical to it), the mixture as played (`babb_mix_F08_BF08`) and the babble track
    (`babb_singleQ_BF08`).
- No transcripts or word/phoneme timings.
- Trial metadata (`raw.info["description"]`, JSON): participant, age group, source array and row, played /
  attended / unattended wav, SNR, attended talker's sex, auditory component, onset shift, derived-stimulus formula
  (babble), preprocessing.

## Alignment
- **No triggers; onset inferred.** The authors epoched every trial to 60 s from stimulus onset *before* the
  causal FIR, so each shared array is delayed by the filter's group delay, 1.5 s (375 samples at 250 Hz). The
  adaptor drops these 375 samples, so t = 0 is stimulus onset and each trial lasts 58.5 s (`onset_only`). Evidence:
  the authors' envelopes match ours only after a +1.50 s shift, the MEG amplitude ramps up over the first 1.5 s
  exactly like the filtered envelope, and the authors' own code drops the first 1.5 s.
- **The first ~1.5 s of every trial carry the filter's start-up transient** (the input before onset was zero).
  Drop them in analyses, as the authors and the validation below did.
- Trigger type and tube/acoustic delay: not documented (unknown, not corrected). The decimation phase of the
  authors' downsampling is unknown (expected < 1 sample at 250 Hz, unverified).
- Drift and jitter: cannot be estimated (no triggers, all trials cut to the same length by the authors); not
  corrected. At a typical 10-35 ppm drift the error is 0.6-2 ms per 58.5 s trial (an estimate, not measured).
- The trial-to-stimulus mapping (same for every subject) was verified against the authors' code and by
  cross-correlating each trial with every stimulus envelope, averaged over subjects.
- **Presentation order is unknown:** trial numbers follow the order of the shared arrays (1-8 quiet, 9-20
  two-talker, 21-23 babble), not the order of presentation. In the experiment, each two-talker block played its
  mixture three times and then the two talkers alone; the babble block was always third (paper).

## Validation
**Low tier** in every condition (quiet, snr0dB, snr-6dB, babble). The `mlr` and `brainstem` tiers cannot be run:
the shared data have nothing above ~12 Hz.
- **Backward** (review script; ridge decoder on the 6 components, lags 0-250 ms, 0.5-8 Hz, 64 Hz, first 1.5 s of
  each trial dropped, leave-one-trial-out within condition; 50 circular shifts and mismatched-story nulls): median
  r quiet 0.184, snr0dB 0.127, snr-6dB 0.154, babble 0.078; one decoder over all trials 0.144. All 34 subjects
  above both nulls in quiet and the two-talker conditions; babble 26/34 above the circular-shift null and 28/34
  above the mismatch null (9 subjects fail at least one null: R2534, R2535, R2538, R2553, R2565, R2595, R2654,
  R2660, R2661). Attended > unattended in 33/34 subjects (snr0dB and snr-6dB) and 32/34 (babble; unattended = the
  babble track).
- **Lag sweep:** peaks at +0.7 ms (quiet), +1.2 ms (snr0dB, snr-6dB), -0.3 ms (babble); a positive offset of
  about 1 ms is a property of the method (habersetzer2025 shows the same) and well within one sample (15.6 ms at
  64 Hz). In babble, 13 subjects peak > 50 ms away (weak responses).
- **TRF** (forward, attended envelope, 1-10 Hz): grand GFP peak at 65 ms in quiet (further peaks near 125 and
  200 ms), 148 ms (snr0dB), 152 ms (snr-6dB), 150 ms (babble). Responses are later in competing speech, as in the
  paper.
- **Age:** reconstruction is better in older than in younger listeners in every condition (Mann-Whitney: quiet
  p = 0.0004, snr0dB 0.03, snr-6dB 0.02, babble 0.009), matching the paper's main result.
- **Repo validator** (forward model, first 1.5 s included, so weaker): median r 0.044, all 34 subjects
  significant; babble 0.028 (21/34).
- **Coherence** (component-envelope, mean of per-subject |coherency|, because component signs and order differ
  across subjects): ratio to the surrogate 1.3-1.7 at 0.2-8 Hz in quiet and the two-talker conditions, 1.1-1.3 in
  babble; flat above ~10 Hz. With this pooling the noise floor depends on the number of trials, so conditions with
  different trial counts are not directly comparable.
- Suitable for: low-frequency envelope tracking and decoding, effects of age, SNR and attention, with 6 inputs per
  subject. **Not suitable for:** sensor-level or source analyses, topographies, anything above ~10 Hz
  (middle-latency or brainstem responses), absolute amplitudes, and analyses of presentation order or
  adaptation over trials.

## Caveats
- Components, not sensors (see above); polarity differs across subjects, so average TRFs over subjects with care
  (e.g. GFP or |TRF|), and use `dss2` for subject 594 as the auditory component.
- The condition called "6 dB SNR" in the paper is **-6 dB** (attended talker 6 dB softer): an exact decomposition
  of the mixture wavs gives -6.0 dB, and the paper's supplement says -6 dB. Labelled `snr-6dB`.
- Wav levels are not presentation levels (stimuli were calibrated to 70 dBA; in the female-attended mixtures the
  attended talker has gain 0.5 relative to its single wav).
- Excluded: a 9th quiet row in six younger subjects (R2509, R2629, R2654, R2660, R2665, R2666), which is junk
  (byte-identical across the six, ~2000x the scale of other trials, unrelated to their data; the authors' code
  ignores it). Not shared upstream: the quiet F08 trial at the end of the babble block, two subjects excluded by
  the authors (saturation), the redundant 100 Hz files (same signal; not used).
- Upstream issues: the junk 9th row; "6 dB" vs -6 dB; the paper describes the data as group-delay compensated, but
  the shared arrays are still delayed by 1.5 s.

Details: `notes.md`.
