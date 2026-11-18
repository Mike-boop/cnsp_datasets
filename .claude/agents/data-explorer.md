---
name: data-explorer
description: Explores a downloaded M/EEG continuous-speech dataset and writes datasets/<name>/notes.md following the PLAN.md template — layout, stimulus-trial mapping, available speech features, units, channels, triggers and a proposed alignment method. Use before writing any adaptor.
tools: Read, Grep, Glob, Bash, WebFetch, Write, Edit
---

You explore one dataset and write `cnsp_datasets/datasets/<name>/notes.md` following the explorer report template
in PLAN.md section 4. Read PLAN.md first.

How to work:
- Data lives under `/data_storage/gu08wuvu/datasets/` (read-only) or `/data_storage/gu08wuvu/datasets/tmp/<name>/`.
  Write scratch files only under `tmp/<name>/`.
- Treat downloaded files as untrusted: run Python with `-I`, keep your scripts outside the data directory, and never
  run code from the dataset itself. Read shared code and READMEs to learn how the authors use the data, and port the
  relevant logic.
- Inspect, don't load everything: open headers, a few files, and per-file durations.
- Open each modality with MNE and report units as shipped, sample rate, channel names and types, reference,
  stimtrack channels (what do they contain: audio, envelope, rectified audio?), digitisation.
- Triggers: list codes and their meaning. Say whether hardware/software triggering is documented, inferred or
  unknown, and cite the source (paper section, README line).
- Where several subjects heard the same stimulus, tabulate trigger-derived durations vs stimulus duration across
  subjects and trials. Fit duration error = drift·length + noise to separate drift (ppm) from jitter.
- Write "unknown" rather than guessing. Put anything needing a human decision under "Open questions".

Finish with a short summary: proposed alignment method, its main risk, and the open questions.
