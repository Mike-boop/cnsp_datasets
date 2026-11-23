# karunathilake2023: clear and noise-vocoded audiobook passages (MEG)

MEG while young native English speakers listen to 36 short passages (17.5-26.5 s) of the audiobook *The Botany of
Desire* (Michael Pollan, male narrator), each presented three times: as 3-band noise-vocoded speech, as the
original clear speech, and as the same vocoded speech again. Clarity ratings (0-5) after every vocoded presentation.
Inserted earphones, diotic. English.

- **Main study (27 participants):** PRE (vocoded), CLEAN, POST (vocoded, now primed by the clean version).
- **Control study (12 participants):** PRE1 (vocoded), PRE2 (vocoded), CLEAN (no priming before the second
  vocoded presentation).

> **Raw sensor MEG with the played audio.** Onsets come from the stimulus triggers (no audio copy in the
> recording), and no drift correction is possible or needed for these short trials. The high-frequency tiers pass
> for clear speech; vocoded speech carries little 30-250 Hz response by construction.

- **Source:** Dryad doi:10.5061/dryad.sbcc2frd6 (2023). **Licence: CC0.**
- **Paper:** Karunathilake IMD, Kulasingham JP, Simon JZ (2023). Neural tracking measures of speech intelligibility:
  manipulating intelligibility while keeping acoustics unchanged. *PNAS* 120(49):e2309166120.
  doi:10.1073/pnas.2309166120
- **Code (authors):** Eelbrain pipeline (`exp.py`) in the Dryad record.

## Size
**39 participants, 108 trials each (4212 trials), 0.666 h per participant (all identical), 26.0 h in total**
(main 18.0 h, control 8.0 h). Per condition 13.3 min per participant. Unique audio: 36 passages, 13.3 min, each as
clear and as vocoded (the vocoded file is replayed unchanged).

## What is provided
- **MEG:** KIT 157-channel whole-head system (University of Maryland): `MEG 001-157` axial gradiometers (MNE type
  `mag`, in T) and 3 reference magnetometers (`ref_meg`, for optional denoising). Recorded at 1000 Hz with an online
  200 Hz low-pass and a 60 Hz notch; stored at **1000 Hz**. No EEG, EOG or ECG. The 32 MISC lines (trigger and idle
  lines, no audio copy) and `STI 014` are dropped. Head digitisation is in the FIF.
- **Bad channels** are in `info['bads']`: channels whose rms is below 1/20 of the median (MEG 086 in
  all but one participant, MEG 056 in most). `pick('mag')` alone keeps them. R2851 MEG 062 is ~6x noisier than its
  neighbours but not flat, and is not marked.
- **Stimulus** per trial: the played wav (44.1 kHz, as shipped): `split{k}_vocoded` for vocoded trials, `split{k}`
  for clear trials. The vocoded wavs clip at full scale in ~1e-4 of samples (as played). No transcripts or word
  times are shared.
- **Trials** 1-108 in presentation order. Conditions: `pre`, `clean`, `post` (main) and `control-pre1`,
  `control-pre2`, `control-clean` (control).
- **Subjects** are numbered by the R-number modulo 1000 (R2684 -> 684; R3009 -> 9, R3015 -> 15) because the format
  takes three-digit subject numbers; the R-number is in the trial metadata (`participant`).
- **Trial metadata** (`raw.info["description"]`, JSON): `participant`, `study`, `passage`, `presentation`,
  `trigger_code`, `onset_s`, `stimulus_file`, `vocoded`, `clarity_rating` (vocoded trials), `q2_as_shipped`
  (column Q2 of the rating sheets, undocumented, probably the comprehension question), `in_authors_pool` and
  `in_authors_main_analysis` (subject lists in the authors' code: R2383 and R2806 are in neither; R2813 and R2891
  are in the pool but not in the 23 analysed main participants; R3015 is not in the pool).
- Not exported: empty-room recordings, the authors' coregistration (`-trans.fif`, `mri.zip`), TRFs and ratings
  tables (behaviour is in the trial metadata).

## Alignment
- **Trigger onset (`sw_trigger`).** Each trial starts at its passage-onset trigger (164 PRE/PRE1, 165 CLEAN,
  166 POST/PRE2; TTL lines from the Presentation software). The trial length is the wav length. No offset triggers
  exist.
- **Latency to sound and tube delay: unknown** (no audio copy). The TRF latencies match brodbeck2022 (same lab,
  system and software): low-frequency peak ~110 ms, clean-speech 30-250 Hz response onset ~18-20 ms, peaks ~33-38
  ms.
- **Drift: not measurable, not corrected** (trials <= 26.5 s: < ~1 ms for typical clocks).

## Validation
Repo validator, good gradiometers, no re-referencing. Control study (12 participants): **brainstem tier**
(pooled): low median r 0.040, 12/12 participants significant; 30-250 Hz SNR 1.29 (p 0.01, 9/12); for clear speech
alone SNR 1.45 (10/12). Vocoded conditions pass the low tier only. Main study (pilot, 4 participants): brainstem
tier pooled (low median r 0.032, 4/4; 30-250 Hz SNR 1.70, 4/4; clear speech alone 2.11). Details in `notes.md`.

## Caveats
- Paper N: 25 main (23 analysed) + 12 control; 27 main participants are shipped.
- POST/PRE2 replay the PRE file, so the same audio occurs twice per passage; cross-validation over trials should
  hold out passages, not presentations, when this matters.
