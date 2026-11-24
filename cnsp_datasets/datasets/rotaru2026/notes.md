# rotaru2026: KUL-AAD-NFB, closed-loop auditory attention decoding with neurofeedback (KU Leuven)

Notes from exploration, standardisation and validation (worker agents, 2026-11-24). Scripts:
`/data_storage/gu08wuvu/datasets/tmp/review/scripts/rotaru2026*` and `.../scripts/rotaru2026/`; logs, json and
figures: `/data_storage/gu08wuvu/datasets/tmp/review/rotaru2026/` (`agent_log.md`). That folder is temporary.

## 1. Source
- Zenodo record 20442638 ("KUL-AAD-NFB: Dataset of Auditory Attention Decoding with Neurofeedback, KU Leuven",
  published 2026-05-29), doi:10.5281/zenodo.20442638. **Licence CC BY 4.0**; the audio (Universiteit van
  Vlaanderen podcasts) only for non-commercial use (`stimuli/README.txt`).
- Paper: Rotaru I, Geirnaert S, Heintz N, Bertrand A, Francart T (2026). When feedback backfires: investigating
  neurofeedback effects in a closed-loop auditory attention decoding paradigm. bioRxiv
  doi:10.64898/2026.04.28.721343 (`data_campaign/papers/rotaru2026.pdf`). Cite the record, the paper and the
  broadcaster (`KUL-AAD-NFB_dataset_description.docx`).
- No code shipped.
- Obtained from the user's archive copy on woody (`zenodo/rotaru2026/20442638/`), md5 identical on woody, here and
  in `record.json` for all 6 files; zips kept in `download/`, extracted to `extracted/`. This server never contacted
  Zenodo.

## 2. Layout
- `eeg.zip` (15.4 GB) -> `eeg/sub-XX/sub-XX_ses-YY_trialN_task-<cond>_eeg.bdf` (raw BioSemi) and, per trial,
  `..._eeg_preprocessed.mat` (~275 MB; the description says `.npy`, the files are MATLAB v5): `eeg_raw` (5-s
  segments at 1024 Hz), `eeg_downsampled` / `eeg_preprocessed` (64 Hz, CAR, 1-9 Hz), `stim_raw` / `stim_preprocessed`
  (2 streams), `attention_labels` per segment, `params_randomization` (stimulus names, condition, switch times,
  initial attended ear, feedback flags, calibration level) and `params_preprocessing`.
- `stimuli.zip` -> 31 mono 44.1 kHz wavs (`<title>_10min_trimmedSilencesTo0.20s.wav`, 487-595 s: 30-s intro cut,
  trimmed to 10 min, silences shortened to 200 ms), `All_stimuli.txt` (the 31 names), `README.txt`.
- `KUL-AAD-NFB_behavioral_results.csv` (ratings per trial, all 19 participants), `..._participants_overview.xlsx`
  (sex, age, decoder, sharing consent), `..._online_decoder_type_per_subject.jsonc`, `..._dataset_description.docx`.

## 3. Stimulus <-> trial mapping (verified)
- 19 participants recorded, **11 shared** (consent): sub-02, 03, 06, 09 (ses-01 SI decoder, ses-02 SS decoder),
  11, 12, 13, 15, 16, 17, 19. Ages 19-40, 6 F / 5 M.
- Per session 2 blocks x (OL, CLV, CLA, psCLA), pseudo-random order, 8-min (480 s) trials, two different male
  Flemish podcasts per trial from loudspeakers at +-14 deg, 1.4 m. sub-11..19 first did 4 x 5-min OL-CAL
  calibration trials (no switch). Each main trial has 1 or 3 cued attention switches (visual arrow) at fixed times
  (e.g. 120/240/360 s).
- Stimulus names, side mapping and the attention schedule come from `params_randomization` in the `.mat`. Left
  loudspeaker = `speakers[0]` (`stim_mapping` = `['L', 'R']` everywhere; sub-03 uses the older field name
  `stimuli_to_chans_mapping` and space-padded names). `id_condition` `CLAsham` = psCLA.
- 122 BDFs; **118 standardised**. Skipped (no `.mat`, so no stimulus names or schedule): sub-02 trials 5 and 10
  (psCLA, BDFs complete), sub-19 trial 7 (CLV, listed as missing in the description), and sub-13 trial 1
  `task-CLAU-CAL` (a 16 kB BDF with no data).
- OL-CAL: sub-15 has trials 2-4 only (27 OL-CAL trials).
- 30 of the 31 wavs are used by the shared trials; every wav is longer than the 480 s trial (stored as shipped,
  cut at the point of use).
- **Stimulus overlap with accou2023 (SparrKULee)**: SparrKULee also used Universiteit van Vlaanderen podcasts. 4-s
  envelope probes (100 Hz) at 30/150/300/450 s of each wav, cross-correlated against all 37 SparrKULee podcasts
  (`scripts/rotaru2026/overlap_sparrkulee.py`, `overlap_sparrkulee.log`), match 10 of the 31 wavs with r 0.82-1.00
  at consistent, increasing positions: Heeft_het_zin_om_fair_trade = podcast_24, Hoe_groot_is_de_kans = 15,
  Hoe_moeilijk_is_het_om_de_trein = 1, Hoe_onterf_je_je_kind = 23, Hoe_word_ik_fit = 28,
  Waarom_gebruiken_we_drugs = 32, Waarom_herinneren_mensen_met_dementie = 20, Wat_kan_je_terugvinden = 25,
  Zijn_led-schermen_gevaarlijk = 19, Zorgt_Waze = 35 (rotaru versions are intro-cut and silence-trimmed). No match
  for the other 21. das2019 uses its own story recordings (no overlap). rotaru2024 (now incorporated) also
  used Flemish podcasts from the same source; 10 of its 30 are SparrKULee ones too, so stimulus (and possibly
  participant) overlap with rotaru2024 is likely; see rotaru2024/notes.md (user, 2026-11-24).
- **Participant overlap** cannot be checked: all KUL releases use anonymised per-study IDs. The BDFs date from
  Aug 2024; sex/age are in the participants sheet only.

## 4. Speech features available
Raw audio of both talkers (the wavs). The authors' 1024 Hz envelopes (`stim_raw`) are not used.
- **Closed-loop feedback alters the stimulus.** In CLA and psCLA the two talkers' gains changed every second
  (complementary, within -6..+6 dB around 57 dBA, i.e. 51-63 dBA; paper 2.3, 2.6): from the online decoder + causal
  HMM in CLA, and from a trajectory precomputed on the matched OL trial in psCLA. In OL, CLV and OL-CAL both
  talkers played at 57 dBA. **The gain trajectories are not in the release.** `stim_raw` in the `.mat` is the
  authors' envelope of the unscaled wav: r 0.92-0.94 with the wav envelope at lag 0, and its per-second level
  ratio to the wav varies as little in CLA (sd 1.2-1.4 dB) as in OL (1.1-1.5 dB) (sub-13 trials 12/13,
  `scripts/rotaru2026/stimraw_env.py`). So the stored wavs are the sources before the feedback gain, not the sound
  heard in CLA/psCLA. Not recoverable here (needs the online decoder output); flagged in the sidecar
  (`audio_feedback`, `audio_feedback_sham`, notes) and asked upstream (section 10).
- Visual feedback (CLV: a slider) is not stored.

## 5. Neural data
- BioSemi ActiveTwo, 64 scalp channels (10-20, BioSemi64 order and names), 1024 Hz, BDF (read into V); no EXG or
  peripheral channels; `Status` used for alignment and dropped. Reference CMS/DRL (reference-free), not
  re-referenced. No digitisation: biosemi64 template montage.
- Bad channels (`BADS`, per subject-session, `scripts/rotaru2026_bads.py`, `bads_scan.png`): 40-200 Hz RMS > 5x
  the session median (median over trials, 60-240 s): sub-02 P2, PO4; sub-06 P2; sub-11 P2; sub-12 P2; sub-13 POz
  (18-42x). Channels with 1-40 Hz RMS < 0.1x the median (PO3, POz, P1 in some sessions) are not marked: they sit
  next to the CMS/DRL electrodes (between PO3, POz and PO4), where low amplitude is expected with the
  CMS-referenced recording.
- Sidecar: participant, session label, file, left/right stimulus, initial attended ear, switch times, feedback
  flags, calibrated level, bad channels, the participant's ratings for that trial (speech intelligibility,
  listening effort, distraction, switch effort, agency, score prediction).

## 6. Alignment
- Triggers: the playback software wrote a **pulse burst (~0.5 s) at the start of every 1-s audio buffer on a
  separate channel of the stimulus sound card** (Behringer UMC1820), recorded in BioSemi Status bit 0 (paper 2.4).
  Burst k marks audio second k; the first burst is wav sample 0 (consistent with the authors' `stim_raw`, which
  matches the wav at lag 0 within their trigger-cut segments).
- Adaptor: first rising edge of each burst (a rise more than 200 samples after the previous fall; blips shorter
  than 20 samples ignored, one in sub-16 trial 8). An interval between consecutive bursts more than 1 sample off
  1 s (quantisation alone gives at most 1) starts a new run. One least-squares fit per trial gives a common slope
  (the drift; same clocks throughout) and one onset per run. Each run is cut with one spline resample onto the
  audio clock (`crop_on_audio_clock`) and the runs are concatenated, so the stimulus stays continuous and the EEG
  during a stall is dropped; the joins keep MNE's `BAD boundary` / `EDGE boundary` annotations. A run that would
  start before the previous run's grid (an early burst) raises.
- **Jitter**: fit residuals 0.25-0.30 ms sd, max 0.6 ms (`burst_jitter.log`, 19 trials), i.e. the 1024 Hz
  quantisation floor (0.28 ms); stored per trial as `jitter_ms`.
- **Drift** (hardware, corrected): sound card vs BioSemi **+6.0 ppm** median (4.4-6.9 ppm per trial in every
  subject), ~3 ms over a trial; `drift_ppm` per trial.
- **Playback stalls**: 9 trials have a ~12.5 ms gap (the bursts after it are 12-13 ms later than the first grid)
  at audio s 236-412 (`stalls.log`): sub-06 t2, t5; sub-09 ses-01 t4; sub-09 ses-02 t8, t9, t11; sub-12 t9;
  sub-17 t9; sub-19 t13. 3 more have one interval 2 samples long (~2 ms; `interval_scan.log`): sub-09 ses-01 t5
  (s 431) and t8 (s 321), sub-17 t8 (s 447). `n_playback_runs`, `run_start_s` in the sidecar.
- **The tmp standardisation and validation (section 9) predate two adaptor changes from the review**: a common
  slope instead of one line per run (the separate fits gave noisy drifts on short tail runs: 0.0, 0.45, 2.49 ppm,
  <= ~0.4 ms), and the 1-sample stall threshold (the first threshold, > 2 samples, absorbed the 3 small stalls
  as 7.4 / 11.5 / 8.1 ppm, <= ~1 ms; now sub-09 t8 is 2 runs at 6.35 ppm). Single-run trials are unchanged
  (sub-13 t13 identical to the stored file within 1e-9 V; `scripts/rotaru2026/check_adaptor.py`). The 12 trials
  with stalls differ by <= 1 ms and lacked the boundary annotations and `jitter_ms`; not re-run (user decision).
- Acoustic path ~4 ms (1.4 m), not corrected.
- Trial onsets 2.4-83.6 s into the BDF (median 9.9 s).

## 7. Cross-subject duration check
Every trial has bursts covering its full 480 s (300 s OL-CAL) without a repeated second
(`scripts/rotaru2026_survey.py`, `survey.log`); durations follow from the burst count, so no separate duration
check is needed.

## 8. Data size
Counted from the EEG trials (the wavs are longer than the trials, so `data_size.py` would overcount): 11
participants (12 sessions), **14.38 h** in total, **1.31 h per participant** (0.80-2.13; sub-09 two sessions).
Per condition: OL 3.20 h, CLA 3.20 h, CLV 3.07 h, psCLA 2.67 h, OL-CAL 2.25 h. Standardised size 16 GB.

## 9. Validation (2026-11-24, all 11 participants, average reference)
Standard validator (`run_validation.log`, `validation.json`, figure `validation/validation.png`). In trials with
switches no stream is flagged as attended, so the validator modelled the left talker (attended about half the
time); in OL-CAL the attended talker.
- **low** pass: mean r 0.019 (median 0.016), 9/11 subjects above the circular-shift null (sub-09 and sub-19 not),
  p_circ 0.02, p_mismatch 0.048, TRF peaks ~30 and ~190 ms, nothing at negative lags.
- **mlr** (30-60 Hz) pass: SNR 1.11, p 0.010, 5/11 subjects; TRF peak ~30 ms (Pa).
- **brainstem** (30-250 Hz) fail: SNR 1.04, p 0.12, 1/11; no wave V, only the ~29 ms response.
- **Attention** (`scripts/rotaru2026_attention.py`; forward models 0.5-8 Hz, attended = left/right talker per cued
  span, leave-one-trial-out per session; `attention_skip3.json`, figure `r-attended-vs-r-ignored_skip3.png`, 3 s
  after each switch left out): attended r 0.023 vs ignored 0.013, **11/12 sessions attended > ignored**, Wilcoxon
  p 0.0015; lag sweep peaks at 0 ms. Per condition (attended > ignored, p): OL-CAL 6/7 (0.047), OL 10/12 (0.042),
  CLV 7/12 (0.20), CLA 10/12 (0.003), psCLA 10/11 (0.002). Without the skip the numbers are nearly identical
  (`attention.json`).
- **DNN timing check** (accou2023 match-mismatch classifier, `scripts/rotaru2026/dnn_wrap.py`, OL-CAL trials only,
  where the attended talker is fixed; 7 subjects, 27 trials): **-9.7 ms** (95% CI -12.8..-7.3), typical for two
  competing talkers (geirnaert2025 -10.2 ms) and including the ~4 ms acoustic path. Documented, not applied.
- Coherence batch not run.

## 10. Upstream issues
- The per-second feedback gain trajectories of CLA and psCLA are not shared; without them the stimulus heard in
  those conditions is unknown (+-6 dB per talker).
- sub-02 psCLA trials 5 and 10 have BDFs but no `.mat` (no stimulus names or schedule) and are not mentioned in the
  description; sub-19 trial 7 has a BDF although the description lists it as missing; sub-13 has an empty
  `task-CLAU-CAL` BDF.
- The description says the preprocessed data are `.npy`; they are `.mat`.
- 9 trials contain a ~12.5 ms and 3 a ~2 ms playback stall (section 6), not mentioned.

## 11. Adaptor
- One TrialRecord per BDF with a `.mat`; condition = task (OL-CAL, OL, CLV, CLA, psCLA); subject and session as in
  the file names.
- Stimuli: left and right wavs (`audio`), names without the common suffix; `is_attended` only in OL-CAL (no
  switch). Attention spans as annotations `attend/left` / `attend/right` (onset, duration in s).
- 1024 Hz kept; one spline resample per run for the drift (no rate change). Wavs via
  `simon_base.common.audio_loader` (checks 44.1 kHz mono int16).
- Off by default / not applied: DNN offset; nothing brain-based.

## Alignment grade
**good**: 1-s pulse bursts played on the stimulus sound card with the audio and recorded in BioSemi Status (as in
accou2023); onset and drift (+6 ppm) per playback run from hardware, residual jitter 0.28 ms (quantisation), stalls
detected; the 30-60 Hz tier passes (Pa ~30 ms), lag sweep at 0 ms, DNN -9.7 ms (two talkers, loudspeakers). No
audio copy in the EEG to check the pulses against. The stimulus heard in CLA/psCLA differs from the stored wavs by
the unknown feedback gains (a stimulus-fidelity caveat, not timing).
