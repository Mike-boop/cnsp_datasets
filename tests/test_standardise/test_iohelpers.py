import mne
import numpy as np
import pytest
import soundfile

from cnsp_datasets.standardise import iohelpers as io
from cnsp_datasets.standardise.adaptor import BaseAdaptor


@pytest.mark.parametrize("subtype,scale", [("PCM_16", 2 ** 15), ("PCM_24", 2 ** 23), ("PCM_32", 2 ** 31)])
def test_read_wav_scales_any_pcm_width(tmp_path, subtype, scale):
    x = np.array([[0.5, -0.25, 0.0, -1.0]], dtype=np.float64).T
    soundfile.write(tmp_path / "a.wav", x, 16000, subtype=subtype)
    y, fs = io.read_wav(str(tmp_path / "a.wav"))
    assert fs == 16000 and y.dtype == np.float32 and y.shape == (1, 4)
    assert np.allclose(y[0], x[:, 0], atol=1 / scale)


def test_read_wav_channels(tmp_path):
    left, right = np.linspace(-0.5, 0.5, 100), np.linspace(0.5, -0.5, 100)
    soundfile.write(tmp_path / "lr.wav", np.stack([left, right], 1), 8000, subtype="FLOAT")
    soundfile.write(tmp_path / "dup.wav", np.stack([left, left], 1), 8000, subtype="FLOAT")
    assert io.read_wav(str(tmp_path / "lr.wav"))[0].shape == (2, 100)
    assert np.allclose(io.read_wav(str(tmp_path / "lr.wav"), channel=1)[0][0], right)
    assert io.read_wav(str(tmp_path / "dup.wav"), collapse_identical=True)[0].shape == (1, 100)
    assert io.read_wav(str(tmp_path / "lr.wav"), collapse_identical=True)[0].shape == (2, 100)
    with pytest.raises(ValueError, match="expected 16000"):
        io.read_wav(str(tmp_path / "lr.wav"), expect_fs=16000)


def test_to_float32():
    assert io.to_float32(np.array([-32768, 16384], np.int16)).tolist() == [-1.0, 0.5]
    assert io.to_float32(np.array([0, 128], np.uint8)).tolist() == [-1.0, 0.0]


def test_status_edges():
    status = np.array([0, 0, 3, 3, 0, 0, 1, 0] , float) + 0xFF00  # upper bits idle high
    assert io.status_edges(status, mask=0xFF).tolist() == [2, 6]
    assert io.status_edges(status, mask=0xFF, kind="fall").tolist() == [4, 7]
    assert io.status_edges(status, mask=0xFFFF, idle=None).tolist() == [2, 6]


def _raw(names=("Fz", "Cz", "EXG1")):
    return mne.io.RawArray(np.vstack([np.ones(10), np.arange(10.0), np.arange(10.0)]),
                           mne.create_info(list(names), 100.0, "eeg"), verbose="ERROR")


def test_mark_bads_keeps_channels():
    raw = _raw()
    io.mark_bads(raw, ["Fz"])
    assert raw.info["bads"] == ["Fz"] and len(raw.ch_names) == 3
    with pytest.raises(ValueError, match="not in the recording"):
        io.mark_bads(raw, ["T7"])
    io.mark_bads(raw, ["T7", "Cz"], strict=False)
    assert raw.info["bads"] == ["Fz", "Cz"]
    assert io.flat_channels(_raw()) == ["Fz"]


def test_bads_for_merges_levels():
    table = {(1, 2, "eeg"): ["A"], (1, 2): ["B"], 1: ["C", "A"]}
    assert io.bads_for(table, 1, 2, "eeg") == ["A", "B", "C"]
    assert io.bads_for(table, 3) == []


def test_rename_channels_types():
    raw = io.rename_channels(_raw(), {"EXG1": "M1", "nope": "x"})
    assert raw.ch_names[-1] == "M1" and raw.get_channel_types()[-1] == "misc"


def test_textgrid_fills_gaps_and_escapes():
    text = io.textgrid({"words": [(0.5, 1.0, 'say "hi"'), (1.2, 2.0, "x")]}, xmax=3.0)
    assert 'text = "say ""hi"""' in text and "intervals: size = 5" in text and 'File type = "ooTextFile"' in text
    with pytest.raises(ValueError, match="overlaps"):
        io.textgrid({"w": [(0, 1, "a"), (0.5, 2, "b")]})


def test_base_adaptor_checks(tmp_path):
    class A(BaseAdaptor):
        def __init__(self, download_dir, mode="a"):
            super().__init__(download_dir)
            self.mode = self.choice("mode", mode, {"a", "b"})

        def parse(self):
            yield from ()

    assert A(tmp_path).mode == "a"
    with pytest.raises(ValueError, match="mode='z'"):
        A(tmp_path, mode="z")
    with pytest.raises(FileNotFoundError):
        A(tmp_path).path("missing")
