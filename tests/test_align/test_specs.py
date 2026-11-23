import mne
import numpy as np
import pytest
import torch

from cnsp_datasets.align.classifiers import SimilarityDetector
from cnsp_datasets.align.specs import (
    ClassifierSpec, CzLinkedMastoids, HighPassStimulus, MONTAGES, choose_spec, load_classifier, save_classifier,
)


def _raw(ch_names, fs=1000, seconds=20, extra=(), seed=0):
    """Random EEG on standard_1020 positions, plus extra misc channels."""
    rng = np.random.default_rng(seed)
    info = mne.create_info(list(ch_names) + list(extra), fs, ["eeg"] * len(ch_names) + ["misc"] * len(extra))
    raw = mne.io.RawArray(rng.normal(size=(len(info.ch_names), seconds * fs)) * 1e-5, info, verbose="ERROR")
    raw.set_montage(mne.channels.make_standard_montage("standard_1020"), on_missing="ignore", verbose="ERROR")
    return raw


def _apply(steps, raw):
    for step in steps:
        raw = step.run(raw)
    return raw


def test_default_n_layers_keep_receptive_field_within_segment():
    assert ClassifierSpec(fs=1024).n_layers == 6
    assert ClassifierSpec(fs=512).n_layers == 5
    assert ClassifierSpec(fs=128).n_layers == 4
    assert ClassifierSpec(fs=1024, band="hf").n_layers == 3
    for fs in (128, 512, 1024):
        assert ClassifierSpec(fs=fs).receptive_field_s < 0.2 * 5


def test_hf_cutoff():
    assert ClassifierSpec(fs=1024, band="hf").l_freq == 80
    assert ClassifierSpec(fs=128, band="hf").l_freq == 32
    assert ClassifierSpec(fs=1024).l_freq == 0.5


@pytest.mark.parametrize("montage", ["1020-26", "1020-32"])
def test_tenten_montage_steps_give_model_channels_average_referenced(montage):
    spec = ClassifierSpec(fs=512, montage=montage)
    raw = _raw(MONTAGES["1020-64"])
    raw.info["bads"] = ["Cz"]
    out = _apply(spec.eeg_steps(), raw)
    assert out.ch_names == spec.ch_names
    assert out.info["sfreq"] == 512
    np.testing.assert_allclose(out.get_data().mean(axis=0), 0, atol=1e-12)


def test_cz_linked_mastoids_with_one_mastoid_as_recording_reference():
    raw = _raw(["Cz", "Fz", "Pz", "C3", "C4"], extra=["A2"])
    cz, a2 = raw.get_data(picks=["Cz"])[0], raw.get_data(picks=["A2"])[0]
    out = CzLinkedMastoids(mastoids=(None, "A2")).run(raw)       # left mastoid is the reference (zero)
    assert out.ch_names == ["Cz"]
    np.testing.assert_allclose(out.get_data()[0], cz - a2 / 2)

    out = CzLinkedMastoids(mastoids=("A2", "A2")).run(raw)
    np.testing.assert_allclose(out.get_data()[0], cz - a2)


def test_cz_mastoids_spec_needs_mastoids_and_resamples():
    spec = ClassifierSpec(fs=128, montage="Cz-mastoids")
    with pytest.raises(ValueError):
        spec.eeg_steps()
    kwargs = spec.session_kwargs(mastoids=("A1", "A2"))
    assert kwargs["picks"] is None
    out = _apply(kwargs["eeg_steps"], _raw(["Cz", "Fz", "Pz"], extra=["A1", "A2"]))
    assert out.ch_names == ["Cz"] and out.info["sfreq"] == 128


def test_highpass_stimulus_removes_low_frequencies():
    fs = 1024
    t = np.arange(10 * fs) / fs
    x = np.sin(2 * np.pi * 5 * t) + np.sin(2 * np.pi * 200 * t)
    y = HighPassStimulus(80).run({"fs": fs, "data": x[None]})["data"][0]
    core = slice(fs, -fs)
    assert np.corrcoef(y[core], np.sin(2 * np.pi * 200 * t)[core])[0, 1] > 0.99


def test_save_and_load_roundtrip(tmp_path):
    spec = ClassifierSpec(fs=512, montage="1020-32", band="hf")
    model = SimilarityDetector(**spec.model_kwargs)
    path = save_classifier(tmp_path / f"{spec.name}.pt", model, spec, test_acc=0.6)
    loaded, loaded_spec, checkpoint = load_classifier(path)
    assert loaded_spec == spec and checkpoint["test_acc"] == 0.6 and checkpoint["reference"] == "average"
    x, s = torch.randn(2, 32, 2560), torch.randn(2, 1, 2560)
    with torch.no_grad():
        torch.testing.assert_close(loaded(x, s), model.eval()(x, s))


def test_choose_spec():
    specs = [ClassifierSpec(fs=fs, montage=m) for fs in (128, 512, 1024) for m in MONTAGES]
    bentum = MONTAGES["1020-26"]
    assert choose_spec(specs, 1000, bentum).name == "fs1024_1020-26_broadband"
    assert choose_spec(specs, 500, MONTAGES["1020-64"]).name == "fs512_1020-64_broadband"
    assert choose_spec(specs, 256, MONTAGES["1020-64"]).name == "fs128_1020-64_broadband"
    assert choose_spec(specs, 256, ["Cz", "A1", "A2"]).name == "fs128_Cz-mastoids_broadband"


def test_linked_mastoids_reference_and_rectified_stimulus():
    from cnsp_datasets.align.specs import HalfWaveRectify, LinkedMastoidsReference
    raw = _raw(MONTAGES["1020-26"], extra=["A1", "A2"])
    eeg, a1, a2 = raw.get_data(picks="eeg"), raw.get_data(picks=["A1"])[0], raw.get_data(picks=["A2"])[0]
    out = LinkedMastoidsReference(("A1", "A2")).run(raw)
    np.testing.assert_allclose(out.get_data(picks="eeg"), eeg - (a1 + a2) / 2)
    out = LinkedMastoidsReference((None, "A2")).run(raw)          # left mastoid is the recording reference
    np.testing.assert_allclose(out.get_data(picks="eeg"), eeg - a2 / 2)
    x = HalfWaveRectify().run({"fs": 100, "data": np.array([[-1.0, 2.0, -3.0, 4.0]])})["data"]
    np.testing.assert_array_equal(x, [[0, 2, 0, 4]])


def test_linked_mastoid_spec_steps_names_and_defaults():
    spec = ClassifierSpec(fs=512, montage="1020-26", band="hf", reference="linked-mastoids", stimulus="rectified",
                          hp_cutoff=30)
    assert spec.name == "fs512_1020-26-lm_hp30_rect" and spec.l_freq == 30 and spec.needs_mastoids
    with pytest.raises(ValueError):
        spec.eeg_steps()
    kwargs = spec.session_kwargs(mastoids=(None, "A2"))
    assert kwargs["picks"] is None
    out = _apply(kwargs["eeg_steps"], _raw(MONTAGES["1020-26"], extra=["A2"]))
    assert out.ch_names == spec.ch_names
    assert np.abs(out.get_data().mean(axis=0)).max() > 1e-9      # not average-referenced
    # unchanged defaults: existing checkpoints keep their names and meaning
    assert ClassifierSpec(fs=1024).name == "fs1024_1020-26_broadband"
    assert ClassifierSpec(fs=1024, montage="Cz-mastoids").reference == "linked-mastoids"
    assert ClassifierSpec.from_dict({"fs": 1024, "montage": "1020-26", "band": "hf"}).name == "fs1024_1020-26_hf"
