import json
import sys

import pytest

from cnsp_datasets import registry


def test_every_dataset_json_is_valid_and_downloads_are_unique():
    cat = registry.catalogue()
    assert len(cat) > 50
    keys = registry.downloads()
    assert all(entry["source"] and entry["identifiers"] for entry in keys.values())


def test_every_adaptor_folder_has_metadata():
    root = registry._package_dirs(registry.PUBLIC_PACKAGE)[0]
    shared_only = {"simon_base", "maddox_base", "jehn2025_base"}
    folders = {p.parent.name for p in root.glob("*/adaptor.py")} - shared_only
    assert folders <= set(registry.catalogue()), sorted(folders - set(registry.catalogue()))


def test_schema_problems_are_reported(tmp_path):
    folder = tmp_path / "x2020"
    folder.mkdir()
    problems = registry.validate_entry({"name": "y", "visibility": "secret", "colour": 1,
                                        "downloads": {"x2020": {"source": "zenodo"}}}, folder)
    text = " ".join(problems)
    for needle in ("'title'", "unknown key 'colour'", "folder name", "visibility", "needs 'source' and 'identifiers'"):
        assert needle in text


def _make_package(tmp_path, pkg, name, entry):
    (tmp_path / pkg / "datasets" / name).mkdir(parents=True)
    (tmp_path / pkg / "__init__.py").write_text("")
    (tmp_path / pkg / "datasets" / "__init__.py").write_text("")
    (tmp_path / pkg / "datasets" / name / "dataset.json").write_text(json.dumps(entry))
    (tmp_path / pkg / "datasets" / name / "adaptor.py").write_text("ADAPTOR = None\n")


def test_extra_packages_from_environment(tmp_path, monkeypatch):
    _make_package(tmp_path, "privpkg", "secret2024", {
        "name": "secret2024", "title": "t", "visibility": "internal",
        "downloads": {"secret2024": {"source": "osf", "identifiers": ["abc"]}}})
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv(registry.PACKAGES_ENV, "privpkg.datasets")
    assert registry.catalogue()["secret2024"].visibility == "internal"
    assert "secret2024" in registry.downloads()
    assert registry.adaptor_module("secret2024") == "privpkg.datasets.secret2024.adaptor"
    monkeypatch.delenv(registry.PACKAGES_ENV)
    assert "secret2024" not in registry.catalogue()
    sys.modules.pop("privpkg", None)


def test_clashing_names_raise(tmp_path, monkeypatch):
    _make_package(tmp_path, "clashpkg", "accou2023", {"name": "accou2023", "title": "t", "visibility": "internal"})
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv(registry.PACKAGES_ENV, "clashpkg.datasets")
    with pytest.raises(ValueError, match="accou2023"):
        registry.catalogue()
