# cervantesconstantino2018: missing-speech restoration, KIT MEG (DRUM) — NOT INCORPORABLE

Explorer notes (2026-11-24). Scratch: `/data_storage/gu08wuvu/datasets/tmp/review/cervantesconstantino2018/`
(temporary; `agent_log.md`, `survey.log`). Script: `tmp/review/scripts/cervantesconstantino2018/survey.py`.
**Outcome: the release ships analysis results only: per-subject, per-condition responses averaged over
repetitions (6 z-scored DSS components, segments concatenated), z-scored 50 Hz envelopes, decoders and TRFs. No
sensor MEG, no single-trial data, no audio. There is nothing to standardise in the v2 format; no adaptor was
written.**

## 1. Source
- DRUM (University of Maryland) item `f3402619-3229-4b27-b4fb-3950f461dfda`, hdl `1903/20259`, DOI
  10.13016/M28911S48, "The neural representation of missing speech and the influence of prior knowledge on
  cortical fidelity and latency", F. Cervantes Constantino & J. Z. Simon, issued 2018. No `dc.rights` field in the
  item metadata (licence not stated).
- Paper: Cervantes Constantino F, Simon JZ (2018). Restoration and efficiency of the neural processing of
  continuous speech are promoted by prior knowledge. Front. Syst. Neurosci. 12:56, doi:10.3389/fnsys.2018.00056
  (`data_campaign/papers/cervantesconstantino2018.pdf`).
- One file in the ORIGINAL bundle: `missing_speech_reconstruction_data.zip`, 1,301,451,147 B, md5
  3d43a38399155cc78edcbfefee473dab. Downloaded with the repo downloader (registry entry
  `cervantesconstantino2018`, 1 worker, 300 s read timeout, ~5 min); md5 matches DRUM; `unzip -t` clean.
- A DRUM search for other items by the first author returned HTTP 503 ("no available server"), not retried.

## 2. Layout (`Results/`, 255 entries incl. macOS `.DS_Store` / `._*`)
- `Results/README.txt` (19 Jan 2018) and one folder per participant `R####` with:
  - `R####-TRF-ENVtoDSS1-Comp{1,2}.mat`: `resp` (1x12 cells, each samples x 6 at 1 kHz), `fw_rf` (500 lags,
    `t0` = 0-0.499 s), `fw_prediction`, `fw_corr`;
  - `R####-REC-DSStoENVclean-Comp3-0_0.5.mat` and `R####-REC-DSStoENV-Comp3-0_0.5.mat` (decoding from clean-speech
    and noise intervals): `stim` (1x12 cells, envelope at 50 Hz), `iv_dc` (3 components x 25 lags = 0-0.5 s at
    50 Hz), `iv_corr`, `iv_reconstruction`, `iv_key` (`High[50%]`, `Medium[25%]`, `Low[12%]`, `Rare[<6%]`,
    `Control High` ... `Control Rare`: top-3 vs bottom-3 reproducible components);
  - a few subjects have extra variants (`-REC-20DSStoENV-Comp{3,20}`, `-REC-DSStoENVnoise-`): permutation results
    (`ivc` 3600 x 3) and earlier runs.
- 35 folders, **34 distinct participants**: folder `R2434` holds `R2433-*` files byte-identical (md5) to those in
  `R2433` (upstream issue). The paper reports 35 participants.

## 3. What the arrays are (`survey.log`)
- `resp` cells 1-4 (clean speech, High/Medium/Low/Rare repetition rate) are 26.4-27.1 s (High/Medium/Low) and
  ~101 s (Rare) at 1 kHz per subject. A verse is 13.1-13.6 s; each half of the poem has its own High verse, played
  32 times in each of the two blocks drawn from that half (64 presentations). So each cell is the response
  **averaged over the repetitions** of each verse (one verse per poem half), with the verses concatenated: about 6 min of data per subject (343-368 s over all 12 cells) against ~1 h of
  recording. Noise-onset and button-press segments were excluded (paper, Statistical analyses), so cells are cut
  segments joined without markers (cell 10: 24,573 response samples vs 547 samples in the clean-decoding
  envelope and 1,230 in the noise-decoding one).
- Every component is z-scored (sd = 1.000 in every cell); envelopes are z-scored dB envelopes (range ~-1.5 to 4).
  Ratio of response to envelope samples is 20 (1 kHz vs 50 Hz) in 11 of 12 cells for the
  clean-decoding envelopes (cell 10 is the exception).
- Spectrum of component 1 (R2199, High): 1-8 Hz passband, -13.6 dB at 8-10 Hz, -27 dB at 10-20 Hz, < -40 dB
  above 20 Hz (the authors' 1-8 Hz order-2 Butterworth).
- Envelope sets differ for every subject (34 distinct clean-stimulus sets), consistent with per-subject
  randomisation and segment exclusion; the order and boundaries of the concatenated verses are not shipped.
- Authors' TRFs (High, component 1): |peak| in 50-250 ms at median 142 ms (range 50-223 ms), i.e. the shipped
  pairs are internally aligned at plausible latencies.

## 4. Speech features available
- **No audio.** The poem ("A Visit from St. Nicholas", read by Grant Raymond, archive.org) is public, but the
  stimuli had their silent gaps shortened to equalise verse durations, 768 noise probes per subject were inserted at
  per-subject random times, and no stimulus files, probe times or presentation logs are shipped, so the played
  audio cannot be rebuilt.
- Only the z-scored 50 Hz envelopes per condition (`stim`), matched to the averaged responses.

## 5. Neural data
- Recording (paper): KIT 160-channel (157 axial gradiometers, 3 reference magnetometers), 1 kHz, online 1 Hz
  high-pass, 200 Hz low-pass, 60 Hz notch; ICA + TSPCA, SNS, 1-8 Hz Butterworth, DSS.
- Shipped: first 6 DSS components only, z-scored, repetition-averaged, cut and concatenated per condition. No
  sensors, reference channels, triggers, head shape or topographies.

## 6. Alignment
- Not assessable: no triggers, no continuous recording, no audio. The shipped response/envelope pairs were aligned
  by the authors; their TRFs peak at plausible latencies (section 3).

## 7. Cross-subject duration check
- Not possible (no triggers or per-trial durations).

## 8. Why not incorporable, and open questions (default chosen)
The v2 format stores continuous single-trial M/EEG with the stimuli as played. Compared with
karunathilake2023_aging (also DSS components only, but per trial, 58.5 s each, with the wavs), this release lacks
both single-trial data and audio, and its averaged segments are joined at unmarked cuts.
1. Incorporate? **Default: no — record as not incorporable** (results only: averaged, z-scored DSS components and
   envelopes). Keep the registry entry so the decision is traceable.
2. Ask the authors (Simon lab) for the raw KIT recordings (`.sqd`/`.con`), stimulus wavs and probe times? The user
   sends upstream requests; text in the worker report.
3. Delete the local download (1.3 GB zip + 1.8 GB extracted in `R/cervantesconstantino2018/`)? **Default: delete
   after the user's sign-off.** No vault backup was made (vault node I/O errors on 2026-11-24); the data are
   results only and can be re-downloaded from DRUM (~5 min).

## Upstream issues
- Folder `R2434` contains `R2433-*` files, byte-identical to `R2433/`: R2434's results are missing (or R2434 does
  not exist and the folder is a stray copy). 34 distinct participants against 35 in the paper.
- The DRUM item has no licence statement.
- The DRUM description ("Study dataset") does not say that only results are shared.

## Alignment grade
`none`: not assessable; the release holds only repetition-averaged DSS components and envelopes, no recording,
triggers or audio.

## Restructure 2026-11-25
- Restructure 2026-11-25 (not yet re-validated on data): dataset.json only: title completed, paper DOI, modality and
  system. Still no adaptor.
