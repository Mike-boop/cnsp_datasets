"""das2019: stimulus index (sorted, duplicates raise), label-count check and float32 audio (synthetic)."""
import numpy as np
import pytest
import soundfile

from cnsp_datasets.datasets.das2019 import adaptor as das


def _download(tmp_path):
    (tmp_path / "S1.mat").touch()
    (tmp_path / "stimuli" / "sub").mkdir(parents=True)
    soundfile.write(tmp_path / "stimuli" / "part1_track1_dry.wav", np.array([[16384, -16384]] * 8, np.int16), 8000,
                    subtype="PCM_16")
    soundfile.write(tmp_path / "stimuli" / "sub" / "part2_track1_dry.wav", np.zeros(8, np.int16), 8000,
                    subtype="PCM_16")


def test_audio_index_and_loader(tmp_path):
    _download(tmp_path)
    a = das.ADAPTOR(str(tmp_path))
    assert sorted(a._audio_index) == ["part1_track1_dry.wav", "part2_track1_dry.wav"]
    x = a._make_audio_loader("part1_track1_dry")()
    assert x["fs"] == 8000 and x["data"].dtype == np.float32 and x["data"].shape == (1, 8) and x["data"][0, 0] == 0.5
    with pytest.raises(FileNotFoundError):
        a._make_audio_loader("part9_track1_dry")()


def test_duplicate_basename(tmp_path):
    _download(tmp_path)
    (tmp_path / "stimuli" / "sub" / "part1_track1_dry.wav").write_bytes(b"")
    with pytest.raises(ValueError, match="part1_track1_dry.wav"):
        das.ADAPTOR(str(tmp_path))


def test_label_count_mismatch(tmp_path, monkeypatch):
    _download(tmp_path)
    trial = {"FileHeader": {"SampleRate": 128, "Channels": {"Label": ["Fp1", "AF7"]}},
             "RawData": {"EegData": np.zeros((10, 3))}}
    monkeypatch.setattr(das.Das2019Adapter, "_read_subject", lambda self, path: {"trials": [trial]})
    with pytest.raises(ValueError, match="2 channel labels for 3 channels"):
        das.ADAPTOR(str(tmp_path))._make_eeg_loader("S1.mat", 0)()
    trial["RawData"]["EegData"] = np.zeros((10, 2))
    assert das.ADAPTOR(str(tmp_path))._make_eeg_loader("S1.mat", 0)().ch_names == ["Fp1", "AF7"]
