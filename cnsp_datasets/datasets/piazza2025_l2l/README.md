# piazza2025_l2l: stories in three speech registers, Spanish-L1 learners of English (EEG)

EEG of 25 Spanish-L1 learners of English (experiment 1 of the paper, BCBL). They heard three English stories, each
in five ~3-min parts, with one story per speech register:
- **L2 Accommodation (`L2A`):** how native speakers address learners.
- **Native Directed Speech (`NDS`).**
- **`Slow_NDS`:** NDS time-warped to the L2A rate.

All stories were played in +16 dB multi-talker babble. Story and register were assigned in a Latin square. The
companion dataset `piazza2025_l1l` holds the native listeners (another lab and EEG system), and the shared code and
full notes are in `piazza2025_base`.

- **Source:** OSF ba3p4 (https://osf.io/ba3p4/), CND files (registry entry `piazza2025`, 7.63 GB, both groups).
- **Licence: unknown.** The OSF node has none, and the article's CC BY 4.0 covers the article only. This is an
  **open question**: ask the authors before redistributing the data or anything derived from them.
- **Paper:** Piazza G, Carta S, Ip EYJ, Pérez-Navarro J, Kalashnikova M, Martin CD, Di Liberto GM (2025). Are you
  talking to me? How the choice of speech register impacts listeners' hierarchical encoding of speech. *Imaging
  Neuroscience* 3. doi:10.1162/imag_a_00539
- **Code (authors):** a forward-TRF script and R analyses on OSF (read, not run).

## Size
**25 participants, 372 trials, 17.0 h in total, 40.8 min per participant (36.6-42.3 min).**
- **Per register:**

  | register | total | per participant: mean | range |
  |---|---|---|---|
  | `L2A` | 6.29 h | 15.1 min | 14.6-15.5 min |
  | `NDS` | 4.53 h | 10.9 min | 7.1-11.9 min |
  | `Slow_NDS` | 6.19 h | 14.9 min | 11.3-15.4 min |

- The figures are stimulus durations from `validation.json` (`stim_s`; totals as in `piazza2025_base/notes.md`
  section 8). `data_size.py` was not run because the standardised data had been deleted.
- **Missing trials:** L2L 19 trial 3 is a placeholder of a failed recording. L2L 16 has 13 trials: NDS parts 2-3
  were never shared.

## What is provided
- **EEG:** BrainVision actiCAP 64 channels with BrainAmp DC, 0.05-500 Hz. **Recorded at 1000 Hz; shared and stored
  at 100 Hz, already preprocessed by the authors** (1-8 Hz band-pass, bad channels interpolated). Units µV, scaled
  to V.
  - **Reference:** the left earlobe (online, hardware; from the paper).
  - **Peripherals:** there are no EOG, mastoid or trigger channels.
- **Channel names are known for L2L 1-5 only.** The shared channel list (`chanlocs64Brain.mat`) fits L2L 1-5, which
  get `standard_1005` template positions.
  - **L2L 6-25:** the channels are named E01-E64 in file order, without positions (`channel_order_known: false` in
    the provenance). A data-derived order scores close to correct but not exactly.
  - Use these subjects for analyses that do not need channel identity, such as envelope tracking over all
    channels, and not for topographies.
- **Interpolated channels:** L2L 1, 5 and 10 have one each, and L2L 12 and 14 have two each. They cannot be
  identified, so they are not in `info['bads']`.
- **Stimuli:**
  - **`NDS` and `Slow_NDS`:** the wavs as played (speech + babble, 44.1 kHz).
  - **`L2A`:** **only the authors' 100 Hz envelope**; no audio was shared.
  - Where both exist, the wav and the authors' envelopes agree at r 0.92-0.96.
  - **Not included:** the authors' model-derived features.
- **Trials and conditions:** `condition` = register, `trial` = presentation position (1-15). Positions of missing
  trials are skipped, not renumbered. Story and part are in the provenance.

## Alignment
- **Software trigger.** The authors epoched at the PsychoPy start trigger: EEG sample 0 = audio onset, kept as
  shipped (`sw_trigger`). Every L2L epoch is stimulus + 1.00 s. No triggers or raw data are shared.
- **Check:** the per-subject TRFs peak at 0-270 ms, with nothing at negative lags (except L2L 19, which has no clear
  peak).
- **Drift and jitter:** cannot be estimated (`drift_ppm` null).
- **Alignment grade: medium.** As piazza2025_l1l: the authors' 100 Hz epochs start at the PsychoPy (software) start
  trigger, the per-subject TRFs peak at 0-270 ms and are flat at negative lags, and drift is not estimable. Low
  tier (21/25).

## Download and adaptor options
- `download_dataset("piazza2025", <dir>)` (OSF, no credentials). This downloads both groups.
- The adaptor is `Piazza2025Adaptor(download_dir, group="l2l")` (in `piazza2025_base`). It has no other options.

## Validation
**Low tier, all 25 participants**, average reference. This is the highest tier reachable with 1-8 Hz data at
100 Hz. The validation does not depend on channel labels.
- **Pooled:** mean r 0.032, 21/25 participants above the nulls, TRF GFP peaks at ~60, 155 and 240 ms.
- **Per register:** `L2A` 0.033 (19/25), `NDS` 0.028 (14/25), `Slow_NDS` 0.025 (16/25). All pass.
- **Weak participants:** L2L 10, 19, 21 and 22 are below the nulls.
- **Not run:** DNN timing check and coherence.

**Suitable for** low-frequency envelope tracking and register or group comparisons that do not need channel
identity in L2L 6-25.
**Not suitable for** topographies of L2L 6-25, middle-latency or brainstem analyses, or re-preprocessing.

## Caveats
- **Licence unknown** (see above).
- **L2L 6-25 channel order unknown (upstream):** asking the authors is an open question.
- **Feature types differ:** `L2A` has the authors' envelope, while the other registers have wavs.

Details: `../piazza2025_base/notes.md`.
