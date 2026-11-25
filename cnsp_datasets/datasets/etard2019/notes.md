# etard2019 notes

## Source: BIDS version (from 2026-11)
The adaptor reads the BIDS version built by `make_bids.py` from the original record (Zenodo 7086209), intended to
replace the HDF5 release as a new Zenodo version:

    python -m cnsp_datasets.datasets.etard2019.make_bids <EtardBrainstemAndComprehension dir> <stimtrack.csv> <bids dir>

`stimtrack.csv` comes from `tmp/review/scripts/etard_stimtrack.py`. The BIDS README (`bids_README.md`) describes it.
Conditions: lb = highest SNR (`sin_highSNR`), hb = lowest (`sin_lowSNR`); same for Dutch (`foreign_*`). The HDF5
release had these swapped and the Dutch babble 1 s early.

## Timing and levels (stimtrack, 672 runs)
Onsets agree with the triggers; babble offsets exact (English -1 s, Dutch +2 s, competing 0); drift 0.8 ppm median
(not corrected). Median SNR: English lb +0.8, mb -1.0, hb -1.8, fM -1.0, fW -0.2 dB; Dutch lb +3.2, mb +0.8,
hb -0.5 dB.

## Validation (BIDS version, 20 subjects)
Brainstem tier. No re-reference: 0.5-8 Hz mean r 0.0245, 30-60 Hz SNR 1.83, 30-250 Hz SNR 1.74 (HDF5 release 0.0243,
1.84, 1.79). Average reference: 0.0254, 1.53, 1.34.

## Latency and coherence by condition
DNN offsets vs accou2023 (negative = later response): clean +8 ms; English high/medium/low SNR -10/-14/-18 ms;
competing fM -8, fW +1; Dutch clean +2, noise -11 to -13 ms. 1-4 Hz coherence falls with SNR in both languages
(details in tmp/review/etard2019/notes.md).

## Annotations (open)
I think we no longer have textgrids, but transcripts are definitely available online. I didn't track these down yet but would be nice to add to the zenodo repo.

## Data size
20 participants, 1.57 h each on average (0.72-1.87; 18 took the English session, 15 the Dutch one), 31.4 h in total. Per condition ~0.16-0.26 h per participant (4 runs). Estimated from the stimuli (tmp/review/data_size.md).

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**good**: Stimtrack (Sound channel, 672 runs) in the BIDS rebuild; triggers coincide with it to 1 ms; drift 0.8 ppm, not corrected; noise DNN offsets are response latency; brainstem tier.

## Restructure 2026-11-25 (not yet re-validated on data)
- BaseAdaptor; sorted glob.
- **Stimulus names are unique per content.** Each stimulus is zero-padded to start at the trial start, and the
  padding is the stream's measured offset from the earliest stream of the run (e.g. the speech 1 s after the
  babble in English noise runs). The sinks save each stimulus name once, so two subjects with different offsets
  under one name would silently share the first subject's padding. Names are now
  `<condition>_part_<run>_<role>` when every stream starts at the trial start, else with `_at<ms>[+<ms>]` (the
  offsets of the summed streams, in 1 kHz samples), e.g. `sin_highSNR_part_1_story_at1000ms`.
- Audio through `iohelpers.read_wav` (the float32 wavs of the BIDS version are unchanged); the summed stimulus is
  float32 (was float64); mono and one rate per sum are checked.
