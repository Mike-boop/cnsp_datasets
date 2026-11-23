# deoisres2023: ignored audiobook speech and speech-modulated noise, in quiet and at 5 SNRs (EEG)

EEG of 22 adults (S01-S22). The sound was task-irrelevant: participants watched a subtitled film
while it played, so the speech was ignored. The sound was either a LibriVox audiobook (*The Children of Odin*,
female narrator) or speech-modulated noise with the same envelope.
- **Quiet:** one continuous ~15.5-min story of each type. S03 and S04 heard a ~26-min version.
- **SNR blocks:** 40 two-minute segments, the 4 chunks of each target type at quiet, 0, -5, -10 and -15 dB SNR, in a
  per-subject order.
- One session per subject, three recordings.

- **Source:** University of Southampton ePrints 476402, doi:10.5258/SOTON/D2578 (registry entry `deoisres2023`,
  source `eprints`). The /da/ syllable recordings (`SIN_EEG_Da.rar`) are excluded. 12.5 GB without the /da/
  archive.
- **Licence: CC BY 4.0** (every file in the ePrints record).
- **Thesis:** Deoisres S (2023). *Auditory cortical responses as an objective predictor of speech-in-noise
  performance.* PhD thesis, University of Southampton, chapter 6. The dataset title differs: "Predicting
  behavioural speech reception threshold using cortical responses to continuous sound".
- **Code (authors):** `SIN_EEG_python_script.rar` in the record (read, not run). It gives the mapping from segment
  index to condition.

## Size
Durations are counted from the stimuli (`notes.md` section 7b, per condition computed from it). `data_size.py` was
not run because the standardised data had been deleted.
- **Speech only:** 22 participants, **20.0 h, 0.91 h per participant (0.26-1.10)**.
- **Speech and modulated noise:** **40.0 h, 1.82 h per participant (0.52-2.19)**. A typical participant has 1.85 h.
- **Per condition:**
  - `speech_story`: 22 participants, 6.0 h. Each has 15.5 min (S03/S04: 25.7 min).
  - `modnoise_story`: 22 participants, 6.0 h.
  - Each of the 10 SNR-block conditions (`speech_` / `modnoise_` x `quiet`, `0dB`, `-5dB`, `-10dB`, `-15dB`): 21
    participants, 8 min each, 2.8 h in total. S11's SNR blocks are skipped.
- The unique speech audio is 0.56 h.

## What is provided
- **EEG:** BioSemi ActiveTwo, 32 scalp channels (biosemi32 names, template positions), CMS/DRL (no reference).
  **Recorded at 2048 Hz, stored at 1024 Hz.**
  - There are no mastoid, EOG, ECG or stimulus channels.
  - The GSR, Erg, Resp, Plet and Temp inputs are unconnected and dropped, and Status is dropped after reading the
    triggers.
  - S07 was recorded with a 224-channel montage; only bank A is used.
- **Bad channels:** none are marked (`BADS` is empty). S03 CP2 carries an electrical copy of the audio plus extreme
  50 Hz. Marking it bad was recommended, because it fakes a brainstem response at -2 ms, but it is not marked yet
  (open question). S11 CP1 also has strong 50 Hz.
- **Stimuli:** the wavs as played (44.1 kHz, channel 1). For the SNR blocks only the **target** is stored. The
  background speech-shaped noise is **not shipped**; `snr` and `masker` are in the sidecar. There are no
  transcripts. The audio is the same as in vanheusden2020 (different participants).
- **Conditions:** `speech_story`, `modnoise_story`, and `<target>_<snr>` for the SNR blocks. The top level is
  labelled `quiet`; the thesis calls it 20 dB "without background noise or in quiet". This was not rechecked,
  because `SIN_README.txt` was not available.

## Alignment
- **Hardware triggers locked to the sound card (inferred).** The wavs have a trigger track on channel 2. Its
  pulses reproduce the Status pulses of each recording: after a linear fit, the intervals agree to under 0.35 ms in
  every quiet file.
  - **Quiet trials:** the onset is the intercept of the fit of all pulses.
  - **SNR segments:** the onset is the rising edge of the opening pulse.
- **Drift:** -24.0 to -24.8 ppm (EEG vs sound card) in the quiet files, and about 1 ppm less negative in the SNR
  files, measured from the pulses. **Corrected by default** (hardware-derived), folded into the single
  2048 -> 1024 Hz resample. The uncorrected error would be 23 ms over 15 min.
- **Jitter:** below one 2048 Hz sample relative to the sound card (`jitter_ms` 0.5).
- **Latency:** the S03 stimulus artefact puts the trigger timeline about 2 ms late relative to the sound card's
  electrical output (trigger-box latency, most likely). This is **documented, not corrected**. The ER-2A tube delay
  is not documented and not corrected either.
- **Alignment grade: good.** The triggers are locked to the sound card (pulses match the wav trigger track to
  < 0.35 ms). The S03 electrical audio copy puts them ~2 ms late (hardware, documented). The -24 ppm drift from the
  pulses is corrected. mlr tier.

## Download and adaptor options
- **Download by hand.** The ePrints files sit behind an Anubis proof-of-work page (HTTP 401 to scripts, 2026-11), so
  scripted download is blocked and was not worked around. Download the files in a browser from
  https://eprints.soton.ac.uk/id/eprint/476402/; the registry listing gives the sizes and MD5s for checking.
- **Extract** the RAR4 archives with `bsdtar` (the downloader's RAR support uses it) into the adaptor's
  `download_dir`. The adaptor searches it recursively.
- `Deoisres2023Adaptor(download_dir, drift_correction=True)`. `drift_correction=False` keeps the nominal rate; the
  measured drift is in the sidecar either way.

## Validation
**mlr tier, piloted on 5 of 22 subjects only** (S01, S03, S07, S11, S20; 170 trials), with average reference over
the 32 channels and drift correction on.

| subset | low r (subjects sig.) | mlr SNR (p) | brainstem SNR (p) | tier |
|---|---|---|---|---|
| pooled | 0.012 (4/5) | 1.12 (0.010) | 1.05 (0.22) | mlr |
| quiet trials | 0.019 (2/5) | 1.34 (0.010) | 1.19 (0.010) | brainstem only via S03 |
| quiet without S03 | - | 1.35 (0.010) | 1.13 (0.069) | mlr |
| SNR -10 / -15 dB | 0.002 / -0.004 | | | none |

- **Low-frequency TRF:** peaks at ~70, 170 and 280 ms, with nothing at negative lags.
- **SNR:** r falls with SNR, as in the thesis.
- **30-60 Hz:** a Pa-like peak at ~37 ms.
- **Brainstem tier:** it passes only because of the S03 artefact.
- **Trial order:** a decoder check supports the order sheet (own order beats 94-99% of shuffled orders in S01, S03
  and S07).

**Suitable for** low-frequency tracking of ignored speech across SNRs, and middle-latency responses.
**Not suitable for** brainstem analyses: there is no ER-2A delay information, and the only pass comes from the S03
artefact. The responses are weak (r ~0.01-0.02): the speech was ignored.

## Caveats
- **S11:** the SNR-block recording is skipped. Its segments last 116.05 s, matching no shipped stimulus (an earlier
  stimulus version). S11's noise story misses its first pulse; the onset comes from the other 15.
- **S01:** the SNR file has one unpaired pulse (an aborted segment), which is skipped.
- The masker noise of the SNR blocks is not shipped. `SIN_README.txt` was not read (missing from the local copy).
- The thesis says "twenty" participants, but all 22 have data.

Details: `notes.md`.
