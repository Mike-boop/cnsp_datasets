import os
import numpy as np
import traceback

from functools import partial
from pathlib import Path
from cnsp_datasets.standardise.trial_record import TrialRecord


def save_textfile(full_path: Path, text: str):
    with open(full_path, "w") as f:
        f.write(text)

class FlatSinkV1:
    def __init__(self, save_directory, fname_separator="_-_"):
        
        self.save_directory = save_directory
        self.fname_separator = fname_separator

    def save_record(self, record: TrialRecord):

        try:
            self._save_neural_data(record)
            self._save_stimuli(record)
        except Exception as e:
            print(f"Error saving record {record}: {e}")
            traceback.print_exc()
            return

    def _get_ns_relative_path(self, record: TrialRecord) -> Path:

        stimulus_modalities = set(stim.modality for stim in record.stimulus)
        stimuli_names = {
            m: [stim.name for stim in sorted(record.stimulus, key = lambda s: (not s.is_attended, s.name) )
                if stim.modality == m] for m in stimulus_modalities
        }

        fname = self.fname_separator.join([
            f"sub-{record.subject:03d}",
            f"ses-{record.session:03d}",
            f"trial-{record.trial:03d}",
            f"cond-{record.condition}",

            *[f"{m}{i:02d}-{name}" for m, names in stimuli_names.items() for i, name in enumerate(names, 1)],
            
            record.ns_type
        ])

        return Path(self.save_directory) / record.ns_type, fname
    
    def _save_neural_data(self, record: TrialRecord):
        save_dir, fname = self._get_ns_relative_path(record)
        save_dir.mkdir(parents=True, exist_ok=True)

        full_path = save_dir / f"{fname}.fif"
        raw = record.neural_data
        raw.save(full_path, overwrite=True)

    def _save_stimuli(self, record: TrialRecord):
        for stim in record.stimulus:

            save_dir = Path(self.save_directory) / stim.modality
            save_dir.mkdir(parents=True, exist_ok=True)
            fname = self.fname_separator.join([stim.name, stim.feature_name])

            data = stim.data_fn()

            # extend these cases to handle other types of data as they arise
            if stim.feature_name == "textgrid":
                fname += ".TextGrid"
                save_fn = save_textfile
            elif type(data) == str:
                fname += ".txt"
                save_fn = save_textfile
            # otherwise we assume a continue feature and its sample rate encoded as an ndarray 
            # and float in a dict TODO: we can actually type check this.
            else:
                fname += ".npz"
                save_fn = lambda path, data: np.savez(path, **data)

            full_path = save_dir / fname
            if os.path.exists(full_path):
                continue # skip if we already processed this stimulus from another record
            save_fn(full_path, data)