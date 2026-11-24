# kulasingham2020: high-gamma TRFs in younger and older listeners, KIT MEG, two 60 s stories in quiet (DRUM)

Explorer notes (2026-11-24); adaptor, full standardisation and validation the same day (sections 10-11). Scripts: `tmp/review/scripts/kulasingham2020/` (named per finding); outputs and
figures in `tmp/review/kulasingham2020/` (`survey_{younger,older}.tsv`, `submap_{younger,older}.tsv`, `figures/`).
**User decision (2026-11-24): separate dataset**, all 40 participants by default; option `subjects="unique"` keeps
only the 8 not in presacco2016; the map in `subject_map.tsv` and the sidecar (`overlaps_with`); denoised flag in
the sidecar and README; the defaults of section 9 (onset edge, 6 x 60 s, drift documented only, MISC dropped, bads
as in question 4, no licence stated).

## 1. Source
- DRUM (University of Maryland) item `da9293b8-cc3c-4965-8b4f-dd1bc91daca5`, hdl 1903/25332, DOI
  **10.13016/33pk-ltqh**, "High gamma cortical processing of continuous speech in younger and older listeners -
  Dataset" (Kulasingham 2019a in the paper).
- Licence: **none stated** (no `dc.rights`), as for presacco2016 and kulasingham2021.
- Paper: Kulasingham JP, Brodbeck C, Presacco A, Kuchinsky SE, Anderson S, Simon JZ (2020) NeuroImage 222:117291
  (`data_campaign/papers/kulasingham2020.pdf`).
- Authors' code: github.com/jpkulasingham/highfreqTRF (`boostTRF.py`; read, not run; copy in
  `tmp/review/kulasingham2020/authors_code/`). It reads the lab's denoised `<subj>_Q{H,L}myF.sqd`, takes KIT stim
  channels 163-175 (0-based) as triggers, drops code 163 (end) and epochs from the onset events.
- Files (ORIGINAL bundle, 13 files): `readme.txt`, `bad_channels.txt`, `stimuli.zip` (212 MB),
  `younger_meg.z01-.z03 + .zip` (5.02 GB), `older.z01-.z03 + .zip` (6.85 GB), and two forward-model zips
  (`ico-4.zip` 1.77 GB, `vol-7-cortex_brainstem_full.zip` 0.26 GB) that the registry excludes. Needed: 12.08 GB.
- Download (2026-11-24): registry `download_dataset("kulasingham2020", ...)`, 1 worker, read timeout 300 s, no
  errors (~30 min). **All 11 files match DRUM's size and md5** (`integrity.tsv`, listing `drum_listing.json`).
  `readme.txt` and `bad_channels.txt` (504 on 2026-11-23) came through.
- **Split zips.** `younger_meg` and `older` are 4-volume Info-ZIP split archives with Zip64 end records. Python's
  zipfile refuses multi-disk archives, and Info-ZIP 3.0 `zip -s 0` produced a truncated joined archive in a test,
  so `download_helpers.extract_archives` streams the volumes (`.z01`, `.z02`, ..., `.zip`) into `bsdtar -f -`
  (libarchive), after the usual listing check (no absolute or `..` entries). `download_dataset(..., extract_archives=True)`
  therefore unpacks this dataset with no extra step; `extract_archives(dir, keep=True)` keeps the zips. A missing
  volume is an error. The review copy was extracted with the same helper into `meg_x/` (zips kept).
- **Vault backup** (DRUM rule, 2026-11-24): `download/` (all 11 files + `download_log.tsv`), `integrity.tsv`,
  `drum_listing.json`, `backup_manifest.tsv` (path, size, md5) in `csnhr:/home/vault/iwpm/iwpm104h/kulasingham2020/`;
  14/14 files checked with `stat` (`backup_verify.txt`; script `tmp/review/scripts/kulasingham2020_backup.sh`).

## 2. Layout
- After extraction: `Volumes/JOSHUA/Drum/JNeuroImage/Dataset/MEG_data/{Younger,Older}_MEG/<Group>_<R####>_Trial{1,2}-raw.fif`
  (the zips store the author's absolute path without the leading `/`). 34 younger + 46 older = **80 fifs**, one
  per subject and story block, 216-286 s each (5.57 h in total).
- `stimuli/Trial1.wav`, `Trial2.wav` (44.1 kHz mono int16, 2,646,000 samples = 60.000 s) and
  `Trial{1,2}-audspec-1000.mat` (auditory spectrograms at 1 kHz, model-derived: off by default, not needed), plus
  `__MACOSX/` resource forks (ignore).
- `bad_channels.txt`: `R####,Trial#,ch,ch,` per block, **1-based MEG numbers** (R1801 105 and R2256 56 are the
  all-zero channels of those files).

## 3. Stimulus <-> trial mapping (verified)
- Readme: Trial 1 = 3 repetitions of `Trial1.wav` (trigger code 166 start, 163 end); Trial 2 = 3 repetitions of
  `Trial2.wav` (171 start, 163 end). Paper: two 60 s passages of The Legend of Sleepy Hollow (male talker) in
  quiet, each repeated three times, 6 min per subject; silent word counting for attention.
- **`Trial1.wav` and `Trial2.wav` are byte-identical to presacco2016's `Quiet_H.wav` and `Quiet_L.wav`** (md5
  589f9ce4... / 52a0b8de..., CRC32 cb8baf28 / 61e84a27; presacco's copies from the vault).
- Every one of the 80 fifs has exactly 3 onset edges on its trial's line and 3 offset edges (`survey.py`).
- Subjects: 17 younger (R1801, R2079, R2085, R2130, R2135, R2148, R2153, R2185, R2196, R2201, R2217, R2223,
  R2230, R2244, R2246, R2256, R2281), 23 older (R0840, R2083, R2084, R2086, R2092, R2093, R2094, R2107, R2145,
  R2154, R2197, R2210, R2247, R2254, R2263 and the new R2338, R2342, R2354, R2363, R2396, R2408, R2409, R2428).
  Paper: younger 18-27 y, older 61-78 y, all clinically normal hearing.

### Subject map to presacco2016 (verified)
The block-length fingerprint (fif length vs presacco's `samples`, `R/listing_check_nonzenodo.md`) matches 28 subjects
one-to-one and leaves two ambiguous pairs. These were resolved from the data (`submap.py`): each fif's three
onset-locked 60,000-sample epochs (cut from one sample before the edge, presacco's convention) vs presacco's Q_H /
Q_L epochs, mean per-channel r over MEG 001-157. The right pairs give **r 0.98-1.00 in all 6 epochs**, the swapped
ones -0.03..0.04 (`figures/subject_map.png`). Controls S01 and S21 likewise 0.99.

| kulasingham2020 | presacco2016 | how |
|---|---|---|
| Younger R2130, R2135, R1801, R2148, R2085, R2153, R2196, R2185, R2079, R2217, R2223 | Younger S01-S11 | block lengths (R2130 = S01 also by correlation) |
| Younger R2201, R2244 | Younger S12, S14 | correlation (r 0.993 vs 0.02) |
| Younger R2230, R2246, R2256, R2281 | Younger S13, S15, S16, S17 | block lengths |
| Older R2092, R0840, R2086, R2145, R2154, R2197, R2210 | Older NH S21, S22, S24, S25, S26, S27, S28 | block lengths (R2092 = S21 also by correlation) |
| Older R2084, R2093 | Older NH S23, S29 | correlation (r 0.992 vs 0.00); R2084's listed bads 111, 146 (+ zero 099) = S23's zero channels |
| Older R2107, R2247, R2083, R2254, R2263, R2094 | Older NH S30-S35 | block lengths |
| Older R2338, R2342, R2354, R2363, R2396, R2408, R2409, R2428 | none (new; recorded 2016-05 to 2017-05) | |

- Trial1 = Q_H and Trial2 = Q_L throughout (onset lines and wavs agree). None of presacco's 14 hearing-impaired
  subjects are here. presacco2016's other conditions (8 noise blocks) are not in this release.
- Zero-channel consistency: presacco S03 105 = R1801 105; S16 56 = R2256 56; S32/S34/S35 56 = R2083/R2263/R2094 56;
  S23 99/111/146 = R2084 (111, 146 listed; 099 zero in Trial1 only).

## 4. Speech features available
- Raw audio (the two quiet foregrounds, same as presacco2016). No transcripts or word alignments. The audspec mats
  are a model representation (off by default).

## 5. Neural data
- KIT 157-channel axial gradiometers (UMD), MNE `-raw.fif`, **1000 Hz, float32, units T** (MEG SD median 95-473 fT
  per block; reference magnetometers T; MISC lines in V, 5 V idle, active-low TTL). `info`: lowpass 200 Hz,
  highpass 0, `meas_date` set (2014-09-26 to 2017-05-10), no subject info.
- Channels (193): MEG 001-157 (`mag`, KIT_GRAD), MEG 158-160 (`ref_meg`, KIT_REF_MAG), MISC 001-032 (`misc`),
  STI 014 (`stim`, synthesised: 0, 163 and 166 or 171).
  - MISC 004 (163 0-based) = offset line, MISC 007 (166) = Trial1/Q_H onset, MISC 012 (171) = Trial2/Q_L onset:
    the same lines as presacco2016 (1-based 164, 167, 172).
  - MISC 001: low for the whole recording in 12 subjects (recording gate), no events. MISC 002, 018, 030-032:
    low-level noise; **no audio copy** (envelope |r| <= 0.045 at any lag +-2 s, `misc_audio.py`). The rest are
    constant.
- **Preprocessed, not raw** (readme and paper 2.2): saturating channels excluded, then TSPCA (reference-channel
  regression) and SNS. Confirmed: the values are not integer ADC steps (94-100 % non-integer in MEG 001, presacco's
  raw epochs are integer steps), and against presacco2016's raw epochs of the same subjects r ~0.99 with the
  difference 15-24 dB below the raw power in every band and **no time shift** (r peaks at lag 0 of +-10 samples,
  symmetric; `denoise_vs_raw.py`, `figures/denoised_vs_raw_R2130_S01.png`). So mild denoising, timing untouched.
- Sensor geometry: channel positions/orientations in KIT device coordinates (two calibration variants: 12
  subjects from 2014-09/10, 28 from 2015-03 on); `dev_head_t` identity, no digitisation/head shape, no fiducials.
  (presacco2016 ships no geometry at all: these fifs could supply its open question 6 for 32 subjects.)
- Bad channels:
  - `bad_channels.txt` (1-based): MEG 056 in 13 subjects (R2083, R2094, R2254, R2256, R2263 and all 8 new
    ones), R1801 105, R2084 111 146; the listed channels are all-zero in the fifs.
  - Unlisted: R2084 Trial1 MEG 099 all-zero; R2281 MEG 056 near-flat (SD < 5 % of median; presacco S17 has 056
    zero).
  - **SNS refills dead channels.** Channels all-zero in presacco2016's raw quiet blocks carry signal here
    (reconstructed from neighbours) and are not listed: R2185 (S08), R2079 (S09), R2230 (S13), R2210 (S28) MEG
    062; R2201 (S12) MEG 062, 157; R2254 (S33) MEG 001, 002; R2084 (S23) Trial2 MEG 099. Not detectable from these
    files alone (presacco `explore/survey.tsv`, `zero_ch` of the Q_H / Q_L files).
  - Noisy block: R2254 Trial1 median SD 473 fT (twice its Trial2 and the cohort).

## 6. Alignment
- Onset: falling edge of MISC 007 (Trial1) / MISC 012 (Trial2) = STI 014 codes 166 / 171; offset: MISC 004
  (163). 4-6 sample active-low pulses. Same hardware lines, system and stimuli as presacco2016.
- Hardware vs software: **unknown** (neither paper says how the triggers were generated). No audio copy.
- Proposed: **t = 0 at the onset edge**, one 60 s trial per repetition (3 per block, 6 per subject) cropped from
  the continuous file with `simon_base.common` (`read_raw`, `stim_events`, `crop_meg`); stimuli not cut. Equivalent
  to presacco2016's onset (its epochs start one sample before the same edge; the fif segments equal presacco's
  epochs at lag 0). No tube-delay compensation (E-A-RTONE 3A, length unknown).
- Evidence carried over from presacco2016 for the 32 shared subjects (same recordings, same samples):
  decoder lag 0 +- 10 ms in 459/460 tests, 30-250 Hz TRF peak ~38-40 ms and flat at negative lags (graded
  **medium**, user 2026-11-24). The 8 new subjects need their own validation.

## 7. Cross-subject duration check (all 40 subjects, 240 repetitions)
- Offset edge - onset edge = **59,998 samples in 179, 59,997 in 61** (mean -2.25 ms per 60 s), in every subject
  and both trials (`figures/trigger_interval_per_subject.png`), as in presacco2016 (-2.21 ms). All wavs are 60.000
  s, so drift (-37.5 ppm) and an early end pulse cannot be separated; <= 2.3 ms at the end of a trial. **Not
  applied**, `drift_ppm` null, as in presacco2016.

## 8. Options (user decision)
**(a) Separate dataset `kulasingham2020`** (40 subjects, R-numbers, 6 x 60 s quiet trials each), with the
presacco2016 subject map in the README and the sidecar (`presacco2016_subject: S12`).
- Mirrors the publication and DRUM record (citation, licence status, readme, bad list) one to one; the adaptor is
  small (continuous fif + `simon_base`), and the 8 new subjects come with it.
- Ships what the authors shipped: denoised (TSPCA/SNS) continuous data, with sensor geometry and `meas_date`.
- Cost: 32 subjects x 6 min (3.2 h) duplicate presacco2016's quiet trials (same recordings, mildly denoised).
  Anyone pooling datasets must use the map to avoid counting them twice.
**(b) A second source inside presacco2016** (8 new subjects as new participants, the 32 overlapping quiet blocks
either replacing or duplicating presacco's Q_H / Q_L).
- One dataset per cohort; no cross-dataset duplicates.
- But it mixes raw (presacco's .mat) and denoised (these fifs) data in one dataset, against the "least processed"
  rule; replacing presacco's raw quiet epochs with denoised ones loses information, duplicating them puts two
  versions of one trial in one dataset. The 8 new subjects would have quiet only (6 of 30 trials), and the naming
  differs (presacco's S-numbers vs the user's R-number rule for KIT). The presacco adaptor and its graded validation
  would need re-running.
**Recommendation: (a)**, with the subject map and a `denoised: TSPCA+SNS` note in the README/sidecar, plus a
`same_recording_as` pointer so pooled analyses can drop the 32 overlapping subjects. Separately (small, optional):
use these fifs' KIT device geometry for presacco2016's 32 shared subjects (presacco open question 6).

## 9. Open questions (recommended default in brackets)
1. Structure: (a) or (b), section 8. [(a)]
2. Licence: none stated. [include; "no licence stated", as presacco2016]
3. Onset at the trigger edge, 60 s trials, no drift correction (section 6-7). [yes; grade **medium** proposed,
   to be confirmed by validation, especially for the 8 new subjects]
4. Bads: union of `bad_channels.txt`, all-zero and near-flat (< 5 % median SD) MEG channels per block; also the
   channels dead in presacco2016's raw and SNS-refilled here (section 5, 7 subjects)? [yes to all, that list
   hard-coded in the adaptor with this note]
5. Keep MISC/STI lines? [drop, as presacco2016 and brodbeck2022; trigger facts in the sidecar]
6. Sensor geometry (device coordinates, identity `dev_head_t`): keep as shipped. [yes]
7. Data-size note: 40 x 6 min = 4.0 h of stimulus-locked data (5.57 h recorded); conditions: quiet only
   (`Trial1` = story segment H, `Trial2` = segment L).

## 10. Adaptor and standardisation (2026-11-24)
- `adaptor.py` (`simon_base.common`: `read_raw`, `stim_events`, `rms_bads`, `crop_meg`, `audio_loader`): per
  participant and block, the three STI 014 onsets (code 166 / 171; equal to the MISC falling edges in all 240
  trials) -> trials of 60,000 samples from the edge; trials 1-3 Trial1, 4-6 Trial2, condition `quiet`, session 1,
  subject = R-number. Channels MEG 001-157 (`mag`) + MEG 158-160 (`ref_meg`), T, 1000 Hz, sensor positions as
  shipped. Stimuli `Trial1` / `Trial2` (44.1 kHz float32).
- Bads per block: `bad_channels.txt` + `rms_bads` (rms < median / 20; catches all-zero channels and R2281 MEG 056)
  + `REFILLED` (dead in both of presacco2016's raw quiet blocks, SNS-refilled here; marked in both blocks).
- Sidecar (`onset_only`, trigger type unknown, `drift_ppm` null): participant, age_group, hearing, file, block,
  repetition, onset/offset trigger codes, onset_s, block_recorded (`meas_date`), stimulus_file,
  identical_stimulus (presacco2016 wav), overlaps_with (presacco2016 S-number or null), units, reference,
  preprocessing (denoised: TSPCA + SNS).
- Checks: dry parse 240 trials (48 with `subjects="unique"`); one written trial equals the source exactly (bads
  MEG 062, 157 for R2201); 38.4 MB per trial. Full run (`R/scripts/kulasingham2020/run_all.sh`): 240 trials, 9.4 GB,
  0 errors, ~10 min. A re-parse after the review changes gives the same descriptions and bads (`reparse_check.py`).

## 11. Validation (2026-11-24; `validation.json`, `R/kulasingham2020/validation.png`, `validation/new8/`)
Basis: standardised data, axial gradiometers (`--picks mag`, bads excluded), no re-reference; tiers low, mlr,
brainstem.

| set | low r (sig.) | low p_circ | mlr SNR (p) | 30-250 Hz SNR (p, sig.) |
|---|---|---|---|---|
| all 40 | 0.038 (35/40) | 0.020 | 0.97 (0.23) fail | 1.34 (0.0099, 29/40) pass |
| 8 not in presacco2016 | 0.042 (7/8) | 0.020 | 1.01 (0.16) fail | 1.33 (0.0099, 7/8) pass |

- low-frequency TRF peaks ~60 and ~190 ms; 30-250 Hz TRF a sharp peak at ~40 ms (all) / ~41 ms (new 8), flat at
  negative lags; 30-60 Hz peaks at ~62 ms, outside the 18-45 ms window (as presacco2016: SNR 0.97).
- Validator tier `low` (mlr fails), the 30-250 Hz tier passes as well. Comparable with presacco2016's pilot (low r
  0.035, 30-250 Hz SNR 1.75 over all 10 conditions; quiet only 1.26).
- R2342 (new) is not significant at low; it passes 30-250 Hz.

## Data size (recorded)
40 participants x 6 trials x 60 s = **6.0 min each, 4.0 h in total** (younger 1.7 h, older 2.3 h; the 8 unique
0.8 h). Continuous recordings 5.57 h. Standardised 9.4 GB.

## Upstream issues
- Readme says saturating channels were "removed", but they are present as all-zero channels; SNS refilled
  channels that are dead in presacco2016's raw recordings (7 subjects) without listing them; R2084 Trial1 MEG 099
  zero but unlisted.
- No licence; the zips store an absolute author path (`/Volumes/JOSHUA/...`).

## Alignment grade
**medium**: onset-trigger edges (type unknown), no stimtrack; validation confirms the timing (30-250 Hz TRF peak
~40 ms, flat at negative lags, also in the 8 new participants alone); -37.5 ppm drift-or-early-end documented, not
applied.
