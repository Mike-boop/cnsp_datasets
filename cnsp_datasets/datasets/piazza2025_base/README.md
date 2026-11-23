# piazza2025: stories in three speech registers, heard by L2 learners and native listeners

EEG while listening to three English stories, each in five ~3 min parts, one story per speech register:
L2 Accommodation (L2A, how native speakers address learners), Native Directed Speech (NDS) and Slow-NDS (NDS
time-warped to the L2A rate). All stories in +16 dB multi-talker babble. Two groups, recorded in different labs with
different EEG systems, standardised as two datasets:
- `piazza2025_l2l`: 25 Spanish-L1 learners of English (experiment 1, BCBL; BrainVision actiCAP, 1000 Hz).
- `piazza2025_l1l`: 25 native English listeners (experiment 2, Trinity College Dublin; BioSemi, 1024 Hz).

- **Source:** OSF ba3p4 (https://osf.io/ba3p4/), CND files. **Licence: unknown** (none on OSF; the article is CC BY
  4.0). Ask the authors before redistributing the data or anything derived from them.
- **Paper:** Piazza G, Carta S, Ip EYJ, Pérez-Navarro J, Kalashnikova M, Martin CD, Di Liberto GM (2025). Are you
  talking to me? How the choice of speech register impacts listeners' hierarchical encoding of speech. *Imaging
  Neuroscience* 3. doi:10.1162/imag_a_00539
- **Code (authors):** a forward-TRF script and R analyses on OSF.

## Size
50 participants, 742 trials, **33.9 h in total, 40.7 min per participant (34.4-42.3)**; L1L 16.9 h (370 trials),
L2L 17.0 h (372). Per register: L2A 12.5 h, NDS 9.1 h (NDS is faster, ~11 min per story), Slow-NDS 12.4 h.
2.05 h of unique audio. Six trials were placeholders of failed recordings and two parts were never shared; they
are absent.

## What is provided
- **EEG:** 64 scalp channels, **already preprocessed by the authors: 1-8 Hz band-pass, 100 Hz**; channels
  interpolated in a few participants (L1L 20, L2L 1, 5, 10, 12, 14). Stored at 100 Hz. No EOG, mastoids or
  triggers. Reference: L2L left earlobe; L1L not documented (not an average reference). Positions are
  `standard_1005` templates.
- **Channel names in L2L 6-25 are unknown**: the shared channel list fits L2L 1-5 only. Their channels are named
  E01-E64 in file order, without positions (`channel_order_known` in the provenance). Use them for analyses that
  do not need channel identity (e.g. envelope tracking with all channels), not for topographies.
- **Stimuli:** NDS and Slow-NDS as the wavs played (speech + babble, 44.1 kHz). **L2A only as the authors' 100 Hz
  envelope** (no audio shared). The authors' phonetic-feature, spectrogram, surprisal, entropy and word-onset
  regressors exist on OSF but are not included.
- `condition` = register; `trial` = presentation position (1-15); story and part in the provenance.

## Alignment
- The authors epoched at the PsychoPy (software) start trigger: EEG sample 0 = audio onset; the EEG continues ~1 s
  past the audio. Confirmed by the TRFs of every participant (peaks at 0-270 ms, nothing at negative lags). Drift
  and jitter cannot be estimated.
- The authors' stimulus files for L1L 13-15 do not match their EEG; trials were assigned to stimuli from the EEG
  trial lengths (unique for every participant) and checked with the EEG (`stim_file_mismatch` in the provenance).

## Validation
**Low tier** (the highest reachable at 100 Hz, 1-8 Hz), average reference, all 50 participants: mean r 0.025 (L1L,
23/25 participants above the nulls) and 0.032 (L2L, 21/25); every register passes in both groups (r 0.018-0.033).
Suitable for low-frequency envelope tracking and register/group comparisons; not for middle-latency or brainstem
analyses.

## Caveats
- Licence unknown; L2L 6-25 channel names unknown; L2A has no audio, so registers differ in stimulus feature type
  (wav envelope vs the authors' envelope; they agree at r 0.92-0.96 where both exist).
- The data cannot be re-preprocessed (no raw EEG); the 1-8 Hz band limits analyses.
