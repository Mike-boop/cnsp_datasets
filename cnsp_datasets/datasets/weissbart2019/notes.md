# weissbart2019 notes

## Source: BIDS version (from 2026-11)
The adaptor reads the BIDS version built by `make_bids.py` from the original record (Zenodo 7086168), intended to
replace the HDF5 convenience release (Zenodo 7775260) as a new Zenodo version:

    python -m cnsp_datasets.datasets.weissbart2019.make_bids <WeissbartSurprisal dir> <stimtrack.csv> <bids dir>

`stimtrack.csv` comes from `tmp/review/scripts/weissbart_stimtrack.py` (onsets and drift from the `Sound` channel).
The BIDS dataset's README (`bids_README.md`) describes the contents: raw continuous recordings with the stimtrack,
measured story onsets, stimuli with TextGrids, transcripts and word-level features, CND data and the authors'
preprocessing files.

## Timing
Onsets from the stimtrack agree with the authors' `onsets.mat` to 1 ms; drift 1.2 ppm (not corrected). Original
participant P04 (sub-03) did not hear BROP01 (left out; the HDF5 release's segment is EEG recorded during BROP02).

## Validation (BIDS version, 13 subjects, 194 trials)
Brainstem tier: 0.5-8 Hz mean r 0.034 (TRF peak 188 ms); 30-60 Hz SNR 1.52; 30-250 Hz SNR 2.46 (the HDF5 release:
0.037, 1.36, 1.53).

## Trials and stimuli
One trial per story (condition `natural`); stimuli: the audio and its word/phone TextGrid (`textgrid`).

## Data size
13 participants, 0.66 h each (15 stories; sub-03 14), 8.6 h in total. Estimated from the stimuli (tmp/review/data_size.md).
