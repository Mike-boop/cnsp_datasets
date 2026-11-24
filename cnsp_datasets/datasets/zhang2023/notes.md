# zhang2023: NJU auditory attention detection dataset (Emotiv EPOC Flex, Zenodo 7253438): DECISION NEEDED

Explorer notes (2026-11-24). Scratch: `/data_storage/gu08wuvu/datasets/tmp/review/zhang2023/` (temporary:
`agent_log.md`, `*.log`, `figures/`). One-off scripts: `tmp/review/scripts/zhang2023/` (`expinfo_lib.py` decodes
the MATLAB `table`/`string` objects with h5py; `exact_bounds.py`, `quick_trf.py`, `xcorr_scan.py`,
`pertrial_scan.py`).

**Outcome: there is continuous speech, the audio is shipped and the trial mapping is unambiguous, but the shipped
EEG does not track the speech envelope in 17 of 21 subjects at any lag within ±10 s. This holds pooled over trials
and per trial. A brain-based alignment is not feasible either: a per-trial scan has no power at this SNR. The other 4 (S18-S21) track weakly, with
late peaks (250-450 ms). No adaptor has been written; the options are in section 8.**

## 1. Source
- Zenodo 7253438 (doi 10.5281/zenodo.7253438), "Auditory Attention Detection Dataset Nanjing University", Zhang
  Y., Yuan Z., Lu J. (Key Laboratory of Modern Acoustics, Nanjing University), published 2022-10-26, CC BY 4.0.
- Paper: Zhang Y, Ruan H, Yuan Z, Du H, Gao X, Lu J (2023). A learnable spatial mapping for decoding the
  directional focus of auditory attention using EEG. ICASSP 2023, doi:10.1109/ICASSP49357.2023.10096819
  (`data_campaign/papers/zhang2023.pdf`, section 3.1-3.2). The record also lists ISCSLP 2024
  (10.1109/ISCSLP63861.2024.10800020) and TNSRE 2025 (10.1109/TNSRE.2025.3591819) as users of the data.
- Code: github.com/NCALab/learnable_spatial_mapping (direction classification only; not read). `script.zip` has
  MATLAB slicers (`sliceTo2d_NJU.m` etc.) for 1-10 s decision windows. It uses subject IDs 2-27 and only the first
  24 ("steady") trials for subjects ≤ 20, so the release appears renumbered. It also ships a stray
  `__pycache__/Utils_Bashivan.cpython-37.pyc`, which was not run.
- Files: `NJUNCA_preprocessed_arte_removed.zip` (10,963,167,735 B) and `script.zip` (6,664 B). Copied from woody's
  Zenodo copy; md5 matches `MD5SUMS` (`md5_local.txt`). No vault backup has been made yet (Zenodo dataset: due if
  incorporated).
- Not in the dev registry before this note; entry `zhang2023` added with it.

## 2. Layout
`NJUNCA_preprocessed_arte_removed/S01.mat` … `S21.mat` (MATLAB v7.3/HDF5, 0.1-0.74 GB each). Each has:
- `data.eeg{t}`: 32 × N float32 per trial, `data.dim.eeg = 'time_chan'` (stored chan × time in HDF5),
  `data.fsample.eeg = 128`;
- `data.leftWav{t}`, `data.rightWav{t}`: 1 × 125·N float64 at 16 kHz;
- `data.leftEnv{t}`, `data.rightEnv{t}`: the authors' envelope at 128 Hz (correlates 0.86-0.89 with
  |hilbert|^0.6; not needed);
- `data.recordWav{t}` (S01-S15 only): 4 × 1,840,000 (115 s at 16 kHz). Two microphone positions, each
  duplicated (channels 0/1 and 2/3 correlate 0.99). It is a room recording of the mixed scene (both talkers
  match it, r ≈ 0.2-0.5) on its own time base, with no link to the EEG clock;
- `data.event.{eeg,leftWav,rightWav}`: sample 1 and the attended label (`string` object) or the azimuth of each
  stream;
- `expinfo`: a MATLAB `table` (MCOS) with `attended_lr`, `l_audio`, `r_audio`, `azimuth`.
  - `pymatreader` cannot read it. `expinfo_lib.py` parses `#subsystem#/MCOS`: region 3 maps object id to a
    property block, a value is a cell index minus 2, and strings are uint64 [ver, ndims, dims, lengths, UTF-16].
  - The table's `attended_lr` equals the per-trial `event.eeg.value` in every subject where both exist.

## 3. Stimulus ↔ trial mapping
- **Pool:** 33 Mandarin news recordings `eeg_01..33_mono.wav` (male and female professional anchors), 115 s
  each with speech to 85-115 s (silence after). The shipped wavs are bit-exact copies of the sources: chunks match
  the unspliced copies in S06 at r = 1.0000.
- **Protocol A (S01-S15):** 16 pairs × 2 = 32 trials. Each pair is played twice in a row, attending
  `l_audio` once and `r_audio` once. "left/right" means stream 1/2, not the side.
  - Trials 1-24 are static, from 14 azimuths (±15…±135°). Some pairs are on one side (e.g. 30/60°), and S01
    trials 7/8 have both talkers at 0°.
  - Trials 25-32 have moving talkers: `azimuth` is a 5-point trajectory, e.g. [-90 -45 0 45 90].
- **Protocol B (S16-S21):** static symmetric ±30/45/60/90° only, no `recordWav`.
  - S17 has 28 trials; its pairs 19/20 are not repeated.
  - S18 trials 9 and 22 are empty (no EEG).
- The pair order and the attended order differ per subject. Each subject hears 30-32 of the 33 stimuli.
- **Trials are the authors' artefact-cleaned concatenations** ("manually remove the residual abnormal EEG
  segments"). Lengths are 10-110 s in 10 s steps: 4 trials of 0 or 10 s, the rest 20-110 s.
  - EEG and both wavs were cut together. Mapping each wav to its unspliced source gives sample-exact
    pieces, and all 146 splice points tested (S01, S02, S16, S17) lie on one 125-sample grid (≡ 61 mod 125,
    i.e. EEG-sample boundaries).
  - The EEG has a one-sample discontinuity exactly at those points: mean |ΔEEG| is 3.5× the median at lag 0 and
    1.1× elsewhere; 58% of splices are individually > 3× (`figures/eeg_jump_at_audio_splices.png`).
  - So within each trial, EEG piece j belongs with audio piece j. Each piece is contiguous in the source but
    jumps by 0.02-60 s at the splice. Pieces range from 0.5 s to the whole trial: S01 trial 3 has 7, S16 trial 4
    has 1, S01 trial 13 about 25.
  - Some trials end in the source's silent tail.
- **S06 trials 1-10 are different:** unspliced 115 s, no events, and **not artefact-cleaned** (SD 25-72 µV,
  peaks up to 0.96 mV, against ~10 µV in its trials 11-32).
- `expinfo` of S01 has 4 empty rows (33-36); they are ignored.

## 4. Speech features
- Raw audio: the two talkers as separate mono 16 kHz wavs (float64, |x| ≤ ~0.2), cut per trial as above. The
  spatial rendering through the loudspeaker array is not shipped. The full 115 s sources can be rebuilt exactly:
  S06 trials 1-10 give 10 of them whole, and the union of pieces across subjects gives the rest.
- The authors' 128 Hz envelopes are not needed. There are no transcripts or word timings.

## 5. Neural data
- Emotiv EPOC Flex Saline, 32 channels. Order as in `data.dim.chan.eeg`: Cz Fz Fp1 F7 F3 FC1 C3 FC5 FT9 T7 CP5
  CP1 P3 P7 PO9 O1 Pz Oz O2 PO10 P8 P4 CP2 CP6 T8 FT10 FC6 C4 FC2 F4 F8 Fp2 (the same list in every file).
  - No EOG, mastoid or peripheral channels.
  - The Emotiv CMS/DRL reference positions are not documented.
- **Preprocessed, not raw** (paper 3.2, EEGLAB):
  - 1-32 Hz band-pass, resampled to 128 Hz (the native rate is unknown);
  - channels with outlying PSD removed, ICA artefact removal, then removed channels interpolated;
  - abnormal segments removed (the splices).
- Not average-referenced: the channel sum is 10-23× a channel SD.
- Units: µV (channel SD 5-15 µV in cleaned trials); read × 1e-6 into V.
- No digitisation; template 10-20 positions apply.
- Interpolated channels are not listed, so bads are unknown.

## 6. Alignment
- **No trigger information is shipped**: trials are already cut and the raw recordings are not released. Emotiv
  systems take software markers (EmotivPRO/LSL). The paper says nothing on synchronisation, so the onset source
  is **unknown (probably software)**. There is no stimtrack; `recordWav` is not on the EEG clock. Drift cannot be
  measured (trials are cut, and 128 Hz).
- **Validation of the shipped timing, all 21 subjects** (0.5-8 Hz, average reference, envelope |hilbert|^0.6):
  - **Forward TRF**, leave-one-trial-out, lags -0.3…0.6 s (`figures/quick_trf_per_subject.png`, `quick_trf.log`):
    - S01-S17: attended r = -0.009…+0.005 (mean ≈ 0), attended > ignored in 10-18 of 28-32 trials (chance), no
      TRF structure;
    - S18-S21: r = 0.021 / 0.039 / 0.015 / 0.017, attended > ignored in 19/25, 18/28, 21/31, 17/32 trials. GFP
      peaks at 429 / 414 / 593 (edge) / 250 ms; S19 and S21 have clear structure.
  - **Pooled cross-correlation, ±10 s** (`figures/xcorr_scan_per_subject.png`, `xcorr_scan.log`):
    - S01-S17: maxima scattered from -7.6 to +8.0 s at 1.8-3.3× the median, i.e. noise. A constant onset
      offset of up to 10 s, common to all trials of a subject, is therefore excluded; it would show as a peak.
    - S18-S21: peaks at +0.45, +0.42, +0.27, +0.26 s (2.6-4.8×).
  - **Per-trial scan, ±10 s, matched vs mismatched envelope** (`figures/pertrial_lag_scan.png`,
    `pertrial_scan.log`): the median peak z is 3.82 matched vs 3.74 mismatched (S01-S17) and 3.73 vs 3.82
    (S18-S21). The fraction of peaks within ±1 s is the same as for mismatched envelopes. The test has no power
    at this SNR: it finds nothing even in S18-S21, which do track when pooled. So per-trial random onsets (e.g.
    software markers) can be neither excluded nor estimated, and a brain-based per-trial onset estimate
    (`align/scan.py`) is not feasible.
- Possible causes, not distinguishable from the release:
  - per-trial software-marker errors (random per trial, which pooling washes out), or a wrong pairing at the authors' end;
  - the cleaning (ICA plus heavy segment removal) removing the auditory response;
  - a low-SNR consumer saline headset in a loudspeaker room.

  Direction-of-attention decoding, the authors' use, relies on spatial and alpha features and does not need
  envelope timing.
- Even S18-S21 peak 0.25-0.45 s, later than the usual ~0.1-0.2 s envelope peak. This fits a software marker
  leading the sound by ~0.1-0.3 s.

## 7. Cross-subject duration check
Not possible: no triggers or recording-length information, and every trial was cut by the authors. The shipped
wav and EEG lengths match exactly (125 audio samples per EEG sample) in every trial.

## 8. Options (decision needed)
1. **Do not incorporate (recommended).** Preprocessed 128 Hz data with authors' splices, unknown onset source,
   and the shipped timing fails the low tier in 17/21 subjects with no recoverable offset. It would get the
   `discarded` tab with this note.
2. Incorporate **S18-S21 only** (1.8 h): grade `medium` at best, if the full low tier passes. Their late peaks
   (250-450 ms) suggest an uncorrected software lead, which may push the grade to `poor`.
3. Incorporate everything as shipped, flagged as failing validation. This goes against PLAN.md section 3: no
   grade fits, since `medium` needs a passing validation and `poor` needs a brain-based estimate, which is not
   possible here.

If incorporated (options 2 and 3), the proposed design is:
- one record per shipped trial, with the EEG in V at 128 Hz (no resampling; native ≤ 1024);
- two stimuli per trial, the shipped spliced wavs named `S<ss>_t<tt>_<l|r>_<eeg_NN>`, since `data_fn` must depend
  only on the name. The alternative, rebuilt 115 s sources plus one record per contiguous piece, would give many
  short pieces;
- condition `attend-<stream>-<static|moving>` with azimuths in provenance;
- S06 trials 1-10 kept but flagged as uncleaned, S18 empty trials skipped, and the splice list (piece starts) in
  provenance;
- `expinfo` decoded with the `expinfo_lib.py` logic ported into the adaptor.

## 9. Size
- Shipped (cleaned) EEG: 13.8 h in total, 21 participants, mean 39.5 min each (21-52 min); S18-S21 1.8 h. This
  counts the trial durations, so the spliced-out time is excluded.
- Output if incorporated: EEG ≈ 0.2 GB; stimuli at 16 kHz float32 for 2 streams ≈ 6 GB (fewer if deduplicated).
- Scratch now: `R/zhang2023` = 21 GB (zip 11 GB plus extracted 11 GB).

## 10. Overlap
- zhang2025 (Zenodo 17393865, NJU cEEGrid AAD) is the same lab but a different system and recording. Participant
  overlap is unknown.
- The IEEE DataPort "NJU auditory attention decoding dataset" named in the repo README is probably a related
  release. It was not checked.
- No other dataset uses these Mandarin news stimuli.

## Upstream issues
- `expinfo` is stored as a MATLAB `table` with `string` columns, which is unreadable outside MATLAB.
- S06 trials 1-10 are uncleaned and full-length, unlike the rest.
- S18 trials 9 and 22 are empty; S17 has 28 trials.
- The S01 table has 4 empty rows.
- Trials are spliced without boundary markers.
- `script.zip` contains a compiled `.pyc`.
