# fuglsang2018 notes

Condensed from the review notes of 2026-11-18 (`tmp/review/fuglsang2018/notes.md`, temporary).

## Data
- Zenodo 1199011. 18 participants x 70 trials of 50 s: 60 two-talker trials (male + female, attended ear L/R, three
  reverberation conditions `noRev`/`lowRev`/`highRev`, `expinfo.acoustic_condition` 1/2/3) and 10 single-talker
  "DSS" trials (`natural-{L|R}`). All 129 wavs are 50.000 s, 44.1 kHz mono, dry (the reverberation as presented is
  not shipped).
- `S*.mat`: continuous BioSemi recording (FieldTrip struct) at 512 Hz in microvolts: 64 scalp + EXG1-8 + Status.
  The authors' `preproc_data.m` uses EXG3/5 as VEOG and EXG4/7 as HEOG (typed `eog`); EXG1/2/6/8 are undocumented
  (EXG1/2 probably the mastoids), kept as `misc`. Status dropped.
- Per-subject experiment tables are committed in `expinfos/` (extracted from the original MATLAB tables).

## Timing
- Onsets: the event with code `expinfo.trigger`, matched to the expinfo trials in order (stray events skipped: in
  S8, trial 46's end trigger is missing and an event coded 192 arrives 19.6 s after its onset). Each trial lasts
  exactly the stimulus duration.
- **FieldTrip `event.sample` is 1-based** (MATLAB indexing: sample 1 is the first sample of `data.eeg`). The
  adaptor uses `event.sample - 1` as the 0-based onset index into the EEG array (user decision 2026-11-25; before
  the restructure the 1-based value was used directly, i.e. every trial started one sample, ~2 ms, late).
- Onset-to-end-trigger intervals are 3-4 samples short of 50 s in every trial: either ~-120 ppm drift or a constant
  end-trigger latency, which 50 s trials cannot separate. A stretch sweep was inconclusive: no correction.

## Validation (before the restructure)
Low tier: 0.5-8 Hz mean r 0.033, 17/18 subjects significant, TRF peak 156 ms. 30-60 Hz passes weakly on the
no-reverb + single-talker trials only (SNR 1.09, p 0.01).

## Data size
18 participants, 0.97 h each, 17.5 h in total (estimated from the stimuli).

## Alignment grade
**medium**: onset triggers look hardware-timed (duration jitter <= 1 sample) but were never checked against audio;
-6..-8 ms per 50 s unresolved, not corrected; DNN -1.4 ms; low tier (mlr without reverb).

## Restructure 2026-11-25 (not yet re-validated on data)
- BaseAdaptor; sorted globs; the wav index raises on two files with one basename; a missing wav raises.
- Onsets are 0-based (`event.sample - 1`, see Timing): every trial starts one sample earlier than before.
- An unknown `acoustic_condition` code raises (was silently used as the condition name).
- Audio through `iohelpers.read_wav` (first channel, float32 scaled to [-1, 1); was unscaled int16 as float64).
