"""
li2025 and libribrain100 rely on MNE's private raw._raw_extras[0]["bounds"] (absolute start sample of every data
buffer of a FIF, plus the end). MNE is pinned in pyproject.toml; these tests fail if an MNE update changes it.
"""
import os

import mne
import numpy as np


def _write(tmp_path, n=5000, sfreq=1000.0, buffer_size_sec=1.0):
    raw = mne.io.RawArray(np.random.default_rng(0).standard_normal((2, n)), mne.create_info(2, sfreq, "mag"),
                          first_samp=123, verbose="ERROR")
    path = tmp_path / "x_raw.fif"
    raw.save(path, buffer_size_sec=buffer_size_sec, verbose="ERROR")
    return path


def test_raw_extras_bounds_are_absolute_buffer_starts(tmp_path):
    raw = mne.io.read_raw_fif(_write(tmp_path), preload=False, verbose="ERROR")
    bounds = np.asarray(raw._raw_extras[0]["bounds"])
    assert bounds[0] == raw.first_samp == 123
    assert bounds[-1] == raw.first_samp + raw.n_times
    assert np.all(np.diff(bounds) == 1000)


def test_li2025_reader_drops_a_truncated_last_buffer(tmp_path):
    from cnsp_datasets.datasets.li2025.adaptor import readable
    path = _write(tmp_path)
    with open(path, "r+b") as f:  # cut into the last data buffer
        f.truncate(os.path.getsize(path) - 6000)
    raw = readable(str(path))
    assert raw.n_times < 5000 and raw.n_times % 1000 == 0
    raw.get_data(start=raw.n_times - 1)
