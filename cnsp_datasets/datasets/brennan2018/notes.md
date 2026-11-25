# brennan2018 notes

Brennan & Hale (2019) "Alice" EEG from the BIDS mirror on NEMAR (nm000180; 45 of the 49 participants). The review
notes of the first pass were not kept in the repository; the alignment is described in the adaptor's docstring:
one trial per subject and audio segment (1-12), onset from the stimtrack (Aux5/AUD) by cross-correlation with the
segment's rectified audio, else from the first word in events.tsv (only for subjects whose software onsets agree
with the stimtrack within 0.1 s wherever both exist). STATUS.md: alignment `good`, tier brainstem.

## Restructure 2026-11-25 (not yet re-validated on data)
- A segment whose onset falls before the start of the recording is skipped and logged; before, the onset was
  clipped to 0, which shifted that trial's EEG against its stimulus. Only software onsets can be negative.
- A recording that ends before its segment is logged (the trial is still shorter, as before).
- `raw.info["description"]` is `standardise.provenance` JSON (`stimtrack_xcorr` / `sw_trigger`, xcorr quality,
  onset) instead of free text.
- TextGrid written by `iohelpers.textgrid` (was `broderick2019_natural.utils.multi_tier_dict_to_textgrid`): long
  text format, xmin 0, xmax = the segment's audio duration (was the last word's offset), gaps filled, quotes
  escaped. Overlapping words would now raise; not yet checked on the word table.
- Audio through `iohelpers.read_wav` (float32 / 32768: unchanged values).
