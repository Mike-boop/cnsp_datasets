"""
The dataset registry: one `dataset.json` per dataset folder.

    cnsp_datasets/datasets/<name>/dataset.json

Each file describes one dataset folder (see SCHEMA below): where its files are downloaded from (`downloads`, keyed
by the name passed to `download_dataset`; usually the folder name, plus extra keys for auxiliary downloads such
as "<name>_audio"), whether it is public, and catalogue metadata (paper, licence, recording, size, alignment
grade, validation tier). Folders holding only shared code (e.g. simon_base) have no dataset.json.

Further dataset packages (e.g. a private repository of non-public datasets) are found through the environment
variable CNSP_DATASET_PACKAGES, a comma-separated list of importable packages laid out like
cnsp_datasets.datasets (one folder per dataset with adaptor.py and dataset.json). Their names must not clash
with the public ones.
"""
from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

PUBLIC_PACKAGE = "cnsp_datasets.datasets"
PACKAGES_ENV = "CNSP_DATASET_PACKAGES"

VISIBILITY = {"public", "internal"}
DOWNLOAD_KEYS = {"source", "identifiers", "description", "url", "include", "exclude"}
# top-level keys and their types (None: any JSON value); "name" must equal the folder name
SCHEMA: Dict[str, Any] = {
    "name": str,
    "title": str,
    "visibility": str,
    "downloads": dict,
    "paper": dict,          # {"citation", "doi", "url"}
    "licence": str,
    "modality": str,        # "EEG", "MEG", "EEG+MEG", "iEEG", ...
    "system": str,
    "participants": int,
    "listening_hours": (int, float),
    "stimuli": str,         # e.g. "competing speakers", "music"
    "alignment_quality": str,
    "validation_tier": str,
    "notes": str,
}
REQUIRED = ("name", "title", "visibility")


@dataclass(frozen=True)
class DatasetMeta:
    name: str
    folder: Path
    package: str
    title: str
    visibility: str
    downloads: Dict[str, dict] = field(default_factory=dict)
    info: Dict[str, Any] = field(default_factory=dict)  # every other key of dataset.json

    @property
    def adaptor_module(self) -> Optional[str]:
        """Importable adaptor module, or None if the folder has no adaptor.py."""
        return f"{self.package}.{self.name}.adaptor" if (self.folder / "adaptor.py").exists() else None


def packages() -> List[str]:
    """The public dataset package followed by those listed in $CNSP_DATASET_PACKAGES."""
    extra = [p.strip() for p in os.environ.get(PACKAGES_ENV, "").split(",") if p.strip()]
    return [PUBLIC_PACKAGE, *[p for p in extra if p != PUBLIC_PACKAGE]]


def _package_dirs(package: str) -> List[Path]:
    module = importlib.import_module(package)
    # namespace packages can list the same directory twice (e.g. once from sys.path, once from a .pth file)
    return sorted({Path(p).resolve() for p in module.__path__})


def validate_entry(entry: dict, folder: Path) -> List[str]:
    """Schema problems of one dataset.json (empty list if none)."""
    problems = [f"missing key {k!r}" for k in REQUIRED if k not in entry]
    for key, value in entry.items():
        if key not in SCHEMA:
            problems.append(f"unknown key {key!r}")
        elif SCHEMA[key] is not None and value is not None and not isinstance(value, SCHEMA[key]):
            problems.append(f"{key!r} should be {SCHEMA[key]}, not {type(value).__name__}")
    if entry.get("name") != folder.name:
        problems.append(f"name {entry.get('name')!r} differs from the folder name {folder.name!r}")
    if entry.get("visibility") not in VISIBILITY:
        problems.append(f"visibility {entry.get('visibility')!r} not in {sorted(VISIBILITY)}")
    for key, dl in (entry.get("downloads") or {}).items():
        if not isinstance(dl, dict):
            problems.append(f"download {key!r} must be an object")
            continue
        unknown = set(dl) - DOWNLOAD_KEYS
        if unknown:
            problems.append(f"download {key!r}: unknown keys {sorted(unknown)}")
        if not dl.get("source") or not dl.get("identifiers"):
            problems.append(f"download {key!r}: needs 'source' and 'identifiers'")
    return problems


def iter_metadata() -> Iterator[DatasetMeta]:
    """Every dataset.json of every dataset package, in package then name order; raises on schema problems."""
    for package in packages():
        for root in _package_dirs(package):
            for path in sorted(root.glob("*/dataset.json")):
                with open(path, encoding="utf-8") as f:
                    entry = json.load(f)
                problems = validate_entry(entry, path.parent)
                if problems:
                    raise ValueError(f"{path}: " + "; ".join(problems))
                info = {k: v for k, v in entry.items() if k not in ("name", "title", "visibility", "downloads")}
                yield DatasetMeta(name=entry["name"], folder=path.parent, package=package, title=entry["title"],
                                  visibility=entry["visibility"], downloads=entry.get("downloads") or {}, info=info)


@lru_cache(maxsize=None)
def _catalogue(pkgs: tuple) -> Dict[str, DatasetMeta]:
    out: Dict[str, DatasetMeta] = {}
    for meta in iter_metadata():
        if meta.name in out:
            raise ValueError(f"dataset {meta.name!r} is defined in {out[meta.name].package} and {meta.package}")
        out[meta.name] = meta
    return out


def catalogue() -> Dict[str, DatasetMeta]:
    """Dataset folder name -> DatasetMeta (cached per value of $CNSP_DATASET_PACKAGES)."""
    return _catalogue(tuple(packages()))


def downloads() -> Dict[str, dict]:
    """Download key -> registry entry (source, identifiers, ...), over all datasets; keys must be unique."""
    out: Dict[str, dict] = {}
    owner: Dict[str, str] = {}
    for meta in catalogue().values():
        for key, entry in meta.downloads.items():
            if key in out:
                raise ValueError(f"download {key!r} is defined by both {owner[key]} and {meta.name}")
            out[key], owner[key] = entry, meta.name
    return out


def adaptor_module(name: str) -> str:
    """Adaptor module of dataset `name`, searched in every dataset package (also folders without dataset.json)."""
    meta = catalogue().get(name)
    if meta is not None and meta.adaptor_module:
        return meta.adaptor_module
    for package in packages():
        for root in _package_dirs(package):
            if (root / name / "adaptor.py").exists():
                return f"{package}.{name}.adaptor"
    raise ModuleNotFoundError(f"no adaptor for dataset {name!r} in {packages()} (set ${PACKAGES_ENV} for others)")
