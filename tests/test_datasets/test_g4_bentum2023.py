"""bentum2023: corpus paths from the config, TextGrid overlaps, wav index (synthetic)."""
import pytest

from cnsp_datasets.datasets.bentum2023 import drift
from cnsp_datasets.datasets.bentum2023.adaptor import Bentum2023Adapter, trim_overlaps


def test_trim_overlaps():
    ivs = [(1.0, 2.0, "b"), (0.0, 1.0005, "a"), (1.5, 1.9, "c"), (2.0, 3.0, "d")]
    assert trim_overlaps(ivs) == [(0.0, 1.0005, "a"), (1.0005, 2.0, "b"), (2.0, 3.0, "d")]


def test_wav_index_duplicates(tmp_path):
    for d in ("a", "b"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "fn001.wav").write_bytes(b"")
    drift.wav_index.cache_clear()
    with pytest.raises(ValueError, match="twice"):
        drift.wav_index(str(tmp_path))


def test_corpus_dirs(tmp_path, monkeypatch):
    (tmp_path / "XML_INFO").mkdir()
    monkeypatch.setenv("CNSP_IFADV_DIR", str(tmp_path / "ifadv"))
    monkeypatch.delenv("CNSP_CGN_DIR", raising=False)
    monkeypatch.setenv("CNSP_PATHS", str(tmp_path / "missing_paths.json"))
    a = Bentum2023Adapter(tmp_path, drift_correction=None)
    assert a.corpus_dirs == {"IFADV": str(tmp_path / "ifadv"), "CGN": None}
    a = Bentum2023Adapter(tmp_path, sdc_dir="/cgn", drift_correction=None)
    assert a.corpus_dirs["CGN"] == "/cgn"
    with pytest.raises(ValueError, match="drift_correction"):
        Bentum2023Adapter(tmp_path, drift_correction="block")
