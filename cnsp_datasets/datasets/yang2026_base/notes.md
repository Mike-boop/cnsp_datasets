# yang2026: notes

Explorer notes (2026-11-22). Scripts and results: `/data_storage/gu08wuvu/datasets/tmp/review/yang2026/`
(`scripts/align.py` audio-copy onset/drift per presentation, `scripts/jumps.py` playback-glitch detection,
`scripts/mfa_check.py`, `scripts/headers.py`; results `audio_lag/{en,ru,all}.csv`, `audio_lag/jumps.csv`,
`audio_lag/lags/*.npz` (per-window lags), `audio_lag/drift_onset_per_subject.png`, `headers.csv`).

## 1. Source
- OSF qdzgh, doi:10.17605/OSF.IO/QDZGH, "Kymata SOTO Language Dataset (English and Russian Conversations)".
  **Licence: CC-BY 4.0** (OSF node licence via the API; paper, Data Records). Both `dataset_description.json` say
  "CC0"; the OSF licence and the paper are the stronger statement, so use CC-BY 4.0. The audio are edited BBC
  podcast excerpts ("You're Dead to Me: The History of Ice Cream", BBC Radio 4 2023; "БибиСева", BBC Russian
  Service 2014); the paper does not discuss their copyright beyond "the stimuli used were edited versions" (open
  question 1).
- Paper: Yang, Parish, Klimovich-Gray, Wingfield, Marslen-Wilson, Zhang, Woolgar & Thwaites 2026, "Kymata Soto
  Language Dataset: an electro-magnetoencephalographic dataset for natural speech processing", Sci Data 13:254,
  doi:10.1038/s41597-026-06579-8. Preregistrations OSF 45DCG (English), TC825 (Russian).
- Code: none for the recordings ("only MNE-BIDS is required"). `stimuli/audio/script_for_bbc_english_podcast_cutting/`
  (English only): `reconstruct_from_csv.py` + `cuts.csv` rebuild the excerpt from the BBC mp3 (44.1 kHz sample
  indices); not needed, the excerpt wav itself is shipped. Validation workflows: kymata-core (GitHub), not used here.
- Downloaded: everything except `anat/`, the visual-stimulus png zips and BIDS-check folders (160 GB).

## 2. Layout
Two BIDS 1.9.0 datasets, one per language/site:
- `english-native-english-conversation/`: `sub-E1..E20`, `sub-E3b` (E3's second session, see 3);
  `sub-EX/meg/sub-EX_task-en_run-N_meg.fif` (+ `_events.tsv`, `_channels.tsv`, `_meg.json`), runs 1-4 (E1: 1-2;
  E8: 1-3), plus `task-emptyroom_run-0` per subject. `sss_cal_triux.dat`, `ct_sparse_triux.fif` at the root.
- `russian-native-russian-conversation/`: `sub-R1..R15`, runs 1-2 + emptyroom. **sub-R6 has no `meg/`
  folder**: its files sit directly in `sub-R6/` (adaptor must glob both). `sss_cal_vectorview.dat`,
  `ct_sparse_vectorview.fif`.
- `stimuli/audio/stimulus.wav` (one per language), MFA tables `mfa_word.txt` + `mfa_word_stime.txt`, and
  `mfa_phone[me].txt` + `mfa_phone[me]_stime.txt` (English uses `phoneme`, Russian `phone` in the file names;
  the paper says `phone`). `stimuli/visual/`: Russian only, `CIEXYZ_colour_changes_over_stimulus/...txt` (colorimetry
  of the dots; out of scope).
- Run = one MEG file = one block of **two presentations** of the same wav with a break (questions) between them.
- `README` files contain only the title. `*_coordsystem.json` claim "CTF" coordinates (mne-bids artefact); the FIF
  dig and `dev_head_t` are what counts.
- **events.tsv `onset` is the absolute FIF time (sample / 1000 including `first_samp`)**, not the time from the first
  stored sample: e.g. sub-E2 run-1 code 3 at 205.905 s in events.tsv = sample 205905, first_samp 79000, i.e.
  `raw.times` 126.905 s. Subtract `first_samp / sfreq`.

## 3. Stimulus <-> trial mapping
- One stimulus per language, the same for all subjects: English `stimulus.wav` 48 kHz float32 stereo (L = R,
  r 0.9999998), 19 273 352 samples = **401.528 s**; Russian 44.1 kHz float32 stereo (L = R), 18 189 579 samples =
  **412.462 s**. (The paper says "400 s", "44.1 kHz 16-bit"; the shipped files differ in rate/format but the audio
  copy confirms them, see 6.) Both wavs have a non-standard RIFF chunk (scipy warns "Chunk (non-data) not understood").
- Presentations per subject (paper, Participants): English 8 (2 per run x 4 runs), E8 6 (3 runs), Russian 4 (2 runs
  x 2). **sub-E1 has only 2 runs (4 presentations)** although the paper says 8 for everyone except E8: runs 3-4
  are not on OSF (unknown why; open question). **sub-E3b** = participant E3's second session ("One participant (E3)
  came for a second session with the same 8 repetitions", paper), recorded 2023-12-22 vs 2023-09-14.
- Practice: a 20 s excerpt of the podcast's opening introduction before run 1 (paper, Procedure; code 1 events,
  10 per practice (E12: 7, E16: 9) at 1 s spacing). Not shipped as a wav; out of scope. Missing in sub-E3 run-1
  and sub-E8 run-1.
- **Verified with the audio copy** (section 6): every presentation is found in the audio channel by envelope
  cross-correlation over the whole run (independent of the triggers; first 60 s of the wav as template), and the
  waveform (2-200 Hz, drift-corrected) matches the shipped wav at a median window r of 0.87-0.999 per presentation
  (English) and 0.87-0.997 (Russian). All 222 presentations (162 English, 60 Russian; exactly 2 per run) were
  found, each with a code 3 that precedes it by 16.9-20.5 ms (English) / 8.4-9.8 ms (Russian), and every code 3 has
  its presentation. sub-E6 run-2's code 3 are missing from events.tsv but present in STI101 (see 6).
- Presentation order: run number = `meas_date` order (checked for all subjects); within a run the two presentations
  are in time order. Trial index = (run - 1) * 2 + presentation.

## 4. Speech features
- Raw audio as shipped (see 3). Transcripts: Whisper large-v2, corrected manually; words and phones force-aligned
  with MFA (English dictionary/acoustic model v3.0.0, Russian v3.1.0) (paper, Stimuli).
- MFA tables give **start times only** (one label per line, one start per line, 10 ms resolution, monotonic);
  `<sp>` = short pause (in both tiers), `spn` = word not in the dictionary (English 21, Russian 51 phones). Every
  word start is a phone start. English 1656 word intervals (1396 words), 5097 phone intervals; Russian 1345 (1131),
  5683. The last entry is `<sp>` starting at 401.50 s (English) / 412.12 s (Russian), i.e. the last interval ends at
  the wav end. To build TextGrids (`words`, `phones`): interval i = [start_i, start_{i+1}), last = [start, wav
  duration]; keep `<sp>` as empty intervals (or label them, standardiser's choice).
- Time base = the wav (`scripts/mfa_check.py`): the `<sp>` intervals carry 3.5x (English) / 4.9x (Russian) less
  envelope rms than words, and shifting the `<sp>` mask by -300..+300 ms gives the best separation at +5 / +10 ms
  (within the 10 ms MFA frame; 0 ms is equal to 3 digits). So the tables start at wav sample 0.
- Phone sets: English ARPAbet with stress; Russian MFA IPA (UTF-8).

## 5. Neural data
Simultaneous EEG + MEG ("EMEG") at both sites; 1000 Hz; raw (no SSS: `proc_history` empty in every file, paper
Preprocessing: "shared raw ... researchers will need to pass the data through SSS"). Units as shipped SI (FIF).
The paper's Procedure **swaps the systems**; the FIF headers are unambiguous:

| | English | Russian |
|---|---|---|
| system (FIF `description`) | "TRIUX system at Cambridge-3146" (MEGIN TRIUX, MRC CBU) | "Vectorview system at Cambridge" (Elekta Neuromag VectorView) |
| recorded | 2023-07 .. 2024-01 | 2015-03 |
| SSS files | `sss_cal_triux.dat`, `ct_sparse_triux.fif` | `sss_cal_vectorview.dat`, `ct_sparse_vectorview.fif` |
| online filter | 0.1-330 Hz | 0.03-330 Hz |
| MEG | 102 mag + 204 planar grad (coil types VV_MAG_T1 / VV_PLANAR_T1), no ref_meg | same |
| EEG | 64 (EEG001-064) | 70 (EEG001-060, EEG065-074) |
| EOG / ECG | EOG001, EOG002 (`eog`), ECG003 (`ecg`) | EOG061, EOG062 (`eog`), ECG063 (`ecg`); R1 and R2 also a channel named `recordedinerror` typed ecg (drop) |
| audio copy | **MISC006, MISC007** (identical: same lags/r) | **MISC005** |
| other MISC | MISC001-005 (unknown content; offsets, not audio), | MISC201-206, MISC301-306 all zero; STI301 a +-10 V ramp, STI201 constant (unknown) |
| triggers | STI101 (+ STI001-016 bits) | STI101 (STI201, STI301 unused) |
| projectors | 12 (dossp-2.1.2), inactive | 8 (`mag_ssp_upright.fif` PCA), inactive |
| bads | none in FIF or channels.tsv | 5-15 per subject in FIF `info["bads"]` (EEG + MEG; MEG0333, MEG2022, MEG0813 recur); channels.tsv says all "good" |
| dig (Polhemus) | 183-306 points (3 fiducials, 5 HPI, EEG electrodes, head shape) | 179-195 |
| cHPI | on (5 coils, 293/307/314/321/328 Hz: lines 1e5x above the floor in a mag PSD) | on (same frequencies) |

- EEG reference: nose electrode (paper, Procedure). The paper says 70 electrodes; the English files have 64.
- `dev_head_t` per run; head position "checked at the start of each block" (paper). No continuous head-position
  files shipped (cHPI is in the data, so it can be computed).
- Run files 1.4-1.6 GB (~950 s, 306 MEG + EEG + aux). Empty-room runs: E10 empty room has no EEG/aux channels.
- Magnetometer rms (raw, broadband, median over channels, 60 s): ~6.8 pT (E2) and ~13 pT (R2), dominated by
  50/150 Hz and the cHPI lines; the data need SSS before analysis (paper; open question 3).

## 6. Alignment
- **Triggers** (paper, Triggers): STI101; 1 = onset of the practice audio, 2 = "each second of the video stimulus",
  3 = onset of each 400 s presentation; 4096-20000 = button presses (forced-choice questions), unmapped. Also seen:
  32768 (bit 16 / STI016, many in some runs: E9 runs 1-2 >370, E6 run-2 142), 95/255/127/4145/32719/49 (single
  events, at run starts). Sent by Psychtoolbox (Matlab); hardware path not described: **trigger type software,
  inferred** (PTB; onset jitter 3 ms, see below). The paper says "the delays in both sound and visual stimuli
  presentations are corrected for in the configuration files" (not shared; not quantified).
- **STI101 decoding**: STI101 is stored as signed int16; when bit 16 is high, code 3 reads -32765 and code 2
  -32766, and events.tsv (mne-bids) then lists them as other values or drops them. **sub-E6 run-2 has no code 3 in
  events.tsv** (and 679 instead of ~800 code 2) although STI001 shows both presentations. Use
  `STI101.astype(int) & 0xFF` (or bits STI001/STI002) and edge detection, not events.tsv.
- Sound delivery: Etymotic ER3 insert earphones with 2.5 m tubes (paper): **acoustic delay of the tubes ~7.3 ms**
  (2.5 m / 343 m/s), not in the audio copy (which is electrical). Whether the "delay corrections in the
  configuration files" already include it is unknown.
- **Audio copy**: the presented waveform (not an envelope) recorded by the MEG ADC at 1 kHz (330 Hz low-pass, same
  as the sensors): English MISC006 = MISC007 (L/R; identical lags and r), Russian MISC005. Where it is tapped
  (sound card output or amplifier) is unknown.
- Measurement (`scripts/align.py`, every run): presentations located by envelope xcorr (100 Hz, whole run); per
  presentation a coarse line through envelope lags (10 s windows every 5 s, +-600 ms), then the wav (1 kHz,
  2-200 Hz) is put on that clock and cross-correlated with the MISC waveform (10 s windows every 5 s, +-30 ms,
  positive sub-sample peak), Theil-Sen line -> onset (fractional MEG sample of wav sample 0) and drift.

- **Results** (`audio_lag/all.csv`, plot `audio_lag/drift_onset_per_subject.png`; drift > 0: the MEG counts more
  samples per audio second, i.e. the MEG clock is fast relative to the audio clock):

  | | English (TRIUX) | Russian (VectorView) |
  |---|---|---|
  | presentations | 162 (21 sessions) | 60 (15 subjects) |
  | audio onset after code 3 | **18.71 +- 0.90 ms** (16.92-20.46) | **9.10 +- 0.35 ms** (8.40-9.78) |
  | drift, audio copy vs MEG | **+537.89 +- 0.41 ppm** (537.05-538.73) | **-0.73 +- 0.14 ppm** (-1.02 to -0.42) |
  | within-subject sd of drift | 0.05 ppm | 0.09 ppm |
  | subject medians | 537.26-538.68: E1-E7 (2023-07..10) 538.44 +- 0.13, E8-E20/E3b (2023-12..2024-01) 537.63 +- 0.17 | -0.98 to -0.61 |
  | residual of window lags about the line (robust sd) | 0.014 ms (median) | 0.024 ms |
  | code-2 ("video second") clock vs MEG | +493.9 ppm | -341.2 ppm |
  | error at the wav end if uncorrected | 216 ms | 0.3 ms |

  - English: a ~538 ppm drift, the same order as habersetzer2025's +485 ppm on another TRIUX; on the VectorView
    (Russian, other stimulus PC and year) the audio and MEG clocks agree to < 1 ppm. The code-2 clock (PTB loop on
    the stimulus PC) is a third clock at both sites (44 ppm / 340 ppm off the audio); not usable for alignment.
    Whether the TRIUX sample clock or the English sound card is off nominal is unknown; that both TRIUX datasets
    show ~500 ppm (with different sound cards) hints at the TRIUX, but this is not established.
  - Onset jitter after code 3 (3.5 ms range in English, 1.4 ms in Russian) is software-trigger jitter: the
    audio-copy onset, not code 3, must define the trial start.
  - **Playback glitch**: sub-E12 run-1 presentation 2 has a +14.9 ms step at wav time ~352 s (1 s windows: lag -2 ms
    up to 351.0 s, +13 ms from 352.5 s on; `scripts/glitch.py`): the playback paused ~15 ms. No other step in any
    presentation (`scripts/jumps.py`: persistent change of the 7-window running median > 0.5 ms; coarse envelope
    lags checked for steps beyond +-30 ms). The presentation's whole-trial Theil-Sen fit is still dominated by the
    pre-glitch part (onset 19.48 ms, drift 537.68 ppm), but the last 50 s are 15 ms late.
  - Truncated presentations: 13 Russian second presentations of a run end 0.1-5.6 s before the end of the wav (the
    recording was stopped early; 23.6 s in total). All English presentations are complete (>= 2.4 s margin).
- **Proposed alignment** (`alignment_method = stimtrack_xcorr`, `trigger_type = software (inferred; PTB)`): per
  presentation, onset = the fitted audio-copy onset (fractional MEG sample of wav sample 0, from the first stored
  sample) + an acoustic delay (default 7.3 ms: open question 4); drift = the presentation's own fitted value
  (English ~538 ppm; Russian ~-0.7 ppm), applied with `standardise/clock.py:crop_on_audio_clock(raw, onset, n_out,
  drift, sfreq_out=1000)`; n_out = wav length at 1 kHz (stops early for the 13 truncated Russian trials). The
  standardiser should port `scripts/align.py` into the repo (`datasets/yang2026/drift.py` -> `drift.csv`, keyed by
  file and presentation), as for habersetzer2025, since tmp is deleted. Trial location without the CSV: code 3
  (decoded from STI101 & 0xFF) + 18.7 ms (English) / 9.1 ms (Russian), error <= 2 ms / 0.7 ms, plus the site drift.
- jitter_ms for the provenance: the audio-copy fit (window residual ~0.02 ms; onset precision well below one
  sample); `drift_ppm` per presentation.

## 7. Cross-subject duration check
- One stimulus per site, so all presentations have the same length and duration error = drift x length + c cannot
  be separated from trigger spans alone; there is also no end-of-audio trigger. The audio copy gives drift and onset
  within every presentation directly (section 6), and the per-subject plot shows it is constant within a session
  (sd 0.05 / 0.09 ppm) with two date clusters in English (538.4 vs 537.6 ppm).
- Trigger-derived spans (code 2, one per "video second"): first to last code 2 of a presentation = 399.178 s
  (English, median) / 398.851 s (Russian) of MEG time for 399 nominal seconds, i.e. the PTB clock at +494 / -341 ppm
  vs the MEG; 399 or 400 code 2 per English presentation (one is merged into code 3 in the second presentation of
  a run), always 400 in Russian.
- Onset jitter of the audio relative to code 3: sd 0.90 ms (English), 0.35 ms (Russian); no difference between
  first and second presentation of a run (18.65 / 18.78 ms; 9.06 / 9.14 ms).

## 8. Data size
Each presentation counts the wav duration (401.528 s English, 412.462 s Russian).
- English: 20 participants, 21 sessions, 162 presentations = **18.07 h**; 8 presentations (0.892 h) per session;
  E1 4 (0.446 h), E8 6 (0.669 h), E3 16 over two sessions (E3 + E3b, 1.785 h). **0.903 h per participant (mean;
  0.446-1.785)**.
- Russian: 15 participants x 4 presentations = **6.87 h** (6.87 h recorded minus 23.6 s truncated); **0.458 h per
  participant** (all equal).
- Total 24.94 h, 35 participants (36 sessions).
- Recording size: 1.4-1.6 GB per run (two presentations); one run in memory as float64 ~3 GB (306 MEG + 64/70 EEG +
  aux, ~950 s). The explorer's per-run pass (STI101 + one MISC channel) peaked at 0.5 GB.

## 9. Open questions (recommended defaults so the standardiser can proceed)
1. **Licence of the audio**: OSF CC-BY 4.0 (the dataset_description says CC0). The wavs are edited BBC programmes;
   the authors redistribute them on OSF. Default: standardise and redistribute under CC-BY 4.0 with the paper's
   attribution and a note on the BBC source; a human should confirm redistribution of the BBC audio is acceptable.
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** CC-BY 4.0 (OSF node + paper); the CC0 in both
   dataset_description.json and the BBC origin of the audio are noted in the README; redistribution of the BBC audio
   still to be confirmed by a human.
2. **One or two adaptors**: recommend **two adaptors, `yang2026_en` and `yang2026_ru`, sharing one module**
   (`yang2026_base`-style: loader, STI decoding, `drift.py`/`drift.csv`), as jehn2025_*: separate BIDS roots,
   participants, MEG systems (TRIUX 2023 vs VectorView 2015), EEG montages, stimuli and drift regimes (538 vs
   -0.7 ppm); validation tiers and data size are then reported per site. Subjects: E1..E20 -> 1..20 (sub-E3b ->
   subject 3, session 2); R1..R15 -> 1..15.
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** two adaptors `yang2026_en`, `yang2026_ru` (`ADAPTOR =
   partial(Yang2026Adaptor, site=...)`) sharing `yang2026_base` (adaptor, STI decoding `STI101 & 0xFF`, `drift.py` ->
   `drift.csv`, notes, README). Both take the single `yang2026` download dir (holding the two BIDS folders) and join
   their site folder, so the registry is unchanged. sub-E3b = subject 3, session 2.
3. **SSS**: the data are raw. Default as habersetzer2025: standardise raw (least processed), keep the FIF bads
   (Russian 5-15 per subject; English none), ship/point to the site's fine-cal and cross-talk files in the
   metadata, apply Maxwell filtering only in validation (`tmp/review/scripts/meg/validate_sss.py`, with the
   matching `sss_cal_*`/`ct_sparse_*`). cHPI lines (293-328 Hz) stay in the data.
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** raw standardised; FIF bads kept (only MEG/EOG/ECG
   bads remain after dropping EEG); Maxwell filtering only in validation; cHPI lines left in (noted in the
   provenance).
4. **Acoustic delay**: the audio copy is electrical; the ER3 earphones have **2.5 m tubes (~7.3 ms at 343 m/s)**,
   plus the ER3 transducer. The paper says delays "are corrected for in the configuration files" (not shared). Default:
   onset = audio-copy onset + **7.3 ms** (`ACOUSTIC_DELAY_MS`, tube only, documented as an assumption); the
   alternative is + 0 (electrical). This is larger than in habersetzer2025 (0.4 ms) and matters for the brainstem/
   MLR tiers.
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** onset = fitted audio-copy onset (fractional) + 7.3 ms
   (`ACOUSTIC_DELAY_MS`, tube only, assumption; precedent schueller2024 +6 ms tube delay).
5. **Drift correction**: English +537.9 ppm (537.05-538.73; 216 ms at the wav end), Russian -0.73 ppm (0.3 ms).
   Evidence plotted per subject (`audio_lag/drift_onset_per_subject.png`). Default: correct every presentation with
   its own fitted value from `drift.csv` (both sites, for uniformity); adaptor option
   `drift_correction="presentation"|"site"|None`.
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** per presentation from `drift.csv` (both sites);
   `drift_correction="presentation"|"site"|None`, default "presentation". alignment_method `stimtrack_xcorr`,
   trigger_type software (inferred, Psychtoolbox).
6. **sub-E12 run-1 presentation 2 (playback glitch at wav 352 s, +15 ms)**: default: fit onset/drift on the windows
   before 351 s and end the neural trial at wav time 351.0 s (stimulus not cut; the longer signal is cut at use);
   note it in the provenance. Alternative: split into two trials (0-351 s and 352.5 s-end with its own onset).
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** the default: fit on the windows before wav 351 s
   (`FIT_END_S`) and end the neural trial at wav 351 s (`fit_end_s` and `glitch` in the provenance).
7. **Truncated Russian presentations** (13, 0.1-5.6 s short): keep; the trial is shorter than the wav; noted in the
   provenance.
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** keep; `truncated_s` in the provenance.
8. **EEG**: simultaneous EEG (nose reference; 64 ch English, 70 ch Russian, with digitised positions) in the same
   FIFs. Default: keep the EEG channels in the MEG trial (`eeg` type, reference "nose" in the metadata; Russian EEG
   bads kept), since the dataset is EMEG and dropping them loses half its value. If the standard format needs one
   modality per trial, drop EEG in `yang2026_*` and consider separate `_eeg` adaptors later.
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** **changed from the explorer default: the EEG is
   dropped** (precedents: the user dropped armeni2022's EEG; habersetzer2025 sub-01's EEG dropped). Alternative: keep
   it as `eeg` in the MEG trial (nose reference), or separate `_eeg` adaptors later.
   **Revised (user, 2026-11-22 evening):** keep the EEG inside the MEG trials as `eeg` channels (nose reference, as
   recorded; flat-channel check extended to EEG). Tested on English sub-1, sub-11 and Russian sub-2 (64/70 EEG
   channels, all with positions, median sd 21-35 uV, FIF EEG bads kept). The validation, coherence and data size
   above were computed on the MEG-only pilot; the EEG has not been validated.
9. **Channels kept**: MEG (306), EEG, EOG (EOG001/002 or EOG061/062), ECG (ECG003 / ECG063), audio copy as `misc`
   (English MISC006 and MISC007, Russian MISC005), described in the metadata. Drop: English MISC001-005 (content
   unknown, not audio), STI*, SYS201; Russian MISC201-206/301-306 (all zero), STI201/STI301, `recordedinerror`
   (R1, R2).
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** as recommended, minus the EEG (see 8): MEG, EOG, ECG,
   audio copy (`misc`; English MISC006 + MISC007, Russian MISC005).
10. **sub-E1 has only 4 presentations** (runs 1-2; paper: 8). Default: include what is there; note as an upstream
    issue (ask the authors whether runs 3-4 exist).
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** include its 4 presentations; upstream issue logged.
11. **sub-E3b** (E3's second session, same stimulus): default include as subject 3 session 2 (trials 1-8 of
    session 2). Users wanting one session per participant can filter.
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** include as subject 3, session 2.
12. **Paper errata** (upstream issues): systems swapped in Procedure (English is TRIUX, Russian VectorView, per FIF
    headers and the SSS file names); stimulus "400 s, 44.1 kHz 16-bit" vs shipped 401.53 s 48 kHz float (English)
    and 412.46 s 44.1 kHz float (Russian); 70 EEG electrodes vs 64 in the English files; `mfa_phone*` vs
    `mfa_phoneme*` file names (English); events.tsv onsets include `first_samp`; events.tsv drops code 3 when bit 16
    is high (sub-E6 run-2); sub-R6 files outside `meg/`; CC0 vs CC-BY.
13. **Out of scope**: practice audio (code 1; 20 s, not shipped), empty-room runs (Russian ones are shared between
    subjects recorded on the same or a nearby day: e.g. R7/R8/R9 share one file), the visual dot stimulus (ran
    simultaneously at 60 Hz, "not meaningfully synchronised" with the audio, paper; its onset coincides with the
    audio onset and may evoke onset responses), button presses.
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** out of scope as listed; the possible visual onset
   responses at the audio start are noted in the provenance.
14. **Conditions / trials**: one condition per adaptor (`conversation`), trial = presentation order within the
    session ((run - 1) * 2 + presentation; E1: 1-4, E8: 1-6). Stimulus: the wav as shipped (stereo L = R; 48 kHz
    / 44.1 kHz float32) and a TextGrid built from the MFA tables (section 4).
   **Decided (coordinator, 2026-11-22, user asleep; revisit):** one condition `conversation`; trial = (run - 1) * 2 +
   presentation; stimulus name `conversation_en` / `conversation_ru`. TextGrid tiers `words`/`phones` from the MFA
   start tables (interval i = [start_i, start_{i+1}), last ends at the wav duration; `<sp>` left as empty intervals,
   `spn` kept; 10 ms resolution). Audio: the wav's first channel as shipped (L = R; one channel saved).

## 10. Standardisation (2026-11-22)
- Code: `yang2026_base/adaptor.py` (`Yang2026Adaptor(download_dir, site)`), `yang2026_en/adaptor.py` and
  `yang2026_ru/adaptor.py` (`partial(..., site=...)`). Both take the shared `yang2026` download directory and join
  `english-native-english-conversation` / `russian-native-russian-conversation`; no registry change.
- `drift.py` ports the explorer's `scripts/align.py` (code 3 locates each presentation; coarse envelope fit
  +-600 ms; fine waveform fit +-30 ms on the coarse clock, 10 s windows every 5 s, Theil-Sen) and writes
  `drift.csv` (222 presentations: `site, file, pres, code3, coarse_ppm, n_windows, onset_samp, drift_ppm,
  end_margin_s`). It uses the **positive** xcorr peak: a first version that reused `jehn2025_base.drift.trial_drift`
  (|xcorr| peak) picked the inverted side lobe in some windows (onsets ~2.4 samples off and drifts up to 10 ppm off
  in 41 presentations, mostly Russian). With the positive peak, drift.csv equals the explorer's `all.csv` to
  < 0.0001 samples (onset) and < 0.0002 ppm (drift, median), except sub-E12 run-1 presentation 2, which is fitted
  on the windows before wav 351 s (69 windows; onset -0.16 samples, drift +0.08 ppm vs the whole-trial fit).
  English: onset 18.68 ms after code 3 (16.92-20.46), drift 537.74 ppm (537.05-538.74); Russian 9.04 ms
  (8.41-9.78), -0.76 ppm (-1.02 to -0.42); 13 Russian presentations truncated (23.6 s in total).
- **Audio-copy check on the standardised trials** (`tmp/review/yang2026/scripts/check_lag.py`, `check_lag.log`:
  audio copy vs wav, 2-200 Hz, 10 s windows, sub-sample peak; expected -7.3 ms = the added tube delay):
  English sub-E2 trials 1 and 8, sub-E3 session 2 trial 2, sub-E12 trials 2 (glitch trial, ends at 351.000 s) and
  4: -7.25 to -7.28 ms in the first, middle and last window (r 0.90-0.96); Russian sub-R1 trial 4, sub-R7
  trials 1-2: -7.21 to -7.35 ms (r 0.94-0.96). No residual drift at the trial end (start-to-end change
  <= 0.012 ms English, <= 0.052 ms Russian, i.e. < 0.13 ppm).

## 11. Validation (2026-11-22)
- Summary in the repo: `validation.json` (per site and variant, tSSS and raw; per-unit results, per-trial tiers,
  tSSS bads, backward decoder and lag sweep, latency TRF, cHPI check, sanity, reference datasets). Scripts (tmp, to
  be deleted): `/data_storage/gu08wuvu/datasets/tmp/review/scripts/meg/yang2026_{validate,summary,chpi_check}.py`,
  `yang2026_run.sh`; log and figures `/data_storage/gu08wuvu/datasets/tmp/review/yang2026/validation/{run.log,figs/}`
  (`validation_yang2026_{en,ru}_{tsss,raw}_all.png`, `backward_sweep_latency.png`).
- Data: English participants 1-10 + sub-E3b (11 units = sessions, 82 trials, 9.15 h); Russian all 15 (60 trials,
  6.87 h). 102 magnetometers, no re-reference. tSSS in the validation only: FIF bads + `find_bad_channels_maxwell`
  (first 120 s of each trial; English 0-10 per trial, Russian 3-12), `maxwell_filter` with the site's
  `sss_cal_*`/`ct_sparse_*`, `st_duration` 10 s, head-shape origin, head frame, no movement compensation, no notch,
  no cHPI removal.
- Results (median; mean SNR in brackets; units significant):

  | | en tSSS | en raw | ru tSSS | ru raw |
  |---|---|---|---|---|
  | low forward r | 0.034 (11/11) | 0.001 (1/11, p 0.14, fails) | 0.030 (15/15) | 0.004 (1/15, p 0.06, fails) |
  | backward r | 0.237 (11/11) | 0.158 (11/11) | 0.219 (15/15) | 0.122 (15/15) |
  | mlr SNR | 1.43 [1.42] (8/11) | 1.08 [1.07] (4/11, p 0.04) | 1.20 [1.24] (6/15) | 0.98 [1.02] (2/15, p 0.27) |
  | brainstem SNR | 1.25 [1.31] (9/11) | 1.06 [1.04] (2/11, p 0.01) | 1.14 [1.15] (7/15) | 0.98 [1.00] (1/15, p 0.63) |
  | tier | brainstem | none | brainstem | none |

- Backward lag sweep (64 Hz): tSSS +1.5 ms (CI +0.8 to +2.1) en, +0.7 ms (+0.3 to +1.3) ru; raw +1.2 / +1.3 ms;
  every unit within one sample (15.6 ms). Validator residual drift -9 +- 47 ppm (en), -7 +- 83 ppm (ru).
- Latencies (tSSS, 1-15 Hz GFP): en M50 43.5 ms, M100 95.3 ms (grand; subject medians 45.3 / 107 ms); ru 38.4 /
  92.6 ms (39.4 / 94.8 ms). HF GFP peaks: 30-60 Hz 39 / 38 ms; 30-250 Hz 29 / 36 ms.
- Per-trial tiers by unit (tSSS): en 58 brainstem, 24 low (S002, S005, S009); ru 20 brainstem (S004, S008, S012,
  S014, S015), 4 mlr (S010), 36 low. Raw: en 4 low (S001), 78 none; ru 4 low, 56 none.
- Raw 30-60 / 30-250 Hz TRFs: periodic ripple at all lags (10-20 ms GFP period), nothing above the null in the
  windows; gone after tSSS. cHPI check (sub-002 trial 1, 120 s): cHPI band < 0.1% of the 30-250 Hz power (raw and
  tSSS), filtering it changes the rms by <= 3.4%; 50 Hz harmonics 99.5% raw, 28% (en) / 35% (ru) after tSSS ->
  ripple most likely mains (not verified).
- No mismatch null (one stimulus per site; `p_mismatch` None). Russian sanity flags: 42 flat channels = the FIF bads
  (all zero); 12 duration flags = truncated presentations > 1 s short.
- Coherence (`/data_storage/gu08wuvu/datasets/tmp/review/coherence_batch/{128,native}/yang2026_{en,ru}.json`, raw
  data): ratios ~1 (en 0.83-1.54 below 60 Hz, 1.04-1.16 above; ru 1.09-1.85 at 128 Hz, NaN at native rate, not
  investigated). tSSS coherence on 4 participants per site: `coherence_batch/native/yang2026_{en,ru}_tsss.json`
  (running at the time of writing; numbers to be added to the README).
- Provenance: `validation_tier="brainstem"` + `validation_note` (VALIDATION_NOTE in `adaptor.py`) in every trial.

## 12. Flat MEG channels not marked in the FIF (2026-11-22)
A scan of all 60 Russian pilot trials found 43 constant MEG channels; 37 are in the FIF bads, 6 are not:
sub-11 MEG0233 (trials 3-4) and sub-12 MEG2042 (trials 1-4), constant non-zero values (std 0 in the stored float32).
The adaptor now adds MEG channels whose std is below 1e-6 x the median std of their type (mag/grad) to `info["bads"]`
and lists them in the sidecar (`bads_added_flat`); the drift interpolation leaves ~1e-22 numerical ripple on a
constant channel, so an exact-zero test misses them. Found because the raw Russian coherence was NaN (the repo
validator then kept bad channels in its picks; fixed in `cnsp_datasets/validate/load.py`, 75b48d4).

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
- yang2026_en: **good**: Onset fitted per presentation on the audio copy (MISC006/007; 18.7 ms after software code 3); drift +538 ppm from the audio copy corrected; +7.3 ms tube delay assumed; brainstem (tSSS).
- yang2026_ru: **good**: Onset fitted on the audio copy MISC005 (9.1 ms after code 3); drift -0.73 ppm corrected; +7.3 ms tube delay assumed; brainstem (tSSS); EEG not validated.
