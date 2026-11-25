# zhang2023 splice maps and DNN pair offsets

The shipped trials are spliced: the authors cut artefact segments out of the EEG and both wavs together. Their
timing fails validation, and only a DNN scan against the unspliced sources recovers offsets, for a minority of
presentation pairs. Details and results: `../notes.md` section 6b. Run from the repository with the extracted
download (the folder holding `NJUNCA_preprocessed_arte_removed/`) as input:

```
M=cnsp_datasets.datasets.zhang2023.alignment
python -m $M.make_maps    <download>              # -> pieces.csv, source_cover.csv (~5 min)
ZHANG2023_DNN=<classifier.pt> python -m $M.dnn_scan <download> <out>/scan  # per-trial lag scans (~2 h, GPU)
python -m $M.pair_offsets <out>/scan [fig.png]    # -> pair_offsets.csv (confident = adaptor pairs="confident")
```

- **`make_maps`** (`splices.py`) hashes the 125-sample blocks of every shipped wav and chains them into the 33
  unspliced 115 s sources.
  - `pieces.csv` keeps a trial's piece → source mapping only where its two streams' rebuilds agree.
  - `source_cover.csv` records which shipped wav supplies each source stretch.
  - With offset 0, the rebuilt trial stimulus equals the shipped wav on every mapped sample.
- **`dnn_scan`** uses the accou2023 classifier `fs128_1020-32_broadband`.
  - EEG goes through the classifier's own preprocessing: the Emotiv montage is interpolated onto BioSemi-32 and
    re-referenced to the average.
  - 5 s windows with a 1 s hop, inside pieces; lags ±12 s.
  - Stimuli scored: the attended, the ignored and two mismatched sources (null; crc32 seed per trial).
- **`pair_offsets`** pools the two presentations of each stimulus pair, which are separate recordings.
  - Confident: p < 0.01 against the null pairs, and the two presentations' peaks within 0.25 s.
  - Sign: a negative lag means the EEG is later than the shipped pairing.
