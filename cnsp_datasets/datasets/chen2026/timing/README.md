# chen2026 latency pipeline: how `../timing.csv` was made

The adaptor's onset is `t0 + latency`. `t0` (the `sd.play()` request time) comes from the ROWS/ROWE triggers and is
recomputed and checked by `../timing.py`. The sound latency (~0.5 s, varying per playback call, up to 1.6 s) is not in
the triggers and was estimated from the EEG by the scripts in this folder (notes.md sections 6b-6d). They are the
analysis scripts as run on 2026-11-23, kept so that `timing.csv` can be reproduced from code; they are not library code
and are not imported by the adaptor. Only the paths were changed (now in `settings.py`); the as-run versions read the
as-shipped zips, `prep_cache.py` now reads the extracted BrainVision files (same samples).

## Setup
Environment variables (see `settings.py`):

| variable | meaning |
|---|---|
| `CHEN2026_DOWNLOAD` | the chen2026 download (`PassiveListening/sub-XX/...` extracted), as given to the adaptor |
| `CHEN2026_AUDIO` | the `chen2026_audio` repo (default `<download>/ChineseEEG-2_audio`) |
| `CHEN2026_WORK` | scratch folder for tables, caches (~6 GB), scans and figures |
| `CHEN2026_DNN` | the accou2023 classifier `fs128_1020-64_broadband.pt` |

Run each script with `python -I <path to script> ...`; every script prints its usage with `--help`. Listener ids are
`01`..`08`. Heavy steps: about 25 s per chapter (cache), 5-10 min per listener (decoder, ~5 GB RAM), a GPU helps the
DNN steps.

## Run order

| step | script | input | output (in `<WORK>`) |
|---|---|---|---|
| 1 | `t0_table.py` | download, audio | `t0_table.csv` (file and t0 per listener x chapter) |
| 2 | `prep_cache.py <sub>` | step 1, download, audio, classifier | `align/cache/sub-XX_<story>_chNN.npz` (DNN input at 128 Hz, decoder input at 50 Hz, envelopes) |
| 3 | `decoder_scan.py <sub>` | cache | `align/decoder/sub-XX.{csv,npz}` (LOCO backward decoder, latency 0-4 s, z, SE, halves, window curves) |
| 4 | `dnn_scan.py <sub> ...` | cache, classifier | `align/scans/` (DNN lag scans, latency -0.5..4 s, 5 mismatched nulls) |
| 5 | `analyse_timing.py <sub> ...` | steps 3-4 | `align/summary/sub-XX*` (v1 rule, DNN - decoder offset per listener, drift) |
| 6 | `timing_overview.py` | step 5, step 1 | `timing_table_proposal.csv` (v1), `align/summary/overview.png` |
| 7 | `reclassify_z2.py` | step 3 | `align/z2/reclass.csv`, `fail_z2.csv` (chapters for step 8), `sub-XX_passes.png` |
| 8 | `ext_scan.py <sub>` | step 7, cache, classifier | `align/ext/` (decoder and DNN, latency -1..+8 s) |
| 9 | `timing_v2.py` | steps 5-8 | `timing_table_v2.csv`, `timing_v2_overview.png`, `align/z2/ext_results.csv`, `sub-XX_ext_curves.png` |
| 10 | `make_timing_csv.py [out]` | steps 1, 7, 9 | `../timing.csv` (default) |

`fail_z2.csv` lists every chapter that fails the full decoder rule below, with the reason (`why`). Steps 2-5 and 8
skip finished outputs.

Supporting checks (not needed for `timing.csv`): `inject_drift.py <sub> <chapter key> ...` (known drift injected into
held-out EEG, recovered by the window method), `joint_fit_synth.py` / `joint_fit_synth2.py` (synthetic tests showing
that `align/scan.py:joint_fit` biases drift towards 0), `plot_decoder_curves.py <sub> ...` (r vs latency per chapter).

## The rule (`latency_s`, the user's rule of 2026-11-23)
Per chapter, the first that applies (`rule` column):
1. **decoder z >= 5** or **decoder z >= 2**: listener-specific ridge backward decoder (EEG lags 0-240 ms), trained
   leave-one-chapter-out; peak of the held-out r vs latency (0-4 s), with z >= 2 against 10 mismatched envelopes,
   jackknife SE <= 25 ms, peak not at the edge of the scan range, and not inconsistent (more than 3 robust SD from the
   listener median while the second-highest peak is >= 0.75 of the main one).
2. **extended search** (-1..+8 s, decoder then DNN) for the rest: z >= 2, SE <= 25 ms (decoder) or 40 ms (DNN), not at
   the edge, latency >= 0, consistent. The DNN latency is corrected by the listener's DNN - decoder offset (pooled -8 ms
   where a listener has < 3 chapters strong in both). Labelled `rescan decoder z>=2` / `dnn z>=2` inside the original
   window, `extended-range ...` outside it (none were found).
3. **listener median** of the rule-1 latencies.

`latency_optionB_s`: the listener median unless the chapter's latency deviates by more than max(40 ms, 3 SE).
Counts (281 chapters): 157 decoder z >= 5, 47 decoder z >= 2, 3 rescan decoder, 9 DNN, 65 listener median.
The latencies come from the same EEG that validation models (circular); see notes.md 6b for the held-out check.
