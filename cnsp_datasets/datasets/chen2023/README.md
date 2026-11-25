# chen2023: German audiobook at six noise-vocoding levels (MEG)

MEG of 24 German speakers listening to Goethe's *Das Märchen* in 24 excerpts (16-194 s). Each excerpt was heard
once, in one of six conditions: original, or noise-vocoded with 7, 5, 3, 2 or 1 channels. Blocks of three excerpts
were presented in a Latin square. There are 525 trials (one per excerpt heard), and five subjects have missing runs
(see Caveats).

- **Source:** Austrian NeuroCloud (ANC) BIDS server, `yc_audiobook_vocoding`, doi:10.60817/v2fd-cq35. It is a
  public GitLab with the data in Git LFS (registry entry `chen2023`, source `gitlab_lfs`, pinned to commit
  `0a5a02a2`, 2026-10-21). 761 files, 108.6 GB.
- **Licence: ANC Data Use Agreement 1.0.2.** Use for scientific or educational purposes is allowed. **Section 2.2
  forbids redistributing the dataset "in whole or in part, in any form". Standardised copies must not be shared or
  uploaded without the data custodian's permission.** Publications must cite the dataset with the commit hash.
- **Paper:** Chen, Schmidt, Keitel, Rösch, Hauswald & Weisz (2023). Speech intelligibility changes the
  temporal evolution of neural speech tracking. *NeuroImage* 268:119894. doi:10.1016/j.neuroimage.2023.119894. The
  MEG data are the same as in Study 2 of Hauswald et al. (2020).
- **Code (authors):** https://gitlab.com/yapingchen/vocoded-speech-trf-meg (MATLAB/FieldTrip). The vocoder is
  Gaudrain's toolbox (https://github.com/egaudrain/vocoder). Both were read but not run.

## Size
**24 participants, 19.4 h in total, 0.81 h per participant on average (0.10-0.88 h).** The 19 complete
participants have 0.88 h each. Two participants have only one run each (3 trials, 0.10 h).
- **Per condition** (original, 7/5/3/2/1-channel): 3.15-3.36 h in total each. A complete participant has 6.8-11.3
  min per condition (mean 8.4-9.2 min).
- Durations come from the stimuli (`notes.md` section 8). `data_size.py` was not run because the standardised data
  had already been deleted.
- There is 0.88 h of unique audio.
- A full standardisation would be about 85 GB.

## What is provided
- **MEG:** MEGIN TRIUX, 204 planar gradiometers + 102 magnetometers, SI units, **1000 Hz native, stored at 1000 Hz**
  (not resampled; the drift correction is a single interpolation, see Alignment). The online filter was 0.1-330 Hz.
  - **MaxFilter 2.2.15 SSS was applied by the authors**, with movement compensation to a common head position.
    `info['bads']` is empty in every file.
  - **Peripherals:** EOG001 and EOG002 (`eog`). Their direction is unknown, and neither looks like a clean VEOG.
    ECG003 (`ecg`). EEG010 (`misc`): one EEG electrode of unknown placement, which tracks EOG001.
  - **Other setup:** two subjects (`sub-5551a7b45438`, `sub-400fb1b90f57`) have EOG002, EOG004, ECG003, EEG010 and
    EEG060 instead.
  - **Dropped:** internal active shielding, SYS201, and STI channels. The triggers are in the repo's
    `triggers.csv`.
  - **No audio copy** is in the recording.
- **Subjects** are numbered 1-24 in the order of their sorted BIDS ids. The original id is in each trial's
  provenance (`original_subject`).
- **Stimuli:** the 24 clean wavs (44.1 kHz, dual mono). **The vocoded sounds are not shipped.** By default
  (`vocoded="clean"`) vocoded trials carry the clean source wav. Its 0.5-8 Hz envelope correlates 0.97-0.99 with a
  vocoded rebuild. See the options below.
- No transcripts or word timings are shipped.
- **Trials and conditions:** trial = 3 x (run - 1) + position in the run. `condition` = original / 7chan ... 1chan.
  Trials map to wavs by the STI101 code (condition base + wav number, from the authors' code). This mapping was
  confirmed by response times and by no subject hearing a wav twice.

## Alignment
- **Onset:** the STI101 trigger plus the **16 ms trigger-to-sound delay that the authors measured** (Black Box
  Toolkit v2, tubes included). The trigger type is not documented. The presentation hardware was a VPixx
  SOUNDPixx with pneumatic in-ear phones.
- **Drift: +510 ppm, applied by default, derived from the data.** There is no audio copy. The value comes from a
  scan of the 30-60 Hz TRF SNR over 350-650 ppm in 12 subjects: peak 510.5 ppm, 95% CI 502-518, per subject
  469-541 ppm. The user approved it on 2026-11-23. It matches the audio-copy values of other TRIUX setups (+485
  ppm habersetzer2025, +538 ppm yang2026). Without it, the 30-60 and 30-250 Hz responses disappear and the low-tier
  r drops by about 14%. The correction is folded into the crop (`crop_on_audio_clock`).
- **Check of the 16 ms:** with the drift corrected, the 30-60 Hz TRF lags habersetzer2025 (audio-copy onsets) by
  +1 ms [0, 3].
- **Jitter:** not measured by hardware. The validator's trial-offset MAD of 17 ms is brain-based and not a timing
  measure.
- **Alignment grade: poor.** STI101 trigger + 16 ms (the authors' Black Box Toolkit). The drift of +510 ppm is
  brain-derived (30-60 Hz TRF-SNR scan) and user-approved. There is no audio copy. Brainstem tier with the drift
  correction.

## Download and adaptor options
- `download_dataset("chen2023", <dir>)`. This needs no credentials. Use is governed by the ANC Data Use Agreement
  (above). Every LFS file is checked against its pointer's sha256.
- `Chen2023Adaptor(download_dir, vocoded="clean", sound_delay_ms=16.0, drift_ppm=510.0)`.
  - `vocoded="rebuild"` gives a vocoded rebuild from `vocoder.py`, with a fixed seed per stimulus. The band
    envelopes match the original, but the noise fine structure cannot be reproduced. `vocoded=None` keeps only the
    original condition.
  - `sound_delay_ms=0` starts at the trigger.
  - `drift_ppm=0` turns off the brain-derived drift correction.
  - With `format_dataset`, pass these as `--adaptor-opt key=value`.

## Validation
On magnetometers, without re-referencing (SSS data):
- **With the default drift correction:** 4 complete subjects that were held out from the drift scans (96 trials).
  This is the **brainstem tier**, with 4/4 subjects significant in every tier:

  | measure | value |
  |---|---|
  | low r | 0.042 |
  | 30-60 Hz SNR | 1.87 (p 0.01) |
  | 30-250 Hz SNR | 1.64 (p 0.01) |

  The TRFs peak at 20-50 ms, with nothing at negative lags.
- **Without the drift correction** (first pilot, 22 subjects, 498 trials): low tier only. Mean r 0.035, 21/22
  subjects significant, and the high tiers fail.
- **Per vocoding level** (no drift correction): r falls from 0.039 (7-ch) to 0.024 (1-ch). The clean wav is never
  worse than the rebuild.
- **Not run:** all 24 subjects with the default options, and the DNN offset check (it is EEG-only).

**Suitable for:** low-frequency tracking versus intelligibility, and high-frequency (30-250 Hz) cortical responses
with the default drift correction.
**Note:** the drift was estimated from the same MEG, so high-frequency results are partly circular. The 4
validation subjects were held out from the scan.

## Caveats
- **No redistribution** of standardised data (licence above).
- **Missing runs (upstream):** 51 of 576 presentations are missing. `sub-400fb1b90f57` has only run-08 and
  `sub-520e215b49cf` only run-02. Runs are also missing for `sub-2bf97e558a62` (run-02), `sub-2224b4d06ea2` (run-05)
  and `sub-78f50f9a795e` (run-04). The README says that no one was excluded.
- `events.tsv` misses one stimulus in 5 runs, so the adaptor uses `alignment/triggers.csv`, which is built from STI101 by
  `alignment/triggers.py`.
- `sub-520e215b49cf`: the run's `meas_date` (2019-04-26) disagrees with `participants.tsv` (2019-04-10).
- The vocoded stimuli of vocoded trials are approximations (clean wav or rebuild), not the presented sounds.

Details: `notes.md`.
