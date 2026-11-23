import mne
import numpy as np
import pytest

from cnsp_datasets.datasets.simon_base import common
from tests.test_datasets.simon_helpers import kit_raw, write_wav


def test_find_one(tmp_path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "b" / "x.wav").touch()
    assert common.find_one(str(tmp_path / "**" / "x.wav")) == str(tmp_path / "a" / "b" / "x.wav")
    (tmp_path / "a" / "x.wav").touch()
    with pytest.raises(FileNotFoundError):
        common.find_one(str(tmp_path / "**" / "x.wav"))
    with pytest.raises(FileNotFoundError):
        common.find_one(str(tmp_path / "**" / "y.wav"))


def test_subject_numbers():
    assert common.subject_number("R2262") == 2262
    assert common.subject_number("R0012") == 12
    with pytest.raises(ValueError, match="not an R-number"):
        common.subject_number("S2262")
    common.check_unique_subjects(["R2262", "R3262"])
    with pytest.raises(ValueError, match=r"not unique: \[2262\]"):
        common.check_unique_subjects(["R2262", "R2375", "R2262"])


def test_audio_loader_scales_and_mutes(tmp_path):
    x = np.array([0, 16384, -32768, 32767, 100, -100], dtype=np.int16)
    path = write_wav(tmp_path / "s.wav", 22050, x)
    out = common.audio_loader(path, 22050)()
    assert out["fs"] == 22050 and out["data"].dtype == np.float32 and out["data"].shape == (1, 6)
    np.testing.assert_array_equal(out["data"][0], (x / 32768.0).astype(np.float32))
    muted = common.audio_loader(path, 22050, mute=3)()["data"][0]
    np.testing.assert_array_equal(muted[:3], 0)
    np.testing.assert_array_equal(muted[3:], out["data"][0, 3:])
    with pytest.raises(ValueError, match="44100 Hz mono int16"):
        common.read_wav(path, 44100)
    stereo = write_wav(tmp_path / "st.wav", 22050, np.zeros((4, 2)))
    with pytest.raises(ValueError):
        common.read_wav(stereo, 22050)


def test_wav_samples(tmp_path):
    path = write_wav(tmp_path / "s.wav", 44100, np.zeros(4410))
    assert common.wav_samples(path, 44100, 1000) == 100
    path = write_wav(tmp_path / "t.wav", 2000, np.zeros(2001))
    assert common.wav_samples(path, 2000, 1000) == 1000  # 1000.5 rounds to even
    with pytest.raises(ValueError):
        common.wav_samples(path, 44100, 1000)


def test_epoch_raw_picks_and_bads(tmp_path):
    raw = kit_raw(3000, sfreq=100.0)
    raw._data[2] = 0  # MEG 003 flat in every epoch
    raw.info["bads"] = ["MEG 005"]
    events = np.array([[100, 0, 1], [1100, 0, 2]])
    epochs = mne.Epochs(raw, events, tmin=0, tmax=5.0, baseline=None, preload=True, verbose="ERROR")
    fname = str(tmp_path / "x-epo.fif")
    epochs.save(fname, verbose="ERROR")
    read = common.read_epochs(fname, 100.0, 501)
    out = common.epoch_raw(read, 1)
    assert out.ch_names == [f"MEG {i:03d}" for i in range(1, 8)]
    assert out.get_channel_types() == ["mag"] * 6 + ["ref_meg"]
    assert out.info["bads"] == ["MEG 003", "MEG 005"]
    np.testing.assert_array_equal(out.get_data(), read.get_data(picks=out.ch_names, item=1)[0])
    with pytest.raises(ValueError, match="epoch length"):
        common.read_epochs(fname, 100.0, 500)
    with pytest.raises(ValueError, match="rate"):
        common.read_epochs(fname, 200.0, 501)


def test_continuous_helpers(tmp_path):
    raw = kit_raw(140_000, events=[(2000, 164), (5000, 177), (8000, 165)])
    raw._data[1] *= 1e-3  # flat
    raw._data[3] *= 100   # saturated
    path = str(tmp_path / "R2682_fif-raw.fif")
    raw.save(path, verbose="ERROR")
    read = common.read_raw(path, 1000)
    assert common.read_raw(path, 1000) is read  # cached
    np.testing.assert_array_equal(common.stim_events(read, [164, 165])[:, [0, 2]], [[2000, 164], [8000, 165]])
    assert common.rms_bads(path, 1000, 20) == ("MEG 002",)
    assert common.rms_bads(path, 1000, 20, 30) == ("MEG 002", "MEG 004")
    out = common.crop_meg(read, 2000, 500, "{}", common.rms_bads(path, 1000, 20))
    assert out.ch_names == [f"MEG {i:03d}" for i in range(1, 8)]
    assert out.info["bads"] == ["MEG 002"] and out.info["description"] == "{}"
    np.testing.assert_array_equal(out.get_data(), read.get_data(picks=out.ch_names, start=2000, stop=2500))
    read.info["bads"] = ["MEG 006"]
    assert common.crop_meg(read, 2000, 10, "{}").info["bads"] == ["MEG 006"]  # shipped bads kept
    with pytest.raises(ValueError, match="sfreq"):
        common.read_raw(path, 200)
