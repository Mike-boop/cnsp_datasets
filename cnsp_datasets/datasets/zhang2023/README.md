# zhang2023: NJU auditory attention detection dataset (Emotiv EPOC Flex)

21 normal-hearing participants (`S01`-`S21`) listened to two competing Mandarin news talkers (professional anchors,
male and female) played from a loudspeaker array and attended one of them. Each stimulus pair was played twice in a
row, attending each talker once. The talkers stood at 14 azimuths (±15…±135°), sometimes both on one side, and moved
in trials 25-32 of S01-S15.

> **Warning: the default output fails validation in 18 of 21 subjects.** As shipped, the EEG of S01-S17 shows no
> envelope tracking at any lag within ±10 s. S18, S19 and S21 track only weakly and late (peaks at 250-450 ms), and
> S20 is not significant. A DNN scan
> finds trial pairs whose timing is off by about 1-3 s (once 9 s), which explains the failure. Those offsets can be
> estimated for only 16 of 313 presentation pairs. Use `pairs="confident"` for the subset with offsets applied.
> **Alignment grade: poor** (see Alignment).

- **Source:** Zenodo 7253438 (doi:10.5281/zenodo.7253438), registry entry `zhang2023`: one 11.0 GB zip of
  per-participant MATLAB v7.3 files (`NJUNCA_preprocessed_arte_removed/S01.mat` … `S21.mat`) and `script.zip`
  (MATLAB slicers, not used).
- **Licence:** CC BY 4.0.
- **Paper:** Zhang Y, Ruan H, Yuan Z, Du H, Gao X, Lu J (2023). A learnable spatial mapping for decoding the
  directional focus of auditory attention using EEG. ICASSP 2023, doi:10.1109/ICASSP49357.2023.10096819.

## Size
- **Default:** 21 participants, 644 trials of 10-115 s. 13.8 h in total, mean 0.66 h per participant (0.35-0.87 h).
  This is the authors' cleaned EEG; the segments they cut out are not included.
- **`pairs="confident"`:** 32 trials (16 pairs) from S05, S06, S09, S10, S16 and S20, 0.84 h. Per subject:
  S06 0.33 h, S16 0.25, S10 0.11, S05 0.05, S09 0.05, S20 0.04.

## What is provided
- **EEG:** the authors' preprocessed data, not raw. EEGLAB processing: 1-32 Hz band-pass, resampled to 128 Hz,
  channels with outlying spectra removed and later interpolated, ICA artefact removal, and manual removal of
  "abnormal segments".
  - **32 Emotiv channels** under their shipped names: Cz Fz Fp1 F7 F3 FC1 C3 FC5 FT9 T7 CP5 CP1 P3 P7 PO9 O1 Pz Oz
    O2 PO10 P8 P4 CP2 CP6 T8 FT10 FC6 C4 FC2 F4 F8 Fp2. Template standard_1020 positions; no EOG, mastoids or
    peripherals.
  - **Units:** µV in the files, stored in V.
  - **Reference:** as shipped. Emotiv CMS/DRL; their positions are not documented, and the data are not
    average-referenced.
  - **Rate:** 128 Hz as shipped; the native rate is unknown. Only the 0.5-8 Hz analyses are possible.
  - **Bad channels:** none marked. The authors interpolated theirs, and no channel is flat or an outlier.
- **Trials are spliced.** The authors cut artefact segments out of each trial's EEG and both wavs together, and
  concatenated the rest. Each record therefore jumps at the splice points: EEG and audio jump at the same sample.
  - The sidecar `splice_pieces` lists the contiguous pieces as [EEG start, samples, position in the 115 s source].
    There are 3205 pieces with a median of 7.8 s.
  - About 3% of the EEG (0.5-7% per subject) has no reliable source position and is absent from the list.
- **Stimuli:** two `audio` stimuli per trial, one per talker, at 16 kHz mono. `is_attended` marks the attended one.
  - Default: the shipped per-trial wavs, named `S<ss>_t<tt>_<l|r>_<eeg_NN_mono>`. They are spliced exactly like
    the EEG, so each stimulus is unique to its trial.
  - `pairs="confident"`: the same names with `_dnn` appended. Each stimulus is rebuilt from the unspliced source at
    the trial's splice map plus the pair's DNN offset; see Alignment. A shifted wav could not be used instead: a
    shift of 1-3 s would cross the splices and pull in audio that was cut out, rather than the audio that was
    playing.
- **Conditions:** `static` or `moving` (talker movement). The streams are `l`/`r` (the table's `l_audio` /
  `r_audio`) and are not sides. The sidecar holds `azimuth_deg`:
  - static trials: per stream;
  - moving trials: the shipped 5-point trajectory, whose meaning is not documented.
- **Sidecar** (`raw.info["description"]`) also holds:
  - `subject_name` and `protocol`: A = S01-S15, B = S16-S21, static ±30-90° only;
  - `l_audio`, `r_audio`, `attended_stream`;
  - `uncleaned`: S06 trials 1-10 are full-length 115 s trials that were never artefact-cleaned (SD 25-72 µV);
  - `mapped_fraction` and the DNN fields.
- **Gaps:**
  - S18 trials 9 and 22 are empty upstream and skipped.
  - S17 has 28 trials, because one pair was not repeated.
  - Each subject heard 30-32 of the 33 source recordings.

## Alignment
- **Shipped timing: unknown and not usable.**
  - The authors cut the trials before release. There are no triggers, raw recordings or audio channel, and the
    onset method is not documented.
  - Emotiv systems take software markers, so the sidecar `trigger_type` is "unknown".
  - Validation fails in 17/21 subjects (see Validation).
- **DNN offsets** (`pairs="confident"`): brain-based, so the grade is `poor`.
  - **Method:** the accou2023 match-mismatch classifier (`fs128_1020-32_broadband`) scanned each trial over ±12 s,
    in 5 s windows inside splice pieces, against the rebuilt unspliced sources.
  - **Per pair:** the two presentations of a stimulus pair are separate recordings, and they share their offset to
    within 10-30 ms. So the offset is estimated per pair.
  - **Confident pair:** the pooled peak beats null pairs (scored with mismatched sources) at p < 0.01, and the two
    presentations' own peaks agree within 0.25 s.
  - **Yield:** 16 of 313 pairs pass, against 1 of 626 null pairs. Offsets range from -1.53 to +1.68 s, with one at
    +9.07 s; negative means the EEG is later than the shipped pairing.
  - **Check:** shifting each presentation by the offset estimated from the other presentation raises the attended
    forward-TRF r from -0.010 to 0.032. This check covers the first run's 14 pairs (28 trials).
  - **Provenance:** `alignment_method` "dnn", plus `dnn_offset_s` and `dnn_pair`.
  - **Circularity:** the offsets come from the same EEG; cross-fitting between presentations reduces this but does
    not remove it.
  - Scripts: `alignment/`. Values: `pair_offsets.csv` (all 313 pairs).
- **Grade: poor.** The shipped timing fails validation, and the only usable timing (`pairs="confident"`) is
  brain-derived.
- No drift can be measured: the trials are cut, and the rate is 128 Hz.

## Validation
Low tier (0.5-8 Hz), average reference. The data are 128 Hz, so the higher tiers do not apply. Details: `notes.md`
section 11.
- **Default** (`validation.json`): fails per subject.
  - Only S18, S19 and S21 are significant (r 0.020-0.035, p_circ 0.02).
  - S01-S17 have r between -0.007 and +0.007, and their TRF peaks are scattered from -78 to +500 ms.
  - The group TRF never exceeds its null band.
  - The validator's group flag is a nominal pass (mean r 0.004, p_circ 0.02), carried by S18-S21.
- **`pairs="confident"`** (`validation_confident.json`): passes.
  - Mean r 0.028; TRF peak at 172 ms; offset jitter MAD 36 ms (default: 346 ms).
  - S06 (r 0.036) and S16 (0.046) are individually significant. S05, S09, S10 and S20 are positive but have only
    2-4 trials each.
  - The pass is circular: the offsets were estimated from the same EEG.

## Usage
```
python -m cnsp_datasets.standardise.format_dataset zhang2023 <download> <out>                          # all, as shipped
python -m cnsp_datasets.standardise.format_dataset zhang2023 <download> <out> --adaptor-opt pairs=confident
```
`<download>` is the folder that holds the extracted `NJUNCA_preprocessed_arte_removed/`. `pieces.csv`,
`source_cover.csv` and `pair_offsets.csv` are derived from the download by the scripts in `alignment/`.
