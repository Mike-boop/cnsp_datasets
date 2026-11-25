"""deoisres2023, vanheusden2020: duplicate recordings and a missing meas_date raise clear errors."""
from types import SimpleNamespace

import pytest

from cnsp_datasets.datasets.deoisres2023 import adaptor as deoisres
from cnsp_datasets.datasets.vanheusden2020 import adaptor as vanheusden


def test_deoisres_duplicate_bdf_raises(tmp_path):
    for sub in ("a", "b"):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / "SIN_S01_speech.bdf").touch()
    with pytest.raises(ValueError, match="two SIN_S01_speech.bdf"):
        deoisres.Deoisres2023Adaptor(tmp_path)


def test_vanheusden_duplicate_condition_raises(tmp_path):
    (tmp_path / "S_001_Aided_Speech-Deci.bdf").touch()
    (tmp_path / "S_001_aided_speech-deci.bdf").touch()
    (tmp_path / "S_001_Unaided_Speech_Deci.bdf").touch()  # the loose duplicate: not matched
    with pytest.raises(ValueError, match="two recordings for one condition"):
        vanheusden.Vanheusden2020Adaptor(tmp_path)


@pytest.mark.parametrize("module", [deoisres, vanheusden])
def test_missing_meas_date_raises(monkeypatch, module):
    monkeypatch.setattr(module, "_read", lambda bdf: SimpleNamespace(info={"meas_date": None}))
    with pytest.raises(ValueError, match="no meas_date"):
        module._meas_date("x.bdf")
