# polonenko2024: peaky speech at shifted f0s (OpenNeuro ds005340)

## 1. Source
- OpenNeuro ds005340 v1.0.4 (`10.18112/openneuro.ds005340.v1.0.4`), EEG-BIDS, licence CC0.
- Polonenko MJ & Maddox RK (2024). Fundamental frequency predominantly drives talker differences in auditory
  brainstem responses to continuous speech. *JASA Express Lett.* 4(11):114401. doi:10.1121/10.0034329
- Code: https://github.com/polonenkolab/peaky_pitchshift (experiment, stimulus generation, analysis). Read for
  this review: `code_experiment/exp_peaky_pitch.py`, `code_analysis/analysis_eeg.py`.

## 2. Layout
- `sub-01`..`sub-15/eeg/sub-XX_task-peakypitch_eeg.{vhdr,vmrk,eeg}` (one recording per subject, one
  `New Segment`, ~150 min), `_events.tsv`, `_channels.tsv`.
- `stimuli/<type>_<f0>/<type>_<f0>_<NNN>_regress.hdf5` (expyfun hdf5): `x` (audio, 48 kHz, 480000 samples = 10 s),
  `fs`, `pinds` (glottal pulse indices at 48 kHz: the peaky-speech regressor), `anm` (auditory nerve model
  regressor, 2 x 480000: two polarities), `f0_info`. Click files have a 2-ear `x`.
- 20 GB in total (10 GB EEG, 10 GB stimuli).

## 3. Stimulus <-> trial mapping
- 810 trials per subject, 10 s each: 90 click trials (3 rates; **left out**: ABR only) and 720 speech trials
  (male/female narrator x f0 low/mid/high = 123/150/183 Hz, 120 per condition). Every subject hears all 720
  speech files once, in random order. File `<narr>_<f0>_NNN` is the same text at each f0 (pitch-shifted copies).
- `events.tsv` columns `trial_type`, `token`, `stim_file` give the mapping. **Verified independently**: the
  11-bit trial ID stamped after each start trigger (S 4 = 0, S 8 = 1; 2 bits type, 2 bits f0, 7 bits token;
  `expyfun.decimals_to_binary`) decodes to the same type/f0/token for all 12,150 trials, 0 mismatches.
- Speech is diotic (`np.tile(x, [2, 1])`), no polarity inversion, rms 0.01 (= 65 dB SPL), ER-2 inserts.

## 4. Speech features
- Raw audio as played (`x`, 48 kHz, float64, mono/diotic). All 720 files are exactly 10.000 s.
- Glottal pulse times (`pinds`) and an auditory-nerve-model regressor (`anm`): derived features the authors use
  for deconvolution. No transcripts or word alignments.

## 5. Neural data
- BrainVision, actiCHamp + EP-PreAmp (passive bipolar), **10 kHz**, float32, units µV in the header (MNE scales
  to V). Channels `A1`, `A2`: FCz (non-inverting) minus left / right earlobe; ground Fpz. `channels.tsv` types
  both as EEG; reference "FCz" in the sidecar. No stimtrack, no aux channels.
- 15 participants (sub-01..15), all included in the paper. Hearing thresholds in `participants.tsv`.

## 6. Alignment
- Triggers: **sound-card triggers** (expyfun `trigger_controller='sound_card'`, RME Babyface Pro), i.e. written
  into the same output stream as the audio: sample-locked, no software jitter (documented in the authors' code).
- S 1 = stimulus start, S 2 = 20 ms before stimulus end (`dur_stamp = 9.98`), then 11 ID bits.
- Acoustic delay: 11-inch ER-2 tubes, 0.81 ms; the authors add `round(0.81 ms * 10 kHz) = 8` samples to every
  marker. `events.tsv` `sample` already includes it (= S 1 + 8 in every trial, every subject).
- **Drift:** S 2 - S 1 is 99802 or 99803 samples vs 99800 nominal: **25.2 ppm (the EEG counts more samples per audio second),
  the same in all 15 subjects** (25.1-25.6, quantised per trial, mean over 810 trials; plot in
  `tmp/review/polonenko2024/drift/drift_from_markers.png`). 0.25 ms by the end of a 10 s trial. The authors
  correct it per subject (`clock_adjust`, resampling their regressors).
- Every trial ends well inside the recording (last S 2 is 6-18 s before the end).

### Proposed adaptor
- One TrialRecord per speech trial; clicks skipped. Condition `<narrator>-f0<low|mid|high>`; trial = order in the
  recording; session 1.
- Onset = S 1 + tube delay (the `events.tsv` sample), so EEG time 0 = sound at the eardrum.
- Stimulus: `audio` from `x` (48 kHz), named `<narr>_<f0>_NNN` (one per file, shared across subjects).
- `drift_correction=True` (default): per-subject drift from the markers (mean of (S2-S1)/(9.98 fs) - 1), applied in
  the same interpolation as the resample.
- `sfreq=1000` (default; `None` keeps 10 kHz): 10 kHz -> 1 kHz is an integer factor (1024 Hz would need a 128/1250
  rational resample). Implementation: zero-phase anti-alias low-pass, then one quintic-spline evaluation at the
  drift-corrected 1 kHz grid (for drift 0 this is plain decimation).
- Channels kept as recorded (`A1`, `A2`, type `eeg`), reference recorded as "FCz to each earlobe (bipolar)".
- Provenance: `alignment_method=hw_trigger` (sound-card trigger), `drift_ppm` per subject, `jitter_ms` ~0
  (sample-locked; below 0.1 ms).

The whole family (ds005408, ds008065, ds006434, on004356, Dryad eLife 2021) uses the same lab setup (expyfun,
sound-card triggers, BrainVision, ER-2), so the onset/drift/resample code should go in a shared module.

## 7. Cross-subject duration check
- All 720 speech files are 480000 samples (10.000 s). Trigger-derived durations (S 2 - S 1 + 20 ms) are
  10.0002-10.0003 s in every trial of every subject: drift only, no jitter or missing triggers.

## 8. Data size
15 participants x 720 x 10 s speech = **2.00 h per participant, 30.0 h in total** (from the stimulus durations;
every trial plays its whole 10 s file). Per condition (6: male/female x f0 low/mid/high): 15 x 0.33 h.

## 9. Decisions (user, 2026-11-20)
1. Stimulus features: `audio` and `pulses` (glottal pulse train) by default; `anm` optional (`save_anm=True`),
   off by default.
2. Default output rate 1000 Hz (integer factor from 10 and 25 kHz) for the whole family; native rates are kept when
   they are at or below 1 kHz (never upsampled).
3. Drift correction on by default.
4. Shared code for the lab's datasets in `datasets/maddox_base/common.py`.

## 10. Validation note
The two channels are both FCz minus an earlobe: validate **without re-referencing** (`--reference ""`). An average
reference would leave (A1 - A2) / 2 and remove the common FCz response.

## 11. Validation (2026-11-20; all 15 subjects, 1000 Hz, drift-corrected, no re-reference)
`tmp/review/polonenko2024/validation.{json,png}`; per condition in `tmp/review/polonenko2024/by_condition/`.

| condition | low r (sig) | low peak | mlr SNR (sig) | brainstem SNR (sig) | tier |
|---|---|---|---|---|---|
| all | 0.064 (15/15) | +16 ms | 3.83 (12/15) | 5.57 (15/15) | brainstem |
| male-f0low | 0.063 (14/15) | 0 ms | 1.53 (4/15) | 3.20 (14/15) | brainstem |
| male-f0mid | 0.061 (14/15) | -16 ms | 1.55 (5/15) | 2.54 (11/15) | brainstem |
| male-f0high | 0.067 (14/15) | 0 ms | 1.51 (5/15) | 2.72 (10/15) | brainstem |
| female-f0low | 0.057 (12/15) | +16 ms | 2.27 (9/15) | 2.74 (11/15) | brainstem |
| female-f0mid | 0.060 (13/15) | +16 ms | 2.25 (11/15) | 2.33 (12/15) | brainstem |
| female-f0high | 0.057 (14/15) | +16 ms | 1.82 (8/15) | 2.14 (10/15) | brainstem |

- Brainstem SNR falls with f0 for both narrators, as in the paper (lower f0, larger ABR): labels consistent.
- Low-tier peaks within one 64 Hz sample of 0 in every condition (the 0.5-8 Hz TRF of two FCz-earlobe channels
  is dominated by early, partly artefactual components; not a timing error).
- The 30-250 Hz TRF has a large spike at about -3..+1 ms: the ER-2 electrical artefact (sound leaves the
  transducer 0.81 ms before our onset; confirmed precisely in polonenko2025, notes section 9). No polarity
  alternation here, so it cannot be averaged out.
- The low tier's per-trial jitter/drift estimates (SD ~0.5 s) are noise: 10 s trials with two channels are too
  short for them. Drift is measured from the markers instead (25 ppm).

## Alignment grade
Grade under the CLAUDE.md rule (weakest part decides), accepted by the user 2026-11-24.
**good**: Sound-card triggers + 0.81 ms; ER-2 electrical artefact at about -3..+1 ms in the 30-250 Hz TRF; drift 25.2 ppm from triggers corrected; brainstem tier.

## Restructure 2026-11-25
- Restructure 2026-11-25 (not yet re-validated on data): adaptor on `BaseAdaptor`; dataset.json: participants 15, paper
  DOI. No other change.
