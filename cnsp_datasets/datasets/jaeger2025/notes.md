# jaeger2025: two competing talkers, phoneme/word TRFs (Zenodo 15518573) — NOT INCORPORABLE

Explorer notes (2026-11-24). Scratch: `/data_storage/gu08wuvu/datasets/tmp/review/jaeger2025/` (temporary;
`agent_log.md`, md5 lists). **Outcome: the release ships no EEG and no stimuli, only model outputs (TRF weights and
prediction correlations). There is nothing to standardise; no adaptor was written.**

## 1. Source
- Zenodo record 15518573 (concept 10.5281/zenodo.15518572), "Attention modulation to linguistic speech units - Data
  and Code", 2025-05-26, CC BY 4.0. Creators: M. Jaeger, M. G. Bleichner.
- Paper: Jaeger M, Zion Golumbic E, Bleichner MG (2025). Attention modulation to linguistic speech units.
  Neurobiology of Language 6, nol.a.14, doi:10.1162/nol.a.14 (`data_campaign/papers/jaeger2025.pdf`). Its data
  statement says "Preprocessed data and analysis scripts", and the record description says "final processed EEG
  data"; in fact no EEG time series is included (section 2).
- The recordings are those of Jaeger et al. (2020, Front. Neurosci., online attention decoding): 21 participants
  (20 analysed; one lost to technical problems), 6 blocks x 10 min, two male talkers reading German fairy tales from
  loudspeakers at +-45 deg, attend one side throughout. The cEEGrid data of the same sessions are in Holtze et al.
  (2022, Front. Neurosci. 16:869426); their availability was not checked (PMC served a bot check; not worked around).

## 2. Layout (all 23 files, md5 identical on woody and here and against the record's MD5SUMS; `unzip -t` clean)
- `Data.zip` (15.3 GB, 2044 entries): only `.mat` results, `Data/<model>_final/`:
  - `C_{attend,ignore}_TRF_<model>.mat`: float32 (96 ch, 251 lags = 0-500 ms at 500 Hz, 6 folds, 20 subjects)
    (single-regressor models; the combined models' files are 2-3x larger, layout not inspected);
  - `C_{attend,ignore}_r_valid_<model>.mat`: float32 (96, 6, 20) prediction r;
  - models: normenv, phonem, word, phonem_word, phonem_normenv, word_normenv, phonem_word_normenv;
  - `*_cl_final/run1..100/`: the same for 100 permuted (chance-level) regressors, which make up ~15 GB;
  - `lambda_final/lambda_cv_{r,err}.mat` (13 lambdas x 20), `electrodes_select_final/...` (96, 6, 20).
- `toolboxes.zip` (0.6 GB): `eeglab13_6_5b.zip`, `fieldtrip-20240111.zip` only.
- `maj_*.m` analysis scripts, `ciplot.m`, `fdr_bh.m`, `chanlocs96.mat` / `elec_96ch.elp` (E01..E96 template,
  spherical), `record.json`, `MD5SUMS`.
- **Not shipped:** raw EEG (`cgr_s<N>_spe0{1,2,3}.xdf`), cleaned EEG (`cgr_s<N>_all.set`), audio, envelopes, the
  phoneme/word onset regressors (`sig{1,2}_<block>_word_silben_phonem.mat`), the MAUS TextGrids/transcripts. The
  scripts load them from the authors' local drives (`G:\Uni_DFG\...`).

## 3. What the scripts tell us about the (unshared) recordings
Recorded for a future search for the raw data; from `maj_preprocessing_lambda.m`.
- Subjects `6 7 8 9 10 11 12 13 14 15 16 18 20 21 22 23 24 25 26 27`, attended stream
  `1 2 2 1 1 2 2 1 1 2 2 1 2 1 1 2 2 1 1 2` (1 = left, 2 = right).
- XDF via LSL (`BrainAmpSeries` stream), 500 Hz, 96 channels (94 cap + 2 EOG below the eyes, nose reference).
  12 channels around the ears/neck not prepared because of the cEEGrids (`28 90 81 95 22 80 71 85 24 72 18 92`)
  were interpolated by the authors.
- Onsets: epochs `StartTrigger` + 0.088 s to + 600.088 s ("BrainAmp delay between marker and sound onset",
  88 ms; holtze2021, same lab and LSL setup, used 102 ms). Software LSL markers, no stimtrack mentioned.
- Subject 16: block 6 lost from 429 s (zero-padded by the authors); subject 21: recording stopped, three files.
- Regressors cut to the first 600 s of each block.

## 4. Overlap with holtze2021
- Same lab (Oldenburg), same amplifier family (BrainAmp, nose reference, 500 Hz, equidistant Easycap layout), same
  LSL marker setup. holtze2021's notes state its narratives were "previously used in Mirkovic et al. (2016) and
  Jaeger et al. (2020)", i.e. these recordings. Probably the same two fairy-tale narratives (holtze2021: 5 blocks of
  600.5-622.6 s; here 6 blocks of 10 min, gaps > 500 ms shortened), but neither audio nor regressors are shipped, so
  this cannot be checked. Participants: different study (Jaeger 2020 vs Holtze 2021); overlap of individuals unknown.

## 5. Open questions (default chosen)
1. Incorporate? **Default: no — record as not incorporable (no neural data, no stimuli).** Keep the registry entry
   so the decision is traceable, or drop it (main session's call).
2. Ask the authors for the raw XDF + regressors? The user sends upstream requests; text in the report.
3. Delete the local download (15.9 GB, `R/jaeger2025/download/`)? Woody keeps the md5-checked copy. **Default:
   delete after the user's sign-off; no vault backup needed** (the woody copy is the archive; nothing standardised).

## Alignment grade
`none`: not assessable; there is no neural time series or stimulus in the release.
