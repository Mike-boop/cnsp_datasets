# rotaru2026: KUL-AAD-NFB, closed-loop auditory attention decoding with neurofeedback

Flemish listeners attended one of two competing male talkers (popular-science podcasts, one per loudspeaker at
+-14 deg) while a real-time attention decoder gave feedback: none (OL), a visual slider (CLV), the talkers' gains
(CLA), or gains decoupled from the listener's brain (psCLA, "sham"). Each 8-min trial has 1 or 3 cued attention
switches. Some participants first did four 5-min calibration trials without switches (OL-CAL).

- **Source:** Zenodo 20442638 (KUL-AAD-NFB), doi:10.5281/zenodo.20442638. **Licence: CC BY 4.0**; the audio
  (Universiteit van Vlaanderen podcasts) only for non-commercial use.
- **Paper:** Rotaru I, Geirnaert S, Heintz N, Bertrand A, Francart T (2026). When feedback backfires: investigating
  neurofeedback effects in a closed-loop auditory attention decoding paradigm. bioRxiv,
  doi:10.64898/2026.04.28.721343. Cite the record, the paper and Universiteit van Vlaanderen.

## Size
11 of the 19 participants are shared (consent): sub-02, 03, 06, 09, 11, 12, 13, 15, 16, 17, 19; sub-09 in two
sessions. 118 trials, **14.4 h in total, 1.31 h per participant (0.80-2.13)**. Per condition: OL 3.2 h, CLA 3.2 h,
CLV 3.1 h, psCLA 2.7 h, OL-CAL 2.25 h (sub-11..19 only).

## What is provided
- **EEG:** BioSemi 64 channels (10-20 names, biosemi64 template positions), 1024 Hz, in volts, original CMS/DRL
  reference (re-reference before use). No EOG or mastoid channels. Noisy channels are listed in `info['bads']`
  (kept in the data).
- **Audio:** the left and right talkers' wavs as shipped (44.1 kHz, longer than the trial; cut at the point of use).
  `audio01` is always the left loudspeaker, `audio02` the right.
- **Attention:** annotations `attend/left` / `attend/right` give the cued talker over time. Only in OL-CAL (no
  switch) is a stimulus flagged as attended. Switch times and the initial ear are also in the sidecar.
- **Conditions:** `OL-CAL`, `OL`, `CLV`, `CLA`, `psCLA`. The sidecar also holds the feedback flags, the calibrated
  level (57 dBA per talker) and the participant's ratings after the trial (intelligibility, effort, distraction,
  switch effort, agency, predicted score).

## Caveat: in CLA and psCLA the stimulus heard is not the stored wav
In CLA and psCLA the two talkers' gains changed every second in opposite directions, by up to +-6 dB (51-63 dBA),
driven by the online decoder (CLA) or by a trajectory from another trial (psCLA). The gain trajectories are not in
the release, so the wavs here are the sources **before** the feedback gain. For analyses that need the exact
acoustic input (e.g. level-dependent responses) use OL, CLV and OL-CAL; envelope TRFs and attention decoding still
work in CLA/psCLA (see Validation).

## Alignment
- The playback software sent a pulse burst at the start of every 1-s audio buffer on a separate channel of the
  stimulus sound card, recorded in the EEG Status channel. Each trial is cut on these pulses: one fit per trial
  gives the sound-card/EEG clock drift (+6 ppm, `drift_ppm`) and the onset of each run of pulses, and the drift is
  corrected in a single resample per run. Residual jitter 0.28 ms (`jitter_ms`; the 1024 Hz sample grid).
- 12 trials contain a playback stall (9 of ~12.5 ms, 3 of ~2 ms); the EEG of the gap is cut so that the audio
  stays continuous, and the join is marked by `BAD boundary` / `EDGE boundary` annotations (`n_playback_runs`,
  `run_start_s` in the sidecar). Loudspeakers at 1.4 m add ~4 ms of acoustic delay (not corrected).
- **Alignment grade: good.** Hardware pulses from the playback sound card give onset and drift, sample-exact; the
  30-60 Hz tier passes; the match-mismatch DNN offset (-9.7 ms) is typical for two talkers.

## Validation (all 11 participants, average reference)
| tier | result |
|---|---|
| low (0.5-8 Hz) | pass: mean r 0.019, 9/11 subjects significant, TRF peaks ~30 and ~190 ms |
| 30-60 Hz (mlr) | pass: SNR 1.11, p 0.01 |
| 30-250 Hz (brainstem) | fail |

- Attended vs ignored talker (forward models, switches followed): attended > ignored in 11/12 sessions
  (p 0.0015); per condition OL-CAL 6/7, OL 10/12, CLV 7/12, CLA 10/12, psCLA 10/11; lag sweep peaks at 0 ms.
- Suitable for cortical envelope tracking, attention decoding with switches, and middle-latency responses. Not
  validated for brainstem analyses.

## Known issues
- Not standardised (no stimulus names in the release): sub-02 psCLA trials 5 and 10, sub-19 CLV trial 7, and an
  empty sub-13 calibration file. Some other trials are missing from the release (description).
- 10 of the 31 podcasts are also in accou2023 (SparrKULee), as different cuts (list in `notes.md`, section 3).

Details: `notes.md`.
