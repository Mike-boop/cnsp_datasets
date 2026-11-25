# nguyen2025: event-based AAD, scalp + in-ear EEG, two competing Danish TTS talkers

Explorer + standardiser notes (2026-11-24). Scratch: `tmp/review/nguyen2025/` (R below); scripts
`tmp/review/scripts/nguyen2025/`.

## 1. Source
- Zenodo 8082867 (version pinned), CC BY 4.0. Nguyen, N. D. T., Mikkelsen, K., Kidmose, P. (2025). Cognitive
  component of auditory attention to natural speech events. *Front. Hum. Neurosci.* 18:1460139,
  doi:10.3389/fnhum.2024.1460139 (`data_campaign/papers/nguyen2025.pdf`). Center for Ear-EEG, Aarhus University
  (same lab and amplifier setup as geirnaert2025).
- Shared code: `sample_code/erp_process.py` (read, not run): reads paradigm 1 with mne-bids, ICA on scalp EEG, ERPs
  at word onsets. Nothing about alignment.
- Download: the vault node's `zenodo_slowpull` (woody `/home/woody/iwpm/iwpm104h/zenodo/nguyen2025/8082867`, complete
  2026-11-24 09:22, MD5SUMS written), rsynced to R/download; all 32 files match record.json (md5 + size), all zips
  pass `unzip -t`. The woody copy is the vault-side copy (zips + record.json + MD5SUMS).

## 2. Layout
- BIDS-like, one zip per participant: `sub-XXX/eeg/sub-XXX_task-<paradigm>_{eeg.set,eeg.json,channels.tsv,
  events.tsv,events.json}` for `multiT~spoken~count` (P1), `discrete~discrete~count` (P2), `speech~speech~focus`
  (P3), `speech~speech~attend` (P4) and `spontaneous`; `sub-XXX_space-CapTrak_electrodes.tsv`. EEGLAB `.set` with
  the data embedded (float64, uV; ~0.5 GB for P4).
- `stimuli.zip`: `discrete_spoken_words/` (P1-P2), `synthesized_story_snippet/` (P3, 20 snippets),
  `real_story_snippet/` (P4, 43 snippets of which 40 are played; 27-29 unused). Per snippet: `stimuli_<n>_<tag>.wav`
  (24 kHz mono int16, the played audio), `trigger_<n>_<tag>.wav` (48 kHz mono, the audio trigger) and
  `trigger_<n>_<tag>.txt` (Latin-1, CRLF; rows `code  onset_ms  0  offset_ms  word`, plus 8/9 start/end rows).
- Each paradigm's `.set` holds only the trial blocks, concatenated (paper 2.4: "cut into trial blocks, and
  concatenated to discard the data between trials").

## 3. Stimulus <-> trial mapping (verified)
- 24 participants (sub-001..025 without 013, `participants.tsv`); all have all paradigms. Identical stimulus order
  and design for every participant; only the attended loudspeaker (`attended_spk`, 2 = left, 3 = right) is
  counterbalanced.
- `events.json` per paradigm: one entry per trial with `stimulies` (two wav paths), `attended_stimulus` (index;
  always 0 in the speech paradigms), `attended_spk`, `attended_event` (P3 target category, P4 7 = "spoken word"),
  `trigger` / `trigger_log` (the trigger wav / txt of each stream).
- `events.tsv`: trial start (8) and end (9) per epoch, and every word of both streams (`stimuli_idx`, `word`, onset
  /offset at 10 ms resolution, from the TTS timings; `invalid` = -1 marks the non-target words).
- Block layout: start event at block sample 0; end event = start + attended wav length + 1.000 s (= the second pulse
  of the attended trigger wav, within the 1 ms grid, `durations.py`, all 24 participants); the block continues 1 s
  past the end event, and the next block starts there (gaps exactly 1.000 s; recording ends 1.000 s after the last
  end event). So each block = attended wav + 2 s.
- P3 (`focus`): 20 trials, attended 19.0-23.3 s (6.9 min in total); each of the 20 snippets is played twice,
  attended once and unattended once. P4 (`attend`): 40 trials, attended 24.4-41.8 s (21.2 min); stimulus pairs
  `stimuli_k` (attended) + another snippet. The unattended wav is longer than the block in 3 (P3) and 11 (P4) trials;
  whether it was stopped at the block end is unknown (stimuli are not cut, as usual).
- P1/P2 are isolated words (20 per trial, 0.8-1.2 s apart): not continuous speech, not included. `spontaneous`:
  no stimulus, not included.

## 4. Speech features available
Raw audio of both streams (24 kHz mono, RMS-normalised Google TTS, voices da-DK-Wavenet-A female / C male). Word
onsets/offsets for every word from the TTS tool (`trigger_*.txt`), with target-word codes (P3: 1 human name,
2 animal name, 4 number, 5 color, 6 plant). Written as TextGrids (tiers `words`, and `targets` for P3).
Two P4 rows end before they start (`-` in
`trigger_38_target.txt` and `trigger_6_target.txt`) and are dropped.

## 5. Neural data
- Two TMSi Mobita amplifiers at 1000 Hz (paper 2.4): scalp (Ag/AgCl, 32 channels, 10-20) and ear (IrO2, six
  electrodes per individualised earpiece: ELA ELB ELC ELE ELI ELT / ERA ... ERT). The two share one combined
  Ag/AgCl + IrO2 electrode at Fpz. Each amplifier was offline re-referenced to its half of that electrode: `Fpz`
  (scalp) and `cRef` (ear) are all zeros in every file. Units: uV in the `.set` (MNE's EEGLAB reader scales by
  1e-6; channels.tsv says V, wrongly); in V after reading, 1-40 Hz SD ~10-30 uV.
- Channels (identical in all files): Fp1 Fpz Fp2 F7 F3 Fz F4 F8 FC5 FC1 FC2 FC6 M1 T7-T3 C3 Cz C4 T8-T4 M2 CP5 CP1
  CP2 CP6 P7-T5 P3 Pz P4 P8-T6 POz O1 Oz O2 (scalp amplifier, 32 = the Mobita's inputs), ELA..ERT, EOG, cRef.
- **EOG is on the ear amplifier**: its DC level matches the ear channels' (median ~150 mV as shipped vs ~6 mV on
  the scalp) and its 100-450 Hz noise correlates more with the ear channels (median r 0.27 vs 0.18;
  `chan_stats.py`). Direction unknown -> `EOG`.
- Positions: `electrodes.tsv` is the same spherical template (r = 0.095 m, CapTrak) for every participant; the ear
  rows copy M1/M2. Template set on the scalp file only.
- Output: ns_type `eeg` = the 32 scalp channels (M1/M2 as `misc`); ns_type `ear-eeg` = 12 in-ear + EOG + cRef.
  Fpz / cRef kept (the reference, all zeros) and listed in `info['bads']`.
- Bad channels (`bads.json`, `bads_rule.py` on `chan_stats.py`, union over P3 and P4 per amplifier): railing
  (DC > 1 V), flat (1-40 Hz SD < 0.5 uV), > 1 mV, or > 10x the group median SD after a median re-reference (scalp
  incl. mastoids / in-ear); EOG only flat or railing. 27 subject/amplifier entries.
  Whole ear amplifier bad for **sub-007** (all zeros in P4, ~1.4 mV noise in P3). **sub-008**'s ear channels sit at a
  uniform +52.5 V DC offset as shipped with normal AC (10-16 uV, 0.023 uV resolution), so the railing rule compares
  each channel's DC with its group's median DC (> 1 V away = railing); only ELT (flat) is bad there. Mastoids bad in
  sub-004/008/012/015/017/020/025 (one or both). EOG bad (flat) in sub-001, sub-004.
- Native 1000 Hz kept; no resampling.

## 6. Alignment
- **Triggers (hardware, inferred):** every stimulus ships a 48 kHz trigger wav with two 625 ms pulses: at sample 0
  (speech onset) and 1 s after the attended speech ends. This is the lab's audio-trigger scheme (geirnaert2025's
  paper: "audio triggers were generated from a separate audio trigger channel"), played by PsychoPy 2022.1.4 with
  the speech. The paper and README do not describe it ("'trigger' and 'trigger_log' are used for debugging"); the
  trigger channel is not shipped (`TriggerChannelCount` 0).
- **End events are design-derived:** for each stimulus, end - start is identical to the sample in all 24
  participants (differences from the trigger wav's end pulse < 0.5 ms, i.e. rounding of the 48 kHz pulse to the
  1 kHz grid; `durations.py`, `durations_all.csv`). Two independent clocks (sound card, Mobita) and the sample
  losses the README mentions for P1/P2 would show up as varying durations, so the end event was computed, not
  measured. Drift and in-trial sample losses are therefore **not estimable** from the release. No correction.
- **Onset:** the start event (block sample 0) is taken as speech onset of both wavs (the trigger wav and the speech
  wavs start together). Speech-shift sweep (`shift_sweep.py`, `shift_sweep.png`; leave-one-trial-out forward model,
  attended envelope -> scalp EEG, 0.5-8 Hz, shifts -1..2.5 s): P4 peaks within +-0.22 s of 0 in 10/12 participants
  (5 at 0 or +-0.06 s; sub-022 +0.84 s and sub-024 -1.0 s at r < 0.02, flat curves); P3 (7 min per participant)
  noisier. No evidence of an offset at the 100 ms scale; the validator's lag sweep (section 12) is the finer check.
- **Inter-amplifier timing** (`amp_sync2.py`, `amp_sync2_all.csv`, `amp_sync.png`): each in-ear group (mean of
  good channels, ref cRef) vs the mastoid on the same side (ref Fpz) sees nearly the same potential difference
  (r 0.95-1.00); 1-15 Hz, 10 s windows, |xcorr| peak within +-60 ms. 98.1% of 10 s windows within +-2 ms
  (19 participants assessable). 19 trials flagged in `amp_steps.json`: 8 with a clear step of 10-16 ms lasting
  several windows (sub-005 trials 14 and 37, sub-016 33, sub-018 40 (+12 ms), sub-019 52, sub-022 27, sub-023 10,
  sub-024 29), 11 single-window excursions (5-25 ms, possibly noise). Same ~15 ms signature as geirnaert2025 (samples
  dropped by one Mobita; which one is unknown). Not assessable: sub-007 (no ear data), sub-008/015/017/025 (bad
  mastoids). Stored per trial in the sidecar (`amplifier_steps`, `amplifier_sync_assessable`).
  Blink-based estimates (EOG vs Fp1/Fp2, `amp_sync.py`) gave per-participant "lags" of up to +-30 ms that the
  ear/mastoid pairs do not confirm (sub-020 blink -19 ms vs pair 0 ms; sub-024 +26 vs 0 ms): EOG and Fp see
  different mixtures of eye sources; not used.
- Insert-earphone latency: none (free-field loudspeakers at +-60 deg; distance not stated).
- **Method:** `onset_only` (the authors' blocks, cut at the hardware audio trigger), no drift or inter-amplifier
  correction.

## 7. Cross-subject duration check
All 1440 speech trials (24 x 60): end - start = attended wav + 1 s to < 0.5 ms, identical across participants
(section 6). Not informative about drift (design-derived).

## 8. Data size
Per participant 60 trials: attended speech 28.2 min (P3 6.9, P4 21.2), recorded blocks 0.50 h. 24 participants:
11.3 h of attended speech (12.0 h of blocks). Standardised: ~0.19 MB/s for both files (one trial: 2.75 MB scalp +
1.20 MB ear for 21.4 s) -> ~334 MB per participant, ~8.0 GB for 24 participants plus ~130 MB of stimuli.

## 9. Upstream issues
- `channels.tsv` says V; the `.set` data are uV.
- sub-008 ear amplifier: +52.5 V DC offset on every channel (AC normal).
- sub-007 ear amplifier: all zeros in P4.
- Two word rows with offset < onset (section 4).
- `electrodes.tsv`: the ear electrodes carry the M1/M2 positions (placeholders); EOG/cRef n/a.
- `README`: does not say that the end event is design-derived or that Fpz/cRef are the (zeroed) references.
- `participants.tsv` / `scans.tsv`: all acquisition times are midnight (date only); paradigm order not recorded
  (paper order P1-P4 assumed for trial numbers, not verified).

## 10. Open questions (defaults taken)
1. P1/P2 (isolated word streams) excluded as not continuous speech. Default: excluded (could be added later as a
   separate option; ~14 min per participant).
2. Inter-amplifier steps documented in the sidecar (`amplifier_steps`), not corrected (which amplifier lost the
   samples is unknown). Default: not corrected.
3. Alignment grade: proposed `medium` (section "Alignment grade").
4. Convention (user, 2026-11-24, CLAUDE.md): one file per montage; scalp and in-ear are separate ns_types (also
   separate amplifiers here), EOG stays with the ear amplifier that recorded it.

## 11. Adaptor
`adaptor.py`: per participant, P3 trials 1-20 (`focus-<side>`) then P4 trials 21-60 (`attend-<side>`), side = the
attended loudspeaker; each trial yields ns_type `eeg` and `ear-eeg` with the same stimuli (attended first): audio
`synth-<n>-<category>` (P3) / `real-<n>-target` (P4) as shipped (int16 -> float32, 24 kHz) plus a TextGrid. EEG =
block start event to end event + 1 s (attended wav + 2 s), uV as shipped (V after reading), original reference, bads
from `bads.json` plus the reference channel. Each `.set` is loaded once and cached (`lru_cache(1)`; both amplifiers
of a trial read the same file). Sidecar: `onset_only`, trigger `hardware (inferred ...)`, `drift_ppm` null,
`validation_tier` (constant `VALIDATION_TIER`), amplifier, paradigm, source epoch, block start sample, attended /
ignored name, attended side, P3 target category, `amplifier_steps` (text from `amp_steps.json`, null when in sync),
`amplifier_sync_assessable`, sex, age, hand, reference, units, positions.

## 12. Validation
2026-11-24, all 24 participants from `R/standardised` (the final run). Average reference per amplifier (scalp: the
30 `eeg` channels minus bads, Fpz excluded as bad, mastoids `misc`; in-ear: the 12 in-ear channels minus bads, cRef
excluded), attended stream, `validate_ns.py` (the validator on one ns_type).
- **Scalp** (`validation.json`; `R/validation_scalp/validation.png`): low tier **pass**, mean r 0.022 (median
  0.022), p_circ 0.020, p_mismatch 0.048, 19/24 subjects significant, TRF peaks ~80 and 188 ms, below the null at
  negative lags. 30-60 Hz nominal pass (SNR 1.08, p 0.010, 4/24) **rejected**: the TRF is a regular ~10 ms ripple at
  all lags inside the null band (LESSONS). 30-250 Hz fail (SNR 1.04, p 0.11). Tier: low.
- **In-ear** (`validation_ear-eeg.json`; `R/validation_ear/validation.png`): sub-007 excluded (all bad); low tier
  **pass**, mean r 0.018 (median 0.014), 13/23 significant; the TRF is broad (peak 94 ms) and already above the
  null from -140 ms; 30-60 Hz fail (SNR 1.03), 30-250 Hz fail (SNR 1.09). The amplifiers are in sync (section 6),
  so the negative-lag spread is probably low SNR smeared by the envelope's autocorrelation, not timing. Tier: low.
- Per paradigm, low tier (`R/validation_{scalp,ear}_{focus,attend}/`): scalp focus r 0.018 (9/24, pass), attend
  0.019 (18/24, pass, TRF peak 78 ms); in-ear attend 0.014 (9/23, pass), **in-ear focus fail** (r 0.011, 4/23,
  p_mismatch 0.24: 7 min per participant, and every focus snippet is also another trial's unattended stream).
- Lag sweep of the validator: per-trial offsets are not informative (trials of 20-40 s; jitter SD ~250 ms, many at
  the search edge); the pooled shift sweep (section 6) peaks at 0 s.
- Attention contrast: backward decoders (`aad_check.py`, a copy of `scripts/earEEG/aad_check.py` with an
  ns_type filter; 0.5-8 Hz, 64 Hz, lags 0-500 ms, original reference, leave-one-trial-out), **seconds 2-60 of each
  trial**: with the onset included, r(attended) ~ r(ignored) ~ 0.17 in every participant (both talkers start at
  sample 0, so the sound-onset response dominates). Scalp (`R/aad_eeg/r-attended-vs-r-ignored_env_2-60s.png`):
  attended > ignored in **24/24** (median r 0.049 vs 0.005, Wilcoxon p 1.2e-7), 30 s accuracy median 75%, lag-sweep
  peak -1 ms (CI 0..0), sharp in every participant. In-ear (`R/aad_ear-eeg/`; sub-007 skipped): 14/23 (median
  0.0075 vs 0.0033, p 0.086, n.s.), accuracy 50%, lag-sweep peak 0 ms (CI 0..0): the in-ear timing matches the
  scalp timing.
- Not run: DNN offset (WORKFLOW 6), coherence (WORKFLOW 5).

## Alignment grade
**medium** (proposed): hardware audio trigger inferred (a trigger wav ships with every stimulus) but not verifiable
(trigger channel not shipped, no audio copy, end events design-derived, so no drift estimate); shipped onsets kept,
low tier passes on scalp (TRF 188 ms, nothing at negative lags) and in-ear, speech-shift sweep and decoder lag
sweeps (scalp and in-ear) peak at 0 ms; inter-amplifier steps of ~10-16 ms in 8 trials documented, not corrected.

## Restructure 2026-11-25 (not yet re-validated on data)
- Adaptor subclasses BaseAdaptor; wavs read with iohelpers.read_wav (float32, same /32768 scaling, mono checked); bads
  (reference channel + bads.json) set with iohelpers.mark_bads (strict). TextGrids now written by iohelpers.textgrid:
  long format, xmin 0 s (was the first word onset), gaps between words filled with empty intervals, quotes escaped;
  overlapping words would now raise (none expected, not checked on data).
