# fuglsang2020: selective attention to competing audiobooks in hearing-impaired and normal-hearing listeners (EEG)

EEG while 44 older Danish listeners, 22 with sensorineural hearing loss (`hi`) and 22 with normal hearing (`nh`),
attend to one of two simultaneous audiobooks (a male and a female talker, spatialised to ±90°, insert earphones) or
listen to one talker in quiet. 48 trials of ~51 s per listener. 19 listeners also wore in-ear EEG. Danish.

> **No audio.** Only the authors' envelopes are released (raw audio "on request"). The stimulus is the shipped
> 512 Hz envelope of what each listener heard. It supports low-frequency envelope tracking and attention decoding,
> and a middle-latency (30-60 Hz) response is visible; brainstem analyses are not possible.

- **Source:** Zenodo record 3618205, doi:10.5281/zenodo.3618205, "Selective auditory attention in normal-hearing
  and hearing-impaired listeners" (`ds-eeg-snhl`, BIDS 1.3.0, one 34.9 GB tar). **Licence:** CC BY 4.0 on the
  Zenodo record (`dataset_description.json` says ODbL; both require attribution).
- **Paper:** Fuglsang SA, Märcher-Rørsted J, Dau T, Hjortkjær J (2020). Effects of sensorineural hearing loss on
  cortical synchronization to competing speech during selective attention. *J Neurosci* 40(12):2562-2572.
  doi:10.1523/JNEUROSCI.1936-19.2020. Cite the paper and the Zenodo record.
- **Code (authors):** gitlab.com/sfugl/snhl (MATLAB; not shipped, not used).

## Size
**44 participants, 2112 trials, 30.1 h** (41.1 min per participant, identical for all: same material, permuted).
Per participant 32 two-talker trials (27.5 min) and 16 single-talker trials (13.5 min), half attending the male and
half the female talker. In-ear EEG: 19 participants (9 hi, 10 nh), 13.0 h. Ages 51-74 (hi, median 69.5) and 53-76
(nh, median 62). Standardised size ~16 GB, of which ~0.56 GB are the per-listener envelopes.

## What is provided
- **Scalp EEG (`eeg`):** BioSemi ActiveTwo, 64 channels (10-20, `biosemi64` names and template positions), at the
  native **512 Hz** (not resampled; BioSemi hardware low-pass ~104 Hz, kept in `info['lowpass']`). In volts,
  CMS/DRL reference (reference-free recording, not re-referenced). The same file holds the external channels, named
  from each participant's `channels.tsv`:
  - participants without in-ear EEG: mastoids `M1`/`M2` (type `misc`) and three electrodes around each eye,
    `VEOG_L_low`, `HEOG_L`, `VEOG_L_high`, `VEOG_R_low`, `HEOG_R`, `VEOG_R_high` (type `eog`);
  - participants with in-ear EEG: `VEOG_L_low` and `HEOG_L` only (no mastoids).
- **In-ear EEG (`ear-eeg`, 19 participants):** `EL1-3` (left ear) and `ER1-3` (right ear), same trials, onsets and
  stimuli as the scalp file, no positions.
- **Bad channels** are kept and listed in `info['bads']` (flat or high-frequency-noisy channels, e.g. a recurring
  P2/PO4/POz fault; see `notes.md` 5b). `pick("eeg")` keeps them: exclude `info['bads']` yourself.
- **Stimuli** (`audio` modality, 512 Hz, one channel; `feature_name` says which feature):
  - `subXXX-target-tNNN` (attended talker, `audio01`) and, in two-talker trials, `subXXX-masker-mNNN` (ignored
    talker, `audio02`). The files are **per listener**: the masker starts at a different time for every listener
    and trial (below), and the hearing-impaired listeners' stimuli were individually equalised.
  - `envelope`: the authors' envelope of the sound as presented (HRTF-spatialised, loudness-matched, and for `hi`
    listeners amplified with an individual CamEQ fit): 24 gammatone bands 100-4000 Hz, full-wave rectified,
    `|x|^0.3`, averaged over bands, of the left/right-averaged sound; 256 Hz low-pass, 512 Hz.
  - `envelope-no-cameq` (`hi` listeners only): the same without the CamEQ amplification; the paper's analyses used
    this one (r ≈ 0.985 with `envelope`).
- **Masker delay.** In two-talker trials the masker (distractor) starts **3.0-5.0 s after the target**, drawn
  uniformly per listener and trial. Each masker file is zero-padded by that delay, so **sample 0 of every stream is
  the target onset** and the streams can be used as they are. The delay is in each trial's sidecar
  (`masker_delay_s`, from the masker trigger). Maskers run past the trial end and are not cut: cut the longer signal
  at use.
- **Trial metadata** (`raw.info["description"]`, JSON): `participant`, `hearing_status` (`hi`/`nh`), `age`,
  `attended_talker` (male/female), `attended_side` (left/right), `masker_delay_s`, `target_segment` /
  `masker_segment` (the shared audio segment, `None` if heard by this listener only), `difficulty_rating`,
  `questionnaire_score`, `run` (sub-024 has two runs), `onset_sample`, trigger code, alignment provenance.
  Audiograms, SRTs and questionnaires are in the source `participants.tsv` (not exported).
- **Conditions:** `two-talker` (attend one of two talkers) and `single-talker` (one talker in quiet).
- Not exported: the tone and resting-state tasks (no continuous stimulus).

## Alignment
- **Trigger onset (`sw_trigger`).** Each trial starts at the target-onset trigger (BioSemi Status; `events.tsv`
  `sample - 1`, matching the Status channel in all 45 files) and lasts as long as the target envelope. The masker
  starts at its own trigger, which equals the shipped masker time stamp to the sample.
- **Trigger type: unknown.** How the stimulus PC generated the triggers is not documented, and there is no audio
  copy or stimtrack. Insert-earphone tube delay is not corrected.
- **Drift: none.** The trial-end trigger comes 5-7 samples (~12 ms) before the end of the target envelope in every
  trial, constant over 50-57 s trials (0 ppm; SD 1.2 ms). Either the sound starts ~12 ms after the onset trigger or
  the end trigger is early; not corrected (fuglsang2018 shows the same pattern).
- **Alignment grade: `medium`.** The trigger source is unknown and the shipped timing is kept, and validation
  confirms it: the lag sweep peaks within 1 ms of zero, the TRF latencies are plausible, and the 30-60 Hz response
  sits at 18-45 ms.

## Validation
**Scalp: `mlr`. In-ear: `low`.** Repository validator (forward model, average reference, bads excluded), all 44
participants:
- **Low tier (0.5-8 Hz, target envelope):** mean r **0.058**, **44/44** subjects above the circular-shift and
  mismatched-stimulus nulls; TRF peak 172 ms. Single-talker 0.070 (40/44), two-talker 0.052 (44/44).
- **Lag sweep:** the per-subject best shift is +0.7 ms (median; range -7 to +26 ms).
- **mlr (30-60 Hz, 18-45 ms):** mean SNR 1.89, p = 0.0099, 34/44 subjects, with peaks at ~27 and ~40 ms.
- **brainstem:** passes the test nominally, but there is no wave V; the MLR leaks into the 4-9 ms window, and the
  512 Hz envelope cannot carry a brainstem response. Not claimed.
- **Attended vs ignored (two-talker):** r 0.052 vs 0.023; attended > ignored in **39/44** listeners (p = 1.4e-10),
  hi 19/22 and nh 20/22. The ignored stream with its per-listener delay is tracked (30/44 subjects, TRF peak
  141 ms), and its lag sweep sits at -1.7 ms (IQR -16 to +17 ms), which confirms the masker delays.
- **In-ear EEG:** mean r 0.015, 7/19 subjects; 30-60 Hz not significant. For group-level analyses.
- **Suitable for:** envelope tracking and auditory attention decoding, hearing-loss group comparisons (hi vs nh,
  with audiograms in the source `participants.tsv`), cortical and middle-latency TRFs, in-ear vs scalp comparisons.
- **Not suitable for:** brainstem responses, anything that needs the audio waveform or other acoustic or
  linguistic features, and latency comparisons at the ~10 ms level.

## Caveats
- **Envelopes only.** No audio, no other acoustic features; the audiobooks are not in the fuglsang2018 release
  either (checked). Envelope-based models only.
- **Per-listener stimulus files.** The same audiobook segment appears under different names in different
  listeners (`target_segment` / `masker_segment` link them); the envelopes of one segment differ slightly between
  listeners (loudness matching, side, CamEQ).
- ~12 ms constant trigger-to-envelope-end offset of unknown origin (see Alignment); latencies at the ~10 ms level
  are uncertain.
- CMS/DRL dropouts in sub-015, 033, 037, 038 and 039 fall in the breaks, not in trials.
- Upstream: `events.tsv` spells the difficulty column `diffulty_ratings`.

Details: `notes.md`.
