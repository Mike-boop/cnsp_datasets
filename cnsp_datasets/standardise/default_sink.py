import os
import re
import mne

import numpy as np

from pathlib import Path
from cnsp_datasets.standardise.trial_record import TrialRecord
from typing import Iterable, Iterator, List, Tuple, Dict, Callable, Any

from cnsp_datasets.standardise.trial_record import TrialRecord, StimulusRecord


def save_textfile(full_path: Path, text: str):
    with open(full_path, "w") as f:
        f.write(text)

class DefaultSinkv1:
    def __init__(self, save_directory, fname_separator="_-_"):
        
        self.save_directory = save_directory
        self.fname_separator = fname_separator

    def save_record(self, record: TrialRecord):

        # try:
        self._save_neural_data(record)
        self._save_stimuli(record)
        # except Exception as e:
        #     print(f"Error saving record {record}: {e}")
        #     return

    def _get_ns_relative_path(self, record: TrialRecord) -> Path:

        stimulus_modalities = set(stim.modality for stim in record.stimulus)
        stimuli_names = {
            m: [stim.name for stim in sorted(record.stimulus, key = lambda s: (not s.is_attended, s.name) )
                if stim.modality == m] for m in stimulus_modalities
        }

        fpath = os.path.join(
            self.save_directory,
            f"sub-{record.subject:03d}",
            record.ns_type,
            f"ses-{record.session:03d}"
            )

        fname = self.fname_separator.join([
            f"sub-{record.subject:03d}",
            f"ses-{record.session:03d}",
            f"trial-{record.trial:03d}",
            f"cond-{record.condition}",

            *[f"{m}{i:02d}-{name}" for m, names in stimuli_names.items() for i, name in enumerate(names, 1)],
            
            record.ns_type
        ])

        return Path(fpath), fname
    
    def _save_neural_data(self, record: TrialRecord):
        save_dir, fname = self._get_ns_relative_path(record)
        save_dir.mkdir(parents=True, exist_ok=True)

        full_path = save_dir / f"{fname}.fif"
        raw = record.neural_data
        raw.save(full_path, overwrite=True)

    def _save_stimuli(self, record: TrialRecord):
        for stim in record.stimulus:

            save_dir = Path(self.save_directory) / "stimuli" / stim.modality
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


class DefaultSourceV1:
    """
    Loader for datasets saved by DefaultSinkv1.

    It yields TrialRecord objects reconstructed from:
      - neural data FIF files at: save_dir/sub-XXX/<ns_type>/ses-YYY/*.fif
      - stimuli under: save_dir/stimuli/<modality>/<name>_-_<feature>.(npz|txt|TextGrid)

    Notes:
      * is_attended cannot be exactly reconstructed; default is False.
        Optionally, set assume_first_attended=True to mark the first stimulus per modality as attended.
    """

    def __init__(
        self,
        save_directory: str | Path,
        fname_separator: str = "_-_",
        assume_first_attended: bool = False,
    ):
        self.root = Path(save_directory)
        self.sep = fname_separator
        self.assume_first_attended = assume_first_attended

        # Filename tokens as written by DefaultSinkv1._get_ns_relative_path
        # sub-<ddd>, ses-<ddd>, trial-<ddd>, cond-<string>, then one or more "<modality><ii>-<name>" tokens, ending with "<ns_type>"
        # Example:
        # sub-001_-_ses-002_-_trial-010_-_cond-speech_-_audio01-storyA_-_audio02-storyB_-_eeg.fif
        self.re_sub = re.compile(r"^sub-(\d{3})$")
        self.re_ses = re.compile(r"^ses-(\d{3})$")
        self.re_trial = re.compile(r"^trial-(\d{3})$")
        self.re_cond = re.compile(r"^cond-(.+)$")
        self.re_stim = re.compile(r"^([A-Za-z]+)(\d{2})-(.+)$")  # modality, index, name

    # -----------------------
    # Public API
    # -----------------------
    def iter_trials(self) -> Iterator[TrialRecord]:
        """Yield TrialRecord objects found under the root directory."""
        for fif_path in self._find_fif_files():
            try:
                yield self._trial_from_fif_path(fif_path)
            except Exception as e:
                # You may prefer to log and continue
                print(f"[DefaultSourceV1] Skipping {fif_path} due to error: {e}")

    # -----------------------
    # Internals
    # -----------------------
    def _find_fif_files(self) -> Iterable[Path]:
        # sub-xxx/<ns_type>/ses-yyy/*.fif
        for sub_dir in self.root.glob("sub-*"):
            if not sub_dir.is_dir():
                continue
            for ns_dir in sub_dir.iterdir():
                if not ns_dir.is_dir():
                    continue
                for ses_dir in ns_dir.glob("ses-*"):
                    if not ses_dir.is_dir():
                        continue
                    for fif_path in ses_dir.glob("*.fif"):
                        yield fif_path

    def _parse_tokens_from_fname(self, fname_stem: str) -> Dict[str, Any]:
        """Parse your compound filename (without extension) into fields."""
        parts = fname_stem.split(self.sep)
        if len(parts) < 5:
            raise ValueError(f"Unexpected filename format: {fname_stem}")

        # required fixed tokens
        sub_m = self.re_sub.match(parts[0])
        ses_m = self.re_ses.match(parts[1])
        trial_m = self.re_trial.match(parts[2])
        cond_m = self.re_cond.match(parts[3])
        if not (sub_m and ses_m and trial_m and cond_m):
            raise ValueError(f"Missing required tokens in: {fname_stem}")

        subject = int(sub_m.group(1))
        session = int(ses_m.group(1))
        trial = int(trial_m.group(1))
        condition = cond_m.group(1)

        # middle tokens are stimuli; final token is ns_type
        stim_tokens = parts[4:-1]
        ns_type = parts[-1]

        stims: List[Tuple[str, int, str]] = []  # (modality, index, name)
        for tok in stim_tokens:
            m = self.re_stim.match(tok)
            if not m:
                # If something else got inserted, you can choose to ignore or raise
                raise ValueError(f"Unrecognized stimulus token '{tok}' in '{fname_stem}'")
            modality, idx_str, name = m.group(1), m.group(2), m.group(3)
            stims.append((modality, int(idx_str), name))

        return dict(
            subject=subject,
            session=session,
            trial=trial,
            condition=condition,
            ns_type=ns_type,
            stim_entries=stims,
        )

    def _trial_from_fif_path(self, fif_path: Path) -> TrialRecord:
        # Example path: <root>/sub-001/<ns_type>/ses-002/<COMPOUND>.fif
        fname_stem = fif_path.stem  # without .fif
        meta = self._parse_tokens_from_fname(fname_stem)

        subject = meta["subject"]
        session = meta["session"]
        trial = meta["trial"]
        condition = meta["condition"]
        ns_type = meta["ns_type"]

        # ---------- neural data (lazy) ----------
        def neural_data_fn():
            # preload=False keeps it lazy
            return mne.io.read_raw_fif(fif_path, preload=False, verbose="ERROR")

        # ---------- stimuli (lazy per feature) ----------
        # For each (modality, index, name) token, discover any saved features:
        # files live at <root>/stimuli/<modality>/<name>_-_<feature>.(npz|txt|TextGrid)
        stimuli: List[StimulusRecord] = []
        stimuli_root = self.root / "stimuli"
        by_modality: Dict[str, List[Tuple[int, str]]] = {}

        for modality, idx, name in meta["stim_entries"]:
            by_modality.setdefault(modality, []).append((idx, name))

        for modality, items in by_modality.items():
            # stable order by idx then name, mirroring your sink
            items.sort(key=lambda x: (x[0], x[1]))
            for j, (idx, name) in enumerate(items):
                feature_files = self._find_feature_files(stimuli_root, modality, name)
                # If no feature files exist, we still create a StimulusRecord whose data_fn raises.
                if not feature_files:
                    stimuli.append(
                        StimulusRecord(
                            modality=modality,
                            name=name,
                            data_fn=self._missing_stim_fn(modality, name),
                            is_attended=(self.assume_first_attended and j == 0),
                            feature_name=modality,  # best-effort default
                        )
                    )
                    continue

                for fpath, feature_name in feature_files:
                    stimuli.append(
                        StimulusRecord(
                            modality=modality,
                            name=name,
                            data_fn=self._make_feature_loader(fpath),
                            is_attended=(self.assume_first_attended and j == 0),
                            feature_name=feature_name,
                        )
                    )

        return TrialRecord(
            subject=subject,
            session=session,
            trial=trial,
            condition=condition,
            ns_type=ns_type,
            stimulus=stimuli,
            neural_data_fn=neural_data_fn,
            anat=None,  # not persisted by DefaultSinkv1
            structural_data_fn=None,
            behavioural_data_fn=None,
        )

    def _find_feature_files(self, stimuli_root: Path, modality: str, name: str) -> List[Tuple[Path, str]]:
        """
        Return list of (path, feature_name) for all files whose base name starts with
        '<name>_-_'. Feature name is parsed from '<name>_-_<feature>.<ext>'.
        """
        out: List[Tuple[Path, str]] = []
        mod_dir = stimuli_root / modality
        if not mod_dir.exists():
            return out

        pattern = f"{name}{self.sep}*"
        for f in mod_dir.glob(pattern):
            if not f.is_file():
                continue
            feature = f.stem.split(self.sep, 1)[1] if self.sep in f.stem else f.stem
            # Normalize feature (e.g., drop extension-specific suffixes)
            out.append((f, feature))
        return out

    # --------- feature loaders (lazy) ---------
    def _make_feature_loader(self, fpath: Path) -> Callable[[], Any]:
        """
        Returns a data_fn that loads the persisted stimulus:
          - .npz: returns a dict-like (same keys you saved)
          - .txt / .TextGrid: returns the file's text (str)
        """
        suffix = fpath.suffix.lower()
        if suffix == ".npz":
            def _load_npz():
                with np.load(fpath, allow_pickle=True) as npz:
                    # Return a plain dict to mirror what was saved
                    return {k: npz[k] for k in npz.files}
            return _load_npz

        elif suffix in (".txt", ".textgrid"):
            def _load_text():
                return fpath.read_text(encoding="utf-8")
            return _load_text

        else:
            # Unknown type — load bytes as a fallback
            def _load_bytes():
                return fpath.read_bytes()
            return _load_bytes

    def _missing_stim_fn(self, modality: str, name: str) -> Callable[[], Any]:
        def _raise():
            raise FileNotFoundError(
                f"No saved feature files found for stimulus '{name}' (modality '{modality}')."
            )
        return _raise