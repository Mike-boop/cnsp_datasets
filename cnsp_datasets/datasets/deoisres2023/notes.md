# deoisres2023: ignored speech and speech-modulated noise in quiet and at 5 SNRs (Southampton ePrints D2578)

Explorer notes, 2026-11-23. Scratch: `tmp/review/deoisres2023/` (data storage); one-off scripts in
`tmp/review/scripts/deoisres2023/` (`survey_status.py`, `timing.py`, `pulses.py`, `pilot.sh`, `validate_pooled.sh`,
`validate_cond.py`, `validate_conds.sh`, `bads.py`, `chunk_check.py`, `artefact_check.py`).
Everything below that explains a choice in the adaptor is recorded here because tmp is deleted.

## 1. Source
- Dataset: Deoisres S (2023). *Dataset in support of the Southampton doctoral thesis 'Predicting behavioural speech
  reception threshold using cortical responses to continuous sound'.* University of Southampton,
  doi:10.5258/SOTON/D2578 (ePrints 476402). Licence: CC BY 4.0 (every file in the ePrints JSON export).
- Thesis: Deoisres S (2023), *Auditory cortical responses as an objective predictor of speech-in-noise
  performance*, University of Southampton; chapter 6 is this experiment (`data_campaign/papers/deoisres2023.pdf`).
  Note the dataset title and the thesis title differ.
- Shared code (`SIN_EEG_python_script.rar`; read, not run): backward-model scripts per stimulus type. They give the
  segment-index -> condition mapping (section 3), the trigger handling (local maxima of the Status channel saved to
  .mat; 82 triggers -> drop entries 41 and 42; S11 noise: a missing first trigger re-inserted) and the analysis
  (re-reference to T7/T8 and drop them, 1-4 / 4-8 Hz FIR, 128 Hz, |Hilbert| envelope at 44.1 kHz, lambda 355,
  0-300 ms backward model trained on quiet, tested on the SNR blocks).
- Access: the ePrints JSON export answers scripts (sizes, MD5s); the files themselves sit behind the Anubis
  proof-of-work page (HTTP 401, checked once 2026-11-23, not circumvented). The user's manual download
  (`/data_storage/gu08wuvu/datasets/deoisres2023/download/`, read-only, 2026-11-22) has 11 of the 12 files, all
  matching size and MD5; **`SIN_README.txt` (7.7 kB) is missing** and was not read for these notes.
- Registry: source `eprints`, id 476402, `SIN_EEG_Da.rar` excluded (/da/ syllable trains are not continuous
  speech). 14.39 GB in total, 12.53 GB without the /da/ archive.

## 2. Layout
All archives are RAR4. The repository's `extract_archives` has no RAR support; extract with
`bsdtar -xf <rar>` (libarchive 3.8) into the adaptor's `download_dir`; the adaptor globs recursively.
- `SIN_EEG_S1_S7.rar`, `_S8_S14`, `_S15_S19`, `_S20_S22`: per subject `SIN_Sxx_speech.bdf`, `SIN_Sxx_noise.bdf`
  (quiet, ~15.7 min; S03/S04 ~26 min) and `SIN_Sxx_MixedSpeechNoise.bdf` (~83 min, the SNR blocks). 66 BDFs.
- `SIN_Stimuli.rar`: stereo int16 wavs, channel 1 = sound, channel 2 = trigger track (500-ms full-scale pulses):
  `odin_04_{speech,mod_amp}_full_65dB_trig.wav` (44.1 kHz, 929.7 / 931.0 s, 16 pulses),
  `odin_04_and_05_{speech,mod_amp}_full_65dB_trig.wav` (1542.0 / 1543.4 s, 32 pulses; S03, S04),
  `odin_01_{speech,mod_amp}_full_65dB_2minsx4_trig.wav` (483.0 s, pulses at 2, 122, 242, 362, 482 s: four 120.000-s
  chunks; the two trigger tracks are identical), `Da_1.11sISI_200_reps_65dB_trig.wav` (48 kHz, not used).
- `SIN_Stimuli_Order.rar`: `Subject_SNRpresent_order_speech_and_noise.xlsx` (40 rows = presentation position,
  28 columns = subject number - 1; only 4 distinct columns, repeated) and `..._da.xlsx`.
- `SIN_SRT.rar`: per subject `SIN_Sxx_matrix_5dBSNR.xlsx` (Matrix-test word scores). Not standardised.
- `SIN_EEG_Da.rar`: /da/ recordings (not used).

## 3. Stimulus <-> trial mapping
- 22 subjects S01-S22 (thesis text says "twenty" but 15 M + 7 F; all 22 have data). One session (one day) each;
  the three files are ordered by `meas_date` (noise and speech in quiet first, then the SNR blocks).
- **Quiet files**: one trial each, condition `speech_story` / `modnoise_story`; the wav is the one whose trigger
  track has the same pulse intervals as the EEG (odin_04 for 20 subjects, odin_04_and_05 for S03/S04; since
  odin_04_and_05 starts like odin_04, the wav with the fewest unmatched pulses wins). The pulses mark 4 sections
  (start, 2 inner, end each; 4-s gaps) of a continuous wav; the whole wav is the stimulus.
- **SNR blocks** (`MixedSpeechNoise`): 40 segments of 120 s, each opened and closed by a pulse 120 s apart (3.0-3.3 s
  software gaps between segments). Position p carries segment index `order[p][subject-1]` (1..40). From the
  authors' scripts (`Speech_ind` and the EEG_SNRs -> label assignments, confirmed by their `SNR` plotting arrays):

  | indices | target | SNR | | indices | target | SNR |
  |---|---|---|---|---|---|---|
  | 1-4 | speech | quiet | | 21-24 | modnoise | quiet |
  | 5-8 | modnoise | 0 dB | | 25-28 | speech | 0 dB |
  | 9-12 | speech | -5 dB | | 29-32 | modnoise | -5 dB |
  | 13-16 | modnoise | -10 dB | | 33-36 | speech | -10 dB |
  | 17-20 | speech | -15 dB | | 37-40 | modnoise | -15 dB |

  Within a group, index 4g+k is 2-min chunk k (1..4) of `odin_01_{speech,mod_amp}_..._2minsx4`. The scripts label
  the groups "100dB" (quiet), "5dB", "9dB", "12dB" and "0dB", and plot them as 5/0/-5/-10/-15; the thesis lists the
  SNRs -15, -10, -5, 0 and 20 dB, and older commented filenames say -5.5/-9.5/-12.5 dB. The adaptor uses the
  thesis values and calls the top level `quiet` (the spreadsheet notes, from the README, say "no noise"; the
  thesis says "20 dB ... without background noise or in quiet"). Condition = `<target>_<snr>`.
- The order cannot be checked against the pulses (all identical). Speech and modulated noise of the same chunk share
  the envelope, so only the chunk number is checkable from low-frequency EEG (section 9).
- **Anomalies (all 66 files surveyed by streaming the Status channel out of the RARs):**
  - S01 SNR blocks: 81 pulses. Pulse 41 (2529.56 s) opens a segment that never closes; the next pulse follows
    83.37 s later and the remaining 40 pulses pair up normally. Interpreted as a segment aborted at a break and
    replayed; the lone pulse is skipped (`stray_pulses_2048` in the sidecar), the 40 pairs map to the 40 positions.
    (The authors' rule for 82 pulses drops entries 41-42; no file has 82.)
  - S11 SNR blocks: 80 pulses, but every segment lasts 116.05 s (EEG clock), recorded 2022-06-09 while S11's quiet
    files are from 2022-05-12; a 222.8-s break after segment 20. No shipped stimulus is 116.05 s long (a different,
    earlier stimulus version; the authors' script comments "no random SNR conditions yet" next to S11).
    **Skipped** (`SKIP` in the adaptor), open question 2.
  - S11 noise: 15 pulses; the first (expected at ~8.66 s, inside the recording) is missing; the other 15 match
    wav pulses 2-16 (intervals within 1 ms) and give the onset (`missing_pulses_at_start=1`).
  - All other quiet files: 16 pulses (32 for S03/S04); all other SNR files: 80 pulses.

## 4. Speech features available
- Raw audio (wav channel 1), 44.1 kHz, LibriVox *The Children of Odin* (Padraic Colum), female narrator. The thesis
  says part 1 chapters 2 and 5; the files are named odin_01 / odin_04 / odin_05 (LibriVox file numbers). Modulated
  noise: speech-shaped noise x the speech envelope (Praat), i.e. the same envelope as the speech chunk.
- The trigger track (channel 2) is not stored (assumed sent only to the trigger box; insert earphones would make the
  500-ms pulses audible otherwise; not documented).
- **Not shipped: the background speech-shaped noise** of the SNR blocks (target fixed at 65 dBA, noise level set
  by the SNR). The stored stimulus is the target only; the sidecar has `snr` and `masker`.
- No transcripts or word alignments. Same audio as vanheusden2020 (envelope r 0.95-1.02: its odin_4_1..4_4 are the
  four sections of odin_04, odin_1_1..1_3 lie inside the odin_01 chunks); different participants.

## 5. Neural data
- BioSemi ActiveTwo, 2048 Hz, 417 Hz hardware bandwidth, CMS/DRL (no reference; kept). 40 channels: A1-A32,
  GSR1-2, Erg1-2, Resp, Plet, Temp, Status; S07 was recorded with a 224-channel montage (A-G), of which only A is
  used. No EXG: no mastoids, no EOG. GSR/Erg/Resp/Plet/Temp are constant (unconnected) and dropped; Status dropped
  after reading the triggers.
- A1-A32 renamed to the biosemi32 template (Fp1, AF3, F7, ...): the authors drop indices 6 and 23 as "T7-8", which
  is the template order. Positions are template positions; no digitisation.
- Units: BDF in uV, scaled to V by MNE. Output 1024 Hz (2048 / 2, the rule's choice with the fewest artefacts).
- Bad channels: section 9.

## 6. Alignment
- **Triggers are hardware, locked to the sound card** (inferred): Status bit 0 pulses reproduce the trigger-track
  pulses of each wav (same intervals to < 0.35 ms after a linear fit, every quiet file), i.e. the second output of
  the RME Fireface UC went to a trigger box into the BioSemi. Pulse width in the EEG 44-61 ms (trigger box) vs
  500 ms in the wav; rising edges are used.
- Onset of a quiet trial = intercept of the fit EEG sample = a * wav time + b over all pulses (wav sample 0); of an
  SNR segment = the rising edge of its opening pulse (chunk start = trigger-track edge k).
- Not corrected: trigger-box latency, ER-2A tube delay (~1 ms for ER-2-type tubephones; not documented here).
- **Drift** (EEG clock vs sound card): quiet files -24.0 to -24.8 ppm (pulse fit over 15-26 min, all 21 subjects
  with 16/32 pulses); SNR files: mean over 40 segment durations / chunk lengths, -22.6 to -23.6 ppm (21 subjects; one
  sample in 120 s = 4.07 ppm, so single segments are quantised), consistently ~1 ppm less negative than the quiet
  fits (0.12 ms per 120 s, a quarter sample; probably edge latency of the closing pulse). Per subject and file in
  `tmp/review/deoisres2023/figures/drift_per_subject.png`, values in `timing.json`. -24 ppm is 23 ms over a 15-min
  trial and 37 ms over 26 min.
- **Stimulus artefact as a timing check (S03).** S03 CP2 (also the channel with extreme 50 Hz) carries an
  electrical copy of the raw audio: 80-400 Hz EEG vs raw audio peaks at -1.96 ms (speech story; -1.94 to -2.00 ms in
  each quarter) and ~-2.0 ms (modulated-noise story, 3 of 4 quarters). Positive = EEG after audio, so the
  trigger-derived timeline is **~2 ms late relative to the sound card's electrical output** (trigger-box latency,
  most likely). The sound reaches the eardrum later by the ER-2A acoustic delay (not documented), so the offset to
  the acoustic onset is smaller. Not corrected (constant offsets are documented, not applied). S11 shows a weaker
  copy with unstable lags; the other pilot subjects none. `figures/artefact_xcorr.png`.
- Adaptor: `drift_correction=True` (default, per the repo rule for hardware-derived drift) folds the per-file
  estimate into the single 2048 -> 1024 Hz resample (`crop_on_audio_clock`); `False` keeps the nominal rate. The
  measured value is in the sidecar either way (`drift_ppm`, `drift_corrected`).

## 7. Cross-subject duration check
- SNR segments: EEG durations 119.997-119.998 s for the 120.000-s chunks in all subjects except S11 (116.05 s).
- Quiet files: the pulse spans match the wav spans after the -24 ppm slope; residuals <= 0.34 ms (sub-sample).
- So jitter is below one 2048-Hz sample relative to the sound card (sidecar `jitter_ms` 0.5 = one sample).

## 7b. Data size (from stimulus durations)
- Speech only: 19 subjects x 0.925 h (929.7-s story + 20 x 120 s), S03/S04 1.095 h (1542-s story), S11 0.258 h
  (story only; SNR blocks skipped): **20.0 h**, mean 0.91 h per subject (range 0.26-1.10).
- With the modulated noise: 40.0 h (typical subject 1.85 h).
- Unique speech audio: odin_04_and_05 (1542 s, contains odin_04) + 4 x 120 s chunks = 0.56 h (the sheet guessed
  0.25 h). The /da/ recordings (~4 min per subject) are not counted.

## 8. Open questions (recommended defaults in brackets)
1. Drift correction on by default? [yes: hardware-derived, the repo rule; -24 ppm]
2. S11 SNR blocks (116.05-s segments, unknown stimulus version)? [skip; ask the authors which stimulus was played]
3. Top SNR level: "quiet" (README per the sheet) or 20 dB SNR (thesis)? [quiet; recheck with SIN_README.txt]
4. Store the SNR-block target only (masker not shipped)? [yes, with `snr`/`masker` in the sidecar; ask the authors
   for the speech-shaped noise file]
5. /da/ recordings? [not standardised: not continuous speech]
6. RAR extraction in the shared downloader (`extract_archives`, e.g. via bsdtar/libarchive)? [add on main]
7. S03 CP2 (electrical stimulus artefact + 50 Hz at 233x the 30-45 Hz level) in `info['bads']`? It carries EEG too,
   so the rule ("flat or noise-only") does not cover it. [yes: it fakes a brainstem response at -2 ms]
8. The ~2-ms trigger latency (section 6)? [document, do not apply]

## Upstream issues
- S11 SNR-block recording uses 116.05-s segments that match no shipped stimulus.
- S01 SNR-block recording has one unpaired pulse (aborted segment).
- The background speech-shaped noise of the SNR blocks is not shipped.
- `SIN_README.txt` is listed in the record (not checked here: the local copy lacks it).

## 9. Pilot (2026-11-23): S01, S03, S07, S11, S20
Chosen to cover the special cases: S01 stray pulse, S03 26-min version, S07 224-ch montage, S11 missing pulse and
skipped SNR blocks, S20 typical. 170 trials (42 per subject, S11 2), 5.2 GB at 1024 Hz, drift correction on.
Standardisation log `tmp/review/deoisres2023/standardise.log`.

**Bad channels** (`bads.py`, `figures/bads_rms.png`, `bads_survey.json`): 1-40 Hz RMS per channel relative to the
montage median: no flat channel (minimum 0.33x), only frontopolar channels above 3x (Fp1/AF3/Fp2 up to 4.9x in
S07: blinks, no EOG recorded). Line noise (50 Hz / 30-45 Hz PSD): S03 CP2 233x, S11 CP1 150x and S11 overall
(median 32x); these channels still carry EEG. `BADS` left empty (open question 7).

**Order check** (`chunk_check.py`, `figures/chunk_order_check.png`, `chunk_check.json`): backward model (0-300 ms,
1-8 Hz, 64 Hz) trained on each subject's two story trials, reconstructing each 2-min segment. Per segment the
labelled chunk wins only at chance (r 0.02-0.08: ignored speech, 2 min). Pooled over the 40 positions, the
subject's own order column beats the other three distinct columns and 99.2% (S01), 99.4% (S03), 94.0% (S07) of
2000 shuffled orders; S20 inconclusive (88%, its decoder gives negative r). Supports the order sheet and the S01
pulse pairing.

**Validation** (average reference, 32 EEG; `tmp/review/deoisres2023/validation/`, figures `*/validation.png`):

| subset | low r (p_circ / p_mismatch, subj sig) | mlr SNR (p) | brainstem SNR (p) | tier |
|---|---|---|---|---|
| pooled, all trials | 0.012 (0.020 / 0.048, 4/5) | 1.12 (0.010) | 1.05 (0.22) | mlr |
| quiet (stories + quiet blocks) | 0.019 (0.020 / 0.048, 2/5) | 1.34 (0.010) | 1.19 (0.010) | (brainstem) |
| quiet without S03 | - | 1.35 (0.010) | 1.13 (0.069) | mlr |
| stories only (2 trials/subj) | 0.0045 (0.098 / 0.048) | 1.24 (0.010) | 1.07 (0.17) | none (low fails) |
| speech, all SNRs | 0.019 (0.020 / 0.048, 3/4) | | | low |
| modulated noise, all SNRs | 0.013 (0.020 / 0.048, 2/4) | | | low |
| SNR quiet / 0 / -5 dB | 0.024 / 0.015 / 0.017 (all 0.020) | | | low |
| SNR -10 / -15 dB | 0.002 / -0.004 (0.35 / 0.78) | | | none |

- Low-frequency TRF (pooled): peaks at ~70, 170 and 280 ms, nothing at negative lags. r is small (ignored speech
  under a subtitled film) and falls with SNR as in the thesis; -10/-15 dB fail as expected.
- The story-only low tier fails because leave-one-trial-out with two trials trains on speech and tests on
  modulated noise (and vice versa).
- 30-60 Hz: a Pa-like peak at ~37 ms on quiet trials, above the null; pooled passes but stays inside the null band.
- 30-250 Hz: the TRF has spikes at -3..0 ms = the S03 stimulus artefact (section 6). The quiet-trial brainstem pass
  depends on S03 (fails without it, p 0.069). **Tier: mlr** (pooled and quiet).
- The validator's brain-based per-trial lag (jitter SD 210 ms, 12 offsets at the edge) is noise at r ~ 0.01, not a
  timing measurement; the hardware pulses give sub-ms jitter (section 7).
