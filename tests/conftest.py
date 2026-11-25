import pytest


@pytest.fixture(autouse=True)
def _no_local_config(tmp_path_factory, monkeypatch):
    """Tests never see the developer's secrets.json / paths.json (cnsp_datasets.config)."""
    empty = tmp_path_factory.getbasetemp() / "no-such-config.json"
    monkeypatch.setenv("CNSP_SECRETS", str(empty))
    monkeypatch.setenv("CNSP_PATHS", str(empty))
