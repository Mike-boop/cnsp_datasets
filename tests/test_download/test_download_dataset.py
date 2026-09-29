import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cnsp_datasets.download.download_dataset import load_registry, Dataset, _gather


MINIMAL_REGISTRY = {
    "datasets": {
        "my_dataset": {
            "source": "zenodo",
            "identifiers": ["10.5281/zenodo.1234567"],
            "description": "A test dataset",
            "url": "https://zenodo.org/records/1234567",
        },
        "multi_id_dataset": {
            "source": "osf",
            "identifiers": ["abc12", "def34"],
            "description": "Dataset spread across two OSF projects",
        },
        "single_string_id": {
            "source": "zenodo",
            "identifiers": "10.5281/zenodo.9999999",
            "description": "Single identifier given as a string",
        },
    }
}


# ── load_registry ─────────────────────────────────────────────────────────────

class TestLoadRegistry:

    def test_returns_dataset_objects(self, tmp_path):
        registry_file = tmp_path / "registry.json"
        registry_file.write_text(json.dumps(MINIMAL_REGISTRY))

        registry = load_registry(str(registry_file))

        assert "my_dataset" in registry
        ds = registry["my_dataset"]
        assert isinstance(ds, Dataset)
        assert ds.source == "zenodo"
        assert ds.description == "A test dataset"

    def test_normalises_string_identifier_to_list(self, tmp_path):
        registry_file = tmp_path / "registry.json"
        registry_file.write_text(json.dumps(MINIMAL_REGISTRY))

        registry = load_registry(str(registry_file))

        assert registry["single_string_id"].identifiers == ["10.5281/zenodo.9999999"]

    def test_multiple_identifiers_preserved(self, tmp_path):
        registry_file = tmp_path / "registry.json"
        registry_file.write_text(json.dumps(MINIMAL_REGISTRY))

        registry = load_registry(str(registry_file))

        assert registry["multi_id_dataset"].identifiers == ["abc12", "def34"]

    def test_optional_url_defaults_to_none(self, tmp_path):
        registry_file = tmp_path / "registry.json"
        registry_file.write_text(json.dumps(MINIMAL_REGISTRY))

        registry = load_registry(str(registry_file))

        assert registry["multi_id_dataset"].url is None


# ── Dataset.resolve_downloadables ─────────────────────────────────────────────

class TestResolveDownloadables:

    def test_raises_on_unknown_source(self):
        ds = Dataset(key="x", source="unknown_repo", identifiers=["abc"], description="")
        with pytest.raises(ValueError, match="Unknown source"):
            ds.resolve_downloadables()

    def test_raises_when_no_files_resolved(self):
        ds = Dataset(key="x", source="zenodo", identifiers=["10.5281/zenodo.0"], description="")
        with patch("cnsp_datasets.download.download_helpers.doi_to_downloadables_zenodo", return_value=[]):
            with pytest.raises(RuntimeError, match="No files"):
                ds.resolve_downloadables()

    def test_routes_to_correct_helper(self):
        helpers = {
            "zenodo": "cnsp_datasets.download.download_helpers.doi_to_downloadables_zenodo",
            "osf": "cnsp_datasets.download.download_helpers.doi_to_downloadables_osf",
            "dryad": "cnsp_datasets.download.download_helpers.doi_to_downloadables_dryad",
            "dataverse": "cnsp_datasets.download.download_helpers.doi_to_downloadables_dataverse",
            "openneuro": "cnsp_datasets.download.download_helpers.doi_to_downloadables_openneuro",
            "deepblue": "cnsp_datasets.download.download_helpers.id_to_downloadables_deepblue",
        }
        dummy_file = [{"url": "http://x.com/f", "name": "f.mat", "checksum": None}]

        for source, helper_path in helpers.items():
            ds = Dataset(key="x", source=source, identifiers=["id123"], description="")
            with patch(helper_path, return_value=dummy_file) as mock_helper:
                result = ds.resolve_downloadables()
                mock_helper.assert_called_once_with("id123")
                assert result == dummy_file


# ── download_dataset (integration-ish) ───────────────────────────────────────

def _dd_module():
    # cnsp_datasets.download.__init__ re-exports the function `download_dataset` under the
    # same name as the submodule, shadowing it in the package namespace. `import ... as`
    # walks parent attributes and hits the function. importlib bypasses that.
    import importlib
    return importlib.import_module("cnsp_datasets.download.download_dataset")


class TestDownloadDataset:

    def test_raises_on_unknown_dataset(self, tmp_path):
        dd_mod = _dd_module()
        with pytest.raises(ValueError, match="not available"):
            dd_mod.download_dataset("nonexistent_dataset_xyz", str(tmp_path))

    def test_calls_downloader_with_resolved_files(self, tmp_path):
        from unittest.mock import patch, MagicMock
        dd_mod = _dd_module()

        dummy_files = [{"url": "http://x.com/f", "name": "f.mat", "checksum": None}]
        mock_dl_instance = MagicMock()

        with patch.object(dd_mod.Dataset, "resolve_downloadables", return_value=dummy_files), \
             patch.object(dd_mod, "DataDownloader", return_value=mock_dl_instance), \
             patch.object(dd_mod, "download_helpers") as mock_helpers:

            dd_mod.download_dataset("fuglsang2018", str(tmp_path), extract_archives=False)

        mock_dl_instance.download_batch.assert_called_once_with(dummy_files)
        mock_helpers.extract_archives.assert_not_called()

    def test_extracts_when_flag_set(self, tmp_path):
        from unittest.mock import patch, MagicMock
        dd_mod = _dd_module()

        dummy_files = [{"url": "http://x.com/f", "name": "f.zip", "checksum": None}]
        mock_dl_instance = MagicMock()

        with patch.object(dd_mod.Dataset, "resolve_downloadables", return_value=dummy_files), \
             patch.object(dd_mod, "DataDownloader", return_value=mock_dl_instance), \
             patch.object(dd_mod, "download_helpers") as mock_helpers:

            dd_mod.download_dataset("fuglsang2018", str(tmp_path), extract_archives=True)

        mock_helpers.extract_archives.assert_called_once()
