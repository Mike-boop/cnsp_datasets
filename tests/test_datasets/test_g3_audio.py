"""Group-3 wav loaders: float32 in [-1, 1) and the channel semantics of each dataset."""
import numpy as np
import pytest
import soundfile

from cnsp_datasets.datasets.li2022.adaptor import _audio_loader as li2022_audio


def _stereo(path, fs=44100, n=100):
    left = (np.arange(n) % 50 - 25).astype(np.int16) * 1000
    right = -left
    soundfile.write(path, np.c_[left, right], fs, subtype="PCM_16")
    return left / 32768.0, right / 32768.0


def test_li2022_talkers_are_the_left_and_right_channels(tmp_path):
    left, right = _stereo(tmp_path / "Trail1.wav")
    for channel, expected in ((0, left), (1, right)):
        d = li2022_audio(str(tmp_path / "Trail1.wav"), channel)()
        assert d["fs"] == 44100 and d["data"].dtype == np.float32 and d["data"].shape == (1, 100)
        np.testing.assert_allclose(d["data"][0], expected, atol=1e-7)
    both = li2022_audio(str(tmp_path / "Trail1.wav"), None)()["data"]
    assert both.shape == (2, 100)
    np.testing.assert_allclose(both, [left, right], atol=1e-7)


def test_deoisres2023_reads_channel_0_and_slices(tmp_path):
    from cnsp_datasets.datasets.deoisres2023.adaptor import _audio_loader
    left, _ = _stereo(tmp_path / "a_trig.wav")
    d = _audio_loader(str(tmp_path / "a_trig.wav"), 10, 30)()
    assert d["data"].shape == (1, 20) and d["data"].dtype == np.float32
    np.testing.assert_allclose(d["data"][0], left[10:30], atol=1e-7)


def test_herrmann2025_babble_is_orthogonal_to_the_clean_speech(tmp_path):
    from cnsp_datasets.datasets.herrmann2025.adaptor import _babble_loader
    rng = np.random.default_rng(0)
    clean = (rng.standard_normal(4410) * 3000).astype(np.int16)
    noise = (rng.standard_normal(4410) * 3000).astype(np.int16)
    soundfile.write(tmp_path / "clean.wav", clean, 44100, subtype="PCM_16")
    soundfile.write(tmp_path / "mix.wav", (clean // 2 + noise // 2).astype(np.int16), 44100, subtype="PCM_16")
    b = _babble_loader(str(tmp_path / "mix.wav"), str(tmp_path / "clean.wav"))()["data"]
    assert b.dtype == np.float32 and b.shape == (1, 4410)
    assert abs(np.dot(b[0], clean / 32768.0)) < 1e-3 * np.dot(clean / 32768.0, clean / 32768.0)


def test_geirnaert2025_skips_the_prelisten(tmp_path):
    from cnsp_datasets.datasets.geirnaert2025 import adaptor
    (tmp_path / "stimuli").mkdir()
    soundfile.write(tmp_path / "stimuli" / "S.wav", np.zeros((48000 * 6, 2), np.int16), 48000, subtype="PCM_16")
    d = adaptor._audio_loader(str(tmp_path), "S")()
    assert d["fs"] == 48000 and d["data"].shape == (2, 48000)


def test_mono_loaders_reject_stereo(tmp_path):
    from cnsp_datasets.datasets.nguyen2025.adaptor import _audio_loader
    _stereo(tmp_path / "x.wav")
    with pytest.raises(ValueError, match="expected mono"):
        _audio_loader(str(tmp_path / "x.wav"))()
