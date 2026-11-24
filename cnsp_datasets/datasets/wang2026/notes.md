# wang2026: AASD, spontaneous auditory attention switching (Zenodo 17413336)

Explorer and standardiser notes, 2026-11-24. Scratch: `/data_storage/gu08wuvu/datasets/tmp/review/wang2026/` (logs,
csv tables, figures) and `tmp/review/scripts/wang2026_*.py`. That folder is temporary; every number that explains a
choice is copied here.

**Headline.**
1. 18 listeners, one Neuroscan CNT each (64 EEG incl. M1/M2, 500 Hz). Per subject: 2 practice trials, 6 blocks x 10
   attention-switching trials and 1 passive block of 10 trials, all 60 s. The shipped stereo wavs carry **one talker
   per channel** (left = left talker only, right = right talker only), so the left and right streams are exact.
2. Attention is self-paced and switches within trials. The listener presses a "left" (code 179) or "right" (184) key
   at each switch. The adaptor stores the presses and the attention spans as **MNE annotations** on each trial.
3. The **StimList mapping (code - 10 = mixed_NNN) is confirmed by the EEG**. S8-S11 heard 30 stimuli twice (codes
   repeat), and S12-S18 had two complementary halves. **The passive-block audio (codes 73-82) is not documented and
   could not be identified from the EEG**, so passive trials carry no stimulus (section 3).
4. Onsets are E-Prime trial codes (software, no audio copy). No drift estimate (60-s trials).
5. Upstream data problems: extensive **gel bridging** in most subjects; the VEO channel carries no blink signal in any
   subject (railed at -207.5 mV in 11); HEO and EMG are unused (section 5).

## 1. Source
- Zenodo 10.5281/zenodo.17413336 (version 17413336, 2025-10-22), registry entry `wang2026`. Files: `Stimuli
  Audio.zip` (0.19 GB), `Processed EEG.zip` (1.9 GB), `Original EEG.zip` (10.8 GB). Licence on the record: **CC-BY-4.0**
  (the article itself is CC BY-NC-ND 4.0; that applies to the paper, not the data).
- Copied from the user's md5-checked pull on woody (`/home/woody/iwpm/iwpm104h/zenodo/wang2026/17413336/`), md5 checked
  again on both ends, `unzip -t` clean. Zenodo itself was not contacted.
- Paper: Wang X, Ding Y, Ban Y, Wang L, Chen F (2026). An open non-invasive EEG dataset for spontaneous auditory
  attention switch decoding. *Scientific Data* 13:883, doi:10.1038/s41597-026-07244-w
  (`data_campaign/papers/wang2026.pdf`).
- Code: https://github.com/XXuefeii/AASD-Processing (`src/AASD_processing.m`, read, not run). It drops the last four
  CNT channels (HEO, VEO, EMG, Trigger), cuts 60 s from each code 11-70 ("only the audio-start labels"),
  band-passes 0.1-45 Hz, resamples to 128 Hz and re-references to (M1+M2)/2. Practice and passive trials are not
  processed.

## 2. Layout
- `Original EEG/S<n>/S<n>.cnt` (n = 1..18), 0.69-1.20 GB each; `Original EEG/StimList.xlsx` (62 rows: TrialID,
  AudioType Test/Train, MaleFile, FemaleFile, MixFile, Trigger, EarCondition, IsSilent = 0).
- `Stimuli Audio/mixed_{001..060,100,200}.wav`: 16 kHz stereo int16, exactly 60.000 s. The MaleFile/FemaleFile wavs
  named in StimList are not shipped, and `mix_NNN.wav` is shipped as `mixed_NNN.wav`.
- `Processed EEG/S<n>/S<n>.mat`: struct `EEG_new` with `data` (62 ch x 7680 x 60 trials, 128 Hz, uV, M1/M2 removed
  after re-referencing) and `event` (type, latency in 128-Hz samples within the epoch, urevent, duration, epoch).
  Epochs are in recording order. Not used by the adaptor.

## 3. Stimulus <-> trial mapping
- **Trial codes** (CNT annotations): 11-70 = attention-switching trials, mixed_(code-10) (StimList); 71 = practice
  `mixed_100` (left male), 72 = practice `mixed_200` (left female); 73-82 = passive block (10 trials, not in
  StimList); 179 / 184 = left / right key; 255 = spurious (S3, S4, S5 between trials; S11 and S17 twice at the end;
  S5's passive block has 9 trials and a 255 where trial 73 would be).
- Codes 11-40: left male, right female; 41-70 and 72: left female, right male (StimList). Verified from the audio:
  the median f0 of the left channel is 128-139 Hz (male) in mixed_001 and mixed_100, and 250-286 Hz (female) in
  mixed_031 and mixed_045.
- **Order** (`events.csv`): practice first (S1 has only 72, S5 starts with a 255), then 6 blocks of 10, then the
  passive block. Trials are 66.0 s apart within a block (60 s + 5 s break + ~1 s); blocks are separated by breaks.
  - S1-S7: blocks = codes 11-20, 21-30, ..., 61-70 in shuffled order within the block.
  - S8-S11: only 30 codes (11, 13, ..., 19, 21, ..., 29, 31, ..., 39 and 42, 44, ..., 70), each presented twice
    (blocks 1-3 and again in blocks 4-6).
  - S12-S18: blocks 1-3 the same 30 codes, blocks 4-6 the complementary 30.
- **EEG check of the mapping** (`scripts/wang2026_ident.py`, `ident_summary.py`): backward decoder per subject
  (0.5-8 Hz, 32 Hz, average reference, EEG lags 0-500 ms, ridge), trained on the switching trials with the
  StimList mapping, leaving out every presentation of the test stimulus. Each trial's reconstruction is correlated
  with the L+R envelope of all 62 wavs.
  - Switching trials: the StimList wav ranks first in 10.1% of 1,080 trials, top-5 in 32.1%, median rank 11 of 62
    (chance: 1.6%, 8%, 30.5). Pooled over subjects, the StimList wav is the best candidate for 47 of 60 codes.
  - Practice: code 71 -> mixed_100 (pooled z 3.4, next 1.8), code 72 -> mixed_200 (z 2.4, next 2.2).
  - S8-S11 repeats: the StimList wav scores alike in the first and second presentation (mean z 1.18 vs 0.96,
    n = 120 each), so the repeated codes replayed the same audio.
  - **Passive block: not identifiable.** Pooled over subjects, the best candidates for codes 73-82 reach z 2.0-3.5
    and differ from code to code (73: mixed_040, 74: 022, 75: 058, 76: 029, 77: 011, ...), the level of a wrong
    candidate. Per trial, the top-candidate z is the same for passive (median 2.21) and switching trials (2.31,
    where the true wav reaches only 0.88), so single-trial identification cannot name the passive audio either.
    The passive audio is either not among the shipped wavs or differs between subjects. Default: passive trials are
    kept with their EEG and key presses, without a stimulus (open question 1).
- **Raw vs processed** (`scripts/wang2026_xcheck.py`, `xcheck_S*.csv`): for every subject and all 60 processed
  epochs, the raw CNT cut at the trial code and processed like the authors' (0.1-45 Hz, 128 Hz, mastoid reference)
  matches the shipped `.mat` epoch: same code order, best lag 0 samples, median channel r 0.98 (S8; others in
  section 9), gain ~0.99. So the CNT is read correctly (scaling, channel order) and the authors cut at the same
  sample.

## 4. Speech features available
- Raw audio of both streams: the stereo wav as played and its two channels (one talker each; L-R correlation |r| <=
  0.02 within +-4 ms, envelope correlation <= 0.1). No transcripts or word timings are shipped (AISHELL-1 has
  sentence transcripts, but which utterances were concatenated is not documented).
- Stored per trial (switching and practice): `mixed_NNN` (stereo), `mixed_NNN_left`, `mixed_NNN_right` (mono), all
  16 kHz float32. None is flagged attended: attention changes within the trial (annotations, section 6).

## 5. Neural data
- Neuroscan Curry 7 CNT, 500 Hz, 68 channels: 62 scalp (10-10 Quik-Cap names incl. CB1/CB2), M1, M2, HEO, VEO, EMG,
  Trigger. MNE reads uV-calibrated values into V (confirmed against the processed `.mat`, gain 0.99). No meas date in
  the header. No digitisation: standard_1005 template positions (CB1/CB2 have none).
- **Reference: unknown.** The paper says "reference electrodes were placed on the left and right mastoids, and an
  additional reference electrode was positioned at the nose tip", but M1/M2 are live recorded channels. The lowest
  0.5-8 Hz variance is at CZ/C1/C2/CPZ in every clean subject (e.g. S3 C1 2.6 uV, S5 C2 2.0 uV vs median 3.5-4.6),
  which suggests the Quik-Cap vertex REF (inferred). Kept as recorded.
- **Peripherals.**
  - VEO: the paper describes a vEOG above/below the left eye, but the channel is railed (mean -207.5 mV, SD < 1 uV)
    in S8-S18 except S9/S14 (both also railed in part) and carries no blink signal in S1-S7 (1-40 Hz correlation
    with FP1 -0.11..0.33; FP1 shows the blinks). Kept as `VEOG` (`eog`) and marked bad in every subject.
  - HEO: no HEOG was recorded (paper); railed or noise only. Dropped.
  - EMG: 0.3-6 mV of noise, uncorrelated with anything; not described in the paper. Dropped.
  - Trigger: digital trigger word (values ~65280-65464); the codes are in the annotations. Dropped.
  - M1/M2: `misc`, kept.
- **Bad channels** (`scripts/wang2026_bads_hf.py`, `bads_hf.csv`; robust 2-s window median SD inside trials,
  average reference, 50 Hz harmonics notched): no channel is flat or dead. Marked bad where the 40-200 Hz noise is
  more than 5x the subject's median: S2 CB2 (6.0x), S3 M2 (5.2x), S4 T8 (5.0x), S5 M2 (6.9x), S12 T7 (5.8x). High
  1-40 Hz SD at FP1/FPZ/FP2/AF3/AF4 (up to 5x) is ocular and not marked.
- **Noise level.** Median 0.5-8 Hz window SD 3.4-10.1 uV per subject; plain SDs are much larger in S8-S15 because of
  transient artefacts (e.g. S8 1-40 Hz SD 64 uV plain vs 6.6 uV robust). S2 has strong 50 Hz on many channels.
- **Gel bridging** (`scripts/wang2026_pairs.py`, 120 s of 1-100 Hz, average reference): clusters of neighbours with
  r > 0.98 and raw difference SD < 1 uV, e.g. S3: PZ-P2-PO4-PO6-PO8-O2, PO7-PO5-PO3-CB1-O1, FP1-AF3, F7-FT7, FZ-FCZ
  (37 pairs); S5: 64 pairs over most of the frontal and centro-parietal montage; S1: 44 pairs (occipital). Bridged
  channels carry real (shared) signal and are not marked bad; spatial analyses should expect it.

## 6. Alignment
- **Onset = the trial code's first sample on the recorded Trigger channel** (`scripts/wang2026_trigchan.py`,
  `trigger_channel.csv`). The Trigger channel holds 0xFF00 + code (read as ~65280 + code "uV"). For every one of
  the 9,157 trial and key events in 17 subjects, the step comes exactly 1 sample (2 ms) after the CNT event-table
  sample; **in S14 it comes 24 samples (48 ms) after, for every event** (72 trial codes, 396 presses). The
  authors' processed S14 epochs also start 6 samples at 128 Hz (46.9 ms) after the event table (all 60 epochs,
  r 0.87-0.997; every other subject: lag 0), so EEGLAB's loadcnt and the Trigger channel agree and the S14 event
  table is the odd one out. The Trigger channel is sampled with the EEG (acquisition hardware), so it is used for
  all trial onsets and key presses (on by default, no option; `event_table_offset_ms` in the provenance gives the
  difference). An earlier run with event-table onsets is in `tmp/review/wang2026/standardised_eventtable/`
  (superseded).
- The trial code is the authors' audio-start label (code comment);
  the paper says EEG, audio and key presses were "temporally aligned using synchronized trigger signals" and that
  presentation was synchronised "using E-Prime 3.0". The sound latency of E-Prime playback after the port code is
  not documented: `sw_trigger`, trigger type software.
- No stimtrack or audio copy (the EMG and Trigger channels are not audio). No end marker, so no trigger-based drift
  estimate; trials are 60 s, so 100 ppm would be 6 ms at the end of a trial.
- Insert/headphone latency: unknown (headphones, 65 dB SPL; model not given).
- Annotations per trial (times from the trial onset, presses with 0 <= t < 60 s):
  - `key/left`, `key/right`: each press (zero duration). Presses fall inside trials (none in the 6 s before or after
    a trial); first press at a median 1.15 s (switching), 6.3 presses per switching trial (range 2-18), 0.16
    same-side repeats per trial.
  - `attend/left`, `attend/right` (switching and practice): from each press to the next press or the trial end. The
    first ~1 s before the first press is unlabelled. Paper: "Based on the recorded attentional focus after each
    completed switch, trials within the corresponding time window were labeled".
  - Passive block: presses only (alternating presses at the switching rate, motor control; paper). 11 of 179
    passive trials have no press.
  - `attention_s` in the provenance gives seconds labelled left/right/unlabelled per trial.
- Brain-based timing (section 9): DNN offset -26 ms vs accou2023, documented, not applied. **Grade: medium.**

## 7. Cross-subject duration check
Not possible: there is one code per trial and no end code. The code-to-code interval within a block is 65.8-66.1 s
(60 s + E-Prime break and inter-trial overhead), constant within a block and differing by up to 0.2 s between
blocks, so it carries no information about the audio clock.

## 8. Open questions (defaults chosen; to confirm)
1. **Passive-block audio** unknown (not in StimList, not identifiable from the EEG). Default: passive trials kept
   without stimulus (EEG + key presses for motor-control analyses). Alternative: drop them. Ask the authors which
   audio was played (upstream issue).
2. **VEOG**: kept and marked bad everywhere (no blink content). Alternative: drop it as an unused port.
3. **Bridged electrodes** not marked bad (they carry real signal). Alternative: mark all but one per cluster.
4. **Practice trials** (codes 71/72) included as condition `practice`, with attention annotations.
5. **Reference** recorded as unknown (vertex REF inferred), not re-referenced.
6. **Attention labels:** no significant attended > ignored effect (11/18, p 0.32); S1-S7 lean the other way. Default: labels as documented (179 = left, 184 = right) for all subjects.
7. **DNN offset -26 ms** documented, not applied (no correction needed for a `medium` grade).

## 9. Validation, timing check, grade and data size
Validation (2026-11-24, `python -m cnsp_datasets.validate wang2026 --tiers low,mlr,brainstem --reference average`,
18 subjects, all 1,115 trials with a stimulus; the 179 passive trials have none and are skipped; feature = envelope
of the stereo wav, i.e. both talkers; `validation.json` here, figure `tmp/review/wang2026/validation/validation.png`):
- **low (0.5-8 Hz): pass.** Mean r 0.023 (median 0.023), p_circ 0.020, p_mismatch 0.048, 16 of 18 subjects
  significant (S15 r 0.003 and S17 r 0.002 are not). Per subject r 0.002-0.043. Low compared with single-talker
  datasets (competing talkers, mixture feature, noisy/bridged recordings), but above the nulls.
- TRF (GFP) peaks at 78-94, 172-188 and ~280 ms (pooled peak 188 ms); nothing separate at negative lags (the rise
  from ~-50 ms is the 8-Hz low-pass smearing the 90-ms peak).
- **Per-trial lag offsets:** per-subject medians -12..+13 ms (S17 +28 ms, r 0.002); S14 -3 ms with the
  Trigger-channel onset. Single-trial offsets are noisy (SD 225 ms, 124 at the search edge) because 60-s trials of
  r ~0.02 cannot locate a peak; the validator's drift_ppm (-160 +- 487) is meaningless for the same reason.
- **mlr (30-60 Hz): fail** (SNR 1.02, p 0.34, 0/18). **brainstem (30-250 Hz at 500 Hz): fail** (SNR 0.96, p 0.61,
  2/18). Expected for software triggers, 500 Hz and these data; no structure at negative lags.
- Per condition: switching is 1,080 of the 1,115 validated trials (practice: 35 trials, too few to validate alone).
- **DNN offset vs accou2023** (`data_campaign/scripts/dnn_offsets.py` `run()` via `tmp/review/scripts/
  wang2026_dnn.py`, 100 random switching trials, attended = the stereo mixture): **-26.1 ms (95% CI -33.7 ..
  -17.2)**, i.e. the EEG ~26 ms later than in accou2023. Competing-talker speech (speech in noise gives ~-15 ms) and
  Mandarin (pkueeg2025 -42..-79 ms) push this negative, and E-Prime/sound-card latency may add to it; not applied
  (documented only). Per-subject values (5-6 trials each) are too noisy to use. Figure
  `tmp/review/wang2026/dnn/offsets.png`. No drift check (60-s trials).
- **Attended vs ignored** (`tmp/review/scripts/wang2026_attention.py`; forward model 0.5-8 Hz, lags -0.2..0.6 s,
  5-fold; attended envelope stitched from the `attend/*` spans; scored on labelled samples;
  `tmp/review/wang2026/r-attended-vs-r-ignored.png`, `attention.json`): attended r 0.0188 vs ignored 0.0150 (mean
  difference +0.0037), attended higher in 11 of 18, Wilcoxon p = 0.32: **no significant attention effect**. S8-S18
  (8 of 11 higher) differ from S1-S7 (3 of 7), which used the other block design; a key-code mapping difference
  in S1-S7 cannot be excluded but is not supported by these numbers (open question 6). Leaving out 2 s after each
  press (`attention_skip2.json`): 12 of 18 higher, difference +0.0046, p 0.28. The paper's own backward-TRF decoding reached only 50.5-63.3% (1-30 s windows).
- **Alignment grade: medium.** Trial codes are software (E-Prime) port codes, timed by the recorded Trigger
  channel; the shipped timing is kept and the low tier passes with a plausible TRF (peaks 90/188 ms), nothing at
  negative lags, per-subject lag offsets within +-13 ms and a DNN offset of -26 ms that needs no correction.

**Data size.** 18 participants. With a stimulus (switching + practice, 60 s each): 1,115 trials, **18.6 h**, 1.03 h
per participant (range 1.02-1.03; S1 has no code-71 practice trial). Per condition:
switching 1.00 h each (18.0 h); practice 0.03 h each (35 trials, 0.58 h). Passive block (EEG + key presses, no
stimulus): 179 trials, 3.0 h (0.17 h per participant; S5 9 trials). Whole recordings: 1.67 h per participant
(1.42-2.44 h). Standardised output: 11 GB.

## Upstream issues
- The passive-block stimuli (codes 73-82) are not documented and not identifiable among the shipped wavs.
- VEO carries no vEOG signal in any subject (railed in most), although the paper describes a vEOG.
- The paper's reference description (mastoids + nose tip) conflicts with M1/M2 being recorded channels.
- StimList names `mix_NNN.wav` but the files are `mixed_NNN.wav`; MaleFile/FemaleFile wavs are not shipped (the
  stereo channels contain them).
- S8-S11 heard only 30 distinct stimuli (each twice); S12-S18 two complementary halves; not described in the paper.
- Extensive gel bridging in most recordings.
