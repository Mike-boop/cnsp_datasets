# kulasingham2021: isochronous sentences and arithmetic equations, single talker and two talkers (MEG)

MEG of 22 adults (R2522, R2566-R2589; R2567 is listed but not shipped) listening to synthesised monosyllabic words
at a fixed rate. The words form 4-word sentences or 5-symbol arithmetic equations, in 18-s trials.
- **Single talker:** 4 blocks x 10 trials, one male and one female voice.
- **Two talkers:** 8 blocks x 6 trials. A sentence stream and an equation stream play in different voices, and the
  listener attends one.
- **Task:** half of the blocks contain a deviant trial, and the listener answers "outlier?" after each trial.
- Each participant has 88 trials.

- **Source:** DRUM (University of Maryland), item `93067450-51d7-43c6-bb8f-53d4195db334`, doi:10.13016/xd2i-vyke
  (registry entry `kulasingham2021`), 4.88 GB. A backup is on the NHR vault.
- **Licence: none stated** on the DRUM item (checked 2026-11-23). This is an **open question**: whether the data,
  or anything derived from them, may be redistributed is unknown. Ask the authors before sharing.
- **Paper:** Kulasingham JP, Joshi NH, Rezaeizadeh M, Simon JZ (2021). Cortical processing of arithmetic and simple
  sentences in an auditory attention task. *J Neurosci* 41(38):8023-8039. doi:10.1523/JNEUROSCI.0269-21.2021
- **Code (authors):** github.com/jpkulasingham/cortical-sentence-equation (one notebook; read, not run).
- **Overlap:** there is no participant overlap with the other datasets in the campaign. `kulasingham2020` extends
  the presacco2016 recordings instead.

## Size
**22 participants x 0.44 h = 9.68 h in total** (26.4 min each, the same for everyone). Durations are counted from
the 18-s stimuli (`notes.md` section 8; `validation.json` gives the same total). `data_size.py` was not run because
the standardised data had been deleted.
- `single_equations` and `single_sentences`: 6 min per participant each, 2.2 h in total each.
- `cocktail_attend_equations` and `cocktail_attend_sentences`: 7.2 min per participant each, 2.64 h in total each.

The stored epochs are 20 s long (18 s of stimulus + 2 s). The standardised output is about 5 GB.

## What is provided
- **MEG: the authors' preprocessed epochs only** (no raw data).
  - **Preprocessing:** KIT 157-channel axial gradiometers (`mag`, T) + 3 reference magnetometers (`ref_meg`),
    recorded at 2 kHz. The authors applied TSPCA, SNS, FIR 0.3-40 Hz and ICA, and decimated to **200 Hz, which is
    stored as shipped**.
  - **Filter band:** the single-talker files of 20 subjects are low-passed at 30 Hz according to their `info`, not
    40 Hz. The sidecar gives each file's band.
- **Peripherals:** the MISC and STI lines are dropped. The end pulse and button presses go to the sidecar. There is
  no audio copy, EOG or ECG.
- **Bad channels:** MEG 040 and MEG 056 in every file, as shipped (de-duplicated). SNS has reconstructed them, so
  they are not flat.
- **Digitisation:** head shapes only for R2522 and R2588 (single). There is a `dev_head_t` per file.
- **Stimuli:** the wavs (22.05 kHz).
  - **Single-talker trials:** the attended stream.
  - **Two-talker trials:** the attended stream (`fg`, `is_attended`), the played mixture (`mix`) and the ignored
    stream (`bg`). `fg` and `bg` are unscaled; the played level is g x stream, with g 0.703-0.711 (`mix_gain`).
  - **Text:** the attended stream's text and deviant flags from `trials.csv` are in the sidecar. There are no
    TextGrids. Word timing is fixed by design (375/360 ms slots), but no onsets are generated.
- **Trials:** 1-40 are single talker and 41-88 two talkers, in presentation order. Subject = full R-number.

## Alignment
- **The authors cut each epoch 18.0 s before an end-of-stimulus pulse** (MISC 014, at 17.996-17.998 s in 1895
  trials). The pulse is one sample later in the R2585 single-talker trials and missing in R2570 cocktail epoch 36.
- **Onset:** the epoch start, as shipped (`onset_only`). The evoked response rises from ~30 ms and peaks at
  75-120 ms after t = 0, and an offset response follows 18 s later, which supports t = 0 = sound onset.
- **Trigger type:** unknown. The paper names no presentation software, and the insert-tube delay is not given.
- **Drift and jitter:** not measurable, because each epoch holds only one pulse. 18 s at a typical sound-card drift
  of 10-50 ppm is under 1 ms.
- **Alignment grade: medium.** The authors' 200 Hz epochs are cut 18 s before the end pulse. t = 0 is supported by
  the evoked onset responses. The TRF rise from -40 ms is attributed to stimulus periodicity. Low tier.

## Download and adaptor options
- `download_dataset("kulasingham2021", <dir>)`. DRUM is slow and times out, so use 1 worker and
  `read_timeout=120`. No credentials are needed.
- Extract the zips (the downloader does this by default). The adaptor searches its root recursively for the
  `R####/` folders and `stimuli/`.
- `Kulasingham2021Adaptor(download_dir)`. It has no options.

## Validation
**Low tier, all 22 subjects** (1936 trials), gradiometers without bads, attended stream. This is the highest tier
possible with 0.3-40 Hz data at 200 Hz.
- **Pooled:** mean r 0.051, 22/22 subjects significant.
- **Per condition:**
  - single equations and sentences: r 0.067 and 0.065, 22/22 each;
  - two talkers, attend equations: r 0.053, 21/22;
  - two talkers, attend sentences: r 0.043, 20/22.
- **Backward decoder:** attended r 0.205 vs ignored 0.121 in two-talker trials. Attended > ignored in 20/22
  subjects. The lag sweep peaks at 0 / +10 ms.
- **Periodicity:** the isochronous envelope repeats every 360-375 ms. The TRF therefore rises from about -40 ms, and
  the validator's per-trial offsets and drift are aliasing, not timing errors.
- **Not run:** DNN offset check (EEG-only) and coherence.

**Suitable for** low-frequency tracking, attention decoding, and analyses at the word, sentence and equation rates.
**Not suitable for** middle-latency or brainstem analyses, or for re-preprocessing (no raw data).

## Caveats
- **Licence not stated** (see above).
- **R2522 block order:** it is **female-first, not male-first as the readme says**. Button presses (p 0.008) and MEG
  decoding agree. The adaptor uses female-first and flags it (`block_order_source`).
- R2567 is listed in the readme but not shipped.
- `info['bads']` has duplicate entries upstream.
- Block `10kateMATH` uses different wav names.

Details: `notes.md`.
