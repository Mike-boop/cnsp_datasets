from pathlib import Path
from typing import Iterable, Tuple

from cnsp_datasets.standardise.trial_record import TrialRecord
from cnsp_datasets.standardise.base_sink import BaseSink, BaseSource


class DefaultSinkv1(BaseSink):
    def _get_ns_relative_path(self, record: TrialRecord) -> Tuple[Path, str]:
        fname = self._build_fname(record)
        save_dir = Path(self.save_directory) / f"sub-{record.subject:03d}" / record.ns_type / f"ses-{record.session:03d}"
        return save_dir, fname


class DefaultSourceV1(BaseSource):
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
                    yield from ses_dir.glob("*.fif")
