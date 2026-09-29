import re
import mne
import numpy as np

from abc import ABC, abstractmethod
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Tuple

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


def save_textfile(full_path: Path, text: str):
    with open(full_path, "w") as f:
        f.write(text)


def _load_npz(fpath: Path) -> dict:
    with np.load(fpath, allow_pickle=True) as npz:
        return {k: npz[k] for k in npz.files}


def _load_text(fpath: Path) -> str:
    return fpath.read_text(encoding="utf-8")


def _load_bytes(fpath: Path) -> bytes:
    return fpath.read_bytes()


def _read_raw_fif(fif_path: Path):
    return mne.io.read_raw_fif(fif_path, preload=False, verbose="ERROR")


def _raise_missing_stim(modality: str, name: str) -> None:
    raise FileNotFoundError(
        f"No saved feature files found for stimulus '{name}' (modality '{modality}')."
    )


class BaseSink(ABC):
    def __init__(self, save_directory: str, fname_separator: str = "_-_", overwrite = False):
        self.save_directory = save_directory
        self.fname_separator = fname_separator
        self.overwrite = overwrite

    def save_record(self, record: TrialRecord):
        try:
            self._save_neural_data(record)
            self._save_stimuli(record)
        except Exception as e:
            print(f"Error saving record {record}: {e}")

    @abstractmethod
    def _get_ns_relative_path(self, record: TrialRecord) -> Tuple[Path, str]:
        """Return (save_dir, fname_stem) for a given trial's neural data."""

    def _build_fname(self, record: TrialRecord) -> str:
        stimulus_modalities = set(stim.modality for stim in record.stimulus)
        stimuli_names = {
            m: [
                stim.name
                for stim in sorted(record.stimulus, key=lambda s: (not s.is_attended, s.name))
                if stim.modality == m
            ]
            for m in stimulus_modalities
        }
        return self.fname_separator.join([
            f"sub-{record.subject:03d}",
            f"ses-{record.session:03d}",
            f"trial-{record.trial:03d}",
            f"cond-{record.condition}",
            *[f"{m}{i:02d}-{name}" for m, names in stimuli_names.items() for i, name in enumerate(names, 1)],
            record.ns_type,
        ])

    def _save_neural_data(self, record: TrialRecord):
        save_dir, fname = self._get_ns_relative_path(record)
        save_dir.mkdir(parents=True, exist_ok=True)

        if not self.overwrite and (save_dir / f"{fname}.fif").exists():
            return

        raw = record.neural_data
        raw.save(save_dir / f"{fname}.fif", overwrite=True)

    def _save_stimuli(self, record: TrialRecord):
        for stim in record.stimulus:
            save_dir = Path(self.save_directory) / "stimuli" / stim.modality
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


class BaseSource(ABC):
    def __init__(
        self,
        save_directory: str | Path,
        fname_separator: str = "_-_",
        assume_first_attended: bool = False,
    ):
        self.root = Path(save_directory)
        self.sep = fname_separator
        self.assume_first_attended = assume_first_attended

        self.re_sub = re.compile(r"^sub-(\d{3})$")
        self.re_ses = re.compile(r"^ses-(\d{3})$")
        self.re_trial = re.compile(r"^trial-(\d{3})$")
        self.re_cond = re.compile(r"^cond-(.+)$")
        self.re_stim = re.compile(r"^([A-Za-z]+)(\d{2})-(.+)$")

    # -----------------------
    # Public API
    # -----------------------

    def iter_trials(self) -> Iterator[TrialRecord]:
        for fif_path in self._find_fif_files():
            try:
                yield self._trial_from_fif_path(fif_path)
            except Exception as e:
                print(f"[{type(self).__name__}] Skipping {fif_path} due to error: {e}")

    # -----------------------
    # Subclass contract
    # -----------------------

    @abstractmethod
    def _find_fif_files(self) -> Iterable[Path]:
        """Yield all .fif paths under the root directory."""

    # -----------------------
    # Internals
    # -----------------------

    def _parse_tokens_from_fname(self, fname_stem: str) -> Dict[str, Any]:
        parts = fname_stem.split(self.sep)
        if len(parts) < 5:
            raise ValueError(f"Unexpected filename format: {fname_stem}")

        sub_m = self.re_sub.match(parts[0])
        ses_m = self.re_ses.match(parts[1])
        trial_m = self.re_trial.match(parts[2])
        cond_m = self.re_cond.match(parts[3])
        if not (sub_m and ses_m and trial_m and cond_m):
            raise ValueError(f"Missing required tokens in: {fname_stem}")

        stim_tokens = parts[4:-1]
        ns_type = parts[-1]

        stims: List[Tuple[str, int, str]] = []
        for tok in stim_tokens:
            m = self.re_stim.match(tok)
            if not m:
                raise ValueError(f"Unrecognized stimulus token '{tok}' in '{fname_stem}'")
            stims.append((m.group(1), int(m.group(2)), m.group(3)))

        return dict(
            subject=int(sub_m.group(1)),
            session=int(ses_m.group(1)),
            trial=int(trial_m.group(1)),
            condition=cond_m.group(1),
            ns_type=ns_type,
            stim_entries=stims,
        )

    def _trial_from_fif_path(self, fif_path: Path) -> TrialRecord:
        meta = self._parse_tokens_from_fname(fif_path.stem)

        neural_data_fn = partial(_read_raw_fif, fif_path)

        stimuli: List[StimulusRecord] = []
        by_modality: Dict[str, List[Tuple[int, str]]] = {}
        for modality, idx, name in meta["stim_entries"]:
            by_modality.setdefault(modality, []).append((idx, name))

        for modality, items in by_modality.items():
            items.sort(key=lambda x: (x[0], x[1]))
            for j, (idx, name) in enumerate(items):
                feature_files = self._find_feature_files(modality, name)
                if not feature_files:
                    stimuli.append(StimulusRecord(
                        modality=modality,
                        name=name,
                        data_fn=self._missing_stim_fn(modality, name),
                        is_attended=(self.assume_first_attended and j == 0),
                        feature_name=modality,
                    ))
                    continue
                for fpath, feature_name in feature_files:
                    stimuli.append(StimulusRecord(
                        modality=modality,
                        name=name,
                        data_fn=self._make_feature_loader(fpath),
                        is_attended=(self.assume_first_attended and j == 0),
                        feature_name=feature_name,
                    ))

        return TrialRecord(
            subject=meta["subject"],
            session=meta["session"],
            trial=meta["trial"],
            condition=meta["condition"],
            ns_type=meta["ns_type"],
            stimulus=stimuli,
            neural_data_fn=neural_data_fn,
            anat=None,
            structural_data_fn=None,
            behavioural_data_fn=None,
        )

    def _find_feature_files(self, modality: str, name: str) -> List[Tuple[Path, str]]:
        out: List[Tuple[Path, str]] = []
        mod_dir = self.root / "stimuli" / modality
        if not mod_dir.exists():
            return out
        for f in mod_dir.glob(f"{name}{self.sep}*"):
            if not f.is_file():
                continue
            feature = f.stem.split(self.sep, 1)[1] if self.sep in f.stem else f.stem
            out.append((f, feature))
        return out

    def _make_feature_loader(self, fpath: Path) -> Callable[[], Any]:
        suffix = fpath.suffix.lower()
        if suffix == ".npz":
            return partial(_load_npz, fpath)
        elif suffix in (".txt", ".textgrid"):
            return partial(_load_text, fpath)
        else:
            return partial(_load_bytes, fpath)

    def _missing_stim_fn(self, modality: str, name: str) -> Callable[[], Any]:
        return partial(_raise_missing_stim, modality, name)
