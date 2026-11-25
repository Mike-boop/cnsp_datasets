"""jehn2025 / jehn2024 adaptors on a synthetic HDF5 archive in the shipped layout."""
import h5py
import numpy as np
import pytest

from cnsp_datasets.datasets.jehn2024.adaptor import Jehn2024Adaptor
from cnsp_datasets.datasets.jehn2025_ci.adaptor import Jehn2025CIAdaptor


def _archive(path, fs, subs=("103", "104")):
    rng = np.random.default_rng(0)
    with h5py.File(path, "w") as f:
        for code in ("111", "221"):
            for role in ("attended", "distractor"):
                f[f"stimulus_files/{code}/{role}_wav"] = (rng.standard_normal(480) * 1000).astype(np.int16)
        for sub in subs:
            for trial, code in ((1, "111"), (2, "221")):
                f[f"eeg/{sub}/{trial}"] = rng.standard_normal((33, 2 * fs))
                f[f"eeg/{sub}/{trial}"].attrs["stimulus"] = code
            f[f"eeg/{sub}/taken_out_indices"] = np.array([3, 5])


def test_jehn2025_ci(tmp_path):
    _archive(tmp_path / "ci_dataset_1kHz.hdf5", 1000)
    trials = list(Jehn2025CIAdaptor(tmp_path).parse())
    assert [(t.subject, t.trial, t.condition) for t in trials] == [
        (3, 1, "natural_fL_ci"), (3, 2, "competing_fR_ci"), (4, 1, "natural_fR_ci"), (4, 2, "competing_fL_ci")]
    raw = trials[0].neural_data_fn()
    assert len(raw.ch_names) == 31 and raw.info["bads"] == [raw.ch_names[3], raw.ch_names[5]]
    names = [s.name for s in trials[1].stimulus]
    assert names == ["polarnacht_1_target", "elbenwald_1_distractor"]
    audio = trials[1].stimulus[0].data_fn()
    assert audio["fs"] == 48000 and audio["data"].dtype == np.float32 and audio["data"].shape == (1, 480)
    assert np.abs(audio["data"]).max() < 1


def test_jehn2025_unknown_group(tmp_path):
    _archive(tmp_path / "ci_dataset_1kHz.hdf5", 1000, subs=("403",))
    with pytest.raises(ValueError, match="first digit"):
        list(Jehn2025CIAdaptor(tmp_path).parse())


def test_jehn2025_option(tmp_path):
    _archive(tmp_path / "ci_dataset_1kHz.hdf5", 1000)
    with pytest.raises(ValueError, match="drift_correction"):
        Jehn2025CIAdaptor(tmp_path, drift_correction="trial")


def test_jehn2024(tmp_path):
    _archive(tmp_path / Jehn2024Adaptor.H5_FNAME, 125)
    trials = list(Jehn2024Adaptor(tmp_path).parse())
    assert trials[0].condition == "natural_fR_ci"  # no swapped sides in jehn2024
    assert [s.name for s in trials[1].stimulus] == ["polarnacht_1", "elbenwald_1"]
    assert trials[0].neural_data_fn().info["sfreq"] == 125
