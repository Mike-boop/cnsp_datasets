# Weissbart et al. 2019: EEG to continuous English audiobooks (BIDS)

13 native English speakers listened to 15 chapters of audiobooks (about 2.5 min each; stories AUNP01-08, BROP01-03,
FLOP01-04) while 63-channel EEG was recorded at 1 kHz (Brain Products actiCHamp), together with the audio sent to the
earphones (channel `Sound`, a StimTrack recording). This is a BIDS version of the original record
(https://zenodo.org/records/7086168) and replaces the HDF5 convenience release (https://zenodo.org/records/7775260).

Weissbart H, Kandylaki KD, Reichenbach T (2020). Cortical tracking of surprisal during continuous speech
comprehension. J Cogn Neurosci 32(1):155-166.

## Contents
- `sub-<nn>/eeg/`: one continuous raw recording per participant (BrainVision, µV, unfiltered apart from the
  amplifier's 280 Hz anti-aliasing filter), 63 EEG channels and the `Sound` channel (type AUDIO).
  `*_channels.tsv` marks the channels the authors rejected (`bad_channels.txt`). `*_events.tsv` lists the stories in
  presentation order with onsets measured from the `Sound` channel.
- `stimuli/<story>/`: the audio as played (`<story>.wav`, 16 kHz), word and phone alignments (`.TextGrid`), the
  text (`.txt`, `.lab`, `clean_*_35K.txt`), and word-level features (`word_frequencies/`, `surprisal/`,
  `transcripts/`).
- `derivatives/CND/`: the authors' preprocessed data in the CNSP Continuous-event Neural Data format (`S<k>.mat`,
  `Stim.mat`; made by `code/toCND.m`).
- `derivatives/authors_preprocessing/sub-<nn>/`: the authors' bad channels, ICA solution (`-ica.fif`), rejected
  components and event files.
- `sourcedata/`: per-participant behavioural files (`beh/*.mat`, `psychoData`: comprehension questions) and the
  authors' list of story onsets (`onsets.mat`).
- `code/`: the authors' conversion code and the script that built this dataset (`make_bids.py`).

Participant labels follow the HDF5 release (sub-00 = P00, ...); `participants.tsv` maps them to the original folder
names (P01 .. P14 without P11) and the CND files.

## Timing (checked against the stimtrack)
- Story onsets in `*_events.tsv` come from cross-correlating the `Sound` channel with each story (1 ms), refined by a
  Theil-Sen fit through the lags of 10 s windows (`onset`, sub-ms). They agree with the authors' `onsets.mat`
  (`onset_listed`) to within 1 ms for all 194 played stories.
- Clock drift of the EEG relative to the audio is small: 1.2 ppm median (0.6-3.0 ppm; ~0.2 ms over a story). It is
  listed per story (`drift_ppm`) and not corrected.
- **Original participant P04 (sub-03) did not hear BROP01:** the story is nowhere in its stimtrack, and the onset
  listed for it in `onsets.mat` (297.7 s) falls 10.5 s before BROP02. It is left out of that participant's events. The
  HDF5 release contains a BROP01 segment for P03 that is EEG recorded during BROP02; do not use it.
- No recording pauses occur during the stories.

## Changes from the HDF5 release (7775260)
- Raw continuous recordings with the stimtrack instead of per-story EEG segments without it.
- Measured onsets and drift per story; the invalid P03 BROP01 trial is removed.
- Alignments (TextGrids), transcripts and word-level features, CND data and the authors' preprocessing files added.
