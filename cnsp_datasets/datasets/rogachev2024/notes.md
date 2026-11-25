# rogachev2024: neural tracking of stories in children aged 3-8 (OSF c3agw, CND)

52 Russian-speaking children (31 boys, 21 girls, 3-8 years) listen to three short stories told by one female
speaker while watching muted, story-related videos. 32-channel actiCHamp EEG, shipped as the authors' **preprocessed
CND** files at **500 Hz** (1-15 Hz band-pass, interpolation, ocular ICA, average reference), with the four story
wavs as presented. No raw recordings, no triggers, no stimtrack.

## 1. Source
- OSF project c3agw (https://osf.io/c3agw/, DOI 10.17605/OSF.IO/C3AGW), "Neural Tracking in Children: the TRF
  approach", created 2023-06. 116 files, 4.99 GB; all matched OSF size and md5 (2026-11-24,
  `tmp/review/scripts/rogachev2024/verify_download.py`).
- **Licence: none stated** (OSF `node_license` is empty; no LICENSE file). Public download.
- Paper: Rogachev A, Sysoeva O (2024). Neural tracking of natural speech in children in relation to their receptive
  speech abilities. *Cognitive Systems Research* 86, 101236. https://doi.org/10.1016/j.cogsys.2024.101236
  (`data_campaign/papers/rogachev2024.pdf`).
- Shared code: none. `data_description.docx` (one page) describes the folders; `TRF_all_data.csv` (ID, age in
  months, sex, PLS-5 receptive score, the authors' channel-averaged envelope and semantic-dissimilarity TRF
  prediction r), `TRF_env_all_chans.csv`, `TRF_SD_all_chans.csv` (per channel).

## 2. Layout
- `dataCND/dataParticipant_NP<6 digits>.mat` (MATLAB 5), struct `eeg`: `fs` 500, `data` {n_trials} of
  [n x 31] float64, `chanlocs` (EEGLAB: labels, XYZ, sph), `origTrialPosition` (always 1..n), and `dataType` /
  `deviceName` as MATLAB string objects that pymatreader cannot read (warning on load; not needed).
- `dataCND/dataStim_NP<...>.mat`, struct `stim`: `fs` 500; `stimIdxs` (1..n); `data` {3 x n}: row 1 the envelope
  [n x 2] (stereo), row 2 word-onset impulses (0/1), row 3 semantic dissimilarity at the word onsets; `names` /
  `condNames` again MATLAB strings (unreadable).
- `stimuli/{HG,BW,GD,WB}_audio.wav` (44.1 kHz, stereo, 16-bit; the channels differ slightly, r = 0.99998) and
  `*_text.txt` (Russian transcripts, no punctuation).
- Subject IDs `NP012301` .. `NP122202` (52). The standardised subject number is the digits (`NP012301` -> 12301,
  `sub-12301`); the original ID is in the provenance (`subject_id`).

## 3. Stimulus <-> trial mapping (all 52 children, `scripts/rogachev2024/explore.py`, `check_env.py`)
- `stimIdxs` 1 = HG (hedgehogs, 292.18 s, 659 words), 2 = BW ("Brick and Wax", 182.23 s, 395 words), 3 = GD ("The
  Golden Duck", 337.68 s, 669 words) **or** WB (wombats, 300.79 s, 604 words). Index 3 is told apart by length:
  every EEG trial and every stim feature is exactly round(wav duration x 500) samples long (146088, 91114, 168838,
  150395), and the shipped envelope matches the wav's envelope (below). Word counts = the paper's.
- 37 children heard HG, BW, GD; **7 heard HG, BW, WB** (NP102202, NP102203, NP112201, NP112203, NP112205,
  NP112207, NP112213: the first recruits); 8 heard only HG and BW (NP022311, NP042305, NP112210, NP112216,
  NP112223, NP112224, NP112228, NP112229; "tiredness"). **The paper says six children heard the wombat story**; the
  shipped data have seven (upstream issue, section 9).
- Presentation order: unknown. `origTrialPosition` is 1..n for everyone and the paper gives no order, so the trial
  number is the shipped index (HG, BW, GD/WB).
- The stim features are identical across children (envelopes equal to 1e-6 relative).

## 4. Speech features available
- **Audio as presented** (paper: edited to normalise level and remove silences > 500 ms; 44.1 kHz). The adaptor
  stores the wavs as shipped (stereo, float32).
- In the stim files: the authors' 500 Hz envelope (Hilbert of the audio; correlates 0.88 with our Hilbert envelope
  of the wav downsampled to 500 Hz, at lag 0, in all four stories), manually labelled word onsets (Audacity), and
  word2vec semantic dissimilarity. Not carried: the envelope is redundant with the audio, semantic dissimilarity is
  model-derived (off by default), and the onsets have no word labels (the transcripts' word counts, 672/397/713/
  602, do not match the 659/395/669/604 onsets, so words cannot be paired safely; open question 2).

## 5. Neural data
- Brain Products actiCHamp, 32 channels, recorded at 500 Hz (some at 50 kHz, downsampled to 500 Hz by the
  authors), online reference FCz, impedance < 50 kOhm (paper).
- **Shipped: 31 channels at 500 Hz** (Fp1, Fz, F3, F7, FT9, FC5, FC1, C3, T7, TP9, CP5, CP1, Pz, P3, P7, O1, O2,
  P4, P8, TP10, CP6, CP2, Cz, C4, T8, FT10, FC6, FC2, F4, F8, Fp2), the same for all children. FCz (the online
  reference) is not restored. The paper's "downsampled to 128 Hz" applies to its TRF analysis only. No EOG, no
  mastoids (TP9/TP10 are scalp channels here), no peripherals, no digitisation.
- Preprocessing (paper, MNE 1.5): zero-phase FIR 1 Hz high-pass (-6 dB at 0.5 Hz) and 15 Hz low-pass (-6 dB at
  16.88 Hz); visual inspection; interpolation of bad channels (mean 0.875, range 0-5 per recording); removal of
  1-3 ocular ICA components; re-reference to the average. Which channels were interpolated is not shipped, so
  `info['bads']` is empty.
- **Units: microvolts** (median per-channel SD 7.6-20.8 uV over all trials, plausible for 1-15 Hz child EEG);
  the adaptor scales to V.
- **Reference: average of the 31 channels**: the channel sum is ~0 in every trial (|sum| / mean |x| < 2e-7).
  Data rank is 31 numerically at default tolerance; ICA removal lowers the effective rank further.
- **Channel order verified**: the shipped chanlocs lie within 7 deg (median; max 12 deg, T7) of standard_1020, and
  inter-channel correlation falls with distance (Spearman rho -0.54 to -0.75 in 5 children; 200 random label
  permutations give >= -0.18). The adaptor uses standard_1020 template positions.

## 6. Alignment
- Paper: "Synchronization of the EEG and stimulus was performed by the event marker at the beginning of each audio
  story", played with Presentation over Panasonic RP-HS46E-K headphones (on-ear, no tubes). Whether the marker went
  through a parallel port or a TriggerBox, and whether it was checked against the sound, is not documented;
  markers are not shipped. Treated as **software** (Presentation port code at playback).
- The authors cut each trial from the marker to the story length: EEG sample 0 = wav sample 0. The shipped
  envelope sits at lag 0 against the wav (above), so no offset is hidden in the features.
- **Drift: not measurable.** There is no end marker and the trials are cut to the stimulus length, so trial
  lengths say nothing about clock drift. Over the longest story (338 s), a typical 20-50 ppm sound-card drift would
  be 7-17 ms at the end, well under the 1-15 Hz resolution.
- Adaptor: shipped timing kept, `alignment_method` `onset_only`, no correction, native 500 Hz (no resampling).

## 7. Cross-subject duration check
- Not possible: every trial has exactly the stimulus length by construction (the authors' epochs).

## 8. Validation (2026-11-24, all 52 children, 148 trials)
- Standardised: 148 trials, no failures, 2.7 GB (one trial 18.1 MB). Listening time 10.9 h; 12.6 min per child
  (7.9-13.5).
- `python -m cnsp_datasets.validate rogachev2024 --tiers low --reference average` (`tmp/review/rogachev2024/
  validation.json`, `validation.png`). Only the low tier applies: the data are low-passed at 15 Hz.
- **Low tier passes**: mean r 0.038, median 0.043 (mean over channels); 42/52 children (81 %) above their
  circular-shift null; population p_circ 0.020, p_mismatch 0.048 (the smallest values 50 / 20 nulls allow).
  Population TRF (GFP) rises from ~25 ms and peaks at 125 ms and ~290 ms, nothing above the null at negative lags;
  median per-child peak 156 ms (significant children).
- Our per-child r reproduces the authors' channel-averaged `env_corr` (`TRF_all_data.csv`): Spearman 0.93.
- **Lag sweep** (per trial, `scripts/rogachev2024/offsets.py`, `offsets_per_subject.png`): in significant children
  the median offset is +9 ms (HG), +2 ms (BW), -3 ms (GD); overall median +2 ms, IQR -16..+19 ms, 85 % within
  +-50 ms. Large offsets occur only in children without significant tracking. 4 trials have no offset estimate
  and 4 offsets sit at the +-0.5 s scan edge. The validator's drift estimate (29 +- 100 ppm) is noise at this
  resolution.
- **The 7 wombat children track weakly in every story** (r ~0.01 in HG and BW too; only NP102203 and NP112213 are
  significant; WB offsets +454 and -33 ms). The authors' env_corr is just as low for them (-0.008..0.038 vs median
  0.05 for the others, Mann-Whitney p = 0.0005), and they are younger (median 54 vs 69 months; r rises with age,
  Spearman 0.37, p = 0.006). This is read as a property of these children, not a WB-specific onset error: their
  HG/BW offsets scatter in both directions rather than sharing one shift. Not testable further without the raw
  data.
- Not run: coherence and the DNN timing check (WORKFLOW steps 5-6).

**Alignment grade: `medium`.** Software story-start marker (Presentation, not shipped), shipped epochs kept
unchanged; the low tier passes with a 125 ms TRF peak, no response at negative lags and per-trial offsets
centred on 0 (median +2 ms) in the children with significant tracking.

## 9. Upstream issues
- The paper says six children heard the wombat story; the shipped data have seven (section 3).
- No licence on the OSF project.
- The paper says EEG was downsampled to 128 Hz; that is the TRF analysis, the shared CND is at 500 Hz.

## 10. Open questions (recommended defaults)
1. Licence: none stated. Default: incorporate with "no licence stated" in the metadata and README; the user may
   want to ask the authors.
2. Word onsets: carry the manual word-onset times as an unlabelled `words` tier? Default: no (labels cannot be
   paired with the transcript; the stim files remain in the download).
3. Raw BrainVision files would allow higher tiers; they are not shared. Default: none (low tier only).

## Restructure 2026-11-25 (not yet re-validated on data)
- BaseAdaptor; sorted glob; wavs through `iohelpers.audio_loader` (soundfile float32, both stereo channels kept, as
  before; 44.1 kHz checked).
