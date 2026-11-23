# karunathilake2025: noise, nonwords, scrambled words and narrative passages (MEG)

MEG while 30 young native English speakers listen to 1-min synthesised (gTTS, US English male voice) passages of
four types: **speech-envelope-modulated noise**, **nonwords** (English-like pseudowords), **scrambled words** and a
**narrative** (excerpts of *The Botany of Desire*, M. Pollan, in story order). Four passages per type, each played
twice in a row: 32 trials per participant, in four blocks of one passage per type. Inserted earphones, diotic.

> **Raw sensor MEG with the played audio.** Onsets come from the stimulus triggers (no audio copy in the
> recording); drift is not measurable and not corrected. The pilot reaches the brainstem tier pooled (30-250 Hz
> response at ~38 ms); speech-modulated noise passes the low tier only, by construction.

- **Source:** Dryad doi:10.5061/dryad.ht76hdrpf (version 2025-01-31). **Licence: CC0.**
- **Paper:** Karunathilake IMD, Brodbeck C, Bhattasali S, Resnik P, Simon JZ (2025). Neural dynamics of the
  processing of speech features: evidence for a progression of features from acoustic to sentential processing.
  *J Neurosci* 45(11):e1143242025. doi:10.1523/JNEUROSCI.1143-24.2025
- **Code (authors):** Eelbrain pipeline (`exp.py`) and notebooks in the Dryad record.

## Size
**30 participants, 32 trials each (960 trials), 32.3 min per participant (all identical), 16.2 h in total.** Per
condition ~8.1 min per participant, ~4.0 h in total. Unique audio: 16 passages, 16.2 min.

## What is provided
- **MEG:** KIT 157-channel whole-head system (University of Maryland): `MEG 001-157` axial gradiometers (MNE type
  `mag`, in T) and 3 reference magnetometers (`ref_meg`, for optional denoising). Recorded at 1000 Hz with an online
  200 Hz low-pass and a 60 Hz notch; stored at **1000 Hz**. No EEG, EOG or ECG. The 32 MISC lines (trigger and idle
  lines, no audio copy) and `STI 014` are dropped. Head digitisation is in the FIF.
- **Bad channels** are in `info['bads']`: rms below 1/20 or above 30x the median (MEG 056 everywhere, MEG 086
  flat in all participants but R2682, where it saturates). `pick('mag')` alone keeps them.
- **Stimulus** per trial: the played wav (22.05 kHz, as shipped), named after the passage (`AS_M01` narrative,
  `ASM_M01` scrambled, `PH_M01` nonwords, `ASN_M01` noise, ...). Transcripts (also of the speech behind each noise
  passage) and the authors' predictors are in the download, not in the standardised data.
- **Trials** 1-32 in presentation order. Conditions: `noise`, `nonwords`, `scrambled`, `narrative`. The order is
  the same for every participant.
- **Subjects** are numbered by the R-number modulo 1000 (R2383 -> 383, R2682 -> 682) because the format takes
  three-digit subject numbers; the R-number is in the trial metadata (`participant`).
- **Trial metadata** (`raw.info["description"]`, JSON): `participant`, `passage_type`, `passage` (1-4),
  `repetition` (1-2), `block` (1-4), `trigger_code`, `onset_s`, `stimulus_file`.
- Not exported: empty-room recordings, behavioural answers, the authors' predictors and TRFs.

## Alignment
- **Trigger onset (`sw_trigger`).** Each trial starts at its passage-onset trigger (codes 164-180, one per passage;
  TTL from the stimulus PC). The trial length is the wav length. No offset triggers exist.
- **Latency to sound and tube delay: unknown** (no audio copy). TRF latencies match karunathilake2023 and
  brodbeck2022 (same lab, system and software).
- **Drift: not measurable, not corrected** (trials <= 62.5 s: ~1-3 ms for typical clocks).

## Validation
Repo validator, good gradiometers, no re-referencing, pilot of 3 participants: **brainstem tier** pooled (low median
r 0.054, 3/3 participants significant; 30-250 Hz SNR 1.28, p 0.01, 3/3). Narrative alone also reaches brainstem;
nonwords and scrambled pass the low tier (30-250 Hz significant, 30-60 Hz not); noise passes the low tier only.
Details in `notes.md`.

## Caveats
- Each passage is played twice back to back, so cross-validation over trials should hold out passages, not
  presentations.
- R2383 and R2684 also took part in karunathilake2023 (different sessions and stimuli).
- Three recordings (R2693, R2740, R2778) were concatenated from several runs by the authors (boundary annotations);
  no trial spans a boundary.
