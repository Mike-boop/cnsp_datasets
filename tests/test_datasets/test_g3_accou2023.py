"""accou2023 file helpers: .npz(.gz) reading and .gz decompression clean up after themselves."""
import gzip
import os

import numpy as np

from cnsp_datasets.datasets.accou2023.adaptor import _load_npz, _plain_file


def test_load_npz_plain_and_gz(tmp_path):
    path = tmp_path / "t_a.npz"
    np.savez(path, audio=np.arange(5.0), fs=np.array(64))
    with open(path, "rb") as src, gzip.open(f"{path}.gz", "wb") as dst:
        dst.write(src.read())
    for p in (str(path), f"{path}.gz"):
        d = _load_npz(p)
        assert int(d["fs"]) == 64 and np.array_equal(d["audio"], np.arange(5.0))


def test_plain_file_removes_the_copy(tmp_path):
    gz = tmp_path / "x_eeg.bdf.gz"
    with gzip.open(gz, "wb") as f:
        f.write(b"abc")
    with _plain_file(str(gz)) as plain:
        assert plain.endswith("x_eeg.bdf") and open(plain, "rb").read() == b"abc"
    assert not os.path.exists(plain) and not os.path.exists(os.path.dirname(plain))
    with _plain_file(str(tmp_path / "y.bdf")) as same:
        assert same == str(tmp_path / "y.bdf")
