# shan2024: music and speech, subcortical and cortical EEG

EEG to 12 s clips of six music genres and six kinds of speech (passive listening). Both a subcortical (ABR)
montage and 32 scalp channels.

- **Source:** NEMAR on004356 v1.0.0 (doi:10.82901/nemar.on004356), content-identical to OpenNeuro ds004356
  v2.2.1. Licence CC0.
- **Paper:** Shan T, Cappelloni MS, Maddox RK (2024). Subcortical responses to music and speech are alike while
  cortical responses diverge. *Sci Rep* 14:789. doi:10.1038/s41598-023-50438-0
- **Code (authors):** https://github.com/maddoxlab/Music_vs_Speech_abr

## Size
22 participants x 480 clips x 12 s = **35.2 h in total, 1.60 h per participant**.
- Music: `music-{acoustic,classical,hiphop,jazz,metal,pop}`.
- Speech: `speech-{chn_aud,eng_aud,interview,lecture,news,talk}`.
- Each condition has 40 clips (0.13 h per participant).

The click trials (ABR only) and some undocumented trials after the experiment are left out.

## What is provided
- **EEG:** 34 channels as recorded, at 10 kHz, stored at **1000 Hz** by default:
  - `EP1`, `EP2`: FCz minus each earlobe (EP-PreAmp), the subcortical montage;
  - 32 active scalp channels; the authors re-reference these to P7/P8 for cortical analyses.
- **Stimuli:** `audio` (48 kHz, as played, mono), stimulus `<type><NNN>`. No transcripts.

## Alignment
- Sound-card triggers (sample-locked).
- Onset = start marker + 0.81 ms tube delay. This can't be checked against the earphone artefact, which isn't
  visible here, but the ABR latencies below agree with it.
- Drift is 25-31 ppm per recording, from start/end markers, corrected by default.
- Mapping verified against the trigger IDs for every trial.

## Validation
- **Middle-latency tier** with the audio feature: low-frequency r 0.038 (22/22 subjects), MLR SNR 1.44.
- The validator's brainstem test uses the audio. The rectified audio is a poor regressor for these natural,
  non-peaky clips (no wave V for music).
- **The brainstem response is present:** with the authors' auditory-nerve-model (ANM) regressor, wave V appears
  at 7.3 ms in 22/22 subjects (music 21/22, speech 22/22). Click ABRs from the same recordings peak at 7.7-8.0 ms.
- The ANM regressors are not part of the dataset. `anm_regressors.py` in this folder reproduces them; it needs
  the `cochlea` package and about 15 CPU-hours.

## Caveats
- Use an ANM-type regressor for subcortical analyses of these clips, not the audio or rectified audio.

Details: `notes.md`.
