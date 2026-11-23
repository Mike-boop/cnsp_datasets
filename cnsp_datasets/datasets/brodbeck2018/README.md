# brodbeck2018: two-talker cocktail party, attend one talker (MEG)

MEG of 26 community participants (R2262-R2375; aged 22-61, 18 M / 8 F) listening to 1-min segments of a LibriVox
audiobook, Dickens' *A Child's History of England*, read by a male and a female talker.
- **Two-talker trials:** each two-talker mixture was heard 4 times attending one talker, then 4 times attending the
  other. Only the to-be-attended talker is heard in the first second.
- **Single-talker trials:** each segment heard alone once.
- Each participant has 16 two-talker and 8 single-talker trials, in two counterbalancing groups.

- **Source:** DRUM (University of Maryland), item `6ce1b090-3446-46d8-9582-f689afcd23de`, doi:10.13016/M2ZC7RZ0F
  (registry entry `brodbeck2018`), 2.29 GB. A backup is on the NHR vault.
- **Licence: none stated** on the DRUM item (checked 2026-11-23). This is an **open question**: whether the data,
  or anything derived from them, may be redistributed is unknown. Ask the authors before sharing.
- **Paper:** Brodbeck C, Hong LE, Simon JZ (2018). Rapid transformation from auditory to linguistic representations
  of continuous speech. *Curr Biol* 28:3976-3983. doi:10.1016/j.cub.2018.10.042
- **Related deposit:** the same recordings were re-analysed in Brodbeck et al. (2020, *PLoS Biol*). Its DRUM
  deposit holds only derived data (ICA, gammatone, TRFs).
- **Code:** none shared.
- **Overlap:** there is no overlap with brodbeck2022 or the other KIT datasets of the campaign.

## Size
**26 participants x 0.40 h = 10.4 h in total** (24 min each, the same for everyone). Durations are counted from the
60-s stimuli (`notes.md` section 8; `validation.json` gives the same total). `data_size.py` was not run because the
standardised data had been deleted.
- `two_speakers`: 16 min per participant, 6.93 h in total.
- `single_speaker`: 8 min per participant, 3.47 h in total.

The standardised output is 2.5 GB.

## What is provided
- **MEG: the authors' preprocessed epochs only** (no raw data in either deposit).
  - **Preprocessing:** KIT 157-channel axial gradiometers (`mag`, T) + 3 reference magnetometers (`ref_meg`),
    recorded at 1 kHz. The authors applied tSSS (mne-python 0.14) and a zero-phase FIR 1-40 Hz, and decimated to
    **100 Hz, which is stored as shipped**.
  - Epochs run 0-60 s from the onset trigger. The stored data equal the shipped epochs exactly.
- **Peripherals:** the MISC trigger lines and STI are dropped. There is no audio copy, EOG or ECG.
- **Bad channels:** MEG 056 in all subjects and MEG 111 in R2356, as shipped.
- **Digitisation:** head shapes, fiducials and `dev_head_t` per subject are kept.
- **Stimuli:** raw audio of everything played (22.05 kHz).
  - **Single-talker trials:** the talker.
  - **Two-talker trials:** the attended talker (`is_attended`), the mixture as played (`{fg}_mix`), and the ignored
    talker as played (`{bg}_from1s`, the shipped wav with its first second zeroed).
  - **Not stored:** the authors' 100 Hz predictor `.mat` files (spectrogram, lexical and phonetic impulses) are
    model-derived and not carried. There are no transcripts or TextGrids.
- **Conditions:** `two_speakers`, `single_speaker`. The attended talker, trigger code and raw onset sample are in
  the sidecar. Trials are in presentation order. Subject = full R-number.

## Alignment
- **Onset:** epoch t = 0 is the onset-trigger sample, kept as shipped. In all 624 epochs the onset line deviates at
  sample 0 and the offset line at 60.00 s.
- **Trigger type: software (inferred).** The paper lists Presentation. Its latency and the insert-earphone tube
  delay are not documented.
- **Drift:** the onset-to-offset interval is 59.995-60.000 s in every trial, so |drift| is below ~80 ppm (< 5 ms at
  the trial end, half a 100 Hz sample). It is not corrected (`drift_ppm` null).
- **Jitter:** below ~5 ms between the onset and offset triggers. It cannot be estimated more finely.
- **Alignment grade: medium.** The authors' 100 Hz epochs start at the (software) onset trigger, and there is no
  audio copy. The decoder lag is 0 ms in 25/26 subjects. The drift (< ~80 ppm) is not corrected. Low tier.

## Download and adaptor options
- `download_dataset("brodbeck2018", <dir>)`. DRUM is slow and times out, so use 1 worker and `read_timeout=120`.
  No credentials are needed.
- Extract the zips (the downloader does this by default). The adaptor searches its root recursively for the
  `R####/` folders and `stimuli/`.
- `Brodbeck2018Adaptor(download_dir)`. It has no options.

## Validation
**Low tier, all 26 subjects** (624 trials), gradiometers without bads, attended talker. This is the highest tier
possible with 1-40 Hz data at 100 Hz.
- **Pooled:** mean r 0.037, 26/26 subjects significant. TRF peaks at ~50, 109 and ~200 ms, at null level at negative
  lags.
- **Per condition:** two talkers r 0.032 and single talker r 0.043, 26/26 each.
- **Backward decoder:** attended 0.183 vs ignored 0.076, attended > ignored in **26/26** subjects. The lag sweep
  peaks at **0 ms in 25/26 subjects** (+10 ms in R2304), and 93% of per-trial peaks lie within ±30 ms.
- **Not run:** DNN offset check (EEG-only) and coherence.

**Suitable for** low-frequency tracking and attention decoding (attended vs ignored).
**Not suitable for** middle-latency or brainstem analyses, or for re-preprocessing (no raw data, 100 Hz).

## Caveats
- **Licence not stated** (see above).
- The authors excluded 2 of the 28 recorded participants, who are not shared.
- `subjects.txt` order is not recording order. The adaptor orders trials by the raw onset sample.

Details: `notes.md`.
