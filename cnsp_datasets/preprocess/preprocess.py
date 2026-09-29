import copy
import os
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from typing import Callable

from cnsp_datasets.standardise.base_sink import BaseSink, BaseSource
from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


def apply_preproc_pipeline(
    record: TrialRecord,
    pipeline: dict[str, list[Callable]],
    on_missing_key: str = "ignore",
) -> TrialRecord:
    """
    Wraps the data loader functions in a TrialRecord with preprocessing steps.

    Steps are applied lazily — they execute when data is first accessed (e.g. by the sinker),
    not when this function is called. Each step must be a higher-order function:
        step: Callable[[Callable[[], data]], Callable[[], data]]

    Pipeline keys should match either record.ns_type (for neural data) or a stimulus
    feature_name (for stimulus data).

    Args:
        on_missing_key: how to handle a pipeline key that matches no stream in the record.
            "ignore"  — silently skip (default)
            "warn"    — emit a warning
            "raise"   — raise a KeyError

    Example pipeline:
        {
            "eeg": [bandpass_filter, resample_256hz],
            "audio": [resample_44khz],
        }
    """
    # copy the stimulus records too, so wrapping their loaders below doesn't
    # mutate the caller's record
    record = copy.copy(record)
    record.stimulus = [copy.copy(stim) for stim in record.stimulus]

    valid_keys = {record.ns_type} | {stim.feature_name for stim in record.stimulus}

    for key, steps in pipeline.items():
        if key not in valid_keys:
            msg = f"Pipeline key '{key}' not found in record (available: {sorted(valid_keys)})"
            if on_missing_key == "raise":
                raise KeyError(msg)
            elif on_missing_key == "warn":
                warnings.warn(msg)
            continue

        if record.ns_type == key:
            fn = record.neural_data_fn
            for step in steps:
                fn = step(fn)
            record.neural_data_fn = fn
        else:
            for stim in record.stimulus:
                if stim.feature_name == key:
                    fn = stim.data_fn
                    current_feature_name = key
                    for step in steps:
                        fn = step(fn)
                        if step.output_feature_name is not None:
                            current_feature_name = step.output_feature_name
                    print(f"Stimulus '{stim.name}' feature '{key}' wrapped with {len(steps)} steps. New feature name: '{current_feature_name}'")
                    stim.data_fn = fn
                    stim.feature_name = current_feature_name

    return record


def _process_single(
    record: TrialRecord,
    pipeline: dict[str, list[Callable]],
    sinker: BaseSink,
    on_missing_key: str,
) -> None:
    record = apply_preproc_pipeline(record, pipeline, on_missing_key=on_missing_key)
    sinker.save_record(record)


def preprocess_dataset(
    source: BaseSource,
    pipeline: dict[str, list[Callable]],
    sinker: BaseSink,
    on_missing_key: str = "ignore",
    n_jobs: int = 1,
) -> None:
    """
    Applies a preprocessing pipeline to all records from a source and persists them via a sinker.

    Args:
        n_jobs: number of worker processes. 1 = sequential (default).
                -1 = use all available cores.
    """
    records = list(source.iter_trials())

    if n_jobs == 1:
        for record in records:
            _process_single(record, pipeline, sinker, on_missing_key)
    else:
        workers = os.cpu_count() if n_jobs == -1 else n_jobs
        fn = partial(_process_single, pipeline=pipeline, sinker=sinker, on_missing_key=on_missing_key)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            list(executor.map(fn, records))
