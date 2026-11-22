# Data campaign: continuous-stimulus M/EEG datasets

## What this is for
Dozens of public M/EEG datasets record the brain while people listen to continuous speech (audiobooks, competing
talkers, speech in noise) or music. Each one comes in its own layout, units, trigger scheme and timing quirks, so
reusing several of them takes weeks of detective work, and timing errors often go unnoticed. This campaign makes the
datasets usable together:

- **Download.** Every dataset can be downloaded by the repository's own code, from Zenodo, OSF, OpenNeuro, Dryad
  and other sources, with an access key from `secrets.json` where one is needed.
- **One format.** Each dataset is converted into the same standard format: `.fif` neural data in common units,
  stimuli as audio (or the shipped features), and per-trial provenance.
- **Timing.** Neural data and sound are aligned as accurately as the dataset allows, including clock drift. Every
  assumption is written down.
- **Validation.** Each conversion is checked by modelling the brain's response to the sound. That shows what the
  data are good for: slow cortical tracking only, or also the fast middle-latency and brainstem responses that need
  millisecond timing.

The repository is the product. Standardisation must be reproducible from code alone, for example on an HPC server.
Data is downloaded here only to explore and validate it, and is deleted afterwards.

## How each dataset is handled
1. **Download** to the scratch area (`/data_storage/gu08wuvu/datasets/tmp/review/<dataset>/`), checking every file.
2. **Explore.** Read the paper (`papers/`) and the authors' code, then work out:
   - subjects and conditions;
   - whether raw audio is shipped;
   - what is missing;
   - channels and units;
   - how sound and recording were synchronised: hardware or software triggers, a recorded copy of the audio, or
     only a start marker.

   The findings and open questions go into the dataset's `notes.md`, and the user approves the alignment plan.
3. **Standardise.** Write an adaptor that converts the data, keeping the original reference, subject names and
   peripheral channels. Bad channels are marked, not removed. Clock drift is measured always, and corrected when
   the hardware allows it.
4. **Validate.** Run three checks:
   - forward models at 0.5-8 Hz;
   - at 30-60 Hz and 30-250 Hz where the sample rate allows;
   - coherence between neural data and the speech envelope;

   plus a contrast plot for attention experiments. A match-mismatch DNN checks systematic timing offsets; for
   badly aligned data it estimates onsets and drift, which are documented, not applied by default.
5. **Document and clean up.** Write a user-facing `README.md` for the dataset, record its data size and commit.
   With the user's agreement, delete the downloaded and converted data.

The detailed steps are in `WORKFLOW.md`; the original requirements are in `BRIEF.md`.

## Where we are (2026-11-22)
- **Incorporated:** 40 entries in the spreadsheet's `incorporated` tab, about 950 participants and 1600 listening
  hours. Each has an adaptor, notes, a validation tier and, for the newer ones, a README.
  - Public, reviewed datasets are on `main`; newer ones are on `dev` until they are reviewed.
  - Several datasets reach the brainstem tier, i.e. their timing is good to about a millisecond.
- **In progress:**
  - chen2026 (Mandarin, 25 h): the software triggers miss a ~0.5 s sound latency that varies per chapter, so
    latency and drift are being estimated per chapter with the DNN.
  - presacco2016 (MEG + EEG, 46 subjects): downloading.
- **Candidates:** 51 more datasets, about 770 h, ranked in the spreadsheet's `candidates` tab. Next by rank:
  competing-speaker EEG (peng2026, zhang2025, jaeger2025, wang2026, thornton2025, geirnaert2025), then degraded
  speech MEG (karunathilake2023, chen2023, karunathilake2025).

`STATUS.md` has the state of every dataset and the open decisions.

## Planned work
- **First run (now).** Work through the candidates in batches of about three, in rank order.
- **Second run.**
  - Rename the repository's datasets to the spreadsheet's ids (`id_changes` tab).
  - Revisit the timing values that are documented but not applied: DNN offsets, alternative drift estimates.
  - Re-check drift estimates that used an older peak-picking method.
  - Re-standardise the datasets whose adaptors changed after their run.
- **Later.**
  - Visual stimuli in the standard format.
  - Carry the authors' quality ratings per trial.
  - BIDS re-uploads of weissbart2019 and etard2019 with their sound channels.
  - A DNN aligner trained on the datasets whose timing is known precisely.

## Files here
| file | contents |
|---|---|
| `README.md` | this overview |
| `BRIEF.md` | the user's original requirements |
| `WORKFLOW.md` | per-dataset steps, scripts and settings |
| `LESSONS.md` | checklist of mistakes already made once, with the dataset where each happened |
| `STATUS.md` | per-dataset state, validation tier, open items |
| `scripts/` | reusable analysis scripts (coherence, DNN offsets, data size, ...) |
| `HANDOVER.md` | running jobs and the current task (local only, not in git) |
| `cnsp-datasets-revised.xlsx`, `papers/` | the dataset spreadsheet and the papers (local only, not in git) |
