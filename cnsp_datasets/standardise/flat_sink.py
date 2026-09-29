from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

import numpy as np
import pandas as pd
import string

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord
from cnsp_datasets.standardise.base_sink import BaseSink, BaseSource, save_textfile


class FlatSinkV1(BaseSink):

    def __init__(self, save_directory: str, fname_separator: str = "_-_", overwrite = False):
        super().__init__(save_directory=save_directory, fname_separator=fname_separator, overwrite=overwrite)

    def _get_ns_relative_path(self, record: TrialRecord) -> Tuple[Path, str]:
        fname = self._build_fname(record)
        save_dir = Path(self.save_directory) / record.ns_type
        return save_dir, fname

    def _save_stimuli(self, record: TrialRecord):
        # Flat layout: <save_directory>/<modality>/ (no 'stimuli' subdirectory)
        for stim in record.stimulus:
            save_dir = Path(self.save_directory) / stim.modality
            save_dir.mkdir(parents=True, exist_ok=True)
            fname = self.fname_separator.join([stim.name, stim.feature_name])

            if stim.feature_name == "textgrid":
                full_path = save_dir / f"{fname}.TextGrid"
                save_fn = save_textfile
                if not self.overwrite and full_path.exists():
                    continue
                data = stim.data_fn()
            else:
                # data could be text or array-like, so the extension isn't known
                # up front: check both candidate paths before loading the data.
                txt_path = save_dir / f"{fname}.txt"
                npz_path = save_dir / f"{fname}.npz"
                if not self.overwrite and (txt_path.exists() or npz_path.exists()):
                    continue

                data = stim.data_fn()
                if isinstance(data, str):
                    full_path = txt_path
                    save_fn = save_textfile
                else:
                    full_path = npz_path
                    save_fn = lambda path, d: np.savez(path, **d)

            save_fn(full_path, data)


class FlatSourceV1(BaseSource):
    def _find_fif_files(self) -> Iterable[Path]:
        # Flat layout: <root>/<ns_type>/*.fif
        for ns_dir in self.root.iterdir():
            if ns_dir.is_dir():
                yield from ns_dir.glob("*.fif")

    def _find_feature_files(self, modality: str, name: str) -> List[Tuple[Path, str]]:
        # Flat layout: <root>/<modality>/ (no 'stimuli' subdirectory)
        out: List[Tuple[Path, str]] = []
        mod_dir = self.root / modality
        if not mod_dir.exists():
            return out
        for f in mod_dir.glob(f"{name}{self.sep}*"):
            if not f.is_file():
                continue
            feature = f.stem.split(self.sep, 1)[1] if self.sep in f.stem else f.stem
            out.append((f, feature))
        return out

    def iter_stimuli(self) -> Iterator[StimulusRecord]:
        """Yield unique StimulusRecord objects across all trials."""
        seen: set[tuple[str, str, str]] = set()
        for trial in self.iter_trials():
            for stim in trial.stimulus:
                key = (stim.modality, stim.name, stim.feature_name)
                if key in seen:
                    continue
                seen.add(key)
                yield stim

    @staticmethod
    def _get_overview(save_directory: str | Path):
        save_directory = Path(save_directory)
        records = []

        for ns_dir in save_directory.iterdir():
            if not ns_dir.is_dir():
                continue
            ns_type = ns_dir.name

            for fif_file in ns_dir.glob("*.fif"):
                parts = fif_file.stem.split("_-_")

                # Drop trailing ns_type suffix if present (e.g. "..._-_eeg")
                if parts and parts[-1] == ns_type:
                    parts = parts[:-1]

                record_dict = {}
                for part in parts:
                    if "-" in part:
                        key, *values = part.split("-")
                        record_dict[key] = "-".join(values)
                    else:
                        record_dict[part] = None

                record_dict["ns_path"] = str(fif_file)
                record_dict["ns_type"] = ns_type

                # Snapshot audio fields BEFORE mutating record_dict
                audio_fields = {
                    k: v for k, v in record_dict.items()
                    if k.startswith("audio") and v is not None
                }

                modality = "audio"
                feature_dir = save_directory / modality
                for audio_name in audio_fields.values():
                    if not feature_dir.is_dir():
                        continue
                    for feature_file in feature_dir.glob(f"{audio_name}_-_*"):
                        stem = feature_file.stem
                        feature_name = stem.split("_-_", 1)[1] if "_-_" in stem else stem
                        record_dict[f"feature_{feature_name}"] = str(feature_file)

                records.append(record_dict)

        df = pd.DataFrame(records)
        return df