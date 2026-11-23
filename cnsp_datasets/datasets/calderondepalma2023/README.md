# calderondepalma2023: audiobook with spectral and temporal modulation degradation

EEG while listening to ~3-min snippets of an English audiobook (*The Old Man and the Sea*, male narrator), each
snippet either clean or with its spectral or temporal modulations low-pass filtered (two strengths each).

- **Source:** OSF gx6rm (https://osf.io/gx6rm/), CND files. **Licence: BSD 3-Clause** (LICENSE file in the
  release; copyright Alejandro Lopez Valdes, Trinity College Dublin).
- **Paper:** Calderón De Palma I, Lopez LS, Lopez Valdes A (2023). Effects of spectral and temporal modulation
  degradation on intelligibility and cortical tracking of speech signals. *Interspeech 2023*, 5192-5196. The
  release also asks to cite the CND paper (Di Liberto et al., arXiv:2309.07671).
- **Code (authors):** none for this dataset; the release points to the generic CNSP workshop scripts.

## Size
13 participants (1-12, 14), 25 snippets each (325 trials of 166-202 s), **16.42 h in total, 75.8 min per
participant** (all heard the same 25 snippets). Five conditions with 5 snippets each (~15.2 min per participant
per condition): `Clean`, `Temporal60` (temporal modulations < 5 Hz), `Temporal80` (< 6 Hz), `Spectral60`
(spectral modulations < 0.3 cyc/kHz), `Spectral80` (< 0.45 cyc/kHz). 60/80 = targeted intelligibility (%).
The condition of each snippet is randomised per participant.

## What is provided
- **EEG:** 64 scalp channels (BioSemi ActiveTwo, recorded at 1024 Hz) plus both mastoids (`M1`, `M2`, type
  `misc`), **as shared by the authors: downsampled to 64 Hz, otherwise unprocessed** (no reference applied, i.e.
  CMS/DRL with large DC offsets; no filtering). Stored at 64 Hz (not upsampled). Re-reference (e.g. to the
  mastoids or the average) and high-pass before use. No EOG, triggers or audio channel.
- Channel names are not in the release; the BioSemi 64 default order is assumed (checked against the
  correlation structure and blink topography in every subject) and `biosemi64` template positions are set.
  Which mastoid is left/right is assumed (`M1` = first column).
- Bad channels: participant 3, P2 (mains noise only), in `info['bads']`.
- **Stimuli:** only the authors' 64 Hz envelope of the **degraded audio as played** (feature `envelope`; the sum
  of a 20-band gammatone spectrogram, 80-8000 Hz), named `s<kk>_<condition>` (snippet kk in that condition). The
  release also contains the 20-band spectrogram and 19 phonetic features, which are not stored. No audio. Note
  that the paper's analysis used the clean speech spectrogram as regressor.

## Alignment
- Stimuli were presented with Presentation, with a parallel-port trigger recorded by the amplifier (software-
  timed); the authors cut the trials and did not share the triggers (`alignment_method` `sw_trigger`). Each EEG
  trial starts at stimulus onset and runs 0.5 s past the stimulus end (kept; cut at the point of use).
- Drift and jitter cannot be estimated (at most ~10 ms over a trial for 50 ppm, below one sample).
- **Match-mismatch DNN offset** (classifier trained on accou2023): +2.5 ms pooled (95% CI -0.8 to +6.0), i.e.
  the onsets agree with the reference dataset. Per condition -4 to +10 ms (documented, not applied).

## Validation
**Low tier**, the highest reachable at 64 Hz. Average reference, all 13 participants.
- Forward model (envelope -> EEG, 0.5-8 Hz): median r 0.030, 12/13 participants above both nulls (participant 4
  shows no tracking). Each condition passes at population level (8-9/13 participants individually); median r
  Clean 0.036, Temporal80 0.030, Temporal60 0.021, Spectral80 0.021, Spectral60 0.019.
- TRF peaks at ~+25 and ~+190 ms; lag sweep centred at 0.
- Suitable for low-frequency (delta/theta) envelope tracking and comparisons between degradation conditions. Not
  suitable for analyses above ~25 Hz (64 Hz rate, weak anti-aliasing: 50 Hz mains appears at 14 Hz).

## Caveats
- The EEG was downsampled without adequate anti-aliasing; mains interference aliases to 14 Hz in several
  participants.
- Envelope amplitudes differ by a gain between participants in the release; one copy per snippet and condition
  is stored (shape identical, r = 1.0000).
- The paper excluded participants 11 and 13 from two conditions and participant 2 from one in its TRF-weight
  analysis (numbering possibly not the file names; there is no file 13). All data are included here.

Details: `notes.md`.
