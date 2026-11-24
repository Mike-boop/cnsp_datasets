# diliberto2023: nursery rhymes, infants at 4, 7 and 11 months and adults (EEG, preprocessed, 50 Hz)

> **Repetition-averaged, preprocessed data.** Each trial is the authors' **average over the 2-3 presentations of
> one rhyme**, not a single presentation. The data are the authors' processed release: 0.1-8 Hz, **50 Hz**,
> ASR-cleaned, noisy channels interpolated (which ones is not shipped), linked-mastoid reference. No raw EEG and no
> audio are public. Use it for low-frequency (< 8 Hz) envelope / phonetic-feature tracking only.

A longitudinal cohort of 47 infants recorded at 4, 7 and 11 months, plus 17 adults, watching 18 audio-visual
nursery-rhyme videos (a woman singing or chanting, infant-directed English), each played 3 times. EGI GES 300 with
a Geodesic Sensor Net, recorded at 1 kHz.

- **Source:** OSF project mdnwg, https://osf.io/mdnwg/ (CND files, `eegCND/`, 2023-09-10).
- **Licence:** none named ("copyright 2021" on OSF, no CC licence). Public download; raw EEG "available upon
  request" from the corresponding author.
- **Paper:** Di Liberto GM, Attaheri A, Cantisani G, Reilly RB, Ní Choisdealbha Á, Rocha S, Brusini P, Goswami U
  (2023). Emergence of the cortical encoding of phonetic features in the first year of life. *Nat Commun* 14:7789.
  doi:10.1038/s41467-023-43490-x
- **Code (authors):** `code/` in the OSF project (mTRF analyses, figures).

## Size
Averaged-trial time (each rhyme counted once; listeners heard 2-3 times as much):
- 4mo: 45 infants with data, 247.5 min; 7mo: 47, 277.3 min; 11mo: 47, 286.7 min; adults: 17, 105.4 min.
- **15.3 h** in 156 sessions, 2616 trials (empty trials skipped). 4.7-79 s per trial, 6.2 min for all 18 rhymes.

## Participants and sessions
- Infants: subject 1-47 = the authors' `dataSub<k>`, **the same child at every age**: session 1 = 4 months,
  2 = 7 months, 3 = 11 months. 4mo `dataSub8` and `dataSub13` ship no trials.
- Adults: subject 101-117 (`dataSub1`-`dataSub17`), session 1. Different people from the infants.
- Condition = age group (`4mo`, `7mo`, `11mo`, `adults`); trial = rhyme number (1-18). The sidecar keeps the
  original file (`age_group`, `original_subject`) and `repetition_averaged: true`.

## What is provided
- **EEG** (`eeg`, 50 Hz, V): 58 channels (EGI `E1`-`E60` without the mastoids), template positions. Shipped in µV
  (assumed, not verifiable; amplitudes are low, so **do not trust absolute amplitudes**). Linked-mastoid reference
  as shipped. **The adults' 128 channels were spline-interpolated by the authors to the infants' 64-channel
  layout** (virtual electrodes). `info['bads']` is empty: which channels the authors interpolated is unknown.
- **M1/M2** (`misc`): the left/right mastoids (E29/E47) in the same linked-mastoid reference, i.e. M1 = (E29 -
  E47)/2, M2 = -M1. The shipped mastoid columns were in an earlier reference (notes section 5).
- **Band copy:** only the 0.1-8 Hz copy, the one the authors fit their TRFs on. The release also has 0.1-1, 1-4 and
  4-8 Hz copies; they are separately filtered versions of the same data and can be approximated by filtering.
- **Stimuli** `rhyme01`-`rhyme18`, all at 50 Hz, the authors' features (no audio is shared):
  - `envelope`: sum of the 8 spectrogram bands (the paper's broadband envelope);
  - `spectrogram`: 8 bands, 250-8000 Hz (Greenwood-spaced), `band_edges_hz`;
  - `envelope_derivative`: as shipped, **not** half-wave rectified (the authors' code rectifies it when loading);
  - `phonetic_features`: 19 binary step features with `labels`, from hand-corrected phoneme alignments (the
    paper's 14 = these minus sonorant, syllabic, consonantal, approximant, obstruent). On by default;
    `--adaptor-opt phonetic_features=False` drops them.
  - The shipped visual-motion feature is not included.

## Alignment
- Trials were cut by the authors at the stimulus onset to the stimulus length (EEG sample 0 = feature sample 0),
  then averaged over repetitions. The paper mentions synchronisation triggers; their route (hardware or software,
  audio or video onset) is not documented. Shipped timing kept, no correction.
- Drift is not measurable (no raw recordings or trigger times); at 50 Hz it is below a sample for plausible clock
  errors.
- **Alignment grade: medium.** Trigger source unknown, authors' epochs kept; every age group passes the low tier
  with no evidence of an offset (adult TRF peak 180 ms), but the TRFs are too weak to pin the latency down.

## Validation
Low tier only (0.5-8 Hz envelope forward model, average reference); the higher tiers are impossible at 50 Hz.
Each age group validated separately (the infants' sessions would otherwise be pooled per child):

| group | subjects | mean r | p circular / mismatch | subjects sig. | TRF GFP peak |
|---|---|---|---|---|---|
| all | 64 | 0.010 | 0.020 / 0.048 | 21/64 | 60 ms |
| 4mo | 45 | 0.008 | 0.020 / 0.048 | 11/45 | 40 ms |
| 7mo | 47 | 0.007 | 0.020 / 0.048 | 8/47 | flat |
| 11mo | 47 | 0.008 | 0.020 / 0.048 | 5/47 | 220 ms |
| adults | 17 | 0.015 | 0.020 / 0.048 | 4/17 | 180 ms |

All groups pass at the smallest attainable p. Tracking is weak and the group TRFs stay within the null 95th
percentile, so latencies are indicative only.

## Caveats
- Repetition-averaged trials (see top); how many repetitions went into each average and the presentation order
  are not shipped.
- Heavily preprocessed (ASR, interpolation, 0.1-8 Hz, 50 Hz); no high-frequency analyses possible.
- Missing trials, mostly in pairs (rhymes 11+12 in many infant files); 4mo `dataSub8` and `dataSub13` are empty
  although the paper reports 47 infants at every age.
- No licence beyond "copyright 2021".

Details: `notes.md`.
