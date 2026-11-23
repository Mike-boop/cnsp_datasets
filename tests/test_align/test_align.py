import mne
import numpy as np
import pytest
import torch

from cnsp_datasets.align.montage import montage_interpolation_matrix


def _biosemi_info():
    montage = mne.channels.make_standard_montage("biosemi64")
    info = mne.create_info(montage.ch_names, 1024, "eeg")
    info.set_montage(montage)
    return info


def test_interpolation_onto_same_montage_is_identity_with_low_regularisation():
    info = _biosemi_info()
    matrix, names = montage_interpolation_matrix(info, mne.channels.make_standard_montage("biosemi64"), alpha=1e-10)
    assert names == info.ch_names
    np.testing.assert_allclose(matrix, np.eye(64), atol=1e-3)


def test_interpolation_onto_other_montage_preserves_constant_signal():
    matrix, names = montage_interpolation_matrix(_biosemi_info(), mne.channels.make_standard_montage("standard_1020"))
    assert matrix.shape == (len(names), 64)
    np.testing.assert_allclose(matrix.sum(axis=1), 1.0, atol=1e-4)


def _smooth_field(info):
    pos = np.array([c["loc"][:3] for c in info["chs"]])
    pos = pos - pos.mean(axis=0)
    pos /= np.linalg.norm(pos, axis=1, keepdims=True)
    return pos @ np.array([0.3, 0.8, 0.5])


def test_pick_montage_keeps_positions_and_order():
    from cnsp_datasets.align.montage import pick_montage
    full = mne.channels.make_standard_montage("standard_1020")
    sub = pick_montage(full, ["Pz", "Fz", "Cz"])
    assert sub.ch_names == ["Pz", "Fz", "Cz"]
    for ch in sub.ch_names:
        np.testing.assert_array_equal(sub.get_positions()["ch_pos"][ch], full.get_positions()["ch_pos"][ch])
    with pytest.raises(ValueError):
        pick_montage(full, ["Fz", "NotAChannel"])


def test_interpolate_to_montage_fills_bad_channels_and_rereferences():
    from cnsp_datasets.align.montage import InterpolateToMontage, pick_montage
    info = _biosemi_info()
    field = _smooth_field(info)
    data = np.outer(field, np.sin(np.linspace(0, 20, 500)))  # a smooth topography, oscillating in time
    data[info.ch_names.index("Cz")] = np.random.default_rng(0).normal(size=500) * 100  # garbage
    raw = mne.io.RawArray(data, info, verbose="ERROR")
    raw.info["bads"] = ["Cz"]

    target = pick_montage(mne.channels.make_standard_montage("standard_1020"), ["Fz", "Cz", "Pz", "C3", "C4"])
    out = InterpolateToMontage(target, alpha=1e-9).run(raw)
    assert out.ch_names == target.ch_names

    cz = out.get_data(picks="Cz")[0]
    assert np.abs(cz).max() < 2  # interpolated from neighbours, not the garbage

    out_ref = InterpolateToMontage(target, alpha=1e-9, average_reference=True).run(raw)
    np.testing.assert_allclose(out_ref.get_data().mean(axis=0), 0, atol=1e-10)


def test_lag_scores_match_direct_model_calls():
    from cnsp_datasets.align.classifiers import SimilarityDetector
    from cnsp_datasets.align.scan import lag_scores
    torch.manual_seed(0)
    model = SimilarityDetector(n_eeg_channels=4, n_stimfeat_channels=1, n_layers=3).eval()
    rng = np.random.default_rng(0)
    eeg = rng.normal(size=(4, 3000)).astype(np.float32)
    stim = rng.normal(size=(1, 3100)).astype(np.float32)
    lags, seg, hop = np.array([-40, 0, 17, 90]), 400, 250

    scores, starts = lag_scores(model, eeg, stim, lags, segment_length=seg, hop=hop, window_batch=3)

    assert scores.shape == (len(lags), len(starts)) and starts[0] == 40
    with torch.no_grad():
        for i, lag in enumerate(lags):
            for j, t in enumerate(starts):
                direct = model(torch.from_numpy(eeg[None, :, t:t + seg]),
                               torch.from_numpy(stim[None, :, t + lag:t + lag + seg])).item()
                assert scores[i, j] == pytest.approx(direct, abs=1e-5)
