"""momenian2024: TextGrid interval trimming and mono sentence audio (synthetic)."""
import numpy as np
import pytest
import soundfile

from cnsp_datasets.datasets.momenian2024.adaptor import _read_mono, _trim


def test_trim():
    ivs = [(0.0, 1.0, "a"), (0.8, 1.5, "b"), (1.2, 1.4, "c"), (2.0, 2.5, "d")]
    assert _trim(ivs) == [(0.0, 1.0, "a"), (1.0, 1.5, "b"), (2.0, 2.5, "d")]


def test_read_mono(tmp_path):
    path = tmp_path / "1.001.wav"
    soundfile.write(path, np.c_[np.full(10, 0.5), np.zeros(10)], 44100, subtype="PCM_16")
    x = _read_mono(str(path))
    assert x.dtype == np.float32 and np.allclose(x, 0.25)
    soundfile.write(path, np.zeros(10), 44100, subtype="PCM_16")
    with pytest.raises(ValueError, match="stereo"):
        _read_mono(str(path))
