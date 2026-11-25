# lin2024: auditory spatial attention (SCUT), not incorporable

Explored 2026-11-24 from the vault-side copy of Zenodo 11541114 (rsynced from woody; md5 of all 28 files matches
`record.json`). **Dropped (user, 2026-11-24): the release ships no stimulus audio and no envelopes.**

## What the release contains
- 400 `.fif` files: S001..S020, each `E1/Trial1..20`, plus the authors' code (`main.py`, `db/`, `eutils/`, `models/`,
  `preproc/`, `results/`, `visualization.ipynb`; read, not run). A listing of every zip finds no audio of any kind.
- EEG: BrainAmp, 500 Hz, volts (plausible µV amplitudes), 64 channels all typed `eeg`: 63 scalp 10-20 channels without
  FCz (probably the online reference) and an ECG at index 31 (SD ~2.9 mV).
- Not raw: `eutils/crop.py` high-passes the BrainVision recording at 1 Hz and cuts each trial from the `STIM/trail<k>S`
  marker to `trail<k>E` (`info['highpass']` = 1.0).
- Trials: Trail k is presentation position k; all 20 subjects heard the same 20 trials in the same order (paper
  Table 1). Per-trial S→E durations agree across subjects within ±30 ms (SD 10-22 ms).
- `crop.py` also writes trials 21-40 as session E2, which is not released.
- Participants: 20 released (24 recorded, 4 excluded; a comment in `crop.py` says 25 and 5). 24.26 min per subject,
  8.09 h in total.

## Stimuli
- 40 stories from the HSK (Chinese Proficiency Test) website (paper ref. 13), HRTF-filtered and played over headphones
  at 10 angles (±90/60/45/30/5°), not only ±60°.
- Not recoverable from li2022 (same group, same code base and `trail<k>S/E` marker scheme): none of the 20 trial
  durations matches any of li2022's 32 wavs (nearest differ by 0.1-1.9 s); rate 500 vs 1000 Hz; recorded 2022-11 to
  2023-03.

## If picked up again
Ask the corresponding author (S. Cai) for the 40 story wavs (and the HRTF versions), session E2 and the unfiltered
BrainVision recordings. Alignment would then follow li2022 (software `trail<k>S/E` markers; check for a constant
playback latency, cf. li2022's 0.216 s).

Scratch scripts (deleted with tmp): `tmp/review/scripts/lin2024/inspect_fif.py`, `trial_table.py`.

## Restructure 2026-11-25 (not yet re-validated on data)
- No adaptor (dropped). dataset.json: title and a `notes` entry saying it is not incorporated.
