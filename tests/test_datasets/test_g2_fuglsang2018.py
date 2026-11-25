"""fuglsang2018: FieldTrip's 1-based event.sample -> 0-based onsets, condition codes and wav index (synthetic)."""
import numpy as np
import pytest
import soundfile
from pymatreader import read_mat
from scipy.io import savemat

from cnsp_datasets.datasets.fuglsang2018 import adaptor as fg

FS = 512


def test_match_onsets_is_zero_based():
    codes = [254, 191, 192, 133, 191]  # stray 192 skipped
    samples = [1, 600, 700, 1001, 1500]  # FieldTrip: 1-based
    assert fg._match_onsets(codes, samples, [254, 133], "S") == [0, 1000]
    with pytest.raises(ValueError, match="could not match"):
        fg._match_onsets(codes, samples, [254, 135], "S")
    with pytest.raises(ValueError, match="1-based"):
        fg._match_onsets([254], [0], [254], "S")


def _download(tmp_path, acoustic=None):
    """S1 with every expinfo trial (real expinfo_S1), 20 ms wavs; EEG channel Fp1 = the 0-based sample index."""
    exp = read_mat(fg.__file__.replace("adaptor.py", "expinfos/expinfo_S1.mat"))["data"]
    wavs = {w for w in exp["wavfile_male"] + exp["wavfile_female"] if isinstance(w, str)}
    (tmp_path / "AUDIO").mkdir()
    for w in sorted(wavs):
        soundfile.write(tmp_path / "AUDIO" / w, np.full(882, 16384, np.int16), 44100, subtype="PCM_16")
    triggers = list(exp["trigger"])
    onsets0 = [100 + 50 * i for i in range(len(triggers))]
    n = onsets0[-1] + 100
    eeg = np.zeros((n, 3))
    eeg[:, 0] = np.arange(n)
    values = [v for t in triggers for v in (t, 191)]
    samples = [s for o in onsets0 for s in (o + 1, o + 11)]  # stored 1-based
    savemat(tmp_path / "S1.mat", {"data": {
        "fsample": {"eeg": float(FS)}, "dim": {"chan": {"eeg": np.array(["Fp1", "EXG3", "Status"], dtype=object)}},
        "eeg": eeg, "event": {"eeg": {"value": np.array(values, float), "sample": np.array(samples, float)}}}})
    return exp, onsets0


def test_parse_zero_based_onsets(tmp_path):
    exp, onsets0 = _download(tmp_path)
    trials = list(fg.ADAPTOR(str(tmp_path)).parse())
    assert len(trials) == len(onsets0)
    for trial, onset in zip(trials[:3], onsets0):
        raw = trial.neural_data
        assert raw.ch_names == ["Fp1", "EXG3"] and raw.get_channel_types() == ["eeg", "eog"]
        assert raw.n_times == round(0.02 * FS)
        assert raw.get_data()[0, 0] == pytest.approx(1e-6 * onset)  # first sample = the 0-based onset
    assert trials[0].condition == "natural-R" and len(trials[0].stimulus) == 1
    assert trials[1].condition == "competing-fL-lowRev"
    audio = trials[1].stimulus[0].stim_data
    assert audio["data"].dtype == np.float32 and audio["data"].shape == (1, 882) and audio["data"][0, 0] == 0.5


def test_unknown_acoustic_condition(tmp_path, monkeypatch):
    _download(tmp_path)
    monkeypatch.setattr(fg, "REVERB_MAP", {1: "noRev", 3: "highRev"})
    with pytest.raises(ValueError, match="acoustic_condition 2"):
        list(fg.ADAPTOR(str(tmp_path)).parse())


def test_duplicate_wav(tmp_path):
    _download(tmp_path)
    (tmp_path / "dss.wav").write_bytes((tmp_path / "AUDIO" / "dss.wav").read_bytes())
    with pytest.raises(ValueError, match="dss.wav"):
        fg.ADAPTOR(str(tmp_path))
