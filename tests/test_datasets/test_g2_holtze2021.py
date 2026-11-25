"""holtze2021: ceegrid_dir default (warning), option check, wav channel semantics and float32 envelopes (synthetic)."""
import logging

import numpy as np
import pytest
import soundfile
from scipy.io import savemat

from cnsp_datasets.datasets.holtze2021 import adaptor as h


def _download(root):
    (root / "stimuli").mkdir()
    (root / h.AUDIO_DIR).mkdir(parents=True)
    (root / "participants.tsv").write_text("participant_id\tattended_ch\n")
    savemat(root / "stimuli" / "name_quest.mat", {"name_quest": {"subj": np.array([1.0]), "len": np.array([500.0])}})
    left, right = np.full(640, 8192, np.int16), np.full(640, -16384, np.int16)
    for b in range(1, 6):
        soundfile.write(root / h.AUDIO_DIR / f"Block_{b}_32k.wav", np.c_[left, right], h.AUDIO_FS, subtype="PCM_16")
        for s in (1, 2):
            savemat(root / "stimuli" / f"sig{s}_{b}.mat", {f"sig{s}": np.arange(10.0)[:, None]})


def test_ceegrid_dir_default_warns(tmp_path, caplog):
    _download(tmp_path)
    with caplog.at_level(logging.WARNING, logger=h.__name__):
        a = h.ADAPTOR(str(tmp_path))
    assert a.grid is None and "ds004015" in caplog.text
    assert a.duration[1] == 10 / h.ENV_FS
    with pytest.raises(FileNotFoundError):
        h.ADAPTOR(str(tmp_path), ceegrid_dir=str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="ceegrid_onset"):
        h.ADAPTOR(str(tmp_path), ceegrid_onset="scalp_shifted")


def test_stimuli(tmp_path):
    _download(tmp_path)
    stimuli = h.ADAPTOR(str(tmp_path))._stimuli(2, "right")
    assert [(s.name, s.feature_name, s.is_attended) for s in stimuli] == [
        ("story1_block2", "audio", False), ("story1_block2", h.ENVELOPE, False),
        ("story2_block2", "audio", True), ("story2_block2", h.ENVELOPE, True)]
    left, env, right = stimuli[0].stim_data, stimuli[1].stim_data, stimuli[2].stim_data
    assert left["data"].dtype == np.float32 and left["data"].shape == (1, 640) and left["data"][0, 0] == 0.25
    assert right["data"][0, 0] == -0.5 and right["fs"] == h.AUDIO_FS
    assert env["data"].dtype == np.float32 and env["data"].shape == (1, 10) and env["fs"] == h.ENV_FS
