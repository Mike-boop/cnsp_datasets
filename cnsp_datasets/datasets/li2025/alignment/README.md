# li2025 onset delays and drift (brain-based)

The shipped files start at the video's start trigger, but the sound starts later. No audio copy or end trigger exists,
so the delays were estimated from the MEG itself (circular). The adaptor applies per-subject delays by default
(`onset.csv`, from `subject_delays.py`); `onset="group"` gives the earlier per-group delays (`ONSET_DELAY_S`) and
`onset="none"` the shipped onset. Details: `../notes.md` section 7.

Run from the repository with the download as input (each script reads it through the adaptor without onset or drift correction):

```
M=cnsp_datasets.datasets.li2025.alignment
python -m $M.poptrf      <download> <out>/poptrf 0,0          # group A GFP peaks at +0.92 s -> delay 0.80 s
python -m $M.trf_weights <download> <out>/trf_weights         # per-subject TRFs, uncorrected and corrected
python -m $M.match_groups <out>/trf_weights <out>/match       # group B matched to group A: 0.44 s (CI 0.41-0.80)
python -m $M.butterfly   <out>/trf_weights <out>/butterfly_topo.png
python -m $M.subject_delays <download> <out>/trf_weights <out>/subject_delays
                                                              # per-subject delays -> onset.csv (adaptor default)
python -m $M.drift       <out>/subject_delays/part_delays.json <out>/drift   # pooled drift; Theil-Sen -> DRIFT_PPM
python -m $M.heldout     <download> <out>/subject_delays/heldout_delays.json <out>/heldout   # per subject vs group
python -m $M.poptrf      <download> <out>/poptrf 0.80,0.42    # check: both groups peak near +0.1 s
```

`common.py` holds the shared preprocessing (HFC, 0.1 Hz high-pass, 0.5-8 Hz envelope and MEG at 64 Hz, ridge TRF over
-1.5..+1.5 s for the template, -1.5..+2.5 s for the TRFs whose delay is searched over 0..1.9 s; each part of a
recording is matched only within `PART_WINDOW` = +-0.3 s of that recording's delay). All of it is analysis only; the
standardised data stay raw apart from the onset crop and the drift correction folded into it (sidecar
`alignment_method = brain_trf`; `drift_ppm` / `drift_corrected_ppm` -16.7 ppm by default, `drift_ppm=0` turns it off;
the crop starts at the delay minus the drift accumulated by the session midpoint, since the delays are
whole-recording estimates).

| group | subjects | delay | how |
|---|---|---|---|
| A | sub-31..47 | 0.80 s | population TRF peak +0.92 s minus ~0.1 s latency; corrected TRF peaks +94 / +250 ms (+-~50 ms) |
| B | sub-48..60 | 0.42 s | B's multichannel TRF matched to A's corrected TRF: best 0.44 s (r 0.60, bootstrap CI 0.41-0.80 s, skewed); user's reading 0.41 s; a component at ~-40 ms remains |
| per subject (default) | all | 0.39-1.26 s | each subject's whole-recording TRF matched to A's corrected TRF (search 0..1.9 s); group delay if match r < 0.15 or the five parts' MAD > 50 ms, parts matched within +-0.3 s of the subject's delay (sub-37/40); held-out test in `../notes.md` section 7 |
| drift (default, user 2026-11-23) | 28 non-fallback | -16.7 ppm, applied | pooled Theil-Sen of part delays relative to each subject's delay (95% CI -27.4..-9.5); OLS -28.7 (-49.9..-8.0) for reference; `../notes.md` sections 6-7 |
