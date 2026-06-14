from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

import numpy as np

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord
from cnsp_datasets.standardise.base_sink import BaseSink, BaseSource, save_textfile


class FlatSinkV1(BaseSink):
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

            data = stim.data_fn()

            if stim.feature_name == "textgrid":
                full_path = save_dir / f"{fname}.TextGrid"
                save_fn = save_textfile
            elif isinstance(data, str):
                full_path = save_dir / f"{fname}.txt"
                save_fn = save_textfile
            else:
                full_path = save_dir / f"{fname}.npz"
                save_fn = lambda path, d: np.savez(path, **d)

            if full_path.exists():
                continue
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
