# Campaign status

One row per dataset. Update it when a dataset's state changes, together with the spreadsheet (see `../CLAUDE.md`).
Tier = highest validation tier passed overall (`low` 0.5-8 Hz, `mlr` 30-60 Hz, `brainstem` 30-250 Hz; for MEG,
brainstem means a high-frequency cortical response). Details live in each dataset's `notes.md` / `README.md`.
"Data" says what is still on disk under `/data_storage/gu08wuvu/datasets/tmp/review/<d>/` (results are always kept).

Last updated: 2026-11-23.

## Done
| repo name | sheet id | branch | tier | data | notes |
|---|---|---|---|---|---|
| accou2023 | accou2024 | main | brainstem | user's read-only copy | DNN anchor for all offsets |
| bentum2023 | bentum2023 | main | low | deleted | marker drift kept; per-block DNN onsets help 8-16 Hz |
| brennan2018 | brennan2019 | main | brainstem | deleted | |
| broderick2019_natural / _cocktail / _av | broderick2018-nat / -cock / -av | main | low | deleted | cocktail DNN -45 ms (documented) |
| das2019 | biesmans2017 | main | low | deleted | DNN -81 ms (documented); size from EEG (~1.3 h/subject) |
| etard2019 | etard2019 | main | brainstem | BIDS in user's folder | BIDS re-upload pending (licence) |
| fuglsang2018 | fuglsang2017 | main | low (mlr without reverb) | deleted | |
| guilleminot2021 | guilleminot2022 | main | mlr | deleted | ~7 ppm, not corrected |
| jehn2025_nh / _hi / _ci | jehn2025-nh / -ha / -ci | main | mlr / mlr / brainstem | deleted | drift correction optional, off; user to decide |
| narayanan2021 | narayanan2021 | main | low | deleted (vault backup) | drift correction on |
| schueller2024 | schuller2023 | main | brainstem (Set1) | user's read-only copy | Sets 2/3 wait for Zenodo |
| varano2022 | varano2026 | main | low | deleted | re-standardise after the audio-cut fix (PLAN 8) |
| weissbart2019 | weissbart2020 | main | brainstem | BIDS in user's folder | BIDS re-upload pending (licence) |
| armeni2022 | armeni2022 | dev | brainstem | deleted | EEG dropped |
| gwilliams2023 | gwilliams2023 | dev | brainstem | deleted | onsets from MISC 009; -46 ppm corrected |
| libribrain100 | mantegna2026 | dev | low | deleted | per-condition validation not done; Sherlock1 embargo |
| polonenko2021 / 2024 / 2025 / 2026 | same | dev | brainstem | deleted | |
| shan2024 | shan2024 | dev | mlr (ABR with ANM regressors) | deleted | |
| stoll2025 (+ _cortex) | stoll2025 | dev | brainstem (cortex weakly) | deleted | |
| harshaiyahav2025 | harshaiyahav2025 | dev | low | deleted | CND envelopes only; DNN -15.6 ms |
| herrmann2025 | herrmann2025 | dev | mlr | deleted | |
| holtze2021 | holtze2021 | dev | low | deleted | v1.1.1 audio |
| momenian2024 | momenian2024 | dev | low | deleted | stimulus rebuilt per participant |
| habersetzer2025 | habersetzer2025 | dev | brainstem (tSSS) | deleted | +485 ppm corrected |
| pkueeg2025 | pkueeg2025 | dev | low (pilot 12 subj) | deleted | drift 76.8 ppm kept; alternatives 47/27 ppm; DNN -75/-42 ms documented |
| wang2025 | wang2025 | dev | low | deleted | +164 ppm; ~-0.19 s offset documented, not applied |
| yang2026_en / _ru | yang2026 | dev | brainstem (tSSS) | deleted | EEG kept inside MEG trials, not validated |
| wang2022 | wang2022 | dev | mlr (6 subj) | deleted | onset Beg + 18.5 ms; stored data/validation used the old onset |
| karunathilake2023_aging | karunathilake2023-aging | dev | low | deleted | DSS components only |
| levy2024 | levy2024 | dev | low | deleted | |
| brodbeck2022 | brodbeck2022 | dev | low (mlr population only) | deleted | no audio (copyright) |
| vanheusden2020 | vanheusden2020 | dev | mlr | deleted; user's manual download kept | |
| presacco2016 | presacco2016 | dev | brainstem (30-250 Hz; mlr fails) | extracted MEG + pilot in tmp (MEG zips deleted); vault backup verified 2026-11-23 | MEG only; pilot 20 subj; licence not stated; drift -37 ppm documented; full run pending storage |
| karunathilake2023 | karunathilake2023 | dev | brainstem (clear speech; vocoded low only) | 203 GB in tmp (zips + extracted + pilot) | pilot 16/39; separate study from _aging; subject = R-number mod 1000; full run pending storage |
| karunathilake2025 | karunathilake2025 | dev | brainstem (pooled, 3 subj; noise condition low only) | 59 GB in tmp (zip + 3 extracted + pilot) | pilot 3/30; full run (~35 GB) pending storage |
| deoisres2023 | deoisres2023 | dev | mlr (pilot 5/22; brainstem only via S03 stimulus artefact) | user's manual download (read-only) + 13 GB extracted + 5.2 GB pilot in tmp | ePrints blocks scripts (Anubis); drift -24 ppm corrected by default; decisions pending |
| chen2023 | chen2023 | dev | low as standardised; brainstem with +485-510 ppm drift (validation only) | 183 GB in tmp (download 102 + pilot 80) | drift_ppm default 0 until user approves +510; 16 ms delay applied; ANC DUA: no redistribution |

Not in the campaign sheet: mai2023 (dev, iEEG, not reviewed), jehn2024 (dev), karengal2025 / koelbl2021 /
schuller2022full (internal).

## In progress
| repo name | sheet id | branch | state | next |
|---|---|---|---|---|
| chen2026 | chen2026 | dev (notes only, no adaptor) | downloaded (49 GB) + NHR vault backup verified (md5 13/13 local, 178/178 sizes on vault); 281 chapters trigger-verified (24.8 h; sub-05 LP 14/27, sub-06 GD 4 absent) | user decisions on per-chapter latency (option B proposed) and +16 ppm drift; then adaptor reading `timing_table_proposal.csv` |
| hassan2026 | hassan2026 | dev (registry + notes, 1273cb2) | blocked: HF repo gated (auto-approve), no token; 5.15 GB without video | user accepts terms + adds HF token (`hf`) to secrets.json; then download, explore, adaptor |

## Open items across datasets
- **Push `dev`**: many commits are ahead of `origin/dev`; needs the user's approval.
- **trial_drift side-lobe re-check**: recompute jehn2025 and schueller2024 drift with a positive-peak fit and
  compare (habersetzer2025 looks unaffected). If it is confirmed, fix `trial_drift` and re-run its users.
- **Documented but not applied**:
  - DNN offsets for das2019, bentum2023, broderick2019_cocktail, pkueeg2025, wang2025;
  - the pkueeg2025 drift value;
  - Jehn drift correction on/off.

  This is the "second pass" in PLAN.md section 8.
- **Validator gaps** (shared code, ask the user): the `hf` feature is missing for envelope-only stimuli, and
  `--picks mag` keeps bads.
- **Upstream reports**: drafts in `tmp/review/upstream_issues.md`; the user sends them.
- **BIDS re-uploads** of weissbart2019 / etard2019: licence in `dataset_description.json`, then upload.
- **Leftovers to review**:
  - tags `dev-old` / `internal-old`;
  - rotate the Dryad token if it was ever pasted in a chat.
- **Second run**: rename the repo datasets to the spreadsheet's ids (`id_changes` tab).
