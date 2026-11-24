# Campaign status

One row per dataset. Update it when a dataset's state changes, together with the spreadsheet (see `../CLAUDE.md`).
Alignment = alignment-quality grade (`good`/`medium`/`poor`/`none`, CLAUDE.md; accepted by the user 2026-11-24;
evidence per dataset in its `notes.md` and in `tmp/review/alignment_quality.md`).
Tier = highest validation tier passed overall (`low` 0.5-8 Hz, `mlr` 30-60 Hz, `brainstem` 30-250 Hz; for MEG,
brainstem means a high-frequency cortical response). Details live in each dataset's `notes.md` / `README.md`.
"Data" says what is still on disk under `/data_storage/gu08wuvu/datasets/tmp/review/<d>/` (results are always kept).

Last updated: 2026-11-24.

## Done
| repo name | sheet id | branch | tier | alignment | data | notes |
|---|---|---|---|---|---|---|
| accou2023 | accou2024 | main | brainstem | good | user's read-only copy | DNN anchor for all offsets |
| bentum2023 | bentum2023 | main | low | poor | deleted | marker drift kept; per-block DNN onsets help 8-16 Hz |
| brennan2018 | brennan2019 | main | brainstem | good | deleted | |
| broderick2019_natural / _cocktail / _av | broderick2018-nat / -cock / -av | main | low | medium / poor / medium | deleted | cocktail DNN -45 ms (documented) |
| das2019 | biesmans2017 | main | low | poor | deleted | DNN -81 ms (documented); size from EEG (~1.3 h/subject) |
| etard2019 | etard2019 | main | brainstem | good | BIDS in user's folder | BIDS re-upload pending (licence) |
| fuglsang2018 | fuglsang2017 | main | low (mlr without reverb) | medium | deleted | |
| gao2024 | gao2024 | dev (a80b901) | low (48/48 subj, median r 0.049; 100 Hz data, no higher tier possible) | medium | deleted 2026-11-24 (user); woody copy, no vault backup | authors' tSSS 100 Hz MEG; +490 ppm trigger-derived drift corrected by default; condition labels verified vs authors' Fig2/3 data (27/27, exp3 21/21); exp2 echo-250 TRF on the mixture peaks early by the echo delay (direct-sound TRF clean); 3 experiments, 48 participants |
| guilleminot2021 | guilleminot2022 | main | mlr | good | deleted | ~7 ppm, not corrected |
| jehn2025_nh / _hi / _ci | jehn2025-nh / -ha / -ci | main | mlr / mlr / brainstem | good | deleted | drift correction optional, off; user to decide |
| narayanan2021 | narayanan2021 | main | low | medium | deleted (vault backup) | drift correction on |
| rogachev2024 | rogachev2024 | dev (3333be6) | low (52 children, mean r 0.038, 42/52; TRF peak 125 ms) | medium | deleted 2026-11-24 (user; re-downloadable from OSF) | OSF; authors' preprocessed CND, 31 ch at 500 Hz (1-15 Hz, ICA, avg ref; FCz online ref not restored); children aged 3-8; onsets = software story-start markers (not shipped), per-trial lag-sweep median +2 ms; 7 (not 6) wombat-story children, younger and weaker trackers; no licence stated (user: incorporate as none stated) |
| rotaru2026 | rotaru2026 | dev (a276a9c) | mlr (all 11; low 9/11, 30-60 Hz p 0.01, brainstem fails); attended > ignored 11/12 (p 0.0015) | good | deleted 2026-11-24 (user); raw copy on woody, no vault backup | 1-s sound-card pulse train in Status: hardware onset + drift (+6 ppm) per trial; 12 playback stalls split into runs (tmp data predates the final adaptor, <= 1 ms); CLA/psCLA feedback gains (±6 dB/s) not shipped, wavs are pre-gain (flagged per trial); 10/31 podcasts also in accou2023; DNN -9.7 ms (documented); 11 of 19 participants public |
| schueller2024 | schuller2023 | main | brainstem (Set1) | good | user's read-only copy | Sets 2/3 wait for Zenodo |
| thornton2025 | thornton2025 | dev (a2a27ee) | low (all 19; r 0.021, 10/19; mlr fails); attended > ignored 17/19 (p 7e-5) | medium | download/extracted/standardised ~2.7 GB in tmp (delete pending) | in-ear dry EEG (2 ch, 256 Hz, FT7 ref); onsets from the authors' microphone xcorr, not re-verifiable; TRF peak 172 ms, decoder lag 0 ms; 19 subjects in release vs 18 in paper; talker identity confounded with attention |
| varano2022 | varano2026 | main | low | medium | deleted | re-standardise after the audio-cut fix (PLAN 8) |
| weissbart2019 | weissbart2020 | main | brainstem | good | BIDS in user's folder | BIDS re-upload pending (licence) |
| armeni2022 | armeni2022 | dev | brainstem | good | deleted | EEG dropped |
| gwilliams2023 | gwilliams2023 | dev | brainstem | good | deleted | onsets from MISC 009; -46 ppm corrected |
| libribrain100 | mantegna2026 | dev | low | medium | deleted | per-condition validation not done; Sherlock1 embargo |
| polonenko2021 / 2024 / 2025 / 2026 | same | dev | brainstem | medium / good / good / good | deleted | |
| shan2024 | shan2024 | dev | mlr (ABR with ANM regressors) | medium | deleted | |
| stoll2025 (+ _cortex) | stoll2025 | dev | brainstem (cortex weakly) | good | deleted | |
| harshaiyahav2025 | harshaiyahav2025 | dev | low | medium | deleted | CND envelopes only; DNN -15.6 ms |
| herrmann2025 | herrmann2025 | dev | mlr | medium | deleted | |
| holtze2021 | holtze2021 | dev | low | medium | deleted | v1.1.1 audio |
| momenian2024 | momenian2024 | dev | low | poor | deleted | stimulus rebuilt per participant |
| habersetzer2025 | habersetzer2025 | dev | brainstem (tSSS) | good | deleted | +485 ppm corrected |
| pkueeg2025 | pkueeg2025 | dev | low (pilot 12 subj) | poor | deleted | drift 76.8 ppm kept; alternatives 47/27 ppm; DNN -75/-42 ms documented |
| wang2025 | wang2025 | dev | low | poor | deleted | +164 ppm; ~-0.19 s offset documented, not applied |
| yang2026_en / _ru | yang2026 | dev | brainstem (tSSS) | good | deleted | EEG kept inside MEG trials, not validated |
| wang2022 | wang2022 | dev | mlr (6 subj) | poor | deleted | onset Beg + 18.5 ms; stored data/validation used the old onset |
| karunathilake2023_aging | karunathilake2023-aging | dev | low | medium | deleted | DSS components only |
| levy2024 | levy2024 | dev | low | medium | deleted | |
| brodbeck2022 | brodbeck2022 | dev | low (mlr population only) | medium | deleted | no audio (copyright) |
| vanheusden2020 | vanheusden2020 | dev | mlr | medium | deleted; user's manual download kept | |
| presacco2016 | presacco2016 | dev | brainstem (30-250 Hz; mlr fails) | medium | deleted (results kept; raw on the NHR vault) | MEG only; pilot 20 subj; licence not stated; drift -37 ppm documented; full run pending storage |
| karunathilake2023 | karunathilake2023 | dev | brainstem (clear speech; vocoded low only) | medium | deleted (results kept; Dryad) | pilot 16/39; separate study from _aging; subject = full R-number; full run pending storage |
| karunathilake2025 | karunathilake2025 | dev | brainstem (pooled, 3 subj; noise condition low only) | medium | deleted (results kept; Dryad) | pilot 3/30; full run (~35 GB) pending storage |
| deoisres2023 | deoisres2023 | dev | mlr (pilot 5/22; brainstem only via S03 stimulus artefact) | good | deleted (results kept; re-downloadable) | ePrints blocks scripts (Anubis); drift -24 ppm corrected by default; decisions pending |
| chen2023 | chen2023 | dev | brainstem (drift +510 ppm default, data-derived, user-approved; 4/4 subj) | poor | deleted (results kept; GitLab re-download) | 16 ms delay applied; vocoded trials carry the clean wav by default; ANC DUA: no redistribution; full run ~85 GB |
| piazza2025_l1l / _l2l | piazza2025 | dev | low (data shared preprocessed 1-8 Hz, 100 Hz) | medium | deleted (results kept; re-downloadable) | all 50 standardised; L2L 6-25 channel order unknown; L1L 13-15 stimulus files remapped by trial length; licence unknown |
| calderondepalma2023 | calderondepalma2023 | dev | low (all 13; all 5 conditions; ceiling at 64 Hz) | medium | deleted (results kept; re-downloadable) | CND; channel order inferred (biosemi64); degraded-audio envelopes only; DNN +2.5 ms; BSD-3 |
| brodbeck2018 | brodbeck2018 | dev | low (all 26; ceiling at 100 Hz); attended > ignored 26/26 | medium | deleted (results kept; re-downloadable; raw on the NHR vault) | 100 Hz tSSS epochs only; no overlap with brodbeck2022; no licence stated (user: incorporate as none stated) |
| straetmans2021 | straetmans2021 | dev | none (no stimulus shipped; sanity only) | none | deleted (results kept; re-downloadable) | kept as EEG-only (user, 2026-11-23); ask the authors for the wavs |
| winchester2026 | winchester2026 | dev | low (all 31; 3 conditions; ceiling at 125 Hz envelopes) | medium | deleted (results kept; re-downloadable) | music (piano); envelopes only, no audio; 9 subj at 250 Hz, 22 at 500 Hz; subject 5 looks broken; licence not stated |
| li2025 | li2025 | dev (929221f) | low (mean r 0.0245, 90% subj) | poor | 18.9 GB download + 12 GB standardised in tmp | OPM-MEG; per-subject brain-based delays 0.39-1.26 s (wide search; fallbacks sub-37/40; ambiguous 33/39/47/53/55) + pooled Theil-Sen drift -16.7 ppm applied by default (both brain_trf, user decisions 2026-11-23); sub-53 fragile |
| diliberto2020 | diliberto2020 | dev | mlr (all 20; 30-60 Hz 13/20; brainstem nominal only) | medium | deleted (results kept; re-downloadable) | music (Bach); wavs from the kern2022 Donders collection are the default stimulus (match the shipped envelope at lag 0, r >= 0.9995); ADC counts scaled to V |
| kern2022 | kern2022 | dev | brainstem (pilot 4/35; 30-250 Hz 3/4 subj) | good | deleted (results kept; re-downloadable) | music; audio copy: onset +4.1 ms and drift +6.5 ppm on by default (user, hardware-derived; validation no worse); full run ~115 GB |
| hassan2026 | hassan2026 | dev | low (all 16; r 0.0097 → 0.0193 with the onset correction) | poor | deleted (results kept; re-downloadable) | alignment poor: +0.718 s DNN onset applied by default (all 6 streams; devices 1/2 within 0.5 ms; per-subject -703..-723 ms); drift +9 ppm not corrected |
| chen2026 | chen2026 | dev | low (pilot 3/8, old per-chapter default; mlr pass is a ripple artefact); defaults now option B onsets, no drift, all 8 kept (2026-11-24) | poor | deleted by the user (results kept; raw on the NHR vault) | onset = t0 (trigger fit) + option-B latency (listener median unless the chapter deviates > max(40 ms, 3 SE); 39/281 chapters own value; user 2026-11-23; onsets_optionB.csv); drift +16 ppm logged in drift.csv, not applied (unreliable); dev 6324961; next: full run of 8 listeners (~48 GB), sub-02 (kept), deletion |
| kulasingham2021 | kulasingham2021 | dev | low (all 22; ceiling at 200 Hz); attended > ignored 20/22 | medium | deleted (results kept; re-downloadable; raw on the NHR vault) | preprocessed epochs only; R2522 block order corrected from the data (readme wrong); no licence stated (user: incorporate as none stated) |
| wang2026 | wang2026 | dev | low (all 18; mlr/brainstem fail); attended > ignored n.s. (11/18, p 0.32) | medium | standardised_final 11 GB + download (delete pending) | Trigger-channel onsets (S14 CNT table 48 ms early); DNN -26 ms (documented); passive block has no stimulus |
| geirnaert2025 | geirnaert2025 | dev | low (all 15; scalp 13/15, ear 8/15; mlr/brainstem fail); attended > ignored scalp 15/15, ear 14/15 | medium | standardised_v3 16 GB + download/extracted (~75 GB total; delete pending) | scalp and ear amplifiers as ns_types eeg / ear-eeg; ~15 ms inter-amplifier steps in 4 trials (documented); DNN -10 ms; CC BY-NC-SA; **second pass**: split in-ear / around-ear into separate files (montage rule) |
| peng2026 | peng2026 | dev | low (all 30; weak: r 0.008, 12/30; TV fails mismatch); AAD (ear proxy) 0.55, restaurant 0.61 | medium | download/extracted/standardised ~47 GB (delete pending) | sub-01..08 onsets rebuilt from the Net Station log (shipped ones drift ~+65 ppm, up to 0.1 s), on by default (user 2026-11-24: keep, **revisit at the next run**), `onset="authors"` restores; DNN -26 ms; mixtures only (no talker streams) |
| zhang2025 | zhang2025 | dev (2d1d927) | low (66 subj, weak: r 0.0069, 14/66; 125 Hz); attended > ignored p 0.008 (40/62) | medium (under review: TRF weak, inside the null band) | 18 GB in tmp (superseded runs + caches 6.6 GB, final standardised_v4 1.5 GB, download + extracted 9.6 GB; delete pending) | cEEGrid/OpenBCI ear-EEG; shipped trial names don't map to the raw files: mapping rebuilt by EEG xcorr (make_mapping.py, 3287 trials); onset = authors' cut 1.023 s after the screen photodiode (no audio copy); 1689 shipped trials have no raw data and 1689 raw recordings match no shipped trial (withheld participants?); bads per chen2026 rule |

Not in the campaign sheet: mai2023 (dev, iEEG, not reviewed), jehn2024 (dev), karengal2025 / koelbl2021 /
schuller2022full (internal).

## In progress
| repo name | sheet id | branch | state | next |
|---|---|---|---|---|
| kulasingham2020 | kulasingham2020 | dev (registry 3333be6, split-zip extraction ecf27b9, notes f7f0e86) | downloaded (DRUM, md5 OK) + vault backup 14/14 (2026-11-24); explored: 80 continuous fifs, 40 subj, DENOISED by the authors (TSPCA/SNS), not raw; 32 subj = presacco2016 quiet blocks (map verified, r 0.98-1.00), 8 new; wavs = presacco Quiet_H/L (md5); triggers as presacco2016, offset-onset -37.5 ppm (document only); proposed medium | **user decision**: separate dataset (recommended) vs source inside presacco2016; then adaptor; 29 GB in tmp |
| jaeger2025 | jaeger2025 | dev (notes 373ebc2) | not incorporable: the Zenodo release has only TRF weights / prediction r (Data.zip), no EEG or stimuli; grade none; download 15 GB in tmp (delete pending sign-off; woody keeps the copy) | ask the authors for the raw XDF + regressors/audio (draft in upstream_issues.md); recordings = Jaeger 2020, probably holtze2021's narratives |
| cervantesconstantino2018 | cervantesconstantino2018 | dev (registry ba87fef, notes b371434) | not incorporable: DRUM release is results only (repetition-averaged z-scored DSS components at 1 kHz, 50 Hz envelopes, decoders, TRFs; ~6 min/subject), no sensor MEG, single trials or audio; grade none; no vault backup; 2.8 GB in tmp (delete pending sign-off) | ask the Simon lab for the raw KIT data + wavs + probe times (draft in upstream_issues.md); R2434 = copy of R2433 |
| zhang2023 | zhang2022 | dev (ed1d660, 5c15ae7) | explored + per-trial DNN rescue (2026-11-24): shipped timing off ~1-3 s per presentation pair; DNN-confident offsets for only 14/313 pairs (0.73 h of 13.8 h, 6 subjects; null 0/626); after shift r -0.010 -> 0.032 on those | **user decision**: discard (recommended) / confident pairs only (poor); 22 GB in tmp (delete on discard) |
| schueller2024 Sets 2/3 | schuller2023 | main | Set2 on woody (38.5 GB, md5 ok), Set3 downloading there | not this pass (user 2026-11-24: Set1 adaptor robust enough); second pass |

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
