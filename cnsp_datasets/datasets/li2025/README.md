# li2025: BABA, a Chinese reality TV show watched with sound (OPM-MEG)

OPM-MEG of 30 native Chinese speakers (sub-31..60) watching the same 25-min excerpt of the reality show "Where Are
We Going, Dad?" (season 1, episode 1, 2013). The sound came through insert earphones (Sinorad ComfortBuds 24). The
excerpt has 11-13 speakers, including five father-child pairs, with overlapping speech and fast turn-taking. Each
participant has one trial (task `baba`, condition `audiovisual`).

- **Source:** OpenNeuro ds005346 v1.0.5 (doi:10.18112/openneuro.ds005346.v1.0.5), registry entry `li2025`. The
  snapshot is 120 GB, most of it the fMRI cohort (sub-01..30) and derivatives. The registry's `include`/`exclude`
  download only the MEG files and `sourcedata` (stimulus video, annotations, quiz): 191 files, **18.9 GB**.
  The fMRI, the MEG participants' T1s and `derivatives/` are not downloaded.
- **Licence: CC0** (`dataset_description.json`). Derived data may be redistributed without restriction. The paper
  itself is CC BY-NC-ND.
- **Paper:** Li J, Wang Q, Wang Y, Wang C, Ma Z, Xu R, Feng S, Jiang X, Meng Z (2025). Naturalistic fMRI and MEG
  recordings during viewing of a reality TV show. *Scientific Data* 12:1809. doi:10.1038/s41597-025-06110-5.
  The paper cites the data as v1.0.4.
- **Code (authors):** github.com/compneurolinglab/baba (fMRI analyses, Whisper transcription, Praat pitch and
  intensity). It has no MEG preprocessing or presentation code.
- **Not standardised:** the `question` run (5 visual multiple-choice items) and the `replay` run (15 min eyes
  closed). Neither has an auditory stimulus.

## Size
**30 participants, 12.42 h in total; mean 0.414 h per participant (range 0.194-0.422 h).** One trial each, from the
sound onset to the end of the shipped 1519.001-s file (about 1518.2-1518.6 s). The exception is sub-54, whose upload
is truncated upstream and has 698 s (697.6 s after the onset crop). There is a single condition, `audiovisual`, so
the per-condition figures are the same. The stimulus is 1519.2 s long. Before the onset crop the recordings total
12.43 h.

## What is provided
- **MEG:** Quanmag OPM-MEG with 64 single-axis radial magnetometers (`MEG001`-`MEG064`, type `mag`, in T) at
  **1000 Hz**. The rate is native: the only processing is the onset crop and the drift correction, which are applied
  together with one spline resampling (see Alignment). The data are raw as shipped: there are no projectors and no
  HFC or SSS. Large DC offsets (up to about 13 nT) and slow drifts remain, as do lines at the 50 Hz harmonics and at
  125/250/375/500 Hz.
  - **No other sensors:** the recording has no EOG, ECG, reference sensors or audio channel. The trigger channel
    STI1 is dropped: it holds a single non-zero sample, and its value is kept in the sidecar as
    `first_sample_trigger`.
  - **Positions:** the sensor positions come from the fixed helmet and are identical in all files. `dev_head_t` is
    the identity matrix and the fiducials are placeholders. Each file still has its own head-shape points.
  - **MEG062 lies on the z-axis** (x = y = 0), and MNE's `compute_proj_hfc` returns non-finite projectors when it
    is included. Leave MEG062 out of HFC. The validation does this; the stored data are unchanged.
- **Bad channels:** marked in `info['bads']` and kept in the data.
  - The paper reports channels 19 and 48 as bad in 16 participants. In the data `MEG019` is flat or about 3000x
    noisier in exactly sub-32..47, so **`MEG019` and `MEG048` are marked bad in sub-32..47**.
  - Channels whose 1-40 Hz spectrum is more than 10x the subject's channel median are also marked: sub-34 `MEG023`
    and `MEG040`, sub-42 `MEG005`, sub-47 `MEG005`, and sub-48 `MEG040`.
  - The authors' own bad-channel lists (PyPREP and visual inspection) are not shipped.
- **Stimuli** (the same for everyone):
  - `audio`: the soundtrack of `sourcedata/stimuli/baba_video.mp4`, decoded with ffmpeg. It is 44.1 kHz, float32
    and 2 channels (L and R are nearly identical, r 0.9995), 1519.235 s long. The audio runs past the end of the
    MEG and is not cut. The authors' Praat features in `wav_acoustics.csv` share the same time base (lag 0).
  - `words_csv`: `word_information.csv` stored verbatim, with 2930 words. It gives Whisper large-v3 timestamps
    (manually reviewed), the speaker (13 labels), onset and offset times, log frequency, POS and parser counts.
    Sixteen word pairs overlap in time (simultaneous speakers), so the words are not given as a TextGrid.
  - `transcript`: `transcripts.csv` (738 sentences), stored as CSV text.
  - The video (the visual stream) is not stored. `wav_acoustics.csv` is not stored either, because its features can
    be recomputed from the audio.
- **Sidecar** (`raw.info["description"]`): the alignment provenance listed below, `recording_group` (A =
  sub-31..47, B = sub-48..60, two recording periods with different spectra), `truncated_upload` and the bad
  channels.

## Alignment
- **No usable hardware timing.** STI1 has a single non-zero sample, **at sample 0** of each shipped file: code 6, or
  code 1 in sub-49, and no code at all in sub-40. The authors cut every recording at this video start trigger and to
  a fixed 1519.001 s. There is no end trigger, no audio copy and no photodiode, and the recording shows no
  audio-locked artefact. The trigger type (hardware or software), the presentation software and the audio latency
  are **not documented**. Sidecar `trigger_type`: "unknown (inferred software: the sound starts after it)".
- **The sound starts 0.4-1.3 s after the shipped first sample.** This was established from the brain response
  itself. Fitted from the shipped onset, the population envelope TRF peaks at +0.92 s in sub-31..47 and at about
  +0.5-0.66 s in sub-48..60. In the validation, the TRF peaks at the edge of the window (0.48 s) when the shipped
  onset is used.
- **Onset correction (brain-based, applied by default; user decisions 2026-11-23).** Each subject gets its own
  delay, taken from `onset.csv` (written by `alignment/subject_delays.py`). The delay is 0.39-1.26 s in whole ms, so
  the crop needs no resampling of its own.
  - **Method:** each subject's uncorrected 0.5-8 Hz envelope TRF (lags -1.5..+2.5 s) is matched to group A's
    corrected TRF. The match is a space-time correlation over lags -0.2..0.6 s on 58 channels, and the search covers
    shifts of 0-1.9 s. The delay is cross-checked against five parts of the recording.
  - **Fallbacks:** sub-37 and sub-40 get group A's delay, 0.80 s (`onset_fallback`), because their match r is below
    0.15 or their parts' MAD exceeds 50 ms.
  - **Ambiguous:** sub-33, 39, 47, 53 and 55 are flagged `onset_ambiguous`, because a second match peak more than
    100 ms away comes within 0.15 of the best r. Their delay is kept.
  - **Early sessions of sub-50, 52 and 53:** in the first ~10 min these subjects sit about 150 ms later than their
    whole-recording delay. This is documented but not corrected, because the early parts are their weakest fits.
    Treat the timing of the first ~10 min of these three recordings as uncertain by about 0.15 s.
  - **sub-53 is fragile:** its parts' MAD is 50.0 ms, exactly at the limit. After the drift correction its match
    switches to the second peak (0.429 -> 0.553 s).
  - **Held-out test:** delays estimated on some parts of the recording and scored on the others give per-subject
    delays that beat per-group delays for group B and for the outlier subjects (sub-43/48/49/60). Across all
    subjects the gain is small and not significant (pooled p 0.10). This test was run with the earlier narrow
    search window and was not repeated for the current one.
- **Drift correction (brain-based, applied by default; user decision 2026-11-23): -16.7 ppm** (MEG clock slow,
  so the delay shrinks by about 25 ms over 1519 s).
  - **Method:** the pooled Theil-Sen slope of the five parts' delays, each relative to its subject's own delay, over
    28 non-fallback subjects. The 95% CI is -27.4..-9.5 ppm. For reference, OLS gives -28.7 ppm (-49.9..-8.0), and
    without sub-50/52/53 it gives -16.3 ppm (-34.1..+1.5).
  - **How it is applied:** the correction is folded into the onset crop as one quintic-spline resampling onto the
    audio clock. The delays are midpoint estimates, so the crop starts at delay - drift x midpoint, about +12.7 ms
    for a full recording.
  - **Check:** on the corrected data, the pooled slope falls to -0.9 ppm.
- **Sidecar:** `alignment_method = brain_trf`, `onset_correction_s` (the actual start of the crop),
  `onset_estimate_s`, `onset_correction_method`, `onset_match_r`, `onset_parts_mad_ms`, `onset_fallback`,
  `onset_ambiguous`, `drift_ppm`, `drift_source` and `drift_corrected_ppm`.
- **Turning it off:** `Li2025Adaptor(download_dir, onset="group")` uses one delay per recording group (0.80 s for
  sub-31..47, 0.42 s for sub-48..60). `onset="none"` keeps the shipped first sample, and `drift_ppm=0` drops the
  drift correction. `onset="none", drift_ppm=0` gives the shipped data (`alignment_method = onset_only`).
  `format_dataset` uses the defaults, so instantiate the adaptor directly for these options. The estimation code is
  in `alignment/` (see `alignment/README.md`).
- **Circularity:** both corrections were estimated from this MEG data, and the template is group A's own corrected
  TRF. They assume an envelope-TRF peak near 100 ms. They cannot separate a late sound from a late response, and they
  read any latency change over the session (e.g. adaptation) as drift. A leave-one-subject-out template gives
  similar delays (within 25 ms for 12 of 15 group A subjects).
- **Jitter:** unknown. The validation's segment-offset MAD is 13 ms, but that figure comes from 250-s segments and
  low frequencies. **Alignment grade: `poor`** (brain-based onset and drift, CLAUDE.md).

## Validation
**Low tier** (all 30 subjects; final run with the adaptor defaults, `validation.json`). Each recording is cut into
6 x 250-s segments. HFC (without MEG062), a 0.1 Hz high-pass and notches are applied to the whole recording before
cutting, for the validation only.

| run | mean r | subjects sig. | p circular / mismatch | TRF peak | MLR SNR (p) | brainstem SNR (p) |
|---|---|---|---|---|---|---|
| default (per-subject onset + drift -16.7 ppm) | 0.0245 | 90% (27/30) | 0.020 / 0.048 | 94 ms | 0.93 (0.77) | 1.02 (0.31) |
| shipped onset | 0.0113 | 67% | 0.020 / 0.048 | 0.48 s (window edge) | - | - |

- With the correction, the TRF has peaks at about 94 and 235 ms (94 ms in group A, 78 ms in group B). The segment
  jitter MAD is 13 ms (68 ms with the shipped onset).
- A control with the stimulus shifted 5 s the wrong way gives r -0.002 and 0% significant.
- In this run, sub-31, 37 and 40 are not significant; sub-37 and sub-40 are the fallback subjects.
- **Higher tiers: not credible.** Earlier runs, including the wrong-offset control, "passed" the MLR tier nominally
  on a lag-0 analysis artefact. In the final run neither MLR nor brainstem passes.
- These numbers are not independent of the onset and drift estimates (same data).

**Suitable for** low-frequency (0.5-8 Hz) envelope or word-level TRFs, and for multi-talker, speaker-switch or
linguistic analyses at a resolution of about 0.1 s or coarser.
**Not suitable for** MLR, brainstem or other millisecond-precise latency analyses: the timing is brain-estimated
with unknown jitter, and absolute latencies are circular by construction. The response may also contain a visual
contribution, since participants watched the video.

## Caveats and upstream issues
- **sub-54 is truncated upstream:** its `baba` and `replay` files stop inside the last data buffer. The adaptor
  drops the incomplete buffer and keeps the 698 s that can be read (`truncated_upload`). The authors' derivative
  for sub-54 appears complete.
- The authors excluded 6 MEG participants for "different PSD patterns" but do not say which. All 30 are included
  here.
- Spectra fall into two groups, sub-31..47 and sub-48..60, which also differ in their sound delay. The cause is
  unknown.
- `meas_date` looks unreliable (12 participants on 2024-10-30, 9 on 2025-01-20).
- The paper says the sensors were not digitised. The files nevertheless contain head-shape points, placeholder
  fiducials and an identity device-to-head transform.
- The sub-44/45/46 MEG derivatives are nearly empty (0.1-0.6 MB). They are not used here.
- High-pass OPM data on the whole recording before cutting it into segments. Filtering each segment separately
  turns the nT DC offsets into edge transients that correlate with the stimulus.

Details: `notes.md`.
