# CNSP-Datasets: tools for downloading and standardising publicly-available data

- Quick start: check out the examples

## Downloading datasets:

CNSP-datasets provides a convenient way to obtain publicly-available data. No more manual downloads of large numbers of files or huge archives, and no need to configure separate download clients for the various repositories where relevant datasets are often found.

Current repositories supported include:

- Zenodo
- OSF (Open Science Framework)
- Openneuro
- Dryad
- KULeuven RDR (possibly extendable to other Dataverse repositories)
- UMD Drum (possibly extendable to other DSpace repositories)
- UMichigan Deep Blue Data

The repositories listed above host the vast majority of publicly available data. Some other repositories are not yet supported; incorporating them would be nice to have at some point:

- ePrints repositories such as [Southampton ePrints server](https://eprints.soton.ac.uk/438737/)
- Exhibits repositories such as [Stanford Exhibits server](https://exhibits.stanford.edu/data/catalog/jn859kj8079)
- Radboud Data Repository (e.g. MEG-fMRI dataset [here](https://data.ru.nl/collections/di/dccn/DSC_3011085.05_995))
- GitHub (e.g. [Phyaat dataset](https://github.com/Nikeshbajaj/PhyaatDataset))
- IEEE dataport (e.g. Chinese AAD dataset [here](https://ieee-dataport.org/documents/nju-auditory-attention-decoding-dataset))
    - (I'm not certain we can access this repo programmatically without an access token..)

A list of datasets is being compiled [here](datasets.tsv).

## Standardising datasets

Putting datasets into a common format has several benefits:

- Reduces the amount of custom user code required to actually load/align/process each dataset
- Enables fast replication studies, should one want to cross-check their results against a different dataset
- Enables fast answers to questions such as "what happens if the participants had listened to noisy speech/competing speakers/different voices/music?"
- Enables large-scale analyses across multiple (and, importantly, complementary) imaging modalities

Standardising the datasets comes with challenges, however. First, one must decide on a "standard format" (BIDS, CND, something else?). Sometimes, one encounters a dataset which doesn't quite "fit" into a particular format, requiring an update to that format. This can create a lot of work for you, if you already wrote code that directly loads the data and saves it into the original format: you would have to go back through the code for every single dataset and update it to match the new format.

To solve this, this repository implements a simplified "hexagonal architecture" (this is just a common software design pattern), consisting of three components:

- A `TrialRecord` class: a complete representation of a particular trial in a dataset. This is a _software_ representation that does not depend on the dataset.
- An `Adaptor` class: this contains code which takes a downloaded dataset (in its original format), and produces a sequence of `TrialRecord` objects.
- A `Sinker` class: this contains code for saving (or _sinking_) `TrialRecord` objects to disk. 

The concept is as follows: first, one writes code which downloads the dataset in its original form. Second, they provide an `Adaptor` for that dataset. Third, they call a `Sinker` object on the software representation of the dataset, which saves (or _sinks_) the data to disk in the desired format. If one wants to change or update their choice of standardised format, they simply have to produce a new `Sinker` object.

## To-dos

### General

1. Add some logging so we can track what is going on (especially in concurrent code)
2. Probably overdid the british english :-(

### Documentation, setup, additional features

1. GUI/browser interface to `download_dataset` function
2. Stop freezing dependencies at specific versions in pyproject.toml
3. Docs - but better to wait until we have a relatively stable version

### Download to-dos:

1. Parallelise extracting archives (see [here](cnsp_datasets/download/download_helpers.py))
2. Support external OSF storage providers (s3, gdrive, etc.)
3. Write tests for UMD Drum: we are currently web-scraping this repo, an approach which is likely to break at some point
4. Check if there is a mapping between Deep Blue dataset IDs and their dois (so we can keep the unified `doi_to_downloadables` convention in [download_helpers.py](cnsp_datasets/download/download_helpers.py)).
    - If not, I supposed one could follow the doi link and scrape the Deep Blue ID...
5. Unify OSF/OpenNeuro tree-walk algorithms (easier to maintain). Add concurrency to OpenNeuro tree-walking.
6. Include a schema to validate the dataset_registry.json file.
7. General testing of the `download_dataset` function (I did not play too much with `retries`, `verify_checksum`, `skip_existing`, ...)
8. Support additional repositories specified above..

### Standardising to-dos:

1. Methods to get and save structural data
2. Methods to get and save behavioural data
3. Methods to get and save fMRI data
4. Didn't encounter any public fNIRS yet but if we come across it, would be nice to handle it.
5. Some authors chose to upload original recordings (i.e. they didn't split the data into trials). Since we represent every trial individually, the same raw data file needs to be accessed multiple times - this can be expensive for large files. We could consider caching, or yielding batches of TrialRecord objects.
6. Concurrency would greatly speed up the standardisation process. Unsure how this would interact with the suggestions in #5 above though... (update: lru_cache is threadsafe...)
7. __repr__ for trial record so we can see when problems went wrong.. perhaps also some verbosity/raise-on-error stuff

### Saving to-do

1. I didn't add a BIDS sink yet but it should be pretty easy (of course we need to decide how to accomodate the stimuli)
2. I also didn't add a CND sink. This one is a bit harder for two reasons:
    - One must first define an (arbitrary?) order for the experimental stimuli, and then understand the actual presentation order which may be different for different participants. This requires more "global knowledge" of the datasets than is currently represented in each `TrialRecord`.
    - Sometimes the participants don't listen to all the stimuli, or other weird edge cases (typically related to randomisation) break the format.
    - Writing to a matlab struct isn't totally fun in python (but we can write .mat matlab data files quite easily)