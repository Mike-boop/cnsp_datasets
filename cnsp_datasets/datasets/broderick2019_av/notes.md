# broderick2019_av notes

Speech-in-noise folder of the Broderick et al. (2019) Dryad package: audio-only (a, runs 1-15), visual-only (v,
16-30) and audiovisual (av, 31-45) runs; word timings only (no audio or envelopes). The mat files' fs field reads
512, but the data are 128 Hz (7680 samples per 60 s run, Readme). Readers shared with broderick2019_natural
(`broderick2019_natural/cnd.py`, see its notes).

## Restructure 2026-11-25 (not yet re-validated on data)
- BaseAdaptor; sorted glob (unchanged order).
- EEG through `cnd.read_eeg` (key `EEG`; orientation decided by the channel count).
- Word TextGrids through `iohelpers.textgrid` (long format, xmin 0, gaps filled, quotes escaped; overlapping words
  now raise).
