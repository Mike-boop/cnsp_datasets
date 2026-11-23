# calderondepalma2023: audiobook with spectral / temporal modulation degradation (OSF gx6rm, CND)

13 participants x 25 snippets (~3 min) of *The Old Man and the Sea* (male narrator), each snippet in one of five
conditions (clean, two temporal and two spectral modulation low-pass filters), 64-channel BioSemi EEG plus both
mastoids. Shared as CND `.mat` files: **EEG downsampled to 64 Hz but otherwise unprocessed** (no filter, no
re-reference: CMS/DRL with DC offsets), and the authors' 64 Hz features of the **degraded audio as played**. No
audio, no raw BDF, no triggers.

## 1. Source
- OSF project gx6rm (https://osf.io/gx6rm/), folder `spectrotemporalModulationsEEG/` (README.txt, LICENSE,
  `dataCND/` with 13 `dataSub<N>.mat` + 13 `dataStim<N>.mat`), 28 files, 2.44 GB. Listing saved as
  `tmp/review/calderondepalma2023/osf_listing.json`; all 28 files matched OSF size and md5 (2026-11-23).
- **Licence: BSD 3-Clause** (LICENSE file, "Copyright (c) 2026, Alejandro Lopez Valdes, Trinity College Dublin").
- Paper: Calderón De Palma I, Lopez LS, Lopez Valdes A (2023). Effects of spectral and temporal modulation
  degradation on intelligibility and cortical tracking of speech signals. *Interspeech 2023*, 5192-5196
  (`data_campaign/papers/calderondepalma2023.pdf`). README also asks to cite the CND paper (Di Liberto et al.,
  arXiv 2309.07671) and mentions a re-analysis (Di Liberto, "Robust evaluation of neural encoding models via
  ground-truth approximation", arXiv).
- Shared code: none for this dataset; the README points to the generic CNSP scripts
  (github.com/CNSP-Workshop/CNSP-resources, `CNSP2025_EEGpreprocessing.m`). Not run.

## 2. Layout
- `dataSub<N>.mat` (MATLAB 5), struct `eeg`: `dataType` 'EEG', `deviceName` 'BioSemi', `Origfs` 1024, `fs` 64,
  `data` {25} of [n x 64] float64, `extChan.description` 'Mastoids', `extChan.data` {25} of [n x 2],
  `origTrialPosition` (25, permutation of 1..25). **No `chanlocs`** (channel names not shipped; section 5).
- `dataStim<N>.mat`, struct `stim`: `names` = Envelope, Spectrogram (20 bands), PhonFeatures (19), Spectrogram+
  PhonFeatures (39); `data` {4 x 25}; `stimIdxs` = 1..25; `condIdxs` (1..5); `condNames` = Clean, Temporal60,
  Temporal80, Spectral60, Spectral80; `fs` 64; `addinfo`: `Hz` and `scale` (the modulation cut-offs per trial),
  `actualAudio` (= 1, a flag, not audio), `Origfs` 44100, `dur` (audio duration, s), `corr_factor`,
  `envelopecompression` = 1, `specgram_nbands` = 20, `specgram_cf` (80-8000 Hz, log spaced).
- Subjects 1-12 and 14 (no 13). 13 = the paper's N.

## 3. Stimulus <-> trial mapping (checked on all 13 subjects, `scripts/calderondepalma2023/explore*.py`)
- Every subject has 25 trials, 5 per condition. Index i (0..24) of `data` = **snippet** `stimIdxs[i]` = i+1:
  `dur` per index is identical across subjects (165.7-202.1 s). `origTrialPosition[i]` = presentation position
  (1..25) of that snippet (inferred from the name; a permutation in every subject).
- Condition codes agree with `Hz`/`scale` in every trial: 1 Clean (128 Hz, 16 cyc/kHz = no filter); 2 Temporal60
  (5 Hz); 3 Temporal80 (6 Hz); 4 Spectral60 (0.3 cyc/kHz); 5 Spectral80 (0.45 cyc/kHz). Paper: cut-offs 5/6 Hz and
  0.3/0.45 cyc/kHz chosen for ~60 % / ~80 % intelligibility (hence the names). Condition per snippet is randomised
  per subject.
- **The envelopes are of the degraded audio as played, not of the clean audio** (the paper's TRFs used the clean
  spectrogram; `actualAudio` = 1 presumably says this). For one snippet, envelopes of different conditions
  correlate 0.69-0.97; within a (snippet, condition) pair they correlate 1.00000 across subjects and differ only
  by a **per-subject gain** (0.87-1.26; identical in some pairs of subjects). Scale is arbitrary.
- Phonetic features are identical across conditions and subjects (binary, transcript-derived); the spectrogram is
  condition-specific like the envelope, and the envelope equals the sum over the 20 spectrogram bands (r = 1).
- Stimulus length = round(`dur` x 64) (within +-0.5 sample).

## 4. Speech features available
- Only 64 Hz features: Envelope (sum of a 20-band gammatone power spectrogram, compressed: paper exponent
  log10(2)?, `envelopecompression` = 1), Spectrogram, PhonFeatures. No audio (raw or degraded), no transcripts or
  word/phoneme timings beyond the phonetic-feature matrix.

## 5. Neural data
- BioSemi ActiveTwo, recorded at 1024 Hz (paper, `Origfs`); 64 scalp + 2 mastoid electrodes (paper). **Shipped at
  64 Hz**, otherwise raw: CMS/DRL (no reference applied; per-channel DC offsets of thousands of uV that change
  between trials), no high-pass. The paper's preprocessing (8 Hz low-pass, nt_detrend, 1 Hz high-pass, ICA,
  interpolation, mastoid re-reference) was **not** applied to the shared data.
- Anti-aliasing: weak. 50 Hz mains aliases to 14 Hz at 64 Hz and shows as a peak in several subjects (sub3 P2:
  ~1300x the median channel power at 14 Hz); the spectra fall only at the very top. Upstream issue (section 9).
- Units: uV (median channel SD 3.5-9.9 uV at 1-8 Hz with linked-mastoid reference, per trial). Scaled by 1e-6.
- Channel names: not shipped. **Assumed: BioSemi 64 default order (A1..B32 = Fp1 ... O2, MNE `biosemi64`).**
  Evidence (`chan_order.log`, `bads_screen.json`): (a) with a linked-mastoid reference, channel correlation vs
  `biosemi64` inter-electrode distance is above the 99th percentile of 200 shuffled orders in 12/13 subjects
  (rho 0.08-0.30; sub4 0.050 vs 0.066); (b) per trial, the highest-variance channels (1-8 Hz) are Fp1/Fp2/Fpz/
  AF7/AF8 (blinks) and the lowest P9/P10/Iz/P7/TP7 (next to the mastoid reference) in every subject.
- Mastoids: `extChan` columns 1-2 -> `M1`, `M2` (left/right **assumed** from the usual EXG1/EXG2 order; not
  documented). Kept as `misc`. No EOG, no stimtrack, no trigger channel shared.
- No NaNs. No flat channels. Bad-channel screen (`bads.py`, paper criterion SD < 1/6 or > 3x median, per trial,
  1-8 Hz, mastoid reference): the only > 3x channels are blink-driven frontal channels (sub4, 7, 8, 9, 10), which
  are physiological and not marked. **Marked bad: sub3 P2** (electrical noise only: mains alias, 0.1x median
  power elsewhere). Not marked but worth knowing: sub9 Fp1/AF7, sub12 AF7 (broadband 10-30x at 2 and 28 Hz;
  eye/muscle).
- Positions: none shipped; `biosemi64` template positions are set.

## 6. Alignment
- Paper: stimuli presented with Presentation, "trigger sent via parallel port and recorded by the EEG amplifier";
  Tascam US-100 sound interface, ER2 insert earphones (tube delay ~0.9 ms? not stated). Triggers are not shared;
  the authors cut the trials. Trigger timing is software-controlled (Presentation), so `trigger_type` =
  `software (Presentation, parallel port; paper)`; latency/jitter unknown.
- **EEG trials are 32-33 samples (0.5 s) longer than the stimulus** in all 325 trials: the epoch is the stimulus
  plus 0.5 s. Where the extra 0.5 s sits was checked by cross-correlating the half-wave-rectified envelope
  derivative with 1-8 Hz average-referenced EEG (RMS over channels, +-2 s) with the stimulus starting at trial
  sample 0: peaks at +16 to +219 ms in 11/13 subjects (sub4, sub8: no clear peak), grand average at ~+30-60 ms,
  nothing at -0.5 s (`xcorr_per_subject.png`, `eeg_checks.png`). So **stimulus onset = trial sample 0** and the
  extra 0.5 s is at the end (as in the CNSP convention).
- Proposed: onsets as shipped (sample 0), `alignment_method` = `sw_trigger`, EEG not cut to the stimulus (rule:
  the longer signal is cut at the point of use), no drift correction (cannot be estimated; see 7).
- Plausible tier: `low` only (64 Hz data and features).

## 7. Cross-subject duration check
- Not possible: trial lengths are set by the authors (stimulus + 0.5 s). Drift cannot be estimated. For scale:
  50 ppm over 200 s is 10 ms, below one 15.6 ms sample.

## 8. Data size
- 13 participants x 25 snippets = 325 trials; 75.8 min of stimulus per participant (all identical: same 25
  snippets), 76.0 min of EEG; 16.42 h in total (stimulus-based). Per condition ~15.2 min per participant
  (14.7-15.8).

## 9. Upstream issues
- No channel labels (`chanlocs`) in the EEG files; order inferred (section 5).
- Mastoid order (left/right) undocumented.
- The README calls the data "segmented into trials" from BDF but does not say the EEG was downsampled to 64 Hz
  without adequate anti-aliasing (mains alias at 14 Hz).
- The envelopes are of the degraded audio, while the paper's analysis used the clean speech spectrogram; not stated
  in the README. Per-subject gain differences in otherwise identical envelopes are unexplained.

## 10. Open questions (recommended defaults in brackets)
1. Sample rate. [Keep 64 Hz as shipped; never upsample (settled by the rules).]
2. Stimulus: envelope of the degraded audio. [One stimulus per (snippet, condition), named `s<kk>_<Condition>`,
   feature `envelope`, 64 Hz; the stored copy comes from the lowest-numbered subject with that pair (the other
   subjects' copies differ by a gain only, checked at parse time). Skip Spectrogram/PhonFeatures (could be added
   as extra features later). Optionally add the clean envelope of the same snippet as a second, unplayed stimulus
   for degraded trials (the paper's regressor). Default: not added.]
3. Channel names: BioSemi 64 default order assumed (evidence above). [Accept.]
4. Mastoids: `extChan` 1/2 -> M1/M2 (left/right assumed). [Accept, say "assumed" in the README.]
5. Reference: none applied (CMS/DRL raw). [Keep; record reference as `CMS/DRL (none applied); mastoids M1/M2
   included`.]
6. Onset at trial sample 0, extra 0.5 s of EEG at the end kept. [Accept.]
7. Bads: sub3 P2 only. [Accept.]
8. Subject exclusions: the paper (TRF-weight analysis only) "had to exclude subjects 11 and 13 from two
   conditions and subject 2 from one condition" (conditions not named; encoding accuracy not above significance).
   There is no file 13, so the paper's numbering may be 1..13 rather than the file names. All other statistics use
   N = 13. [Include all 13 subjects and all trials; mention the paper's partial exclusions in the README.]
9. Trial number = `origTrialPosition` (presentation position). [Accept.]

## 11. Adaptor (implemented with the defaults of section 10, 2026-11-23)
- Stimuli: `s<kk>_<Condition>` (120 of the 125 possible pairs occur), feature `envelope`, `{"fs": 64, "data": (1, n)}`
  float32, starting at trial sample 0, read from the lowest-numbered subject with that pair. At parse time every
  other subject's copy must have the same length and r >= 0.9999 with it (gain only), otherwise the adaptor
  raises. Spectrogram and PhonFeatures are not stored.
  The 120 envelopes are kept in memory from that check (no re-reading of the 92 MB stim files per trial).
- Trial = `origTrialPosition`; condition = `condNames`; session 1. Per-trial provenance: `sw_trigger`, trigger
  type software (Presentation via parallel port), drift/jitter null, snippet, temporal/spectral cut-offs,
  stimulus source subject, shipped trial index, `channel_names` = inferred (biosemi64 order). Parse checks:
  EEG and stimulus fs = 64 per subject, `origTrialPosition` a permutation of 1..25.
- EEG: 64 `eeg` (MNE `biosemi64` names and template positions) + `M1`, `M2` (`misc`), 64 Hz, x 1e-6 to V, no
  reference, no filtering, EEG not cut (runs 0.5 s past the stimulus). `info['bads']`: sub3 P2.
- Pilot = all 13 subjects: 325 trials, 120 envelope files, 1.0 GB, 40 s
  (`tmp/review/calderondepalma2023/standardised/`).

## 12. Validation (2026-11-23, all 13 subjects, average reference, `validation.json`)
- Sanity: 325 trials, no flags, no flat or NaN channels; EEG - stimulus = 0.500-0.516 s in every trial; median
  channel SD 3.4-12.3 uV.
- **Tier `low`** (64 Hz: mlr/brainstem impossible). Pooled: median r 0.030 (mean 0.031), 12/13 subjects above
  both nulls (sub4 r = 0.000: no tracking, also no peak in the cross-correlation check), p_circ 0.02,
  p_mismatch 0.048 (minimum attainable), TRF GFP peaks at ~+25 ms and +188 ms, above the null 95th percentile
  from -140 to +500 ms. Per-trial lag-sweep offsets: MAD 38 ms (64 Hz, 1-8 Hz).
- Per condition (5 trials = ~15 min per subject each; `validation_conditions/<cond>/`): all pass at population
  level, 8-9/13 subjects significant each. Median r: Clean 0.036, Temporal80 0.030, Spectral80 0.021,
  Temporal60 0.021, Spectral60 0.019 (the paper's ordering: clean best).
- Figures: `tmp/review/calderondepalma2023/validation.png`, `validation_conditions/<cond>/validation.png`,
  `eeg_checks.png`, `xcorr_per_subject.png`, `chan_order_blink_topo.png`.

## 13. Timing check: match-mismatch DNN offset (2026-11-23, note only)
`fs128_1020-64_broadband` classifier (accou2023), 100 random trials (pooled) / all 65 per condition, +-500 ms,
5 s windows, 1 s hop (`data_campaign/scripts/dnn_offsets.py`, run through
`tmp/review/scripts/calderondepalma2023/dnn_offsets_cdp.py`; the classifier's own preprocessing interpolates the
64 Hz EEG to 128 Hz, analysis only). Negative = neural data later than accou2023.

| set | offset | 95% CI (bootstrap over 13 subjects) |
|---|---|---|
| pooled | +2.5 ms | -0.8 .. +6.0 |
| Clean | +6.2 ms | +2.4 .. +9.0 |
| Temporal60 | +9.6 ms | +4.1 .. +15.4 |
| Temporal80 | +7.7 ms | +2.7 .. +13.5 |
| Spectral60 | -4.0 ms | -7.1 .. -1.2 |
| Spectral80 | -3.7 ms | -6.9 .. -0.3 |

Within the +-5 ms expected for clean speech with correct onsets, so trial sample 0 = stimulus onset is
confirmed independently. The condition differences (temporal degradations ~+8-10 ms, spectral ~-4 ms) are below
one 64 Hz sample and plausibly response-latency effects; documented, not applied. Figure:
`tmp/review/calderondepalma2023/dnn_offsets/offsets.png`.

## 14. Review (2026-11-23)
Reviewer findings applied (envelopes from memory, one name helper, fs checks once per subject, permutation check, channel-type list from the montage, provenance `channel_names`). Re-standardised all 13 subjects to `tmp/review/calderondepalma2023/standardised_v2/`: all 445 files identical to the pilot (EEG data, channels, bads, provenance apart from the new field; envelopes byte-equal). Not changed here (main-branch infrastructure): `base_sink` calls a stimulus `data_fn` before checking whether the file already exists.
