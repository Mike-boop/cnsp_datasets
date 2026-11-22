# chen2026: ChineseEEG-2, 128-ch EGI EEG, Passive Listening (8) and Reading Aloud (4), two Mandarin novels

Explorer notes, 2026-11-22 (written while the download ran: sub-01/02 checked from partially downloaded zips; group m1
= 05-08 still pending). Scratch scripts, tables and figures:
`/data_storage/gu08wuvu/datasets/tmp/review/chen2026/` (`scripts/*.py`, `triggers*.csv`, `decode*/`, `xcorr_*.txt`,
`code/` = clone of the authors' repository). That folder is temporary; every number that explains a choice is copied
here.

**Headline.**
1. PassiveListening (PL): 8 listeners each heard one reader's recordings of *The Little Prince* (27 chapters) and
   *Garnett Dream* (9 or 8 sections), one wav per chapter, ~3.0-3.3 h per listener. **Listeners 01-04 heard reader
   f1, 05-08 heard reader m1** (HF audio repo note; paper Fig. 1b/2; confirmed by trigger timelines, section 3).
2. The audio is **not** on Science Data Bank; it is the Hugging Face repo `moriartyJM/ChineseEEG-2_audio` (12 kHz
   stereo, L = R). The per-reader `events_data.json` there is the reader's own EEG trigger timeline, which the
   listening script replayed as ROWS/ROWE triggers. This gives a **sample-level fingerprint** for every listening
   chapter: ROWS/ROWE times in the listener's EEG fit the json timeline with ~3.3 ms SD (section 6).
3. **No stimtrack/audio channel** (EGI, 128 scalp channels only; VREF = Cz dropped by the authors). All triggers are
   **software** (PsychoPy/sounddevice -> zmq -> egi-pynetstation over TCP), although the paper says "hardware-level".
4. **CH markers in PL are unreliable** (missing at the start of runs 14, 21, ...; relative numbering in places):
   map chapters by run name + ROWS timeline fit, not by CH labels.
5. **The sound starts ~0.5 s after the trigger-implied onset, and this latency varies by chapter** (sub-01, 14
   chapters with good tracking: 471-617 ms, median 498 ms; section 6). The triggers are scheduled on the presentation
   PC clock from the moment `sd.play()` was *requested*, so they cannot see the audio output latency; it differs
   between listeners for the same wav, so it is playback-side and cannot be pooled across listeners.
6. ReadingAloud is **skipped** (decided by the user, 2026-11-22; section 9).

## 1. Source
- Science Data Bank, doi:10.57760/sciencedb.CHNNeuro.00001, version V5, licence CC0 (landing page/listing,
  `scidb_files.json`). The registry entry `chen2026` (source `scidb`) downloads the raw BIDS zips, participants and
  README; derivatives (`filtered/`, `preprocessed/`) and embeddings are excluded.
- Audio: Hugging Face `moriartyJM/ChineseEEG-2_audio` (registry entry `chen2026_audio`; README front matter only
  says `license: cc`, no variant). Not referenced in the paper or the scidb README, which says the audio is in
  `ReadingAloud/` (it is not).
- Paper: Chen S, Li B, He C, Li D, Wu M, Shen X, Wang S, Wei X, Wang X, Wu H, Liu Q (2026). An EEG dataset for
  multimodal semantic alignment and neural decoding during reading and listening. *Scientific Data* 13:148,
  doi:10.1038/s41597-025-06466-8 (CC BY-NC-ND article licence; the data are CC0).
- Code: https://github.com/ncclab-sustech/ChineseEEG-2 (HEAD b1c4ba8, 2026-03-22). Relevant files:
  `experiment/experiment_listen.py` + `recording_listen.py` (PL playback and triggers), `experiment/ui_experiment.py`
  + `recording.py` (RA display, audio recording, triggers), `data_preprocessing/preprocessing.py` (chapter cutting,
  BIDS export), `novel_segmentation/*.xlsx` (one row per displayed text line).
- Predecessor: ChineseEEG (Mou et al. 2024, Sci Data 11:550), silent reading of the same texts, same lab.

## 2. Layout
- `PassiveListening/sub-0{1..8}.zip` (5.4-6.6 GB each) and `ReadingAloud/sub-{f1,f2,m1,m2}.zip` (1.6-2.2 GB). Inside:
  `sub-X/ses-{garnettdream,littleprince}/eeg/sub-X_ses-S_task-{lis,reading}_run-XY_{eeg.vhdr,eeg.vmrk,eeg.eeg,
  eeg.json,channels.tsv,events.tsv,events.json}` plus per-session `space-CapTrak_{electrodes.tsv,coordsystem.json}`.
  BrainVision written by pybv 0.7.5 (IEEE float32, multiplexed).
- **Run naming** `run-XY`: X = run (1 or 2), Y = chapter within the run (README; paper "Data Records"). Little Prince:
  run 1 = ch 1-14 (`run-11`..`run-114`), run 2 = ch 15-27 (`run-21`..`run-213`). Garnett Dream: 01-04 and RA f1/f2/m2:
  run 1 = ch 1-5, run 2 = ch 6-9 (`run-21` = ch 6); 05-08 and RA m1: run 1 = ch 1-4, run 2 = ch 5-8 (paper; to be
  confirmed for 05-08 when their zips arrive). This BIDS run split is the reader's, **not** the 4 listening sessions
  of Table 1.
- One file per chapter, cut from the authors' continuous `.mff` recordings by `preprocessing.py`
  (`segment_runs`: from CH(n) minus `remaining_time_at_beginning` to CH(n+1); the last chapter to the end of the
  recording). Observed: RA files start 5.0 s before CH(n); PL files start at CH(n) (0 s) or, where the CH marker is
  missing, at an earlier point (run-14 starts 6.1/25.2 s before the sound, run-21 34/57 s before; section 6). The PL
  Garnett Dream `run-11` also contains the preface (practice, 20 ROWS) played before ch 1; the Little Prince `run-11`
  starts at CH01 (no preface).
- Audio repo: `{littleprince,garnettdream}_{f1,f2,m1,m2}/audio_K.wav` (K = 0 preface, 1..N chapters; 12 kHz, 2 ch
  identical, int16), `events_data.json` for f1, m1, m2 (not f2), `littleprince.xlsx` / `garnettdream.xlsx` (one row per
  displayed line; garnettdream columns E/F mark the last line of each f1/m1 section), and `说明.txt` (GBK): "listening
  participants 01-04 correspond to f1, 05-08 to m1; f1 and m1 are segmented differently in garnettdream".
- `materials&embeddings/original_novel.zip` (text), README (5.4 kB, read). Derivatives not downloaded.

## 3. Stimulus <-> trial mapping
- **Listener -> reader**: 01-04 = f1, 05-08 = m1 (audio repo note; paper Fig. 1b "the audio from female and male
  subject 1 in Reading-aloud group were chosen"; Table 1 durations). Verified for sub-01 and sub-02 (f1): every
  chapter's ROWS/ROWE sequence matches f1's json timeline (section 6); 05-08 pending download.
- **Chapters heard** = audio_1..audio_27 (Little Prince) and Garnett Dream audio_1..9 (f1) or audio_1..8 (m1); audio_0
  is the preface (practice). Table 1 durations equal the wav sums exactly, e.g. 01-04 GD session 1 = ch 1-3 =
  562.14 + 654.84 + 413.94 s = 27 min 11 s; 05-08 GD session 1 = 1211.94 + 413.91 + 850.53 s = 41 min 16 s;
  LP session 1 = ch 1-7 = 24 min 43 s. So the listeners heard the shipped wavs unmodified (no trimming).
- f1's Garnett Dream folder has **audio_10 and audio_11** (355 s, 341 s) that no listener heard (Table 1 lists 9
  sections); they are RA-only and irrelevant with RA skipped.
- Same stimuli across the 4 listeners of a group; the two groups share the Little Prince text and reading pace
  (LP chapter wavs of f1 and m1 differ by <= 0.06 s) but are different recordings.
- **Mapping method for the adaptor:** segment the run's ROWS markers at CH markers (and file start); match each
  segment to the json chapter with the same ROWS count and the smallest residual of a linear fit
  (`scripts/triggers.py`). Every segment so far (29 files, 2 listeners) matches uniquely with 2.5-3.8 ms SD. CH labels disagree with this in
  several runs (section 6), so do not use them.
- RA: each reader's run-XY = chapter XY of their own audio folder; BEGN in the RA EEG = audio sample 0 (exact match
  of the json timeline, residual 0 ms; section 6).

## 4. Speech features available
- Raw audio (12 kHz, 16-bit, stereo with identical channels; L-R correlation 1.000), post-processed by the authors
  with Auphonic and Audacity (paper). Lengths are multiples of the 360-sample (30 ms) recording chunk, so they were
  not trimmed. No envelope or alignment files.
- Text: one row per displayed line (`*.xlsx`, also the novels in `original_novel.zip`). The json gives each line's
  highlight start/end (ROWS/ROWE) in the reader's EEG time, which maps to audio time as (index - begn_k)/250 s. This is
  the **display** timing (0.25 s per character), not the spoken timing: the reader's speech precedes or follows the
  highlight by -0.7..+0.3 s depending on chapter (`scripts/reader_lag.py`), so it is not a word/line alignment.
- No word or phoneme alignment. Embeddings (BERT/wav2vec2) excluded.

## 5. Neural data
- EGI HydroCel GSN 128 (paper); `eeg.json` says "Manufacturer: Brain Products" (pybv default; wrong).
- PL: **1000 Hz**; RA: **250 Hz** (paper "EEG data collection"; headers). Keep native (both <= 1024).
- 128 channels `E1`..`E128`, all type EEG. No EOG/ECG/misc, **no stimtrack/aux/Sound channel**, no trigger channel
  (markers in `.vmrk`/`events.tsv`). EGI's VREF (Cz, E129) was dropped by the authors' reader
  (`read_mff_file`: `pick_types(eeg=True)`, `drop_channels(['VREF'])`).
- **Reference: Cz (VREF)**, inferred from EGI's recording reference and the dropped VREF; sidecar says
  `EEGReference: n/a`. Recommended: add VREF back as a zero channel (`mne.add_reference_channels(raw, 'VREF')`), then
  average reference (129 channels).
- Units: `.vhdr` declares µV (resolution 0.1, float32); MNE returns volts. channels.tsv says V. Amplitudes are
  plausible: PL 1-8 Hz per-channel SD median 29 µV (sub-01), 11-69 µV (sub-02); DC offsets of several mV (EGI is
  DC-coupled). PL has **strong 50 Hz mains** (median PSD 2.7e6 µV²/Hz at 50 Hz, harmonics at 100/150/250 Hz), so
  notch/low-pass before anything broadband.
- Filters: channels.tsv 0-500 Hz (PL) / 0-125 Hz (RA), i.e. none recorded; PSD falls to ~1e-5 µV²/Hz at 490 Hz
  (amplifier anti-alias filter).
- Digitisation: `space-CapTrak_electrodes.tsv` holds the **template** GSN-HydroCel-128 positions (identical across
  subjects, origin between the ears, NAS/LPA/RPA symmetric); no individual head shape.
- `IBEG`/`IEND` (NetStation impedance-check markers, inferred) appear in RA files (e.g. f1 GD run-13: IEND at 19.1 s inside the
  chapter, IBEG..IEND 815.7-1067.9 s after the chapter). EEG during impedance checks is unusable; mask IBEG..IEND
  where it overlaps a stimulus (none in PL so far).
- `meas_date` is not set. No recording-pause annotations (pybv files; MNE shows only `Stimulus/S n`).
- Paper exclusions: none in the release. Participants 03 and 04 were dropped from one source analysis for artefacts;
  participant 05 lacks triggers for 10 min of LP run-213 (ch 27); participant 04 needed 5 sessions (interruption in
  session 2).

## 6. Alignment
**Trigger codes** (paper Table 1, experiment README, code). `events.tsv` `trial_type` holds the name; `value`/`S n`
codes are per-file MNE enumerations, so use names.
| name | meaning | sent by |
|---|---|---|
| `BEGN` | RA: audio stream opened (= audio sample 0) | `recording.py` `record_audio`, after `pyaudio.open` |
| `STOP` | stop recording (not seen in files so far) | |
| `CHxx` | chapter start | RA: `ui_experiment.py` before the 5-s lead-in; PL: `experiment_listen.py` before loading the wav |
| `ROWS`/`ROWE` | line highlight start/end | RA: display loop; PL: replayed from the reader's json |
| `PRES`/`PREE` | preface start/end | RA only |
| `IBEG`/`IEND` | NetStation impedance check (inferred from the names; not in the paper) | NetStation |

**Hardware or software:** software, documented by the authors' code (the paper's "Temporal Alignment" claims
"hardware-level trigger synchronization"). The code sends strings over zmq to `recording*.py`, which calls
`egi_pynetstation` v1.0.1 `send_event` (event time = presentation-PC clock "now", NTP-synchronised to the amplifier
once at `connect`) from a new thread per event.

**How the PL triggers relate to the audio** (`experiment_listen.py`, `play_audio_with_triggers`): per chapter it
sends `CHxx`, reads the wav, starts `sd.play()` in a thread, sets `global_start_time = time.time()`, then busy-waits and
sends `ROWS`/`ROWE` at `global_start_time + (json_index - begn_k)/250`. So the ROWS/ROWE times are a replay of the
reader's EEG timeline, on the presentation-PC clock, relative to the moment playback was *requested*.

**Trigger fit** (`scripts/triggers.py`, `triggers.csv`): per chapter, EEG_t = t0 + (1 + d) a over all ROWS+ROWE
(a = audio time from the json). sub-01 (Garnett Dream 0 (preface)-9, Little Prince 1-3 and 10-14) and sub-02 (Garnett Dream 0-9, Little Prince
10-12); 29 files:
| listener | chapter | rows | CH label at segment start | t0 - CH | d (ppm) | residual SD / max (ms) |
|---|---|---|---|---|---|---|
| 01 | GD 0 (preface) | 20 | none | | -10 | 3.1 / 10 |
| 01 | GD 1 | 232 | CH01 | +0.040 s | -0.3 | 3.2 / 14 |
| 01 | GD 2 | 263 | CH02 | +0.138 | -0.5 | 2.8 / 14 |
| 01 | GD 3 | 169 | CH03 | +0.129 | -1.3 | 3.5 / 22 |
| 01 | GD 4 | 341 | **none** (file starts 25.2 s before t0) | | -0.0 | 3.5 / 21 |
| 01 | GD 5 | 294 | CH05 | +0.144 | -0.4 | 3.4 / 20 |
| 01 | GD 6 | 197 | **none** (56.6 s before t0) | | +0.1 | 3.2 / 14 |
| 01 | GD 7 | 282 | **CH01** | +0.045 | -0.8 | 3.3 / 18 |
| 01 | GD 8 | 235 | **none** (35.2 s before t0; file ends at a `CH03`) | | +0.1 | 3.8 / 18 |
| 01 | GD 9 | 134 | **CH03** | +0.112 | +1.3 | 3.6 / 16 |
| 01 | LP 1-3 | 75, 117, 85 | CH01-CH03 | +0.022, +0.133, +0.118 | -3.6, +4.7, +2.7 | 2.8-3.8 / 10-20 |
| 01 | LP 10-14 | 219, 55, 28, 151, 125 | CH10-CH14 | +0.123..+0.137 | -12..+14 | 2.9-3.8 / 11-20 |
| 02 | GD 0-9 | as sub-01 | same pattern (GD 4 starts 6.1 s, GD 6 33.9 s, GD 8 3.7 s before t0) | +0.036..+0.191 | -2.2..+1.2 (GD 0 +8) | 2.5-3.8 / 7-22 |
| 02 | LP 10-12 | 219, 55, 28 | CH10-CH12 | +0.132..+0.167 | -22..+3 | 2.9-3.4 / 11-16 |
- Every segment matched exactly one json chapter (ROWS count + linear fit; the next-best candidate with the same count
  is off by seconds, e.g. 3.5 s SD for GD 9, 5.0 s for LP 1 vs LP 27, both 75 rows).
- Jitter ~3.3 ms SD (max ~22 ms) per event, from the threaded zmq/TCP path.
- d ~ 0 ppm (|d| <= 6 ppm in chapters > 2 min, as expected from 3 ms jitter) is **expected by construction**: both the scheduling and the event
  timestamps use the presentation-PC clock, so these triggers cannot measure drift between the sound card and the EEG
  amplifier.
- `CHxx` precedes t0 by 22-191 ms (wav loading), so CH is not an onset.
- CH labels: missing at the start of GD 4, 6 and 8; GD 7 is labelled `CH01` and GD 9 `CH03`, i.e. numbered within the
  listening session (Table 1 sessions: GD 6-7 and 8-9). LP labels are correct so far. Chapter identity comes from the
  timeline match, never from the label.
- No `IBEG`/`IEND`/`BEGN`/`STOP` in any PL file so far.

**RA**: ROWS/ROWE in the RA EEG minus BEGN equal the json exactly (f1 GD ch 1-3, residual 0 ms), so the json is the
RA EEG timeline, and audio sample 0 = BEGN (to within the pyaudio-open -> event latency, unknown). BEGN follows CHxx by
0.22-0.24 s.

**EEG check of the PL onset** (envelope = |audio| (L = R), 1-8 Hz; EEG 128 ch average reference, 1-8 Hz, 50 Hz; sound
placed at t0; backward ridge decoder, EEG lags 0-240 ms):
1. Within-chapter decoder, 5-fold CV, envelope shifted -3..+3 s in 0.1 s steps (`scripts/decode.py`, `decode/`):
   sub-01 best shift +0.4..+0.6 s in GD 1-5, 7, 8 (z 7-15, r 0.11-0.20); GD 6 no peak (z 2.0, and none within +-30 s
   or for any other Garnett Dream wav of f1 or m1: `scripts/candidates.py`, `candidates_sub01_run21.txt`). sub-02 tracks
   weakly: +0.5 s in GD 2, 6, 7, 8 (z 3.3-7.3), no peak in GD 1, 3, 4, 5 (z 1.6-3.1). sub-02 has noisy frontal
   channels and a noisy run-13.
2. Forward cross-correlation, fronto-central E6/E7/E106/E13/E112/VREF, average reference incl. VREF
   (`scripts/xcorr.py`, `xcorr_gd_01_02.txt`): sub-01 positive peak at **570-660 ms** in GD 1-5, 7, 8 (r 0.05-0.09),
   negative at 750-970 ms. Clean speech with correct onsets peaks at ~0.1-0.2 s (momenian2024 +0.20 s), so the sound
   is ~0.45 s later than t0.
3. **Per-chapter latency, unbiased** (`scripts/crossdec.py`, `crossdec_01.txt`, `crossdec_02.txt`): decoder trained
   on all other chapters of the same listener (target at +0.5 s, GD 6 left out of training), applied to the held-out
   chapter, r vs shift 0-1 s in 20-ms steps (parabolic peak). The r curve is sharp (e.g. GD 8: r 0.03 at 500 ms, 0.17
   at 617 ms), so the peak is good to ~10-20 ms where r > 0.08.
   | sub-01 chapter | GD1 | GD2 | GD3 | GD4 | GD5 | GD6 | GD7 | GD8 | GD9 | LP1 | LP2 | LP3 | LP10 | LP11 | LP12 | LP13 | LP14 |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
   | peak (ms) | 474 | 476 | 519 | 542 | 474 | (537) | (522) | **617** | (452) | 495 | 511 | 489 | 471 | 501 | 518 | 516 | 490 |
   | r | .19 | .22 | .17 | .16 | .15 | .06 | .06 | .16 | .04 | .08 | .17 | .15 | .14 | .13 | .10 | .09 | .18 |
   In brackets: r < 0.07. Over the 14 good chapters: **median 498 ms, range 471-617 ms** (13 of 14 within 471-542 ms).
   sub-02 (weak; r 0.02-0.06 with its own decoder) peaks at 493-508 ms in GD 1-3, 7-9 and at 468 ms in GD 6 (r 0.09);
   no usable peak in GD 4, 5 and LP 10-14. Figure: `latency_per_chapter.png` (r vs shift per chapter, both listeners).
   The same wav gives different latencies in different listeners (GD 8: sub-01 617 ms with r 0.16; sub-02 495 ms
   median over 60-s windows of its within-chapter decoder, z 5.8), so the variation is on the playback side, per
   `sd.play()` call, not in the wav. (The within-chapter decoder of item 1 is biased towards its 0.1-s coarse grid,
   e.g. GD 2 403 ms there vs 476 ms here; use these unbiased values.)
4. Interpretation: output latency of `sounddevice` on the "system-default" device (paper: "no specific audio hardware
   was used"; the code starts playback in a thread and stamps `global_start_time` immediately, so stream opening and
   device buffering add to the delay). ~0.5 s suggests a high-latency path (e.g. default host API with large
   buffers or a wireless headset). Unknown and undocumented; not visible in the triggers.

**Drift (EEG, within chapter)**: held-out 60-s windows of the within-chapter decoder, Theil-Sen slope
(`scripts/slide.py`): sub-01 GD 1 +39 [-54, +129], GD 2 +31 [-96, +159], GD 3 +2, GD 4 -19 [-68, +37], GD 5 -1
[-69, +47], GD 7 +47 [-252, +117], GD 8 +208 [+80, +585] ppm (first window an outlier). Median of the 7: **+31 ppm**,
no consistent slope; the 12 kHz wav played on the listening PC shows no detectable drift against the EGI clock at
the ~+-50 ppm level (10-min chapters: +-30 ms). Not enough to justify a correction.

**EEG check of RA (own speech)** (`decode_ra/`): f1 GD 1-3, best shift -0.10 s, r 0.28-0.33, z 13-22; window peaks rise
linearly from about -150 to -55 ms across each chapter: **+177 [+123, +223], +192 [+162, +215], +221 ppm**. So the
reading PC's capture card drifts ~+190 ppm against the EGI clock. Not needed for PL (the listeners' playback is a
different device, see above). The json ROWS/ROWE timeline is on the reader's EEG clock, so in the listener's EEG the
ROWS markers slide by up to ~0.1 s per chapter relative to the speech; do not use them as line timings.

**Proposed alignment (PL):**
1. Reader by listener (01-04 f1, 05-08 m1); chapter -> wav by the ROWS timeline match (section 3).
2. t0 = intercept of the per-chapter fit of ROWS+ROWE to the json timeline (precise to < 1 ms for the playback
   request time; jitter averages out over 28-500 events). CH markers are not used.
3. Onset = t0 + L, with **L = 0.50 s** (dataset-wide constant from sub-01's 14 good chapters, median 498 ms; to be re-estimated over
   all listeners and checked with the DNN offset before standardising; the forward cross-correlation, compared with
   the usual ~0.15-0.2 s peak, suggests 0.40-0.46 s, so the final value should come from the DNN offset). Residual per-chapter error about +-50 ms
   (range -30..+115 ms in sub-01), which cannot be removed from the triggers. Option for the human checkpoint: a
   per-chapter EEG estimate for chapters with strong tracking (circular with validation; not recommended by default).
4. No drift correction (section above). Native rate 1000 Hz kept.
5. Trial = one chapter (27 LP + 9 or 8 GD per listener); prefaces excluded (practice). Each wav is used whole; the
   chapter file contains the full wav in every case checked (10-96 s spare at the end).

## 7. Cross-subject duration check
- Trigger-derived duration: the ROWS/ROWE span equals the json span to within the 3 ms jitter in every chapter (|d| <=
  6 ppm for chapters > 2 min). End-of-audio markers do not exist in PL. Because the triggers and their timestamps share
  the presentation-PC clock, this check is a consistency check of the trigger path, not a drift measurement.
- Stimulus vs file: every wav fits inside its chapter file with 10-96 s to spare at the end (sub-01/02, all 27 chapter files checked).
- Same wav, two listeners: the latency differs per chapter by up to 0.11 s (above), i.e. jitter of the playback start,
  not drift. Drift (EEG windows) ~0 +- 50 ppm. Group m1 (05-08) not yet checked (downloads pending).

## 8. Data size (from the wavs; listener totals exclude the prefaces)
- PL: f1 group 5561.6 s (LP 1-27) + 5363.1 s (GD 1-9) = **3.035 h** per listener; m1 group 5561.6 + 6170.6 s =
  **3.259 h**. 8 listeners: **25.2 h** (LP 12.4 h, GD 12.8 h). The paper's 21.6 h is "~3 h x 8" rounded down. Minus
  sub-05 LP ch 27 (513 s) if it cannot be aligned.
- RA (skipped; for the record): f1 3.228 h (GD 1-11; 3.035 h with GD 1-9), f2 3.035 h, m1 3.259 h, m2 3.033 h; total 12.5 h.
- Prefaces (practice, excluded by the authors): 57-171 s each.

## 9. Reading Aloud
**Decided by the user (2026-11-22): ReadingAloud skipped** (speech production, outside the continuous-listening
scope). The readers' recordings remain the PassiveListening stimuli (f1 for 01-04, m1 for 05-08), so the reader
mapping above stays.
- What it is: EEG (250 Hz) of 4 readers (f1, f2, m1, m2) reading aloud at a forced 0.25 s/character pace, with their
  own recorded speech (the Hugging Face wavs). Not explored beyond the checks above: BEGN = audio sample 0 (exact,
  f1 GD 1-3), decoder r ~0.3 at a negative lag (EEG leads the sound: production/EMG), +177..+221 ppm drift between the
  reading PC's sound card and the EGI clock.
- Registry: to stop downloading the RA zips (7.7 GB: f1 2.22, f2 2.20, m1 1.62, m2 1.66 GB), add `"ReadingAloud/*"`
  to the `chen2026` `exclude` list (fnmatch on the listing path, e.g. `ReadingAloud/sub-f1.zip`). Recommendation only;
  the registry was not edited.

## 10. Open questions (recommended default in brackets)
1. Playback latency ~0.5 s after the trigger-implied onset, varying by chapter (471-617 ms in sub-01): add a constant
   L to every onset? [yes, L = 0.50 s, re-estimated over all listeners and confirmed by the DNN offset before the full
   run; residual +-50 ms per chapter documented as a caveat]
   Deferred by the user (2026-11-22): no decision until more data are in. Before deciding: re-run the coarse
   (unanchored, -3..+3 s) decoder scan and the forward cross-correlation on all 8 listeners, and the DNN offset vs
   accou2023. The per-chapter refinement (`crossdec.py`) trains at a fixed +0.5 s and is anchored to it.
2. Per-chapter EEG-estimated onsets instead of a constant? [no: circular with validation and impossible for weak
   listeners such as sub-02]
3. Drift: correct? [no; EEG slopes ~0 +- 50 ppm, triggers cannot measure it]
4. sub-01 Garnett Dream 6 (run-21) shows no envelope tracking (z 2.0; nothing within +-30 s or with any other wav)
   although its triggers are normal and the EEG looks clean: keep, or drop? [keep; record as a caveat, recheck once all
   listeners are in]
5. sub-02 tracks weakly overall (r <= 0.09; no peak in 7 of 12 chapters checked): keep? [keep; it is the data]
6. Include the prefaces (practice, 57-80 s, same reader)? [no; the authors exclude them]
7. ~~Include Reading Aloud?~~ Decided by the user (2026-11-22): skipped (section 9). Registry: add `"ReadingAloud/*"`
   to the `chen2026` exclude list? [yes, saves 7.7 GB]
8. Reference: add VREF (Cz) back as zeros before average reference? [yes]
9. sub-05 LP ch 27 (paper: triggers missing for 10 min of run-213): skip, or align from its CH marker + L? [skip if
   fewer than ~20 ROWS remain to fit t0; pending inspection]
10. Group m1 (05-08): reader mapping, Garnett Dream run split (1-4 / 5-8) and latency not yet verified (downloads
    pending). [verify with `scripts/triggers.py` before the adaptor pilot]
11. Licence: data CC0 (scidb V5); the audio repo says only "cc". [treat the audio as part of the CC0 record; ask the
    authors if it matters]

## 11. Upstream issues (to report)
- Paper claims hardware triggers; code shows software triggers over zmq/TCP (pynetstation).
- The audio is only on Hugging Face (not mentioned in the paper/README; README says audio is in `ReadingAloud/`).
- PL CH markers missing at the start of several runs and partly numbered per listening session.
- `eeg.json` Manufacturer "Brain Products" (actually EGI); `EEGReference` n/a (Cz/VREF, dropped).
- ~0.5 s, chapter-dependent audio output latency not documented (playback starts in a thread after the trigger
  clock is stamped).
- The json ROWS/ROWE timeline replayed to listeners is on the reader's EEG clock, which drifts ~+190 ppm against the
  reader's audio; ROWS markers in the listener EEG therefore slide against the speech by up to ~0.1 s per chapter.
