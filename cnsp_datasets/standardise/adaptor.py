"""
Base class of the dataset adaptors.

An adaptor turns one download (its original layout) into TrialRecords. Every dataset folder's adaptor.py defines
ADAPTOR, a BaseAdaptor subclass constructed as ADAPTOR(download_dir=..., **options) by format_dataset; options
are keyword arguments with defaults, checked in __init__ with `self.choice` / `self.require` (never `assert`,
which `python -O` strips). Variants of one dataset (e.g. two languages) are subclasses that fix some options,
not functools.partial objects.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Collection, Iterator

from cnsp_datasets.standardise.trial_record import TrialRecord


class BaseAdaptor(ABC):
    def __init__(self, download_dir: str | os.PathLike):
        self.download_dir = str(download_dir)

    @abstractmethod
    def parse(self) -> Iterator[TrialRecord]:
        """Yield one TrialRecord per trial (and per montage file), in a deterministic order."""

    # -- option checks ------------------------------------------------------------------------------------------

    @staticmethod
    def choice(option: str, value: Any, allowed: Collection) -> Any:
        """`value` if it is one of `allowed`, else ValueError naming the option."""
        if value not in allowed:
            raise ValueError(f"{option}={value!r}: expected one of {sorted(map(repr, allowed))}")
        return value

    @staticmethod
    def require(condition: bool, message: str) -> None:
        """ValueError(message) unless condition (use instead of assert)."""
        if not condition:
            raise ValueError(message)

    def path(self, *parts: str, must_exist: bool = True) -> str:
        """A path inside the download; FileNotFoundError if it should exist and does not."""
        path = os.path.join(self.download_dir, *parts)
        if must_exist and not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found (is {self.download_dir} the dataset's download directory?)")
        return path

    @staticmethod
    def sorted_glob(root: str | os.PathLike, pattern: str, hidden: bool = False) -> list[str]:
        """
        Sorted glob (the file system's order is arbitrary). Like glob.glob, files and folders whose name starts
        with "." (e.g. macOS "._*" resource forks) are skipped unless hidden=True (Path.glob returns them).
        """
        paths = sorted(Path(root).glob(pattern))
        if not hidden:
            root = Path(root)
            paths = [p for p in paths if not any(part.startswith(".") for part in p.relative_to(root).parts)]
        return [str(p) for p in paths]
