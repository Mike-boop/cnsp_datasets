# wang2026: AASD, spontaneous auditory attention switching, Mandarin (EEG)

EEG of 18 young Mandarin listeners who hear two AISHELL-1 talkers at once (one male, one female, one per ear) in
60-s trials and switch their attention between them **at will**, pressing a "left" or "right" key at each switch.
Per listener: 2 practice trials, 6 blocks of 10 attention-switching trials, and 1 passive block of 10 trials
(alternating key presses at the switching rate without the attention task: a motor control).

- **Source:** Zenodo 10.5281/zenodo.17413336 (version 17413336; registry entry `wang2026`). The adaptor uses
  `Original EEG.zip` and `Stimuli Audio.zip`; `Processed EEG.zip` (128 Hz) was used only to cross-check the raw
  data and trial order. **Licence: CC-BY-4.0** (Zenodo record; the article is CC BY-NC-ND 4.0).
- **Paper:** Wang X, Ding Y, Ban Y, Wang L, Chen F (2026). An open non-invasive EEG dataset for spontaneous
  auditory attention switch decoding. *Scientific Data* 13:883. doi:10.1038/s41597-026-07244-w
- **Code (authors):** https://github.com/XXuefeii/AASD-Processing (EEGLAB preprocessing of the 60 switching
  trials).

## Size
**18 participants; 1,115 trials with a stimulus (60 s each), 18.6 h; per participant 1.03 h (range
1.02-1.03 h).**
- `switching`: 1,080 trials, 18.0 h (1.00 h each);
- `practice`: 35 trials, 0.58 h (S1 has one);
- `passive`: 179 trials, 3.0 h of EEG **without a stimulus** (S5 has 9).

Standardised output: 11 GB (500 Hz).

## What is provided
- **EEG:** Neuroscan (Curry 7 CNT) at 500 Hz (native, not resampled), 62 scalp channels (`eeg`, 10-10 Quik-Cap
  names as shipped, incl. CB1/CB2), mastoids `M1`/`M2` (`misc`), `VEOG` (`eog`, marked bad: it carries no blink
  signal in any recording). HEO, EMG and the trigger channel are dropped (unused or digital). In V. **Original
  reference, unknown**: the paper names mastoids and nose tip, but M1/M2 are recorded channels; the data suggest
  the cap's vertex reference (inferred). Template positions (`standard_1005`; CB1/CB2 have none). No meas date.
- **Stimuli** (switching and practice trials), the shipped 16 kHz wavs:
  - `mixed_NNN`: the stereo wav as played (left channel = left talker only, right channel = right talker only);
  - `mixed_NNN_left`, `mixed_NNN_right`: its two channels, i.e. the left and the right talker alone (exact).

  None is flagged attended, because attention changes within the trial. No transcripts or word timings are
  shipped.
- **Attention labels as MNE annotations** on each trial (times from the trial start):
  - `key/left`, `key/right`: every key press (zero duration);
  - `attend/left`, `attend/right` (switching and practice): from each press to the next press or the trial end.
    The ~1 s before the first press is unlabelled. Passive trials have presses only.

  Read them with `raw.annotations`. To build an attended envelope, take the left talker inside `attend/left`
  and the right talker inside `attend/right`.
- Trial metadata (`raw.info["description"]`, JSON): participant, trial code, block (0 practice, 1-6, 7 passive),
  stimulus, ear condition and the talker on each side, presentation count (S8-S11 heard every stimulus twice),
  seconds labelled left/right/unlabelled, onset sample and its source, bad channels, reference.

## How it was aligned
- **Onset = the E-Prime trial code**, timed by its first sample on the recorded **Trigger channel**
  (acquisition hardware). The CNT event table is 1 sample (2 ms) earlier than that channel in 17 subjects and
  **48 ms earlier in S14**; the authors' processed S14 epochs agree with the Trigger channel.
- The code is sent by the presentation software at the start of each wav; its latency to the sound is not
  documented (`sw_trigger`, trigger type software). No drift correction or estimate (60-s trials, no end code,
  no audio copy).
- **Alignment grade: medium.** Software trial codes; the shipped timing is kept, and the 0.5-8 Hz validation
  confirms it: TRF peaks at ~90 and ~188 ms, nothing at negative lags, per-subject lag offsets within +-13 ms. The
  accou2023 DNN offset is -26 ms (95% CI -34..-17; EEG later), in the range expected for competing talkers. It is
  documented, not applied.
- The stimulus mapping (trial code - 10 = `mixed_NNN`, codes 71/72 = `mixed_100`/`mixed_200`) is the authors'
  StimList, and an EEG decoder confirms it.

## How to get it
Registry entry `wang2026` (Zenodo; no key). The adaptor expects the zips extracted in place
(`<download>/Original EEG/S<n>/S<n>.cnt`, `<download>/Original EEG/StimList.xlsx`,
`<download>/Stimuli Audio/mixed_*.wav`); `Processed EEG.zip` is not needed. No adaptor options.

## Validation
`validation.json` (18 subjects, average reference, envelope of the stereo mixture):
- **Highest tier: `low` (0.5-8 Hz).** Mean prediction r 0.023, above circular-shift (p 0.02) and mismatched-stimulus
  (p 0.048) nulls; 16 of 18 subjects significant (S15 and S17 not). This is low, as expected with two competing
  talkers and noisy recordings.
- `mlr` (30-60 Hz) and `brainstem` (30-250 Hz) fail: SNR 1.02 and 0.96. Not suitable for high-frequency or
  brainstem analyses.
- **Attended vs ignored talker** (0.5-8 Hz forward model with the key-press labels): attended r 0.019 vs ignored
  0.015, higher in 11 of 18 subjects, **not significant** (Wilcoxon p 0.32). The authors' own backward decoding
  reached 50.5-63.3% for 1-30 s windows. Attention decoding from these data is hard; the labels are behavioural
  (key presses) and may carry motor activity.

## Known issues
- **Passive block: the audio is unknown.** It is not in StimList.xlsx and could not be identified among the
  shipped wavs from the EEG. These trials are provided without a stimulus (EEG and key presses only).
- **Gel bridging** in most recordings: clusters of neighbouring electrodes are nearly identical (raw difference
  < 1 uV). They are not marked bad.
- Bad channels (40-200 Hz noise > 5x median): S2 CB2, S3 M2, S4 T8, S5 M2, S12 T7, plus VEOG everywhere. Frontal
  channels carry large blink artefacts (no usable EOG).
- Design differences not described in the paper: S1-S7 heard all 60 stimuli once; S8-S11 heard 30 stimuli twice;
  S12-S18 two complementary halves. S1 lacks the first practice trial; S5 has 9 passive trials.
- S1-S7 show no attended > ignored trend while S8-S18 do (8 of 11); not significant. The key mapping (179 = left,
  184 = right, from the Zenodo description) is used for everyone.
