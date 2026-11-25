# yang2026_en, yang2026_ru: one podcast conversation, repeated (Kymata SOTO language dataset)

MEG of native listeners hearing the same ~400 s excerpt of a BBC podcast conversation several times: 20 English
listeners (English podcast, "You're Dead to Me: The History of Ice Cream", BBC Radio 4) and 15 Russian listeners
(Russian podcast, "БибиСева", BBC Russian Service), recorded at the MRC CBU Cambridge on two different MEG systems.
Two adaptors, one per site (`yang2026_en`, `yang2026_ru`), sharing the code in `yang2026_base`.

- **Source:** OSF qdzgh, doi:10.17605/OSF.IO/QDZGH ("Kymata SOTO Language Dataset (English and Russian
  Conversations)"). **Licence CC-BY 4.0** (OSF node and the paper; both `dataset_description.json` say CC0):
  derived data may be redistributed with attribution. The audio are edited BBC programmes, redistributed by the
  authors; whether the BBC audio may be redistributed further is not discussed in the paper (**unverified**, to
  be confirmed by a human). Registry entry `yang2026` (one download for both sites; anatomy, the visual-stimulus
  images and the BIDS-check folders are not downloaded). Pass that download directory to either adaptor.
- **Paper:** Yang C, Parish G, Klimovich-Gray A, Wingfield C, Marslen-Wilson W, Zhang Y, Woolgar A, Thwaites A
  (2026). Kymata Soto Language Dataset: an electro-magnetoencephalographic dataset for natural speech processing.
  *Sci Data* 13:254. doi:10.1038/s41597-026-06579-8

## Size
One condition per site (`conversation`); hours = wav duration x presentations.
- `yang2026_en`: **20 participants (21 sessions), 162 trials of 401.5 s, 18.07 h; per participant mean 0.903 h
  (range 0.446-1.785 h).** 8 trials (0.892 h) per session; sub-E1 4 (0.446 h), sub-E8 6 (0.669 h); participant 3
  has two sessions (16 trials, 1.785 h).
- `yang2026_ru`: **15 participants, 60 trials of 412.5 s, 6.87 h; 0.458 h per participant (all equal**; 13 trials
  end 0.1-5.6 s early, 23.6 s in total).
- The validation used English participants 1-10 (11 sessions incl. sub-E3b, 82 trials, 9.15 h) and all Russian
  participants (60 trials, 6.87 h).

## What is provided
- **MEG:** 102 magnetometers (`mag`, T) and 204 planar gradiometers (`grad`, T/m), recorded and stored at
  **1000 Hz** (resampled only for the drift correction, see Alignment). English: MEGIN TRIUX (2023-2024, online
  0.1-330 Hz); Russian: Elekta Neuromag VectorView (2015, 0.03-330 Hz). No reference sensors. **Raw, as shipped: no
  SSS/MaxFilter.** Bad channels as marked in the FIF files (Russian 3-9 MEG channels per trial, all-zero in the
  data; English none). The fine-calibration and cross-talk files are in each site's folder of the download
  (`sss_cal_triux.dat`/`ct_sparse_triux.fif`, `sss_cal_vectorview.dat`/`ct_sparse_vectorview.fif`).
- **Other channels:** EOG (2, `eog`), ECG (`ecg`) and the recorded copy of the sound (`misc`; English MISC006 and
  MISC007, identical; Russian MISC005). Head-shape digitisation, fiducials, HPI coils and the device-to-head
  transform are kept. Continuous HPI (5 coils, 293-328 Hz) is in the data.
- **EEG:** the simultaneous EEG (`eeg`; English 64, Russian 70 channels, digitised positions), nose reference as
  recorded; FIF bads kept and flat channels marked bad. Not validated (validation, coherence and data size below are
  from the MEG).
- **Not included:** the 20 s practice
  excerpt (no wav), the empty-room recordings, button presses, and the visual dot stimulus shown during listening.
- **Stimuli** (one per site, shared by all trials): `conversation_en` (48 kHz, 401.53 s), `conversation_ru`
  (44.1 kHz, 412.46 s).
  - `audio`: the wav as shipped (float32; one channel, the shipped stereo has L = R);
  - `textgrid`: `words` and `phones` tiers built from the authors' Montreal Forced Aligner tables (transcript:
    Whisper, corrected manually; start times only, 10 ms steps: each interval ends where the next begins; pauses
    `<sp>` are empty intervals, `spn` = word not in the dictionary).
- **Condition:** `conversation`; trial = (run - 1) * 2 + presentation (two presentations per run, with questions
  between them). English participant 3's second session is session 2.
- Trial metadata (`raw.info["description"]`, JSON): file, run, presentation, code-3 sample, audio onset after code
  3, acoustic delay, drift measured and applied, fit windows, bads, SSS files, cHPI, truncation/glitch,
  `validation_tier` and `validation_note`.

## Alignment
- Triggers (code 3 = presentation onset) are sent by Psychtoolbox (paper): **software, inferred**; the audio starts
  18.7 +- 0.9 ms (English, 16.9-20.5) / 9.1 +- 0.35 ms (Russian, 8.4-9.8) after code 3. They only locate the
  presentations.
- Per presentation, the onset and the clock drift are measured on the audio copy (`alignment_method`
  `stimtrack_xcorr`: waveform cross-correlation with the wav in 10 s windows, positive peak, Theil-Sen line;
  `alignment/drift.py` -> `alignment/drift.csv`). Window residual 0.014 ms (English) / 0.024 ms (Russian) (`jitter_ms`). A further
  **7.3 ms acoustic delay** is assumed for the 2.5 m tubes of the insert earphones (not in the electrical audio copy;
  the authors' delay settings are not shared): an assumption, not measured.
- **Clock drift: English +538 ppm** (median +537.7, 537.05-538.73 ppm; the MEG counts ~1000.538 samples per audio
  second; without correction the end of a presentation is ~216 ms late), **Russian -0.76 ppm** (-1.02 to
  -0.42; 0.3 ms at the end). Corrected per presentation in the same interpolation that cuts the trial
  (`drift_correction="presentation"` default; `"site"` uses the site median, `None` turns it off).
- `alignment/drift.py` uses the positive-peak window fit `jehn2025_base/alignment/xcorr.window_fit`: jehn2025's
  `jehn2025_base.alignment.drift.trial_drift` (|xcorr| peak) locked onto an inverted side lobe here (41 presentations ~2.4 samples / up to 10 ppm off).
- Checked on the standardised data: the audio copy matches the wav at a lag of -7.3 ms (the assumed tube delay)
  at the start and the end of the trials, with < 0.13 ppm residual drift (notes.md section 10).

## Validation
**Brainstem tier with tSSS at both sites** (`validation_tier: brainstem` in every trial); the raw data as stored
reach **no tier** (the low forward tier fails). Magnetometers (102), no re-referencing; units = sessions (English
participants 1-10 + sub-E3b, 11 units; Russian 15). For MEG the "brainstem" tier tests the 30-250 Hz cortical
response at 28-45 ms; it shows high-frequency timing accuracy, not a brainstem response.

tSSS was applied in the validation only (the standardised data stay raw): bads = FIF bads +
`mne.preprocessing.find_bad_channels_maxwell` on the first 120 s of each trial (English 0-10 per trial, median 0;
Russian 3-12, median 7), `maxwell_filter` with the site's shipped fine-calibration and cross-talk files, tSSS
`st_duration` 10 s, origin fitted to the head shape, head frame, no movement compensation, no notch.

| | en tSSS | en raw | ru tSSS | ru raw |
|---|---|---|---|---|
| low forward (0.5-8 Hz), median r | 0.034 (11/11) | 0.001 (1/11, fails) | 0.030 (15/15) | 0.004 (1/15, fails) |
| backward (0-250 ms), median r | 0.237 (11/11) | 0.158 (11/11) | 0.219 (15/15) | 0.122 (15/15) |
| mlr (30-60 Hz, 18-45 ms) | 1.43 / 1.42 (8/11) | 1.08 / 1.07 (4/11) | 1.20 / 1.24 (6/15) | 0.98 / 1.02 (2/15) |
| brainstem (30-250 Hz, 28-45 ms) | 1.25 / 1.31 (9/11) | 1.06 / 1.04 (2/11) | 1.14 / 1.15 (7/15) | 0.98 / 1.00 (1/15) |
| tier | **brainstem** | none | **brainstem** | none |

(mlr, brainstem: SNR median / mean; participants significant in brackets; all tSSS group p 0.01-0.02. Raw
English mlr and brainstem pass at group level, p 0.04 and 0.01, but the tiers build on the low tier; raw Russian
mlr p 0.27, brainstem p 0.63.)
- **Raw data:** the low-frequency TRF does not exceed the circular-shift null at either site, and the 30-60 and
  30-250 Hz TRFs show a periodic ripple at every lag (10-20 ms period in the GFP), with nothing above the null in
  the response windows. tSSS removes it. In the raw data > 99% of the 30-250 Hz magnetometer power is at 50 Hz and
  its harmonics (cHPI check below), so the ripple is most likely mains interference (not verified). The raw
  backward decoder is above its null in every unit, with lower r than after tSSS.
- **Per-trial tiers by unit** (tSSS): English 58 trials brainstem, 24 low (S002, S005, S009); Russian 20 brainstem
  (S004, S008, S012, S014, S015), 4 mlr (S010), 36 low. Raw: English 4 low (S001), 78 none; Russian 4 low, 56 none.
- **Backward lag sweep** (64 Hz, +-1 s): peak at **+1.5 ms (95% CI +0.8 to +2.1) English, +0.7 ms (+0.3 to +1.3)
  Russian**, every unit within one sample (15.6 ms; unit peaks -0.1 to +3.9 / -1.0 to +5.4 ms). Without the drift
  correction the English stimulus would slide by up to 216 ms over a trial, so this confirms the audio-copy onsets
  and the per-presentation drift end to end. It is consistent with the assumed +7.3 ms tube delay but cannot
  establish it (one-sample resolution; the peak also depends on the response shape; habersetzer2025: +0.7 ms with
  a 0.4 ms delay). The validator's residual drift estimate is -9 +- 47 ppm (en) / -7 +- 83 ppm (ru), consistent
  with 0.
- **Latencies (tSSS):** 30-60 Hz TRF GFP peaks at 39 ms (en) / 38 ms (ru); 30-250 Hz at 29 / 36 ms. Low-frequency
  TRF (1-15 Hz, GFP): English M50 44 ms, M100 95 ms (grand average; subject medians 45 / 107 ms); Russian M50 38 ms,
  M100 93 ms (subject medians 39 / 95 ms).
- **cHPI check** (sub-002 trial 1, first 120 s, magnetometers): the cHPI band (290-332 Hz) holds < 0.1% of the
  30-250 Hz power, raw or after tSSS; filtering it out changes the 30-250 Hz rms by <= 3.4%. Negligible, not
  removed.
  50 Hz harmonics hold 99.5% of the raw 30-250 Hz power and 28% (en) / 35% (ru) after tSSS (rms 4.8 / 4.5 pT raw,
  0.14 pT after tSSS).
- **No mismatch null:** one stimulus per site, so the mismatched-stimulus null is not defined; the circular-shift
  null only.
- **Comparison with other MEG datasets** (same code, magnetometers; mean SNR, participants significant):

  | dataset | n | low median r | mlr SNR | brainstem SNR | tier |
  |---|---|---|---|---|---|
  | yang2026_en, tSSS | 11 | 0.034 (11/11) | 1.42 (8/11) | 1.31 (9/11) | brainstem |
  | yang2026_ru, tSSS | 15 | 0.030 (15/15) | 1.24 (6/15) | 1.15 (7/15) | brainstem |
  | yang2026_en / _ru, raw | 11 / 15 | 0.001 / 0.004 (fail) | 1.07 / 1.02 | 1.04 / 1.00 | none |
  | habersetzer2025, tSSS | 24 | 0.060 (24/24) | 1.40 (18/24) | 1.25 (14/24) | brainstem |
  | habersetzer2025, raw | 24 | 0.030 (23/24) | 1.26 (7/24) | 1.01 (1/24) | mlr |
  | gwilliams2023 | 20 | 0.046 (20/20) | 2.09 (20/20) | 1.55 (19/20) | brainstem |
  | armeni2022 | 3 | 0.061 (3/3) | 2.57 (3/3) | 3.03 (3/3) | brainstem |
  | schueller2024 | 19 | 0.020 (19/19) | 1.05 (4/19) | 1.68 (18/19) | brainstem |

- **Coherence** (MEG vs the envelope, 102 magnetometers, no re-reference; 5 s Hann windows, 4 s overlap; ratio to
  one global-shift surrogate): on the raw data weak (English 0.83-1.54 below 60 Hz, 1.04-1.16 above; Russian
  1.09-1.88, 128 Hz and native rate alike, after the flat channels were marked bad). With tSSS (4 participants per
  site, native rate) envelope coherence is clear at low frequencies: English 3.29 (0.2-1 Hz), 2.35 (1-4 Hz),
  2.62 (4-8 Hz), 1.52 (8-15 Hz); Russian 2.08, 1.57, 2.39, 1.39; ~1.02-1.09 from 15 to 500 Hz at both sites.
- **DNN offset:** not applicable (the match-mismatch classifier is trained on EEG).
- **Suitable for**, **after tSSS as validated above**: low-frequency envelope tracking and decoding, word- and
  phone-level analyses (forced-aligned TextGrids), middle-latency and 30-250 Hz cortical responses (timing to
  ~1 ms with an assumed 7.3 ms tube delay; triggers are software and are not used for timing), and repetition
  effects (the same stimulus 4-8 times per participant). **Apply tSSS (or equivalent Maxwell filtering) for any
  analysis**: the raw data fail even the low tier. Not suitable for between-stimulus comparisons within a site
  (one stimulus). Subcortical (ABR/FFR-type) responses were not tested.

## Decisions taken (coordinator, 2026-11-22; to revisit)
- **Raw data standardised** (least processed); Maxwell filtering is up to the user (see Validation for settings).
- **EEG kept in the MEG trials** (user, 2026-11-22), nose reference as recorded; not validated.
- **Onset = fitted audio-copy onset + 7.3 ms assumed tube delay** (precedent: schueller2024's +6 ms tube delay).
- **Drift corrected per presentation** from `drift.csv` at both sites (default `drift_correction="presentation"`).
- **sub-E12 run-1 presentation 2:** the playback paused ~15 ms at wav ~352 s; onset and drift are fitted on the
  windows before wav 351 s and the trial ends at wav 351 s (`fit_end_s`, `glitch` in the metadata).
- **Truncated Russian presentations** (13 second presentations of a run, 0.1-5.6 s short): kept, shorter than the
  wav (`truncated_s` in the metadata).
- **Licence:** CC-BY 4.0 (OSF node + paper) over the CC0 in both `dataset_description.json`; redistribution of the
  BBC audio still to be confirmed by a human.
- **sub-E3b** = participant 3, session 2; **sub-E1** included with its 4 presentations.
- **Channels kept:** MEG, EOG, ECG, audio copy; cHPI lines left in.

## Caveats
- **No SSS:** every analysis needs Maxwell filtering first (raw fails the low tier); the FIF bads are kept, but
  `find_bad_channels_maxwell` flags further channels in some trials, which are not marked in the stored data.
- The acoustic delay (7.3 ms) is an assumption (tubes only; the ER3 transducer and the authors' delay
  configuration are not accounted for).
- 13 Russian second presentations are 0.1-5.6 s shorter than the wav (the recording stopped early).
- English sub-E12 trial 2 (run 1, presentation 2) ends at wav time 351 s (playback glitch, see above).
- sub-E1 has only 4 trials (runs 3-4 are not on OSF; the paper reports 8).
- Russian FIF bads are all-zero channels in the data (excluded by tSSS; exclude them in any other analysis).
- The visual dots started with the audio and may add visual onset responses.
- The paper swaps the two MEG systems in its Procedure section; the file headers are followed here.
- `events.tsv` drops code 3 when bit 16 of STI101 is high (sub-E6 run 2); the adaptor decodes STI101 & 0xFF.

Details: `notes.md`.
