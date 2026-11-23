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
| presacco2016 | presacco2016 | dev | brainstem (30-250 Hz; mlr fails) | deleted (results kept; raw on the NHR vault) | MEG only; pilot 20 subj; licence not stated; drift -37 ppm documented; full run pending storage |
| karunathilake2023 | karunathilake2023 | dev | brainstem (clear speech; vocoded low only) | deleted (results kept; Dryad) | pilot 16/39; separate study from _aging; subject = full R-number; full run pending storage |
| karunathilake2025 | karunathilake2025 | dev | brainstem (pooled, 3 subj; noise condition low only) | deleted (results kept; Dryad) | pilot 3/30; full run (~35 GB) pending storage |
| deoisres2023 | deoisres2023 | dev | mlr (pilot 5/22; brainstem only via S03 stimulus artefact) | user's manual download (read-only) + 13 GB extracted + 5.2 GB pilot in tmp | ePrints blocks scripts (Anubis); drift -24 ppm corrected by default; decisions pending |
| chen2023 | chen2023 | dev | brainstem (drift +510 ppm default, data-derived, user-approved; 4/4 subj) | deleted (results kept; GitLab re-download) | 16 ms delay applied; vocoded trials carry the clean wav by default; ANC DUA: no redistribution; full run ~85 GB |
| piazza2025_l1l / _l2l | piazza2025 | dev | low (data shared preprocessed 1-8 Hz, 100 Hz) | ~15 GB in tmp (download, standardised, v1) | all 50 standardised; L2L 6-25 channel order unknown; L1L 13-15 stimulus files remapped by trial length; licence unknown |
| calderondepalma2023 | calderondepalma2023 | dev | low (all 13; all 5 conditions; ceiling at 64 Hz) | 2.4 GB download + 1.0 GB standardised in tmp | CND; channel order inferred (biosemi64); degraded-audio envelopes only; DNN +2.5 ms; BSD-3 |
| brodbeck2018 | brodbeck2018 | dev | low (all 26; ceiling at 100 Hz); attended > ignored 26/26 | download, x/ and standardised (2.5 GB) in tmp; vault backup verified | 100 Hz tSSS epochs only; no overlap with brodbeck2022; no licence stated |
| straetmans2021 | straetmans2021 | dev | none (no stimulus shipped; sanity only) | download 1.2 GB + standardised in tmp | kept as EEG-only (user, 2026-11-23); ask the authors for the wavs |
| winchester2026 | winchester2026 | dev | low (all 31; 3 conditions; ceiling at 125 Hz envelopes) | download 5.4 GB + standardised 4.4 GB in tmp | music (piano); envelopes only, no audio; 9 subj at 250 Hz, 22 at 500 Hz; subject 5 looks broken; licence not stated |
| li2025 | li2025 | dev | low (per-subject onset: r 0.024, TRF peak 78 ms both groups) | 18.9 GB download + 12 GB standardised in tmp | OPM-MEG; brain-based per-subject onset delays by default (onset.csv; 0.39-0.89 s; 3 fallbacks), per-group as option (user confirmed per-subject; fallbacks sub-35/37/40 accepted; sub-50/52/53 early ~150 ms lag documented) |
| diliberto2020 | diliberto2020 | dev | mlr (all 20; 30-60 Hz 13/20; brainstem nominal only) | 12 GB download+extracted + 0.3 GB wavs + 13 GB standardised in tmp | music (Bach); wavs from the kern2022 Donders collection are the default stimulus (match the shipped envelope at lag 0, r >= 0.9995); ADC counts scaled to V |
| kern2022 | kern2022 | dev | brainstem (pilot 4/35; 30-250 Hz 3/4 subj) | 207 GB download + 13 GB pilot in tmp | music; audio copy: onset +4.1 ms and drift +6.5 ppm on by default (user, hardware-derived; validation no worse); full run ~115 GB |
| chen2026 | chen2026 | dev | low (pilot 3/8, old per-chapter default; mlr pass is a ripple artefact) | deleted by the user (results kept; raw on the NHR vault) | onset = t0 (trigger fit) + option-B latency (listener median unless the chapter deviates > max(40 ms, 3 SE); 39/281 chapters own value; user 2026-11-23; onsets_optionB.csv); drift +16 ppm logged in drift.csv, not applied (unreliable); dev 6324961; next: full run of 8 listeners (~48 GB), sub-02 (kept), deletion |
| kulasingham2021 | kulasingham2021 | dev | low (all 22; ceiling at 200 Hz); attended > ignored 20/22 | 4.9 GB zips + 11 GB extracted + 5 GB standardised in tmp; vault backup verified | preprocessed epochs only; R2522 block order corrected from the data (readme wrong); no licence stated |

Not in the campaign sheet: mai2023 (dev, iEEG, not reviewed), jehn2024 (dev), karengal2025 / koelbl2021 /
schuller2022full (internal).

## In progress
| repo name | sheet id | branch | state | next |
|---|---|---|---|---|
| hassan2026 | hassan2026 | dev (adaptor e24fecd, not run) | downloaded 5.15 GB, verified; EEG in volts; ~0.8 s latency after the playback timestamp (lag sweep, all 16 subj; documented); per-device timestamps not acoustic | user: allow pyarrow + soundfile in the venv; decide the 0.8 s offset; then pilot + validation |
| peng2026 | peng2026 | dev (registry fe3393d) | Zenodo 403 (unusual traffic) at 21:09 on 2026-11-23; not downloaded; 21.6 GB single zip; sub-01..09 E-Prime trigger bug (authors re-aligned) | user: Zenodo support?; then download |
| zhang2025 | zhang2025 | dev (registry fe3393d) | Zenodo 403; not downloaded; file list unverified (may need an exclude) | after peng2026 |

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
