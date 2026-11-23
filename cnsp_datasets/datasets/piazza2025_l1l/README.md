# piazza2025_l1l: stories in three speech registers, native English listeners (EEG)

EEG of 25 native English listeners (experiment 2 of the paper, Trinity College Dublin). They heard three English
stories, each in five ~3-min parts, with one story per speech register:
- **L2 Accommodation (`L2A`):** how native speakers address learners.
- **Native Directed Speech (`NDS`).**
- **`Slow_NDS`:** NDS time-warped to the L2A rate.

All stories were played in +16 dB multi-talker babble. Story and register were assigned in a Latin square. The
companion dataset `piazza2025_l2l` holds the L2 learners (another lab and EEG system), and the shared code and full
notes are in `piazza2025_base`.

- **Source:** OSF ba3p4 (https://osf.io/ba3p4/), CND files (registry entry `piazza2025`, 7.63 GB, both groups).
- **Licence: unknown.** The OSF node has none, and the article's CC BY 4.0 covers the article only. This is an
  **open question**: ask the authors before redistributing the data or anything derived from them.
- **Paper:** Piazza G, Carta S, Ip EYJ, Pérez-Navarro J, Kalashnikova M, Martin CD, Di Liberto GM (2025). Are you
  talking to me? How the choice of speech register impacts listeners' hierarchical encoding of speech. *Imaging
  Neuroscience* 3. doi:10.1162/imag_a_00539
- **Code (authors):** a forward-TRF script and R analyses on OSF (read, not run).

## Size
**25 participants, 370 trials, 16.9 h in total, 40.6 min per participant (34.4-42.3 min).**
- **Per register:**

  | register | total | per participant: mean | range |
  |---|---|---|---|
  | `L2A` | 6.19 h | 14.8 min | 8.6-15.5 min |
  | `NDS` | 4.53 h | 10.9 min | 8.7-11.9 min |
  | `Slow_NDS` | 6.21 h | 14.9 min | 11.9-15.4 min |

- The figures are stimulus durations from `validation.json` (`stim_s`; totals as in `piazza2025_base/notes.md`
  section 8). `data_size.py` was not run because the standardised data had been deleted.
- **Missing trials:** L1L 4 trials 1-2 and L1L 17, 19, 20 trial 1 are placeholders of failed recordings and are
  absent.

## What is provided
- **EEG:** BioSemi, 64 scalp channels. **Recorded at 1024 Hz; shared and stored at 100 Hz, already preprocessed by
  the authors** (1-8 Hz band-pass, bad channels interpolated). Units µV, scaled to V.
  - **Reference:** not documented. An external left-earlobe electrode was recorded but is not shipped, and the data
    are not average-referenced.
  - **Peripherals:** there are no EOG, mastoid or trigger channels.
  - **Positions:** template `standard_1005` positions.
- **Interpolated channels:** L1L 20 has 3 interpolated channels. They cannot be identified, so they are not in
  `info['bads']`.
- **Stimuli:**
  - **`NDS` and `Slow_NDS`:** the wavs as played (speech + babble, 44.1 kHz).
  - **`L2A`:** **only the authors' 100 Hz envelope**; no audio was shared.
  - Where both exist, the wav and the authors' envelopes agree at r 0.92-0.96.
  - **Not included:** the authors' phonetic, spectrogram, surprisal, entropy and word-onset features.
- **Trials and conditions:** `condition` = register, `trial` = presentation position (1-15). Story and part are in
  the provenance.

## Alignment
- **Software trigger.** The authors epoched at the PsychoPy start trigger: EEG sample 0 = audio onset, kept as
  shipped (`sw_trigger`). The EEG runs ~1 s past the audio. No triggers or raw data are shared.
- **Check:** the per-subject TRFs peak at 0-270 ms, with nothing at negative lags (except L1L 16, which has no clear
  peak).
- **Epoch lengths:** for L1L 1-8 the epochs are 30-80 ms shorter relative to the stimulus than for the others. The
  difference is deterministic per stimulus, and the TRF latencies are normal.
- **Drift and jitter:** cannot be estimated (`drift_ppm` null).
- **Alignment grade: medium.** The authors' 100 Hz epochs start at the PsychoPy (software) start trigger. The
  per-subject TRFs peak at 0-270 ms and are flat at negative lags. Drift is not estimable. Low tier.

## Download and adaptor options
- `download_dataset("piazza2025", <dir>)` (OSF, no credentials). This downloads both groups.
- The adaptor is `Piazza2025Adaptor(download_dir, group="l1l")` (in `piazza2025_base`). It has no other options.

## Validation
**Low tier, all 25 participants**, average reference. This is the highest tier reachable with 1-8 Hz data at
100 Hz.
- **Pooled:** mean r 0.025, 23/25 participants above the nulls, TRF GFP peak at 62 ms.
- **Per register:** `L2A` 0.024 (16/25), `NDS` 0.018 (10/25), `Slow_NDS` 0.022 (14/25). All pass.
- **Weak participants:** L1L 16 is below the nulls, and L1L 2 and 25 are near them.
- **Not run:** DNN timing check (its preprocessing does not match 1-8 Hz, 100 Hz data) and coherence.

**Suitable for** low-frequency envelope tracking and register comparisons.
**Not suitable for** middle-latency or brainstem analyses, or for re-preprocessing.

## Caveats
- **Licence unknown** (see above).
- **Wrong stimulus files (upstream):** the stimulus files of L1L 13, 14 and 15 belong to other subjects. The
  adaptor assigns stimuli from the EEG trial lengths, which are unique per participant; the EEG confirms this
  mapping (r 0.035 vs 0.004 for L1L 13). Such trials are flagged `stim_file_mismatch`. The authors' published L1L
  13-15 results probably used the wrong envelopes.
- **Feature types differ:** `L2A` has the authors' envelope, while the other registers have wavs.

Details: `../piazza2025_base/notes.md`.
