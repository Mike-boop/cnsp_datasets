import os
import json
import importlib.resources as resources

from typing import Dict,  List, Optional, Iterable, Callable, Any
from dataclasses import dataclass
from cnsp_datasets.download import download_helpers
from cnsp_datasets.download.data_downloader import DataDownloader

REGISTRY_PATH = resources.files("cnsp_datasets.download").joinpath("dataset_registry.json")

### First define a structure for the entries in dataset_registry.json

@dataclass(frozen=True)
class Dataset:
    key: str
    source: str
    identifiers: List[str]
    description: str
    url: Optional[str] = None

    def resolve_downloadables(self) -> List[dict]:
        if self.source == "zenodo":
            getter = download_helpers.doi_to_downloadables_zenodo
            return _gather(getter, self.identifiers)
        if self.source == "dataverse":
            getter = download_helpers.doi_to_downloadables_dataverse
            return _gather(getter, self.identifiers)
        if self.source == "osf":
            getter = download_helpers.doi_to_downloadables_osf
            return _gather(getter, self.identifiers)
        if self.source == "dryad":
            getter = download_helpers.doi_to_downloadables_dryad
            return _gather(getter, self.identifiers)
        if self.source == "deepblue":
            getter = download_helpers.id_to_downloadables_deepblue
            return _gather(getter, self.identifiers)
        if self.source == "openneuro":
            getter = download_helpers.doi_to_downloadables_openneuro
            return _gather(getter, self.identifiers)

        raise ValueError(f"[{self.key}] Unknown source '{self.source}'")

def _gather(getter: Callable[[str], Iterable[dict]], identifiers: List[str]) -> List[dict]:
    files: List[dict] = []
    for ident in identifiers:
        files.extend(getter(ident))
    if not files:
        raise RuntimeError("No files resolved for the provided identifiers.")
    return files


### Now create a function to load dataset_registry.json into a dictionary of Dataset objects

def load_registry(path: str) -> Dict[str, Dataset]:
    with open(path, "r", encoding="utf-8") as f:
        registered_datasets = json.load(f)["datasets"]

    registry: Dict[str, Dataset] = {}
    for key, entry in registered_datasets.items():
        if not isinstance(entry, dict):
            raise ValueError(f"[{key}] dataset entry must be an object.")
        
        source = entry.get("source")
        identifiers = entry.get("identifiers")
        description = entry.get("description", "").strip()
        if isinstance(identifiers, str):
            identifiers = [identifiers]

        url = entry.get("url")

        registry[key] = Dataset(
            key=key,
            source=source,
            identifiers=identifiers,
            description=description,
            url=url,
        )
    return registry


### Finally, create the main function to download a dataset by its name in dataset_registry.json

def download_dataset(
    dataset_name: str,
    download_dir: str,
    max_workers: Optional[int] = None,
    retries: int = 3,
    skip_existing: bool = False,
    extract_archives: bool = True,
    verify_checksum: bool = False,
) -> None:
    """
    Download a named dataset to a specified directory.

    Parameters:
    - dataset_name (str): Name of the dataset as specified in dataset_registry.json.
    - download_dir (str): Directory to download the dataset into.
    - max_workers (int): Number of parallel download workers.
    - retries (int): Number of retries for failed downloads.
    - skip_existing (bool): Skip files that already exist and match the expected checksum.
    - extract_archives (bool): Whether to extract archives after download.
    - verify_checksum (bool): Whether to verify checksums if provided in the metadata.
    """
    registry: Dict[str, Dataset] = load_registry(REGISTRY_PATH)

    if dataset_name not in registry:
        available = ", ".join(sorted(registry.keys()))
        raise ValueError(f"Dataset '{dataset_name}' is not available. Available datasets are: {available}")
    
    # if max_workers is not specified, set it to the number of CPUs
    if max_workers is None:
        max_workers = os.cpu_count() or 4

    ds = registry[dataset_name]
    downloadables = ds.resolve_downloadables()

    download_manager = DataDownloader(
        download_dir,
        max_workers=max_workers,
        retries=retries,
        skip_existing=skip_existing,
        verify_checksum=verify_checksum,
    )
    download_manager.download_batch(downloadables)

    if extract_archives:
        download_helpers.extract_archives(download_dir, recursive=True)