# Etard et al. 2019: EEG to audiobooks in quiet, babble noise and with a competing speaker (BIDS)

20 native English speakers listened to audiobooks while 63-channel EEG was recorded at 1 kHz (Brain Products
actiCHamp), together with the audio sent to the earphones (channel `Sound`, a StimTrack recording). This is a BIDS
version of the original record (https://zenodo.org/records/7086209) and replaces the HDF5 convenience release
(https://zenodo.org/records/7778289).

Etard O, Reichenbach T (2019). Neural speech tracking in the theta and in the delta frequency band differentially
encode clarity and comprehension of speech in noise. J Neurosci 39(29):5750-5759.

## Design
Two sessions, four parts (runs) per condition, one recording per run.
- `ses-english` (18 participants), English audiobooks:
  - `task-clean`: speech in quiet;
  - `task-lb`, `task-mb`, `task-hb`: speech in low, medium and high babble noise (lb = highest SNR);
  - `task-fM`: attend a male speaker with a competing female speaker;
  - `task-fW`: attend a female speaker with a competing male speaker.
- `ses-dutch` (15 participants), Dutch audiobooks, a language the participants did not understand, with short English
  sentences inserted in the speech pauses for the participants to detect:
  - `task-clean`: Dutch speech in quiet;
  - `task-lb`, `task-mb`, `task-hb`: Dutch speech in low, medium and high babble noise.

Task labels are the original condition codes (`hbDutch` becomes `ses-dutch` `task-hb`).

## Contents
- `sub-<nn>/ses-<session>/eeg/`: raw continuous recordings (BrainVision, µV, unfiltered apart from the amplifier's
  280 Hz anti-aliasing filter) with 63 EEG channels and `Sound` (type AUDIO). `*_events.tsv` lists, per run:
  - each played stream (`speech`, `babble`, `competing`, `english_track`) with its file in `stimuli/`;
  - the English sentences (`english_sentence`);
  - the stimulus PC's triggers (`trigger`).
- `stimuli/<session>/<task>/run-<n>_<stream>.wav`: every stream as played, 44.1 kHz float32. These are the same for
  all participants and are taken from the original `.mat` files. The Dutch speech and the English
  sentences were normalised to the same RMS and summed when played (`.mat` comment: "Dutch and English already
  normalised to 1 RMS; just add them"). The wavs do not carry the presentation levels; see `snr_db`.
- `sourcedata/`: per-participant experiment parameter files (`beh/*EEGExpParam.mat`) and the per-run stimtrack
  measurements (`stimtrack.csv`).
- `code/`: the script that built this dataset (`make_bids.py`).

Participant labels follow the HDF5 release (sub-00 = P00, ...); `participants.tsv` maps them to the original IDs
(YH00 .. YH20 without YH05).

## Timing and levels (measured from the stimtrack, every run)
- **Speech onset:** cross-correlation of the `Sound` channel with the attended speech (1 ms), refined by a Theil-Sen
  fit through the lags of 10 s windows (sub-ms). The software triggers coincide with it (English babble runs: the
  trigger marks the babble onset, 1 s before the speech).
- **Babble timing:**
  - English: from 1 s before to 1 s after the speech.
  - Dutch: from 2 s after the speech onset (`nRamp`) to its end.
  - Competing speaker: starts with the attended speech.
  - Each noise or competing stream's onset is measured independently and listed in `*_events.tsv`.
- **Presented SNR** (`snr_db`): least-squares gains of the `Sound` channel on the two streams. Medians over all
  runs (SD across runs 0.3-1.1 dB):

  | | lb | mb | hb | fM | fW |
  |---|---|---|---|---|---|
  | English | +0.8 dB | −1.0 dB | −1.8 dB | −1.0 dB | −0.2 dB |
  | Dutch | +3.2 dB | +0.8 dB | −0.6 dB | | |

  So lb/mb/hb are low/medium/high babble *levels*, i.e. high/medium/low SNR.
- **Clock drift** of the EEG relative to the audio: 0.8 ppm median (IQR 0.4-1.6), listed per run (`drift_ppm`)
  and not corrected.
- All 672 runs: the noise streams sit at the expected offsets to the ms, and the triggers coincide with the measured
  onsets.
- YH09's cleanDutch run 4 has a second header (`YH09_clean_4_dutch.vhdr`) for the same data; it is included once.

## Changes from the HDF5 release (7778289)
- Raw continuous recordings with the stimtrack instead of segments without it; measured onsets, SNR and drift.
- **English sentences of lbDutch, mbDutch and hbDutch:** the release copied them from cleanDutch, so they did not
  match those stories. Here every condition has its own sentences, with onsets.
- **Dutch babble:** the release placed it 1 s after the speech onset; it starts 2 s after.
- **SNR labels:** the release described lb/mb/hb ambiguously; the measured SNRs above settle the order.
- Separate wavs for each played stream; trigger markers and experiment parameter files added.
- Not included, as they remain in the earlier versions of this record: the original stimulus `.mat` files (the same
  streams as `stimuli/`), the authors' CND-format data and conversion code, and the recordings the authors set aside
  and repeated (`eeg/<subject>/info/`: YH06 hb run 3, interrupted by a fire alarm; YH03 fM run 1, where the
  participant attended the female speaker; header-only copies for YH01 and YH06 hb run 4).
