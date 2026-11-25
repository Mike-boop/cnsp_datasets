"""Group-2 CND adaptors: option checks, variant subclasses, duplicate subject files and wav scaling (synthetic)."""
import numpy as np
import pytest
import soundfile

from cnsp_datasets.datasets.diliberto2020 import adaptor as dl20
from cnsp_datasets.datasets.levy2024 import adaptor as levy
from cnsp_datasets.datasets.piazza2025_base import adaptor as piazza
from cnsp_datasets.datasets.piazza2025_l1l import adaptor as l1l
from cnsp_datasets.datasets.piazza2025_l2l import adaptor as l2l
from cnsp_datasets.standardise.adaptor import BaseAdaptor


def test_piazza_variants(monkeypatch):
    seen = []
    monkeypatch.setattr(piazza.Piazza2025Adaptor, "__init__", lambda self, download_dir, group: seen.append(group))
    l1l.ADAPTOR("x"), l2l.ADAPTOR("x")
    assert seen == ["l1l", "l2l"]
    assert issubclass(l1l.ADAPTOR, BaseAdaptor) and issubclass(l2l.ADAPTOR, piazza.Piazza2025Adaptor)


def test_piazza_group_checked(tmp_path):
    with pytest.raises(ValueError, match="group"):
        piazza.Piazza2025Adaptor(str(tmp_path), group="l3l")


def test_diliberto2020_stimulus_checked(tmp_path):
    with pytest.raises(ValueError, match="stimulus"):
        dl20.DiLiberto2020Adaptor(str(tmp_path), stimulus="midi")


def test_diliberto2020_wav(tmp_path):
    x = np.array([[0, 16384], [-32768, 32767]] * 64, dtype=np.int16)  # 128 stereo samples
    soundfile.write(tmp_path / "a.wav", x, dl20.AUDIO_FS, subtype="PCM_16")
    n_stim = int(np.ceil(128 * dl20.STIM_FS / dl20.AUDIO_FS))
    data = dl20._read_wav(str(tmp_path / "a.wav"), n_stim)
    assert data.dtype == np.float32 and data.shape == (2, 128)
    np.testing.assert_array_equal(data[:, :2], [[0, -1], [0.5, 32767 / 32768]])
    with pytest.raises(ValueError, match="length"):
        dl20._read_wav(str(tmp_path / "a.wav"), n_stim + 1)


def test_levy_duplicate_subject(tmp_path):
    (tmp_path / "dataSub7.mat").touch()
    assert list(levy.Levy2024Adaptor(str(tmp_path)).paths) == [7]
    (tmp_path / "dataSub07.mat").touch()
    with pytest.raises(ValueError, match="subject 7"):
        levy.Levy2024Adaptor(str(tmp_path))
