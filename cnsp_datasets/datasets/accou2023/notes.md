# accou2023 notes

SparrKULee (Accou et al. 2024, Data 9(8):94; preprint bioRxiv 10.1101/2023.07.24.550310). KU Leuven RDR
doi:10.48804/K3VSND (v3.1, CC BY-NC 4.0). 64-channel BioSemi EEG at 1024 Hz plus EXG1-8, 85 participants, one
session each (`shortstories01`: 26 participants, 10 audiobook parts; `varyingStories01-10`: audiobooks and
podcasts), one BIDS run per stimulus. Authors' code: github.com/exporl/auditory-eeg-dataset.

## Contents of the public release
- Files of sub-019, 020, 021, 022 and 026 (196) are restricted: RDR answers 403; access on request to the authors
  (non-commercial). The public part gives 81 participants and 620 runs (617 complete, 3 truncated).
- 7 runs (sub-050, 077, 081) have events.tsv and .apr but no EEG upstream either.
- There are some SRTs in this dataset; code to extract them exists but is not incorporated.

## Conditions (do not trust events.tsv)
- events.tsv lists every run as `in_noise` with snr 100 (or `no_noise`). The run's APEX results file
  (`*_eeg.apr`, interactive entry SNR) has 5 dB for 41 shortstories01 runs (about two per participant), matching
  the paper ("Two out of ten trials ... speech-weighted-noise (SNR = 5dB)") and the authors' preprocessing (SNR
  from the .apr). The adaptor takes the .apr SNR and falls back to events.tsv: `sin5dB`.
- sub-027..031 have audiobook_7_5 / 7_6 at -4 / 2.5 dB in events.tsv (`sin-4dB`, `sin2.5dB`, 5 runs each). Their
  .apr has no SNR entry; the experiment files (`stimuli/eeg/audiobook_7_5.apx`, `7_6.apx`) set the noise gain to -4
  and 2.5 (inverted gain, noise `swn_n/audiobook_7_1.npz`, not shipped; events.tsv names `audiobook_6_1_swn`), so
  these labels are kept.
- `av`: podcast_10 with video of the speaker for sub-027..036 except sub-030 (paper, figure 4); events.tsv has no
  video files.
- `control`: audiobook_1_artefact, the first 5 min of audiobook_1 played with the insert phones out of the ears
  (one run). `pitchshifted`: audiobook_1_1_shifted / 1_2_shifted (2 runs in the public part). The halves
  audiobook_1_1 / 1_2 are `natural`. The authors' technical validation leaves out artefact, shifted and the halves.
- The noise is not given as a stimulus: APEX played it as a loop starting at a random point (`dataloop`,
  `randomjump`), so the shipped noise files (RMS-matched to the speech) do not give the noise as played.

## Alignment
- The stimulus trigger track (`t_<stim>.npz`, a pulse every second from the first audio sample; on the last sample
  for most stimuli) was played on a second sound-card channel and recorded in the BioSemi Status channel. The
  adaptor resamples the EEG between its first and last trigger to the stimulus' first-to-last trigger span (the
  authors' drift correction, linear interpolation).
- Drift of the trigger clock against the EEG (613 runs): -34.5 ppm median (about -31 ms over a 15-min run), stable
  within a participant (sd 0.04 ppm) but set-up dependent: sub-015/016 -55 ppm, sub-017/018 -40 ppm. Jitter 0.28 ms
  (sampling at 1024 Hz) except sub-006 run-05 (0.73 ms, max 1.7 ms) and sub-071 run-03 (1.3 ms, max 3.0 ms). The
  adaptor's first-to-last-trigger resampling removes the drift.
- The resampling is linear interpolation (as the authors'). Against a quintic spline (12 subjects, 111 runs): EEG
  amplitude x0.97 at 100 Hz, x0.88 at 200 Hz, x0.77 at 300 Hz (sqrt((2 + cos w) / 3), signal and noise alike);
  30-300 Hz TRF SNR, per-subject SNR and 1024 Hz coherence unchanged, no timing difference. Kept linear; an option
  for either is planned (PLAN.md section 8).
- Use the trigger file events.tsv names: audiobook_2_2's experiment played `t_audiobook_2_1` with it (both after
  1 s of silence, so the onset holds); those trials have 29 s of EEG after the speech. The trigger tracks of
  audiobook_6_1, audiobook_6_2 and audiobook_1_artefact end 0.3-0.6 s before the audio.
- The README calls three runs unalignable (sub-006 run-06, sub-017 run-03, sub-048 run-04). They are truncated, not
  unalignable: 847 / 332 / 622 EEG pulses (the stimulus has 911 / 954 / 1155); sub-006 and sub-048 recordings end
  there, sub-017's triggers stop at 340 s (plus a stray pulse 0.26 s after the last) while the recording continues
  to 983 s. The EEG pulses are the first N of the stimulus' (not shifted by lost first pulses): a decoder trained on
  the participant's other runs gives r 0.138 / 0.089 / 0.102 with the first pulses matched against -0.03 to 0.03
  when shifted by 1-3 pulses, best lag 0 ms. The adaptor includes them (`TRUNCATED`, `first_pulses`): EEG pulses
  up to the first irregular spacing, matched to the stimulus' first pulses; their EEG ends at the last pulse
  (846 / 330 / 621 s, 30 min in all).

## Channels
- The first 64 channels are named by position (BioSemi 64 order); sub-015..018 files spell PO7/PO3 as P07/P03.
- EXG1/EXG2 are the mastoids (A1/A2, misc). They are unconnected (0.4 uV noise floor) in sub-061 and sub-064 and
  missing in one sub-052 file; flat ones go into bads. EXG3-8 are unconnected and dropped.

## Validation (2026-11-20, average reference, `tmp/review/accou2023/avgref/`)
- 81 participants, 617 trials (before the 3 truncated runs were added), no load errors. Tier **brainstem**: envelope decoding mean r 0.030, 96% of
  participants significant, broad TRF (about 50-150 ms); MLR SNR 1.52, p = 0.01 (peaks about 25 and 37 ms);
  30-250 Hz TRF SNR 1.22, p = 0.01 (35% of participants alone), a small bump at 4-9 ms besides the 25-ms MLR peak.
- Coherence, natural (554 trials, 81 participants; ratio to null): 0.2-1 Hz 16.0, 1-4 Hz 6.4, 4-8 Hz 6.3, 8-15 Hz
  4.3, 15-30 Hz 1.7, 30-60 Hz 2.2; above the null's 95% at almost every bin to 63 Hz, with a 30-50 Hz hump (the
  envelope-following response): the alignment holds to a few ms across the dataset.
- Coherence, other conditions (envelope, ratio to null, 1-4 / 4-8 Hz): sin5dB 2.2 / 2.4 (41 trials), av 1.9 / 1.5 (9), sin2.5dB
  1.3 / 1.3 (5), sin-4dB 1.2 / 1.1 (5); the small conditions are close to the null for want of data.
