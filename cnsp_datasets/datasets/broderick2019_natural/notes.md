# broderick2019_natural notes

## Shared readers (broderick2019_natural/cnd.py)
The three Broderick 2019 adaptors (natural, av, cocktail) read the same Dryad package and use `cnd.py`:
`read_eeg` (128 BioSemi channels A1..D32 + M1/M2 as misc when the file has `mastoids`, µV -> V, 128 Hz) and
`words_textgrid` (word tier from `Run<k>.mat`). Orientation: the files store (n_times, n_channels). The old adaptors
used two heuristics (natural/av concatenated the mastoids before deciding whether to transpose, which fails for a
channels-first file; cocktail transposed first). Both gave the same result on the shipped (n_times, 128) files;
`cnd.channels_first` now decides by the channel count (128 or 2) and raises on any other shape. `utils.py` is the
old TextGrid writer, kept only for other adaptors until they migrate.

## Restructure 2026-11-25 (not yet re-validated on data)
- BaseAdaptor; `mode` checked with `choice`.
- EEG through `cnd.read_eeg` (same values; orientation by channel count, see above).
- Word TextGrids through `iohelpers.textgrid`: long format (the header no longer says "short"), xmin 0, gaps
  between words filled with empty intervals, quotes escaped; overlapping words now raise. Reverse mode: words
  mirrored about the envelope duration, as before.
