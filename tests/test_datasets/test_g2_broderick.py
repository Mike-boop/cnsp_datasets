"""Broderick 2019 trio (natural, av, cocktail): the shared CND readers and parse/load on synthetic downloads."""
import numpy as np
import pytest
from scipy.io import savemat

from cnsp_datasets.datasets.broderick2019_av import adaptor as av
from cnsp_datasets.datasets.broderick2019_cocktail import adaptor as cocktail
from cnsp_datasets.datasets.broderick2019_natural import adaptor as natural
from cnsp_datasets.datasets.broderick2019_natural import cnd

N = 300  # samples (> 130, so the orientation is unambiguous)


def _run(path, key="eegData", mastoids=True, channels_first=False):
    rng = np.random.default_rng(0)
    eeg, mas = rng.standard_normal((N, 128)), rng.standard_normal((N, 2))
    m = {key: eeg.T if channels_first else eeg, "fs": 128}
    if mastoids:
        m["mastoids"] = mas
    path.parent.mkdir(parents=True, exist_ok=True)
    savemat(path, m)
    return eeg, mas


def _save(path, m):
    path.parent.mkdir(parents=True, exist_ok=True)
    savemat(path, m)


def _words(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    savemat(path, {"wordVec": np.array(["The", "Cat", "sat"], dtype=object),
                   "onset_time": np.array([[0.5], [1.0], [2.0]]), "offset_time": np.array([[0.9], [1.5], [2.5]])})


def test_channels_first():
    x = np.zeros((N, 128))
    assert cnd.channels_first(x, 128, "x").shape == (128, N)
    assert cnd.channels_first(x.T, 128, "x").shape == (128, N)
    assert cnd.channels_first(np.zeros((100, 128)), 128, "x").shape == (128, 100)  # shorter than 128 samples
    with pytest.raises(ValueError):
        cnd.channels_first(np.zeros((N, 64)), 128, "x")


@pytest.mark.parametrize("channels_first", [False, True])
def test_read_eeg(tmp_path, channels_first):
    eeg, mas = _run(tmp_path / "r.mat", channels_first=channels_first)
    raw = cnd.read_eeg(str(tmp_path / "r.mat"))
    assert raw.ch_names[:2] == ["A1", "A2"] and raw.ch_names[127] == "D32" and raw.ch_names[128:] == ["M1", "M2"]
    assert raw.get_channel_types()[128:] == ["misc", "misc"] and raw.info["sfreq"] == 128
    np.testing.assert_allclose(raw.get_data()[:128], 1e-6 * eeg.T)
    np.testing.assert_allclose(raw.get_data()[128:], 1e-6 * mas.T)


def test_read_eeg_without_mastoids(tmp_path):
    _run(tmp_path / "r.mat", key="EEG", mastoids=False)
    assert len(cnd.read_eeg(str(tmp_path / "r.mat"), "EEG").ch_names) == 128


def test_words_textgrid(tmp_path):
    _words(tmp_path / "Run1.mat")
    tg = cnd.words_textgrid(str(tmp_path / "Run1.mat"))
    assert 'name = "words"' in tg and 'text = "the"' in tg and "intervals: size = 6" in tg  # 3 words + 3 gaps
    rev = cnd.words_textgrid(str(tmp_path / "Run1.mat"), reverse_duration=3.0)
    texts = [ln.split("=")[1].strip() for ln in rev.splitlines() if "text =" in ln]
    assert [t for t in texts if t != '""'] == ['"sat"', '"cat"', '"the"']
    assert "xmin = 0.5\n            xmax = 1.0\n            text = \"sat\"" in rev  # 3 - 2.5 .. 3 - 2.0


def test_natural_parse(tmp_path):
    root = tmp_path / "Natural Speech"
    eeg, _ = _run(root / "EEG" / "Subject1" / "Subject1_Run1.mat")
    _save(root / "Stimuli" / "Envelopes" / "audio1_128Hz.mat", {"env": np.arange(384.0)[:, None]})
    _words(root / "Stimuli" / "Text" / "Run1.mat")
    _run(tmp_path / "Natural Speech - Reverse" / "EEG" / "Subject2" / "Subject2_Run1.mat")
    with pytest.raises(ValueError):
        natural.ADAPTOR(str(tmp_path), mode="forward")
    trials = list(natural.ADAPTOR(str(tmp_path), mode="both").parse())
    assert [(t.subject, t.condition) for t in trials] == [(1, "natural"), (2, "reverse")]
    env, tg = (s.stim_data for s in trials[1].stimulus)
    assert env["data"].dtype == np.float32 and env["data"][0, 0] == 383
    assert '"sat"' in tg and "xmax = 2.5" in tg  # 3 s envelope: last word = 3 - 0.5
    np.testing.assert_allclose(trials[0].neural_data.get_data()[:128], 1e-6 * eeg.T)


def test_av_parse(tmp_path):
    root = tmp_path / "Speech in Noise"
    _run(root / "EEG" / "sub2" / "sub2_av_31.mat", key="EEG")
    _run(root / "EEG" / "sub2" / "sub2_a_1.mat", key="EEG")
    _words(root / "Stimuli" / "Run1.mat")
    trials = list(av.ADAPTOR(str(tmp_path)).parse())
    assert [(t.condition, t.trial, t.stimulus[0].name) for t in trials] == [("sin", 1, "Run1"), ("AV-sin", 31, "Run1")]
    assert '"cat"' in trials[0].stimulus[0].stim_data
    assert trials[1].neural_data.ch_names[-1] == "M2"


def test_cocktail_parse(tmp_path):
    root = tmp_path / "Cocktail Party"
    _run(root / "EEG" / "Subject1" / "Subject1_Run2.mat")
    for story in ("Journey", "20000"):
        _save(root / "Stimuli" / "Envelopes" / story / f"{story}_2_env.mat", {"envelope": np.ones((50, 1))})
        _words(root / "Stimuli" / "Text" / story / "Run2.mat")
    (trial,) = list(cocktail.ADAPTOR(str(tmp_path)).parse())
    assert trial.condition == "competing-fR"  # subject 1 attended Journey (correction note)
    assert [(s.name, s.feature_name, s.is_attended) for s in trial.stimulus] == [
        ("Journey_2", "envelope", True), ("Journey_2", "textgrid", True),
        ("20000_2", "envelope", False), ("20000_2", "textgrid", False)]
    assert trial.stimulus[0].stim_data["data"].shape == (1, 50)
    assert len(trial.neural_data.ch_names) == 130
