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
