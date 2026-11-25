import json

from cnsp_datasets import config


def test_environment_wins_then_file_then_legacy_key(tmp_path, monkeypatch):
    secrets = tmp_path / "s.json"
    secrets.write_text(json.dumps({"HF_TOKEN": "from-file", "ru-rdr-usr": "legacy"}))
    secrets.chmod(0o600)
    monkeypatch.setenv("CNSP_SECRETS", str(secrets))
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("RADBOUD_USERNAME", raising=False)
    assert config.get_secret("HF_TOKEN") == "from-file"
    assert config.get_secret("RADBOUD_USERNAME") == "legacy"
    assert config.get_secret("DRYAD_TOKEN") is None
    monkeypatch.setenv("HF_TOKEN", "from-env")
    assert config.get_secret("HF_TOKEN") == "from-env"


def test_paths_and_required(tmp_path, monkeypatch):
    paths = tmp_path / "p.json"
    paths.write_text(json.dumps({"CNSP_IFADV_DIR": str(tmp_path)}))
    monkeypatch.setenv("CNSP_PATHS", str(paths))
    monkeypatch.delenv("CNSP_IFADV_DIR", raising=False)
    assert config.get_path("CNSP_IFADV_DIR") == tmp_path
    assert config.get_path("CNSP_CGN_DIR") is None
    try:
        config.get_path("CNSP_CGN_DIR", required=True)
    except FileNotFoundError as e:
        assert "CNSP_CGN_DIR" in str(e) and "paths.json" in str(e)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_world_readable_secrets_warn(tmp_path, monkeypatch, caplog):
    secrets = tmp_path / "s.json"
    secrets.write_text(json.dumps({"HF_TOKEN": "x"}))
    secrets.chmod(0o644)
    monkeypatch.setenv("CNSP_SECRETS", str(secrets))
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with caplog.at_level("WARNING"):
        config.get_secret("HF_TOKEN")
    assert "readable by other users" in caplog.text
