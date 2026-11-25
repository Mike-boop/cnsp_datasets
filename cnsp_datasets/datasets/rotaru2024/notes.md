# rotaru2024: explorer and alignment notes

Scratch: `R=/data_storage/gu08wuvu/datasets/tmp/review/rotaru2024/` (scripts in `R/../scripts/rotaru2024/`).

## 1. Source
- Zenodo 11058711 (v1, CC BY-SA 4.0): "Audiovisual, Gaze-controlled Auditory Attention Decoding Dataset KU Leuven
  (AV-GC-AAD)". Paper: Rotaru, Geirnaert, Heintz, Van de Ryck, Bertrand & Francart (2024), J Neural Eng 21:016017
  (`data_campaign/papers/rotaru2024.pdf`). Cite both.
- Release: README.txt, record.json, MD5SUMS and one `2024-AV-GC-AAD-subXX_preprocessed.mat` per participant
  (124-165 MB, 2.0 GB). Downloaded from the woody mirror (`zenodo/rotaru2024/11058711/`); md5 identical on both
  ends (`R/md5_local.txt`, `R/md5_woody.txt`).
- No audio or video (copyright): the authors ship 128 Hz envelopes. The record's author note: published AAD
  algorithms reach chance on this dataset, a linear stimulus-reconstruction baseline does not (their report), and
  results should be given per condition because MovingVideo and StaticVideo still contain gaze shortcuts.

## 2. Layout (per .mat, pymatreader)
- `data`: list of trials, (76800, 68) = 600 s at 128 Hz, 64 EEG + EXG3..6 (sub16: 63 EEG, no P9; see 5).
- `stimulus.{attended,unattended,left,right}Envelopes`: per trial, 76803 samples (600.02 s). `left`/`right` follow
  the talker, not the ear (left = the talker heard on the left first; = attended in both halves when the attended
  talker started on the left), so they add nothing to attended/unattended.
- `conditionID`, `initAttention`, `fs` (128), `params.filter` (Chebyshev 1-40 Hz), `subjID`
  (`2024-AV-GC-AAD-subXX`).
- `metadata[i]`: the raw BDF header (file name `sub-2022movingtargetpilotNN_ses-01_task-<cond>_eeg.bdf`, start
  time, channel labels, `TotalFrames` at 8192 Hz) and `RawData.Triggers` (trigger samples at 8192 Hz).
- `randomization[j]`: per presented trial, `conditionID`, `left`/`right` wav, `first_attended_side`,
  `switch_times` (300), `time` (600), `visuals`: the video (mp4) in MovingVideo/FixedVideo, `Gray_Target.png` in
  MovingTargetNoise (the moving crosshair, paper 2.3), and an mp4 also in NoVisuals, where the screen was black
  (paper 2.3): the adaptor stores `visual_stimulus` None for NoVisuals.

## 3. Stimulus-trial mapping
- 13 participants (sub01, 03, 04, 07-16; 02, 05, 06 not shared). 4 conditions x 2 blocks of 10-min trials:
  MovingVideo, MovingTargetNoise (not sub01, 03: added later), NoVisuals, FixedVideo (= StaticVideo in the paper).
  sub14 lacks FixedVideo2. 99 trials, 16.5 h.
- **`randomization` is not in trial order** (upstream issue): its rows are in another order than `data` /
  `conditionID` / `metadata` / `stimulus` in 9 of 13 participants (sub07, 09-16; `R/labels.log`). Read by row
  index, 30 of 99 trials get the wrong podcast names and attention side; mapped by `conditionID`, each of the 30
  podcast names maps to exactly one of the 30 distinct shipped envelopes (198 envelopes, r > 0.999 within a
  cluster, < 0.03 between; `R/env_clusters.log`, `R/names_by_cond.log`) and `initAttention` always equals
  `first_attended_side`. The adaptor maps rows by `conditionID`. Data, envelopes and metadata agree with each
  other (`conditionID` = BDF task name).
- `data` is not in recording order either (e.g. sub07 MovingTargetNoise2 at index 2 was recorded after index 5);
  the adaptor numbers trials by the BDF start time and keeps the shipped index in the provenance.
- Each trial: two podcasts (attended, unattended), the attended talker fixed for 10 min; at 300 s both talkers swap
  ears. Annotations `attend/left` (or right) for 0-300 s and the other side for 300-600 s.
- Same podcast heard by several participants (30 podcasts, 198 presentations). Podcasts were drawn per
  participant from their most/least preferred lists (paper 2.2).

## 4. Speech features
- Shipped: per podcast a 128 Hz envelope of the dry speech (README: 44.1 kHz -> 8192 Hz, gammatone filterbank,
  |.|^0.6 per band, same 1-40 Hz filter as the EEG, summed, 128 Hz). Copies across trials and participants are
  identical. Stored for all 30 podcasts as feature `envelope` (128 Hz, 76803 samples, starts at trial onset).
- **Audio recovery.** The podcasts are Universiteit van Vlaanderen videos; the audio tracks were cut to 10 min,
  silences kept (paper 2.2). Candidate sources, matched by envelope (authors' recipe re-implemented:
  `audio_env.py`; 10-s probes, then 10-s windows at 1/1024 s: `match_audio.py`, `R/match_audio.log`, figure
  `R/audio_match.png`):
  - SparrKULee (accou2023, `stimuli/eeg/podcast_N.npz`, 48 kHz): **10 of 30 podcasts match** with one constant
    offset, 0 ppm, residual <= 0.4 ms over 19-20 of 20 windows (r = 0.84-0.91, the remaining gap being our
    approximation of the authors' envelope): podcast_24 / 25 / 20 / 28 / 23 / 19 from 18.000 s, podcast_35 / 32 /
    1 / 15 from 17.964 s (checked with a whole-length cross-correlation). These are the 10 podcasts that rotaru2026
    shares with SparrKULee. Stored as feature `audio` (the 600.02-s SparrKULee excerpt at 48 kHz, level as in
    SparrKULee, not the -27 dB FS of the experiment) when the adaptor gets `sparrkulee_dir`; the shipped envelope
    is stored too, as a check.
  - rotaru2026 wavs (all 30 titles): silences trimmed to 0.2 s, 550-592 s long; they match only piecewise, the
    offset stepping at each trimmed pause (5-45 s over the trial, panel C). Not the played audio: not used. A
    rebuild (re-inserting silence of the measured lengths) would be possible but would rest on envelope-estimated
    splice points; not done.
  - The other 20 podcasts: shipped envelope only.
- Played sound differed from the dry podcasts: each talker convolved with anechoic HRIRs at -90/+90 deg (ILD
  ~10.6 dB), insert phones (Etymotic ER10, RME Fireface UC), 65 dB SPL; MovingTargetNoise added babble noise at
  -1 dB SNR to each ear (not shipped). No transcripts or alignments.

## 5. Neural data
- BioSemi ActiveTwo, recorded at 8192 Hz; shipped: authors' preprocessing per trial (anti-alias decimation to
  256 Hz, 1-40 Hz zero-phase Chebyshev II, 128 Hz). Units microvolts (EEG robust SD ~6-7 uV); scaled to V.
  No reference (CMS/DRL; README: re-reference before use); kept. Montage: BioSemi 64 labels, template positions.
- Output rate 128 Hz (native of the release; nothing resampled).
- EOG (paper 2.3: two electrodes 1.5 cm above/below the right eye, two at the outer canthi). From the data
  (`eog.py`, `chan_check.py`; average reference): EXG3 correlates with Fp1+Fp2 (r 0.72-0.99) and EXG4
  anticorrelates (blinks) -> `VEOG_high`, `VEOG_low`; at the 300-s side switch in FixedVideo (gaze jumps to the
  other side) EXG5 turns positive and EXG6 negative for a rightward gaze shift in 9 participants (4 ambiguous, none
  opposite) -> `HEOG_right`, `HEOG_left` (inferred).
- sub16: 67 columns; its label list (67) lacks P9, so 63 EEG + 4 EOG (all four EOG present: EXG3 r 0.90 with Fp).
- Bad channels (robust SD < 0.1 x the participant's median, all trials): sub03 P1, PO3; sub16 P1. Kept, listed in
  `info['bads']`. The shipped 40 Hz low-pass leaves no high band to screen.

## 6. Alignment
- Triggers: `RawData.Triggers` hold a square pulse every second of the trial ("squared-pulse triggers presented
  every second", paper 2.3; same lab as rotaru2026, whose pulses are the start of each 1-s sound-card buffer).
  The pulse train: 600-601 pulses per trial, jitter 0.035 ms (= 1/8192 s quantisation), grid drift -6.0 to -6.7 ppm
  against the EEG (`R/grid.log`, `R/triggers.log`); plus spurious extra events (up to 45 per trial, codes 1/2).
  Inferred hardware.
- The authors cut each 600-s epoch, presumably at the first pulse; the cut sample is not shipped.
- **First-buffer stalls** (`stalls.py`, `R/stalls.log`): in 25 trials the first pulse interval deviates from 1 s:
  +380/570/760/950 samples at 8192 Hz (+46.4/69.6/92.8/116 ms, multiples of one 1024-sample block at 44.1 kHz; 11
  trials, all in sub04 and sub07) or -4..-191 samples (14 trials; `alignment/decoder_lags.csv`). Mid-trial, almost all
  deviations are single displaced pulses (+x then -x); net stalls only in sub04 MovingVideo2 (+46 and +70 ms at
  490/494 s).
- **The pulses do not follow the audio after a stall.** Backward decoder (64 ch average reference, 1-9 Hz, EEG
  lags 0-250 ms, ridge; leave-one-participant-out, trained on trials without deviation; `dec_cut.py`,
  `dec_rec.py`, `dec_whole.py`, `dec_time.py`; figures `R/dec_cut_groups.png`, `R/dec_whole.png`,
  `R/dec_time.png`):
  - trials without a deviation (n = 69): pooled peak +3.8 ms (95% CI 0.8-7.0);
  - negative first deviation (n = 13; sub14's -0.5 ms left out): +0.7 ms (-4.8-7.1), so they are fine as shipped;
  - +46.4 ms (n = 6): +34 ms (28-46); +69.6 ms (n = 3): +43 ms; +92.8/+116 ms (n = 2): +41 ms. Per trial the lag
    starts at or above the stall (sub07 FixedVideo1/NoVisuals1: ~120-160 ms in the first 100-200 s) and decays
    to ~10-30 ms by the end: the audio catches up while the pulse grid stays rigid. sub04 MovingVideo2 is
    aligned near 0 after 495 s despite +232 ms of pulse stalls. A pulse-derived onset/drift correction would
    therefore be wrong; none is applied. The -6 ppm grid drift (3.6 ms over 600 s, 0.5 sample) is recorded in
    the provenance (`pulse_grid_drift_ppm`), not applied, because the pulses are not shown to keep the audio
    clock.
  - **sub04 MovingTargetNoise2** (pulse train looks normal): lag -994 ms (z 6.4; both halves -1002 / -987 ms):
    the shipped epoch starts ~1 s into the audio (one pulse late).
  - Most other trials have too little decoder SNR (z < 4) for a single-trial lag; their peaks scatter at
    +-0.5..1.5 s by chance (no consistency across halves).
  - Per-trial estimates: `alignment/decoder_lags.csv` (first pulse-interval deviation, whole-trial and half-trial lag, r, z).
    Brain-based: documented only. Trials flagged in the provenance (`timing_flag`): the 11 positive-stall trials
    (sub04, sub07) and sub04 MovingTargetNoise2.
- Insert-phone tube delay unknown (ER10: no tube; the paper gives none). No stimtrack.
- Proposed alignment: shipped timing (`alignment_method` `onset_only`), no drift correction.

## 7. Cross-subject duration check
- All trials are 600 s by construction (authors' epochs); envelopes 600.02 s. Pulse trains span 599-600 s in every
  trial. Drift from the pulse grid -6.2 ppm (median), not applied (6).

## 8. Validation
All 13 participants, 99 trials, average reference, 128 Hz (`R/validation.json`, `R/validation.png`, `R/validate.log`;
`standardise_validate.sh rotaru2024 --adaptor-opt sparrkulee_dir=<accou2023>`). The validator picks the attended
`audio` where it exists (10 podcasts), else the attended `envelope`.
- **low (0.5-8 Hz): pass.** Mean r 0.014 (median 0.014), p circular shift 0.020, p mismatch 0.048, 11/13
  participants significant (sub09 r 0.005 and sub10 0.002 inside the null); TRF GFP peaks at ~0-15, ~90 and
  172 ms, nothing above the null before -30 ms. Jitter SD 159 ms / MAD 35 ms, 2 offsets at the edge (consistent with
  the flagged trials, 6). Drift fit -20 ppm +- 103 (not informative at this SNR).
- 30-60 Hz and 30-250 Hz: not testable (shipped data low-passed at 40 Hz, 128 Hz). The validator runs them on the
  10 podcasts with audio (re-run after the review fixes, 2026-11-24): mlr SNR 1.08, p 0.089, fail; "brainstem"
  SNR 1.15, p 0.030, 2/13 participants, but that band is capped at 57.6 Hz (0.45 x 128 Hz), above the authors'
  40 Hz low-pass: not a brainstem result. Overall tier: low.
- **Attended vs ignored** (`scripts/rotaru2024/attention.py`, `R/attention.json`, figure
  `R/r-attended-vs-r-ignored.png`): forward models 0.5-8 Hz on the shipped envelopes of both talkers,
  leave-one-trial-out per participant. Attended 0.020 vs ignored 0.017, attended > ignored in 9/13 participants
  (Wilcoxon p 0.13; without the 12 flagged trials 0.021 vs 0.015, 9/13, p 0.094), 62/99 trials. Per condition:
  MovingTargetNoise 10/11 (p 0.010), MovingVideo 7/13, NoVisuals 8/13, FixedVideo 8/13. Lag sweep peak 0 ms.
  The channel-mean forward model separates the talkers poorly here (both are speech at the same level, one per
  ear; the ignored talker is tracked almost as well), except under babble noise.
- **Label check, backward decoder** (`scripts/rotaru2024/aad_backward.py`, `R/aad_backward.json`; 64 Hz, 1-9 Hz,
  EEG lags 0-250 ms, ridge, trained on the attended envelope, leave-one-trial-out per participant): r attended
  0.055 vs ignored 0.009; attended > ignored in **97/99 trials** and all 13 participants; 60-s window accuracy
  0.77 (MovingVideo 0.80, NoVisuals 0.81, FixedVideo 0.75, MovingTargetNoise 0.70; per participant 0.66-0.88). The
  attended/ignored labels (and the `conditionID` mapping, 3) are right; this matches the authors' note that
  stimulus reconstruction works on this dataset.

## 9. Grade
**poor.** Onsets are the authors' 600-s epochs, cut presumably on a 1-s pulse train (inferred hardware), with no
audio copy or stimtrack to verify them; in 12 of 99 trials the decoder shows the shipped epoch is misaligned
(11 first-buffer stalls, +20-130 ms; sub04 MovingTargetNoise2 ~-1 s), documented and flagged, not corrected
(brain-based). Graded by the weakest part. The 87 unflagged trials alone would rate medium (decoder lag +3.8 ms,
95% CI 0.8-7.0; low tier passes).

## 10. Upstream issues
- `randomization` rows not in trial order (sub07, 09-16): stimulus names and attention side must be matched by
  `conditionID`.
- sub04 MovingTargetNoise2: epoch cut ~1 s late (decoder).
- First-buffer playback stalls (sub04, sub07): shipped epochs misaligned by ~20-130 ms, varying within the trial.
- README: data "first 64 channels are EEG", but sub16 has 63 (no P9).

## Possible overlap with rotaru2026 (user, 2026-11-24)
- Same lab (KU Leuven), same Flemish podcast source, and 10 of rotaru2024's 30 podcasts are also SparrKULee
  (accou2023) podcasts that rotaru2026 uses (intro-cut, silence-trimmed versions there). Stimulus overlap is
  therefore likely beyond these 10; participant overlap cannot be checked (anonymised per-study ids) but is possible
  (same lab, overlapping years). Treat rotaru2024 and rotaru2026 as possibly sharing listeners and stimuli in pooled
  analyses; not yet resolved (would need the authors or a podcast-by-podcast envelope match against rotaru2026).

## Decisions and open questions (defaults accepted by the user, 2026-11-24)
1. Timing-flagged trials (11 stall trials + sub04 MovingTargetNoise2): keep with the flag (default), or exclude by
   default / apply the decoder's -1 s to sub04 MovingTargetNoise2 (brain-based; would need a trial-specific
   stimulus cut). Recommended: keep, flagged; users filter on `timing_flag`.
2. Audio of the 20 non-SparrKULee podcasts: shipped envelopes (default) vs a rebuild from rotaru2026's trimmed
   wavs (not done).

## Restructure 2026-11-25 (not yet re-validated on data)
- Adaptor subclasses BaseAdaptor; bads set with iohelpers.mark_bads (strict); `decoder_lags.csv` moved to `alignment/`
  (documentation only, the adaptor does not read it; its script is in tmp/review/scripts/rotaru2024/). SparrKULee
  excerpts read with the fixed accou2023 `_load_npz` (closes the file). EOG names (VEOG_high, ...) unchanged.
