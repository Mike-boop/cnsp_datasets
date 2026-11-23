# kern2022: monophonic classical music pieces (MEG)

MEG of 35 participants (sub001-sub035) listening to 19 monophonic Western classical pieces. The pieces were
synthesised for piano, oboe or flute and last 78.8-275.9 s (43.3 min in all). Each piece was played once, in a
pre-randomised order. Three short volume-setting test snippets come first. Trials 1-3 are the test snippets and
trials 4-22 the pieces, in recording order.

- **Source:** Donders Repository DSC_3018045.02_116_v1, doi:10.34973/5qxw-nn97 (registry entry `kern2022`, source
  `radboud_rdr`). The registry keeps 1162 of 3736 files, **207 GB of 358 GB**. It excludes empty MRI folders,
  source models, the authors' preprocessed data, eye-tracker EDFs and the MCCC corpus.
- **Licence: CC BY 4.0 plus the Radboud data use agreement** (`LICENSE.txt`). Acknowledge "Data were provided (in
  part) by the Radboud University, Nijmegen, The Netherlands".
- **Paper:** Kern, Heilbron, de Lange & Spaak (2022). *eLife* 11:e80935. doi:10.7554/eLife.80935
- **Code (authors):** in the release (`Code/`: Psychtoolbox presentation, FieldTrip preprocessing and analysis).
  Read, not run.

## Size
**35 participants, 25.7 h in total, 0.733 h per participant (0.733-0.744 h).**
- **Per condition:**
  - `music`: 0.722 h per participant (identical for everyone), 25.27 h in total.
  - `test`: 40 s per participant (80 s in sub008, who heard the snippets twice), 0.40 h in total.
- Durations come from the stimuli (`notes.md` section 11). `data_size.py` was not run because the standardised data
  had been deleted.
- A full standardisation would be about 115 GB.

## What is provided
- **MEG:** CTF-275, 269 axial gradiometers (MNE `mag`, T) and 29 reference sensors (`ref_meg`). **Recorded at
  1200 Hz, stored at 1000 Hz** (`sfreq=None` keeps 1200 Hz). The online low-pass was 300 Hz.
  - The data are stored without synthetic gradiometer compensation (grade 0, as recorded).
  - Fiducials and `dev_head_t` are kept. There are no head shapes.
- **Peripherals (`misc`):** UADC002, the recorded copy of the played audio (inverted, low-passed at 300 Hz), and
  UADC005-007 (EyeLink x, y, pupil).
- **Dropped:** UADC001 (the same audio), UADC003/004, UADC008-013, the unconnected EEG057-064, head-localisation and
  trigger channels. These follow the armeni2022 choices.
- **Bad channels:** none are marked. The authors' `BadChannels` files are empty.
- **Stimuli:** the wavs as played (44.1 kHz), named by file name (e.g. `JSBach_FlutePartitaBWV1013-4`, `test1-3`).
  - The wavs are stereo with different channels. Only the left channel (channel 0) was played on both ears; this is
    confirmed by the audio copy, against the paper's "right channel". The adaptor stores it mono.
  - The MIDI note annotations (`MidiDataMEG.csv`) are not carried yet.
- **Conditions:** `music` and `test`. The volume may have been adjusted during the test snippets.

## Alignment
- **Software trigger** (BITSI box, parallel port), sent after Psychtoolbox reports the playback start.
- **Onset: trigger + 4.1 ms, measured on the audio copy** (UADC002) and applied by default.
  - 210 reliable fits over 6 pieces x 35 participants: median 4.08 ms, IQR 3.83-4.42 ms, participant medians
    3.74-4.59 ms.
  - Only 6 of the 19 pieces have enough energy below the copy's 300 Hz low-pass to fit; the others get the
    constant.
  - **Test snippets** were triggered *before* a non-blocking start. Each test trial gets its own measured delay
    (7.6-30.6 ms).
- **Drift: +6.5 ppm** (MEG clock fast), from the audio copy. The median of the 210 fits is +6.47 ppm (IQR
  6.21-6.85). The Psychtoolbox logs give an independent +6.0 ppm. It is **corrected by default**, folded into the
  1200 -> 1000 Hz resample: 1.8 ms over the longest piece.
- **Jitter:** piece delays vary by 0.14-0.62 ms SD within a participant (`jitter_ms` 0.4; 2.5 for the test
  snippets).
- **Not corrected:** the ER3A tube delay. The tube length is not reported (~1 ms per ~34 cm).
- **Alignment grade: good.** Software trigger + 4.1 ms measured on the audio copy UADC002 (6/19 pieces fit, 210
  fits; the others get the constant). Test snippets are measured per trial. The +6.5 ppm drift from the audio copy
  (logs +6.0) is corrected. Brainstem tier (pilot of 4).

## Download and adaptor options
- `download_dataset("kern2022", <dir>)`. This needs a data.ru.nl account and its WebDAV credentials (`secrets.json`
  keys `ru-rdr-usr` / `ru-rdr-pwd`), exported as `RADBOUD_USERNAME` / `RADBOUD_PASSWORD`. Access worked with them
  and needed no manual agreement step. Every file matched `MANIFEST.txt` (sha256).
- `Kern2022Adaptor(download_dir, sfreq=1000, audio_delay=True, drift_correction=True, subjects=None)`:
  - `audio_delay=False` starts trials at the trigger;
  - `drift_correction=False` turns off the +6.5 ppm drift correction;
  - `sfreq=None` keeps 1200 Hz;
  - `subjects` limits the run to a subset.

  With `format_dataset`, pass these as `--adaptor-opt key=value`.
- The release also contains the diliberto2020 wavs (registry entry `diliberto2020_audio`).

## Validation
**Brainstem tier (high-frequency cortical response for MEG), piloted on 4 of 35 participants only.** The pilot used
sub001, sub010, sub020 and sub030, the first 10 pieces each, music only, axial gradiometers, no re-referencing:

| tier | uncorrected (trigger, no drift) | defaults (+4.1 ms, +6.5 ppm) |
|---|---|---|
| low 0.5-8 Hz | r 0.020, 3/4 | r 0.020, 3/4 |
| mlr 30-60 Hz | SNR 1.08 (p 0.030), 1/4 | SNR 1.19 (p 0.010), 2/4 |
| 30-250 Hz (28-45 ms) | SNR 1.33 (p 0.010), 2/4 | SNR 1.32 (p 0.010), 3/4 |

- The high-frequency peaks move ~4 ms earlier with the corrections, as predicted. No tier is worse.
- The 30-250 Hz peak is at ~33 ms, with no spike at 0 ms or negative lags.
- The 0.5-8 Hz TRF is periodic (note rate ~200 ms), so its reported peak flips between 0 and 78 ms.
- **Not run:** all 35 participants, and the test condition.

**Suitable for** low-frequency and high-frequency cortical responses to music.
**Caution:** responses are weak per participant. Most of the music's energy is above the MEG's 300 Hz low-pass, and
the data are uncompensated.

## Caveats
- The wav channel played differs from the paper's description; the audio copy decides it.
- The MIDI onsets of pieces 111 and 112 gave odd lags (270 and 510 ms) against the audio. This was not checked
  further.
- sub008 heard the three test snippets twice.

Details: `notes.md`.
