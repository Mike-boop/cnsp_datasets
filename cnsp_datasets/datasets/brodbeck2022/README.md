# brodbeck2022: Appleseed audiobook, 47 min of continuous narrated English (MEG)

MEG while 12 native English speakers (19-23 years) listen to 11 consecutive excerpts (205-331 s each) of the
audiobook *The Botany of Desire* (Michael Pollan), in chronological order, one recording per subject. Earphones
inserted into the ear canal. English.

> **No audio.** The audiobook is copyrighted and was never released. The stimulus features are derived from the
> authors' 1000 Hz gammatone spectrogram, plus Praat TextGrids with word and phone times. Triggers are
> probably software-generated (~10 ms quantisation, inferred). Usable for low-frequency envelope tracking; the
> 30-60 Hz (middle-latency) response is only marginal, and brainstem analyses are not possible.

- **Source:** OpenNeuro ds007870 v1.3.4 "Appleseed Audiobook MEG", doi:10.18112/openneuro.ds007870.v1.3.4 (BIDS,
  converted with MNE-BIDS by the curators). Original release on Dryad, doi:10.5061/dryad.nvx0k6dv0 (same
  recordings). **Licence: CC0** (no restriction on redistributing derived data). The audio is not covered: it is
  copyrighted and in neither release.
- **Paper:** Brodbeck C, Bhattasali S, Cruz Heredia AAL, Resnik P, Simon JZ, Lau E (2022). Parallel processing in
  speech perception with local and global representations of linguistic context. *eLife* 11:e72056.
  doi:10.7554/eLife.72056
- **Code (authors):** Eelbrain and TRF-Tools (github.com/christianbrodbeck/TRF-Tools, commit 0928036 cited in the
  paper). No experiment or alignment code is shipped.

## Size
**12 participants, 132 trials, 9.3 h in total, 0.775 h (46.5 min) per participant (range 0.76-0.78 h).** One
condition (`appleseed`). Every subject hears excerpts 1-11 in order. sub-04 and sub-05 heard a different, shorter
excerpt `11b` (205.5 s) instead of `11` (284.9 s), so they have 0.757 h, the others 0.779 h.

## What is provided
- **MEG:** KIT/Yokogawa 157-channel whole-head system (UMD): `MEG 001-157` axial gradiometers (MNE type `mag`,
  in T) and the 3 reference magnetometers `MEG 158-160` (`ref_meg`, kept for optional denoising). Recorded at
  1000 Hz with online 200 Hz low-pass and 60 Hz notch; stored at **1000 Hz**. No EEG, EOG or ECG. No software
  gradient compensation and no projectors applied. The 32 MISC lines (trigger and idle lines, low-level noise;
  no audio copy or stimtrack) and `STI 014` are dropped.
- Bad channels from the shipped `channels.tsv` are in `info['bads']` (2-9 per subject; MEG 056 and 067 in every
  subject). MEG 056 is dead (constant value) in every subject and is among these bads. Use `info['bads']`:
  `pick('mag')` alone keeps the bad channels.
- Head digitisation (3 fiducials, 5 marker coils, ~1100 head-shape points) and `dev_head_t` are in the FIF. The
  release has no individual MRIs, only scaled-fsaverage coregistrations (`derivatives/`, not exported).
- **Stimulus** per trial: `appleseed-NN` (NN = 01-11, or `11b`) with three features:
  - `envelope`: broadband envelope, the sum over the 256 bands of the authors' gammatone spectrogram (linear
    amplitude, negative values clipped at 0, no compression), 1000 Hz.
  - `gammatone`: the 256-band spectrogram itself (20-4938 Hz, ERB-spaced, linear RMS amplitude), 1000 Hz.
  - `textgrid`: Praat TextGrid with `words` and `phones` tiers (Montreal Forced Aligner, from the authors).
  Both acoustic features are **10 ms shorter** than the stimulus, and each sample summarises audio [t, t+10) ms.
  So they **lead the audio by ~5 ms**, and TRF latencies come out ~5 ms late. This is not shifted. It is inferred
  from TRF-Tools parameters and the file lengths, because the script that made the shipped files is not shipped.
  The authors' log-compressed 100 Hz and 1000 Hz predictors are not exported.
- Trial = segment number (1-11) in presentation order. Trial metadata (`raw.info["description"]`, JSON) holds the
  provenance: `onset_s`, `stimulus_file`, `flagged`, drift and jitter estimates and notes.
- Not exported: the Tone task (~100 tones, 166 s; not continuous speech), empty-room recordings, ICA and
  coregistration derivatives.

## Alignment
- **Trigger onset (`sw_trigger`).** Each trial starts at the segment-onset trigger (code 162; `events.tsv`
  `onset`, which equals `STI 014` to the sample). The trial length is the stimulus length. No offset or drift
  correction is applied.
- **Trigger type: software (inferred, not documented).** The triggers are TTL lines recorded by the KIT system,
  but the paper does not say how they were generated. The offset-minus-onset trigger intervals differ from the
  stimulus durations by a few discrete values ~7-10 ms apart, which points to software triggers or audio buffers
  of ~10 ms. There is no stimtrack, so the absolute delay from trigger to sound (sound card, earphone tubing) is
  **unknown**.
- **Drift: none measurable.** Across the 126 regular trials the interval errors do not scale with length. In the
  six subjects with a stable pattern (01, 03, 09-12) the drift is +3.4 ppm (95% -14..+18). Recorded as 3.4 ppm and
  not corrected.
- **Jitter: ~10 ms** (order of magnitude). In about half of the recordings, one of the two triggers is displaced by
  ~7-10 ms from trial to trial. Whether the onset or the offset trigger carries it cannot be told without audio.
- **Flagged trials (7):**
  - sub-04, 05, 06, trials 6 and 7: the trigger interval is 1.265 s longer than the shipped stimulus. Envelope
    reconstruction places the shipped stimulus at the onset trigger (within ±30 ms), with the extra time after its
    end. The extra time is not used.
  - sub-11, trial 6: the trial starts at a restart of segment 6. An earlier false start (onset trigger 131 s
    before, no offset trigger) may have played the beginning once before.

## Validation
**Low tier, with marginal mlr.** The 30-60 Hz response passes only at population level. The brainstem tier was
not attempted.
- **Backward model** (ridge decoder on good gradiometers, lags 0-250 ms, 0.5-8 Hz, 64 Hz, leave-one-trial-out;
  circular-shift and mismatched-stimulus nulls): mean r **0.281** (median 0.296, range 0.171-0.335), **12/12
  subjects** above both nulls, and all 132 trials above the circular-shift null. Lag-sweep peak +2.8 ms, and every
  subject is within one sample. Repo validator (forward model): mean r 0.032, 12/12 significant.
- **mlr (30-60 Hz, 18-45 ms):** mean SNR 1.11, population p = 0.0099, but only **4/12 subjects** individually
  (sub-06, 09, 10, 12). The 30-60 Hz response peaks at 58 ms, outside the 18-45 ms window, so it is late and
  smeared. This fits the ~10 ms trigger jitter and the 10 ms window of the feature.
- **Forward TRF** (envelope, 1-10 Hz, 128 Hz, GFP): **M50 44 ms, M100 105 ms**. These include the ~5 ms feature
  lead. There is no sign of a large trigger-to-sound latency. The DNN offset check against accou2023 has not been
  run.
- **Flagged trials do not differ** from the rest (median r 0.238 vs 0.253 in the same subjects, p = 0.90).
- **Coherence** (MEG-envelope, complex mean over subjects, 5 s windows, ratio to a surrogate; bad channels
  excluded):

  | rate | 0.2-1 Hz | 1-4 Hz | 4-8 Hz | 8-15 Hz | 15-30 Hz | 30-60 Hz |
  |---|---|---|---|---|---|---|
  | 128 Hz | 6.4 | 2.9 | 2.7 | 1.34 | 1.05 | 1.04 |
  | native 1 kHz | 6.4 | 2.9 | 2.7 | 1.37 | 1.08 | 1.06 |

  At native rate: 60-120 Hz 1.02; 120-250 and 250-500 Hz ~1.00.
- **Suitable for:** low-frequency (≤ 8 Hz) envelope tracking and decoding, cortical TRFs (M50/M100), and
  linguistic-context models using the word and phone timings, with sensor-level MEG and reference sensors.
- **Not suitable for:** brainstem responses (no audio and no waveform regressor; ~10 ms software-trigger jitter;
  10 ms boxcar feature), latency comparisons at the ~10 ms level (unknown audio latency, ~5 ms feature lead),
  individual-subject middle-latency analyses, and any model that needs the audio waveform or its fine structure.

## Caveats
- **No audio** (copyright). Features come from the authors' spectrogram. A few spectrogram values are slightly
  negative (0.02% of samples, high bands), which points to post-processing of unknown nature. They are clipped
  at 0.
- **~5 ms feature lead and 10 ms short features** (see What is provided). The stimulus is not cut. Cut the longer
  signal at use.
- MEG 056 is flat in every subject and is marked bad. Exclude `info['bads']` before computing variance-based
  statistics (including it gave NaN coherence).
- Trigger type, absolute audio latency and the source of the 1.265 s excess in sub-04/05/06 trials 6-7 are unknown.
- Upstream issues: sub-11 `events.tsv` `sample` for the offset of segment 5 has a dropped digit (`onset` is right);
  sub-11 has an extra, unpaired onset trigger (false start of segment 6); `events.tsv` onset-row `duration` is the
  stimulus duration + 1.0 s; `derivatives/predictors` use 80-15000 Hz and log(x+1), not the paper's 20-5000 Hz and
  exponent 0.6; `_meg.json` says Elekta for a KIT system.

Details: `notes.md`.
