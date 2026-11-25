"""narayanan2021 pulse-train onset and drift (synthetic Trigger channel)."""
import numpy as np
import pytest

from cnsp_datasets.datasets.narayanan2021.adaptor import pulse_drift, train_onset


def _trigger(starts, n=600_000):
    trig = np.zeros(n)
    for s in starts:
        trig[s:s + 34] = 1
    return trig


def test_stray_pulse_skipped():
    period = 1000 * (1 - 10e-6)
    train = np.round(50_000 + np.arange(390) * period).astype(int)
    trig = _trigger([33_000, *train])  # stray pulse 17 s before the train
    assert train_onset(trig, 1000.0) == train[0]
    assert abs(pulse_drift(trig, 1000.0) + 10e-6) < 1e-6


def test_no_train_raises():
    with pytest.raises(ValueError, match="no 1-s pulse train"):
        train_onset(_trigger([1000, 5000, 9000]), 1000.0)
    with pytest.raises(ValueError, match="no 1-s pulse train"):
        pulse_drift(_trigger([]), 1000.0)
