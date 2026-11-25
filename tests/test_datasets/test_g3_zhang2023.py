"""zhang2023: the adaptor reads the precomputed alignment tables only; the DNN scan needs its model path set."""
import subprocess
import sys

import pytest


def test_adaptor_import_is_light():
    code = ("import sys, cnsp_datasets.datasets.zhang2023.adaptor as a; "
            "print(sorted(m for m in sys.modules if m == 'torch' or m.startswith('cnsp_datasets.align')))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "[]"


def test_tables_are_in_alignment():
    from cnsp_datasets.datasets.zhang2023.adaptor import read_csv
    assert read_csv("pieces.csv") and read_csv("source_cover.csv")
    assert read_csv("pair_offsets.csv", text=("subject", "lag_s", "z", "p", "lag_a_s", "lag_b_s", "confident"))


def test_dnn_scan_model_path_has_no_default(monkeypatch):
    pytest.importorskip("torch")
    from cnsp_datasets.datasets.zhang2023.alignment import dnn_scan
    monkeypatch.delenv("ZHANG2023_DNN", raising=False)
    with pytest.raises(RuntimeError, match="ZHANG2023_DNN"):
        dnn_scan.model_path()
    monkeypatch.setenv("ZHANG2023_DNN", "/x/model.pt")
    assert dnn_scan.model_path() == "/x/model.pt"
