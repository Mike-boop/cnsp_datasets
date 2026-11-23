# chen2026: ChineseEEG-2, 128-ch EGI EEG, Passive Listening (8) and Reading Aloud (4), two Mandarin novels

Explorer notes, 2026-11-22 (written while the download ran: sub-01/02 checked from partially downloaded zips);
all 8 listeners checked and the per-chapter latency/drift campaign done on 2026-11-23 (section 6b). Scratch scripts,
tables and figures:
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
5. **The sound starts ~0.5 s after the trigger-implied onset, and this latency varies by chapter** (all 8 listeners,
   section 6b: listener medians 504-581 ms, most chapters within +-30 ms of their listener's median, 8 chapters
   0.1-1.0 s later). The triggers are scheduled on the presentation PC clock from the moment `sd.play()` was
   *requested*, so they cannot see the audio output latency; it differs between listeners for the same wav, so it is
   playback-side. Proposed per-chapter timing table: section 6b (not applied; user decision pending). Drift ~+16 ppm
   (EEG-derived, small).
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
   request time; jitter averages out over 28-500 events). CH markers are not used. Use the robust matcher
   (`triggers2.py`, section 6b): dropped events and multi-chapter files are common.
3. Onset = t0 + L. **Superseded by section 6b** (2026-11-23): L from a per-chapter timing table (listener median,
   with per-chapter values where the EEG shows a significant deviation; 8 chapters start 0.1-1.0 s late, so a
   dataset-wide 0.50 s is not adequate). The adaptor would read the table (precedent `yang2026_base/drift.py` ->
   `drift.csv`). Pending the user's decision.
4. Drift: ~+16 ppm from the EEG (section 6b); proposed: document, not apply. Native rate 1000 Hz kept.
5. Trial = one chapter (27 LP + 9 or 8 GD per listener); prefaces excluded (practice). Each wav is used whole; the
   chapter file contains the full wav in every case checked (10-96 s spare at the end).

### 6b. Per-chapter latency and drift campaign (2026-11-23, all listeners; nothing applied)
Scratch: `tmp/review/chen2026/` (`scripts/triggers2.py`, `make_t0.py`, `prep_cache.py`, `dnn_scan.py`,
`decoder_scan.py`, `joint_fit_synth*.py`; tables `triggers2.csv`, `t0_table.csv`; figures under `align/`).

**Robust trigger matching (`triggers2.py`).** `triggers.py` needs the exact ROWS count per CH-delimited segment and
fails on dropped events, runs without any CH and multi-chapter files. `triggers2.py` instead takes, per file and json
chapter, the mode of all (EEG ROWS - json ROWS) differences (5 ms bins), keeps json events with an EEG event of the
same type within 30 ms, accepts the chapter if >= 50% of its ROWS are found, and fits t0 + (1 + d) a on the inliers
(two refits, tolerance max(15 ms, 4 SD)). CH markers are not used. `make_t0.py` keeps per listener x chapter the best
covered match (>= 80% of the json ROWS; json chapters < 10 rows, i.e. RA-only entries, and prefaces dropped).
- Result (01-05, 07; 06 and 08 pending): **every heard chapter matched** except sub-05 LP 14 and LP 27. f1 group 9 GD
  + 27 LP, m1 group 8 GD + 27 LP. Residual SD 1.9-4.4 ms, wav inside the file with >= 10.3 s spare in every chapter.
- **Group m1 confirmed**: 05 and 07 follow m1's json timeline in every chapter; Garnett Dream runs 1 = ch 1-4,
  2 = ch 5-8.
- Dropped/extra events are common: up to 4 ROWS missing per chapter (e.g. sub-07 LP 15 146/150, sub-04 LP 25
  138/145); the old ROWS+ROWE fit broke on mis-paired ROWE (sub-02 LP 14: 1 s SD; ROWS-only fine).
- CH markers missing at the start of GD 4/6/8 (f1 group), GD 4/5/7 (m1 group) and LP 8, 15, 25 in several
  listeners; sub-04 LP 25 (run-211) has no CH marker at all.
- **sub-05**: LP run-114 is 5.8 s with no ROWS, run-213 is 12.9 s with 1 ROWS: the EEG of **LP 14 and LP 27 is not in
  the release** (paper: "triggers missing for 10 min" of ch 27; ch 14 not mentioned). LP run-17 is a 1.6 k-s file
  holding ch 7-13 back to back (ch 8-13 also shipped as their own files, identical fits): use the single-chapter
  files. sub-05 also ships stray `*_bad_channels.json` (empty lists) and `*_ica_components.json` (40 x 3229 matrix,
  `exclude` indices) next to every run: preprocessing leftovers, ignore.

**`align/scan.py:joint_fit` on synthetic data (first use; `joint_fit_synth.py`, `joint_fit_synth2.py`).** Score
matrices with a known onset and drift (Gaussian peak, sigma 60 ms, white or lag/window-correlated noise), 5-s windows
at 1-s hop, 128 Hz. Onset: unbiased (median |bias| <= 20 ms), RMSE 20-35 ms for per-window SNR >= 0.2 and >= 300 s;
breaks down (RMSE > 300 ms) at SNR 0.05-0.1 in short chapters. **Drift: biased towards 0 and imprecise**: RMSE 50-130
ppm for single chapters of 300-600 s even at SNR 0.5, 43 ppm at 1200 s / SNR 0.2, and the median estimate sits
exactly at 0 for many settings (the linear lag interpolation smooths the noise at every drift except multiples of a
sample, so the argmax favours b = 0; smoothing the scores along lags helps only partly). Jackknife SEs are not
calibrated in the breakdown regime. Consequence: per-chapter DNN drift is not usable here; drift has to be pooled
and estimated from smooth (decoder) curves.

**DNN lag scan (`dnn_scan.py`, fs128_1020-64 broadband, lags -1.5..+0.5 s around t0).** chen2026 is weak for the
accou2023 classifier: per-window score noise SD ~0.45 vs a peak of ~0.1 above the curve's baseline, curves jagged
sample-to-sample, and a mismatched-envelope null reaches the same prominence in most short LP chapters. sub-01: clear
peaks only in GD 4, 5, 7, 8 (latency 0.53, 0.52, 0.59, 0.73 s after t0); figure `align/dnn_curves_sub-01.png`.
The listener-specific backward decoder (crossdec) is far more sensitive, so it is the primary per-chapter estimator
below; the DNN is a second, independent estimator for chapters where the decoder is weak.

**Analysis cache (`prep_cache.py`).** Per chapter, from the as-shipped zip: VREF (Cz) added as zeros, HydroCel-129
montage, bad channels for the analysis = SD (1-40 Hz) > 5x or < 1/5 of the median (0-2 per chapter; a z-score rule on
log SD flagged ~30 posterior channels and was dropped). DNN input = the classifier's own steps (0.5 Hz high-pass,
128 Hz, 64-ch 10-20 interpolation, average reference); decoder input = 129 ch with bads interpolated, average
reference, 1-8 Hz, 50 Hz. Both start at floor(t0 * fs); the sub-sample remainder is added back to every latency.

**Decoder estimator (`decoder_scan.py`).** Ridge backward decoder, EEG lags 0-240 ms, trained leave-one-chapter-out
on all other chapters of the same listener; target = envelope at shift s after t0, s on 0-4 s (a 1.5-s range clipped
real latencies). Pass 1, unanchored: the training shift S0 is chosen on 0.2-1.0 s by the mean held-out r at S0
(sub-01: flat maximum 0.44-0.52 s, S0 = 0.52 s). Pass 2: training chapters placed at their own pass-1 latency.
Per held-out chapter: r vs shift (20 ms grid, parabolic peak), jackknife SE over 10 contiguous chunks, z of the peak
against 10 mismatched envelopes (other chapters), 30-s window curves (drift) and odd/even 30-s block halves
(validation). Strong = z >= 5 and SE <= 25 ms. What the decoder measures is relative to its training shift: the
absolute level assumes the response sits inside the 0-240 ms lag window (envelope responses ~100-150 ms), so the
absolute latency is good to roughly +-50 ms per listener, the relative latencies to the jackknife SE.

**DNN estimator.** Mean lag-scan curve smoothed along lags (Gaussian, 23 ms), global peak over 0-4 s, z of its
prominence against 5 mismatched envelopes, jackknife SE over 10 window chunks; strong = z >= 4 and SE <= 40 ms. The
DNN is on its own (accou2023) scale: per listener, offset = median(DNN - decoder) over chapters strong in both.
Caveat found on the way: an earlier version picked the DNN peak within +-0.3 s of the decoder latency, which made the
two "agree" by construction (it seemed to confirm sub-01 GD 9 at 1.19 s; unrestricted, the DNN finds no significant
peak there). Only unrestricted DNN peaks are used.

**Proposed per-chapter latency (`analyse_timing.py`)** = decoder if strong; else DNN - listener offset if the DNN is
strong; else the listener median (fallback for weak chapters).

**Results, all 8 listeners, 281 chapters** (`align/summary/sub-XX.json`, `sub-XX_chapters.csv`, figures
`align/summary/sub-XX_timing.png`, `sub-XX_decoder_curves.png`, `overview.png`; proposal
`tmp/review/chen2026/timing_table_proposal.csv`):
| listener | decoder strong / DNN / fallback | S0 (s) | median L (ms) | IQR (ms) | late outliers (> median + 100 ms) | halves: median abs(A - B) (ms), r without outliers | held-out r: own / median / 500 ms | drift Theil-Sen ppm [95% CI] |
|---|---|---|---|---|---|---|---|---|
| 01 | 32 / 0 / 4 | 0.52 | 511 | 493-534 | GD 8 612, GD 9 **1194**, LP 7 661, LP 8 762 | 7, 0.93 | .212 / .187 / .187 | +15 [-7, +52] |
| 02 | 5 / 5 / 26 | 0.60 | 581 | 566-610 | LP 21 752 (DNN) | 50, -0.23 | .060 / .076 / .024 | (+144, uninformative) |
| 03 | 18 / 0 / 18 | 0.56 | 544 | 533-557 | LP 9 **1565** | 12, 0.13 | .136 / .124 / .100 | +16 [-4, +36] |
| 04 | 20 / 0 / 16 | 0.56 | 545 | 528-553 | - | 8, 0.92 | .125 / .111 / .086 | -4 [-39, +25] |
| 05 | 26 / 1 / 6 | 0.52 | 510 | 502-520 | - | 5, 0.03 | .138 / .135 / .130 | +1 [-8, +12] |
| 06 | 15 / 0 / 19 | 0.52 | 506 | 496-515 | - | 7, 0.87 | .133 / .126 / .125 | +19 [-3, +42] |
| 07 | 22 / 0 / 13 | 0.52 | 504 | 493-520 | GD 1 **917**, GD 3 732 | 7, 0.60 | .125 / .118 / .117 | +22 [-1, +43] |
| 08 | 19 / 0 / 16 | 0.52 | 505 | 495-515 | - | 12, 0.41 | .131 / .130 / .129 | -3 [-15, +15] |
- **Latency is ~0.5 s and listener-specific**: m1 group 504-510 ms, f1 group 511-581 ms. Within a listener most
  chapters sit within +-30 ms of the median; **8 chapters start 0.1-1.0 s later** (single clean decoder peak, no peak
  near the median: e.g. sub-01 GD 9, sub-03 LP 9, sub-07 GD 1 in `sub-XX_decoder_curves.png`). A constant 0.5 s would
  misplace those by up to 1 s. The same wav does not give the same latency in different listeners, so this is the
  playback side (`sd.play()`), per call.
- **Absolute level**: where both estimators are strong, DNN (accou2023 scale) - decoder = -7 ms (sub-05, 19 chapters,
  MAD 5 ms), +6 ms (sub-07, 3), -39 ms (sub-03, 3), -71 ms (sub-02, 3): the decoder's absolute latency agrees with the
  DNN reference for the good listeners. Weak listeners' absolute level is anchored by their training shift S0 (sub-02:
  flat S0 curve 0.52-0.64 s), so +-50 ms.
- **Held-out validation (step 7)**: latency from one half of the chapter, r on the other half (decoder trained on other
  chapters). Per-chapter latency beats the listener median in 7 of 8 listeners and a constant 500 ms in all 8, but
  part of the gain comes from the outliers. Without them (chapters within 150 ms of the median), per-chapter values
  help in sub-01 (.220 vs .202), sub-04 (.125 vs .111) and sub-06 (.133 vs .126), the three listeners whose
  half-estimates reproduce (r 0.87-0.93); they are neutral in 03, 05, 07, 08 (within +-0.003) and worse in sub-02
  (weak). Hence option B in the proposal table: listener median, except chapters whose estimate deviates by more than
  max(40 ms, 3 SE) (11 chapters in sub-01, 1-4 elsewhere).
- **Drift**: the decoder window method recovers injected drifts of +-50 ppm to within 0-6 ppm with the right sign
  (`scripts/inject_drift.py`, sub-01 GD 1/2/4/5). Single chapters scatter by +-25-40 ppm, so drift is pooled: per
  listener Theil-Sen -4..+22 ppm (sub-02 uninformative), median over listeners **+16 ppm**; inverse-variance pool of the
  per-listener joint_fit values (lag axis upsampled x10; sub-05 excluded, where joint_fit stuck at 0 +- 0 again)
  +16.5 +- 3.2 ppm (Garnett Dream +16 +- 3, Little Prince +13 +- 10). Sign: the sound slides later through the
  chapter, i.e. the audio is stretched by ~16 ppm in EEG time. Effect at the end of the longest chapter (1212 s):
  19 ms; median chapter (~250 s): 4 ms.
- **Circularity**: the per-chapter latencies and the drift come from the same EEG that the validation tiers will model;
  any validation score after applying them is optimistic. The held-out halves above are the honest check; the
  validator should report results with the trigger-only timing (t0 + listener median) next to them.
- Not used: `joint_fit` per chapter (bias to 0, grid-edge hits on short chapters), DNN drift.

**Open decisions for the user (nothing applied):**
1. Onsets: (A) per-chapter latency for every strong chapter (`latency_s`), (B) listener median except
   significantly deviating chapters (`latency_optionB_s`), or (C) one constant per listener. Recommended: B, which
   keeps the 8 large outliers right and adds no per-chapter noise where the held-out test shows no gain; A differs from
   B by < 75 ms (mostly < 40 ms) and gains held-out r only in 01, 04, 06 (+0.007..+0.018). (A per-listener choice, A for 01/04/06
   and B elsewhere, is also defensible.)
2. Fallback for the 118 weak chapters: listener median (proposed) vs dataset median (~510 ms).
3. Drift: document +16 ppm (recommended; <= 19 ms, below the per-chapter latency uncertainty) or apply it
   dataset-wide in the single resample.
4. sub-02 (weak, 26 of 36 chapters on the fallback) and sub-01 GD 6 (no tracking in either estimator): keep with
   fallback timing (recommended) or exclude.
5. Missing EEG: sub-05 LP 14 and LP 27, sub-06 GD 4 (no file / 1 ROWS): record as absent.

### 6c. Timing proposal v2: z >= 2 (user review, 2026-11-23; nothing applied)
The user judged several trial-level peaks below z 5 convincing and asked for z >= 2, consistency checks, and an
extended search for the rest. Scripts `reclassify_z2.py`, `ext_scan.py`, `timing_v2.py`; outputs
`tmp/review/chen2026/timing_table_v2.csv` (v1 columns + `rule`, `latency_se_ms`, `listener_median_ms`, `v1_latency_s`,
`v1_source`), `timing_v2_overview.png`, `align/z2/sub-XX_passes.png`, `align/z2/sub-XX_ext_curves.png`,
`align/z2/reclass.csv`, `align/z2/ext_results.csv`.
- **z >= 2 on the decoder (0-4 s scan)**: 216 of 281 chapters pass (v1: 157), 59 newly admitted. Replication across
  odd/even 30-s halves: both halves within 50 ms of the full estimate in 31 of the 59 new (151 of 157 old), one half in
  26, neither in 2. Where one half disagrees, that half usually has no peak near the full estimate at all (half the
  data of a weak chapter), not a competing peak.
- **What the SE <= 25 ms check adds**: it removes 10 z >= 2 passes, of which only 2 replicate across halves, and 4 of the
  5 inconsistent ones. Kept. With it, the 49 new passes split 29 both halves / 20 one half / 0 neither.
- **Consistency**: per listener, median and robust SD (1.4826 MAD, 14-61 ms) over the z >= 2 passes; peak ratio =
  second-highest local maximum (outside +-150 ms) / main peak, clean < 0.75. Inconsistent (> 3 robust SD and not
  clean): sub-01 GD 6 (1012 ms, SE 648), sub-02 LP 16 (3753), sub-02 LP 21 (793, SE 1439), sub-06 LP 17 (2026,
  SE 1754), sub-07 GD 4 (2662, SE 2741); all but sub-02 LP 16 are also removed by the SE check. Edge artefact: sub-02
  LP 18 at -18 ms (peak at the scan boundary). Beyond 3 robust SD but clean (kept): the v1 late outliers plus newly
  sub-02 LP 4 (864 ms), sub-03 LP 4 (976 ms, halves 994/944), sub-04 LP 8 (612), sub-05 LP 11 (567), sub-06 LP 15 (590).
- Note: z near 2 is at the level of null-sampling noise. The same chapter can cross 2 with another draw of the 10
  mismatched envelopes, e.g. sub-01 LP 6 at 1.4 in the 0-4 s scan and 3.1 in the extended one, same latency.
- **Extended search** (-1..+8 s; decoder and DNN, 5-10 mismatched nulls) for the 77 chapters failing the decoder rule
  (z < 2: 65, SE > 25: 10, inconsistent 1, edge 1; sub-02 has 28 of them). Accept if z >= 2, SE <= 25 (decoder) / 40 ms (DNN),
  not at the range edge, latency >= 0, and consistent. **No extended-range peak was found**: the 11 peaks with z >= 2
  outside the 0-4 s window are either at negative latency (-0.8..-0.9 s, i.e. before the playback request; all in short
  LP chapters with multi-peak curves, e.g. sub-04 LP 23 DNN z 15.8, peak ratio 0.95), or at +4.8..+6.5 s with SEs of
  2-5 s. Accepted inside the original window: 3 decoder rescans (sub-01 LP 6 575 ms, sub-04 LP 12 518, sub-08 LP 20 500)
  and 9 DNN peaks (DNN - listener offset; offsets as before, else the pooled -8 ms; sub-02 GD 2, GD 3, LP 12, 14,
  16, 17, 21, sub-06 LP 27, sub-07 LP 20; 451-754 ms).
- **Counts per listener** (decoder z >= 5 / decoder z >= 2 / rescan decoder / DNN z >= 2 / listener median):
  01 32/2/1/0/1, 02 5/3/0/7/21, 03 18/6/0/0/12, 04 20/9/1/0/6, 05 26/4/0/0/3, 06 15/10/0/1/8, 07 22/8/0/1/4,
  08 19/5/1/0/10; total 157/47/3/9/65 (v1: 157 decoder / 6 DNN / 118 median).
- Effect: only 3 chapters move by > 100 ms against v1 (sub-02 LP 4 581 -> 864 ms, sub-02 LP 12 581 -> 754, sub-03
  LP 4 545 -> 976); the other new admissions are within tens of ms of the listener median. Listener medians now over
  the z >= 2 passes (e.g. sub-01 506 ms, sub-02 583 ms). Option B is recomputed the same way (`latency_optionB_s`).

### 6d. Adaptor (2026-11-23; the user's z >= 2 rule)
- `timing.csv` (repo; built from the v2 table by `tmp/review/chen2026/scripts/make_timing_csv.py`): one row per
  listener x chapter (281): file, `t0_s` and trigger-fit details, `latency_s` (z >= 2 rule; default),
  `latency_optionB_s` + `optionB_per_chapter`, `listener_median_s` (one value per listener, identical to the fallback
  values; an earlier double rounding gave sub-03 0.5458 vs 0.5457), `listener_latency_rsd_ms` (robust SD of the
  per-chapter latencies about the median, 14-33 ms; used as `jitter_ms` for median-based trials), `rule`, `rule_z`,
  `latency_se_ms`, odd/even `halves_*`, `peak_ratio`, decoder values.
- `timing.py` recomputes the t0 part from events.tsv + the reader json and checks it against `timing.csv` (file,
  t0 within 0.01 ms, ROWS found, event count, residual SD; exit 1 on a mismatch): all 281 match (max difference
  0.005 ms). Trigger slope max |d| 28.9 ppm over files > 2 min (meaningless for drift, same clock). The latency
  columns come from the EEG analysis scripts, now in the repo under `timing/` (README there: run order, inputs, outputs,
  rule; paths via environment variables in `timing/settings.py`). Re-running the light steps (t0 table, analysis,
  re-classification, v2 table, make_timing_csv) on the stored scans reproduced `timing.csv` byte for byte (2026-11-23).
- Adaptor options: `latency` = `chapter` (default) | `option_b` | `listener_median`; `drift_ppm` (default 0; the
  +16 ppm estimate is in the provenance as `drift_ppm`, applied only if passed); `audio_dir` (default
  `<download>/ChineseEEG-2_audio`, the holtze2021_audio layout: download or link the chen2026_audio entry there).
  With drift 0 the onset is rounded to the nearest sample (<= 0.5 ms, below the latency SEs), so the native 1000 Hz
  samples are kept without interpolation; with drift, onset and drift go into one quintic-spline interpolation
  (`crop_on_audio_clock`).
- Trials: condition = story, session = BIDS session (1 garnettdream, 2 littleprince; the listening order is not
  recoverable from the files), trial = chapter, stimulus `<story>_<reader>_chNN` (12 kHz wav, left channel). 129 EEG
  channels: E1-E128 + VREF (zeros; Cz position of the HydroCel-129 template), original reference, V. Bads per participant
  (`bads.json`, written by `bads.py`): flagged (SD 1-40 Hz > 5x or < 1/5 of the median) in >= 20% of the chapters.
  Per-trial flags (first version) were unstable (9-25 distinct channels per listener, flags come and go with the
  impedances) and broke the validator, which needs one channel set per subject. `alignment_method` = `dnn` when a
  per-chapter EEG latency is used, else `sw_trigger` (t0 + listener median of the EEG estimates); `jitter_ms` = the
  latency SE, or the listener spread for median-based trials.
- Size: one 387-s trial = 200 MB (float32 fif) + audio; ~5.7 GB EEG per listener, ~48 GB for all 8.
- Review (agent `reviewer`): applied: latency source taken from `rule` / `optionB_per_chapter` instead of comparing
  values; jitter for median trials; wav format check; NaN-safe provenance floats; line lengths; stronger timing check.

**Pilot and validation (2026-11-23; sub-01, 02, 05 = 105 trials, 9.2 h; average reference; validator `low,mlr,brainstem`).**
Two standardisations of the same EEG, differing only in the onsets: `latency="chapter"` (per-chapter EEG latency) and
`latency="listener_median"` (trigger-only timing, t0 + listener median). Scratch: `tmp/review/chen2026/
standardised_v2`, `standardised_trigger_v2`, `validation_{chapter,trigger}_v2/` (validation.json, validation.png).
| timing | tier | low: mean / median r | subjects sig. | TRF peaks | validator trial offsets SD / MAD | mlr | brainstem |
|---|---|---|---|---|---|---|---|
| per-chapter | low (mlr*) | 0.0156 / 0.0178 | 3/3 | ~120, 234 ms | 173 / 44 ms | SNR 1.07, p 0.02* | SNR 1.01, p 0.30 |
| trigger-only | low | 0.0116 / 0.0121 | 2/3 | ~140, 250 ms | 192 / 88 ms | SNR 1.04, p 0.34 | SNR 1.03, p 0.34 |
- Per subject (low r): sub-01 0.019 vs 0.012, sub-02 0.010 vs 0.006, sub-05 0.018 vs 0.016 (per-chapter vs trigger-only).
- **Circularity effect**: per-chapter timing raises the mean r by ~35% and halves the validator's per-trial offset MAD.
  The latencies were estimated from this EEG (decoder, held out per chapter), so part of the gain is circular; the
  held-out-halves test (section 6b) is the non-circular evidence that the per-chapter values are real.
- *The mlr "pass" is an artefact: the 30-60 Hz and 30-250 Hz TRFs are a regular ~10-ms ripple at all lags (-75..+75 ms),
  in both timings, i.e. a stimulus-locked periodicity (mains-related hum in the recordings and the EEG, inferred) and
  no response. **Validation tier: low** (cortical tracking only; no evidence for usable high-frequency responses).
- DNN offset vs accou2023 (`data_campaign/scripts/dnn_offsets.py` via `tmp/review/chen2026/scripts/dnn_offsets_chen2026.py`,
  +-500 ms): per-chapter +13.6 ms (95% CI over 3 subjects -169..+77), trigger-only +7.9 ms (-133..+85); per subject
  (01, 02, 05) -169/+77/+13 and -133/+84/+7 ms. The pooled curves are clean and peak near 0, so the absolute onset level
  matches the accou2023 convention to ~10 ms; single subjects are unreliable (weak tracking of this dataset by the
  classifier; sub-05, the only listener with many DNN-strong chapters, gives +13 / +7 ms). Figure
  `tmp/review/chen2026/dnn_offsets/offsets.png`. Documented, not applied.
- First pilot (`standardised`, `standardised_trigger`) used per-trial bads and broke the validator (subjects with
  different channel sets); superseded by the `_v2` folders (same EEG samples, per-participant bads).

## 7. Cross-subject duration check
- Trigger-derived duration: the ROWS/ROWE span equals the json span to within the 3 ms jitter in every chapter (|d| <=
  6 ppm for chapters > 2 min). End-of-audio markers do not exist in PL. Because the triggers and their timestamps share
  the presentation-PC clock, this check is a consistency check of the trigger path, not a drift measurement.
- Stimulus vs file: every wav fits inside its chapter file with >= 10.3 s to spare at the end (all 8 listeners, 281
  chapters; `t0_table.csv` `margin_end_s`).
- Same wav, different listeners: the latency differs per chapter (up to 1 s for the late outliers, section 6b), i.e.
  jitter of the playback start, not drift. Drift from the EEG windows: ~+16 ppm pooled (section 6b).

## 8. Data size (from the wavs; listener totals exclude the prefaces)
- PL: f1 group 5561.6 s (LP 1-27) + 5363.1 s (GD 1-9) = **3.035 h** per listener; m1 group 5561.6 + 6170.6 s =
  **3.259 h**. 8 listeners: **25.2 h** (LP 12.4 h, GD 12.8 h). The paper's 21.6 h is "~3 h x 8" rounded down. Minus the
  chapters whose EEG is not in the release: sub-05 LP 14 (240.0 s) and LP 27 (169.7 s), sub-06 GD 4 (1225.7 s), 0.454 h
  in total -> **24.72 h** (281 chapters; from timing.csv: per listener 2.92-3.26 h, mean 3.09 h; Garnett Dream 12.47 h,
  Little Prince 12.25 h).
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
1-3. Latency, per-chapter onsets and drift: done for all 8 listeners on 2026-11-23 (unanchored, 0-4 s, decoder + DNN);
   the decisions are listed at the end of section 6b [option B timing table; document the +16 ppm drift].
   (Earlier default "constant L = 0.50 s" is superseded: 8 chapters start 0.1-1.0 s late.)
4. sub-01 Garnett Dream 6 (run-21) shows no envelope tracking (z 2.0; nothing within +-30 s or with any other wav)
   although its triggers are normal and the EEG looks clean: keep, or drop? [keep with fallback timing; still no
   tracking with the 0-4 s decoder or the DNN (2026-11-23)]
5. sub-02 tracks weakly overall (decoder strong in 5 of 36 chapters, DNN in 8): keep? [keep; it is the data; 26
   chapters on the listener-median fallback]
6. Include the prefaces (practice, 57-80 s, same reader)? [no; the authors exclude them]
7. ~~Include Reading Aloud?~~ Decided by the user (2026-11-22): skipped (section 9). Registry: add `"ReadingAloud/*"`
   to the `chen2026` exclude list? [yes, saves 7.7 GB]
8. Reference: add VREF (Cz) back as zeros before average reference? [yes]
9. sub-05 LP 27 and LP 14, sub-06 GD 4: the EEG is not in the release (12.9-s / 5.8-s files, no run-14 file).
   [record as absent]
10. ~~Group m1 (05-08)~~ verified 2026-11-23 (section 6b): reader m1, Garnett Dream runs 1-4 / 5-8.
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
