# Campaign brief

The user's requirements for the campaign (2026-11-22), reorganised for reading; the original wording is in git
history (commit 7d827e7, `data_campaign/README.md`). `README.md` gives the overview and `WORKFLOW.md` turns this into
steps.

## Objective
Add the capability to download continuous-stimulation M/EEG datasets and convert them into a standardised form.
Validate each conversion by modelling the relation between the stimuli and the neural signals.

## Approach
- **Order.** Work through the *candidates* tab of `cnsp-datasets-revised.xlsx` in batches.
- **Downloading.**
  - Make sure the repository's code can download each dataset.
  - If it can't, find out whether the user needs to supply an access key; keys go in
    `/home/gu08wuvu/cnsp_datasets/secrets.json`.
  - Manual downloading is the worst case.
- **Storage.**
  - Download to `/data_storage/gu08wuvu/datasets/tmp` and do the standardisation and tests there.
  - Keep it below 1 TB long term. Up to 2 TB is allowed when the data is scheduled for deletion, with the user's
    sign-off.

## Exploration
- **Paper.** Read the dataset's paper in `papers/` (file named by dataset ID).
- **Files.** List the data files and establish:
  - the number of subjects;
  - whether raw audio is available or only derived features;
  - which conditions there are;
  - whether any data is missing or incomplete.

  Standardisation may use derived features, but raw audio is preferred.
- **Alignment.** Work out how the neural data are aligned with the audio:
  - **Recorded audio channel:** it usually gives more precise clock drift and onset/offset times.
  - **Insert earphones:** their tube-induced latency may be unknown.
  - **Event markers:** these may be software triggers with a random offset to the audio onset (mean + jitter), which
    complicates estimating onset and drift.
  - **Second sound channel presented only to the acquisition system:** this usually gives highly accurate onset and
    drift estimates.

## Standardisation
- **Units:** common units per modality: stored in SI (V, T), shown by MNE as µV / fT.
- **Channels:**
  - keep mastoid electrodes, named M1/M2;
  - keep EOG, ECG and other peripherals;
  - name EOG VEOG or HEOG if the direction of the setup is known, otherwise EOG;
  - drop completely unused channels (e.g. disconnected peripheral ports);
  - mark useless channels (flat, or only electrical noise) as bad in the `.fif` files; a channel that is flat for
    one participant is only marked bad for that participant.
- **Files:**
  - several EEG systems recorded at the same time are saved as separate files (this avoids problems with MNE
    re-referencing);
  - simultaneous EEG and MEG can live in the same `.fif` file.
- **Not for now:**
  - structural/anatomical data (avoid downloading MRI where possible);
  - visual stimuli (to be revised in a future version).

  The EEG of multimodal experiments is still standardised, together with the audio.
- **Drift:**
  - always attempt to measure it and save the estimate in the notes; it can be plotted in the validation folder;
  - if it can be identified from hardware triggers, correct it automatically.
- **Subjects and sessions:** keep the original subject names (usually numbers, but not necessarily); this helps when
  discussing the data. Label sessions as accurately as possible.
- **Notes:** write usage notes, assumptions and conventions to `notes.md` in the dataset's folder
  (`cnsp_datasets/datasets/<dataset_id>/`).

## Validation
- **Forward models, 0.5-8 Hz:** per-channel correlation between the model's prediction and the recorded signal.
- **Forward models at 30-60 Hz (MLR) and 30-250 Hz (ABR):** only if the data are available at 500 Hz or more.
- **Reference:**
  - average reference for EEG setups with 32 or more channels, mastoids for fewer;
  - this applies only to the analysis: the standardised data keep the original reference.
- **Figures:**
  - plot the forward models as a four-panel figure in
    `/data_storage/gu08wuvu/datasets/tmp/review/<dataset>/` (or a `figures/` subfolder), named by the repo dataset name;
  - put the coherence plots in the same folder.
- **Coherence between the neural signals and the envelopes:**
  - one plot at 100/125/128 Hz (depending on the original rate), and one at the original rate if it is 500 Hz or
    more;
  - above 1200 Hz, resample first to 1000, 1024 or 1200 Hz as appropriate;
  - Welch method, 5 s windows, 4 s overlap;
  - average the complex coherence over participants;
  - efficient reference code: `/home/gu08wuvu/eeg-envelope-coherence-neuroimage/scripts/coherence/get_pooled_coherence.py`;
    make reusable code of our own, here in `data_campaign` or elsewhere.
- **Contrasts:** for experiments with particularly interesting contrasts, such as auditory attention, plot a summary
  using the forward-model scores (0.5-8 Hz only), e.g. `r-attended-vs-r-ignored.png`. Be selective: no granular
  analyses.

## Poorly aligned data: CNN alignment
Some datasets are very poorly aligned. For these, CNN-based match-mismatch decoders are provided (branch
`bentum-cnn-align`).
- **When to use them:** if the data are of sufficient quality and length, use the CNN to estimate the onset and,
  where necessary, the drift.
- **Plots:** show the results, with the four-panel validation before and after the CNN-based estimate.
- **Results:** the CNN values are normally not used in the standardisation. They are documented in a json in the
  dataset's folder in `cnsp_datasets` for possible future use.
