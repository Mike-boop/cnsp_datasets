# schueller2024: selective attention to one of two audiobooks (MEG)

MEG of 58 German speakers listening to two audiobooks at once, read by a low-pitched (LP) and a high-pitched (HP)
narrator, attending to one of them; attention switched every chapter.

- **Source:** Zenodo 12793944 (Set1: participants 1-19 and the audio), 12794769 (Set2: 20-38), 12794808 (Set3:
  39-58). Licence CC BY 4.0.
- **Papers:** Schüller A, Schilling A, Krauss P, Reichenbach T (2023). Attentional modulation of the cortical
  contribution to the frequency-following response evoked by continuous speech. *J Neurosci* 43(44):7429-7440.
  doi:10.1523/JNEUROSCI.1247-23.2023. Preprints with the full sample: doi:10.1101/2024.07.25.605057,
  doi:10.1101/2024.08.01.606154.
- **Code (authors):** https://github.com/Al2606/MEG-Analysis-Pipeline

## Size
58 participants x 10 chapters (3-5 min each, 36.8 min in all): **35.6 h in total, 0.61 h per participant**.
Conditions `lp-attended` and `hp-attended`, 5 chapters (0.31 h) each per participant.

## What is provided
- **MEG:** 248 magnetometers (4D Neuroimaging Magnes 3600 WH), in T, 1000 Hz (the authors resampled from 1017.25 Hz
  and notched 50 Hz harmonics), online band-pass 1-200 Hz. Head-shape points are kept in the files. No EEG, EOG,
  reference sensors or audio channel in the release.
- **Stimuli** (44.1 kHz, shared across participants): per trial the attended and the ignored chapter, as shipped
  (`audiobook{1,3}_k` attended, `audiobook{4,2}_k` ignored; the ignored chapter starts ~5 s later, inside its wav).
- No transcripts or word alignments.

## Alignment
- The release cuts each chapter at the sound-card output (the authors cross-correlated the audio with the MEG's audio
  channel, which they did not release). Checked against the raw recordings: within ~1 ms.
- **Tube delay:** the sound reached the ear through 2 m tubes, 6 ms later; each trial starts 6 ms after the chapter
  boundary (`tube_delay=True`, default).
- **Clock drift** of the sound card against the MEG: +8.5 ppm (7-10 ppm per participant, ~2.5 ms over a 5 min
  chapter), measured on the raw recordings and corrected by resampling onto the audio clock. `drift="subject"`
  (default; participant 15, without raw data, gets the dataset median), `"dataset"` or `None`.

## Validation
**Brainstem tier** (MEG: 30-250 Hz response at 28-45 ms), Set1 (19 participants): low-frequency r 0.021 (19/19
significant), middle-latency SNR 1.05, 30-250 Hz SNR 1.68 (18/19 significant; 1.60 and 16/19 without drift
correction).

## Caveats
- Only Set1 has been downloaded and checked here (Zenodo blocked this server on 2026-11-21); Sets 2 and 3 are
  assumed to have the same layout.
- Each run in the release is the authors' concatenation of five chapters; the MEG between chapters (questions,
  breaks) is not released.
- Chapter order is inferred from the paper (LP first, then alternating).
- The FIF header's 1-500 Hz filter entry is a default left by the resampling; the recording was 1-200 Hz.

Details: `notes.md`.
