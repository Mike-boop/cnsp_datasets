"""schueller2024 drift rows matched to a run by meas_date (synthetic table)."""
import datetime as dt

import pandas as pd
import pytest

from cnsp_datasets.datasets.schueller2024.adaptor import subject_rows


def _table(drift_b=9.0):
    d = pd.DataFrame(dict(folder=["P1", "P1", "P2", "P2b"], speaker=["LP", "HP", "LP", "LP"], chapter=[1, 1, 1, 1],
                          drift_ppm=[7.0, 8.0, 9.0, drift_b],
                          meas_date=["2023-01-13 16:07:38+00:00"] * 2 + ["2023-06-22 13:04:32+00:00"] * 2))
    d["meas_date"] = pd.to_datetime(d.meas_date, utc=True)
    return d


def test_match_by_timestamp():
    t = _table()
    when = dt.datetime(2023, 1, 13, 17, 7, 38, tzinfo=dt.timezone(dt.timedelta(hours=1)))  # same instant, CET
    assert subject_rows(t, when).drift_ppm.tolist() == [7.0, 8.0]
    assert subject_rows(t, None).empty
    assert subject_rows(t, dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc)).empty


def test_duplicate_folders():
    when = dt.datetime(2023, 6, 22, 13, 4, 32, tzinfo=dt.timezone.utc)
    assert subject_rows(_table(), when).folder.tolist() == ["P2"]
    with pytest.raises(ValueError, match="different drifts"):
        subject_rows(_table(drift_b=5.0), when)


def test_fallback_logged(monkeypatch, caplog):
    import mne
    import numpy as np

    from cnsp_datasets.datasets.schueller2024 import adaptor as mod

    monkeypatch.setattr(mod, "_drift_table", _table)
    mod._log_fallback.cache_clear()
    raw = mne.io.RawArray(np.zeros((1, 10)), mne.create_info(1, 1000.0), verbose="ERROR")
    adaptor = mod.Schueller2024Adaptor("unused")
    raw.set_meas_date(dt.datetime(2023, 1, 13, 16, 7, 38, tzinfo=dt.timezone.utc))
    assert adaptor.drift_of(raw) == pytest.approx(7.5e-6)
    assert not caplog.records
    raw.set_meas_date(dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc))
    with caplog.at_level("WARNING"):
        assert adaptor.drift_of(raw) == pytest.approx(8.5e-6)  # median of 7, 8, 9, 9
        adaptor.drift_of(raw)
    assert sum("no raw-data drift" in r.getMessage() for r in caplog.records) == 1
    assert mod.Schueller2024Adaptor("unused", drift="dataset").drift_of(raw) == pytest.approx(8.5e-6)
    assert mod.Schueller2024Adaptor("unused", drift=None).drift_of(raw) == 0.0
