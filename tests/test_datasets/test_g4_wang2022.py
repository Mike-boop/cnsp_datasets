"""wang2022: annotation lookup and merged TextGrid intervals (synthetic)."""
import numpy as np
import pytest

from cnsp_datasets.datasets.wang2022.adaptor import annotation_files, merged_intervals


def test_merged_intervals():
    out = merged_intervals(np.array([0.0, 1.0, 1.0, 2.0]), np.array([1.0, 1.5, 1.5, 2.0]), ["a", ",", "。", "x"])
    assert out == [(0.0, 1.0, "a"), (1.0, 1.5, ",。")]  # zero-length "x" dropped


def test_annotation_files(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "story_1_word_time.mat").write_bytes(b"")
    assert list(annotation_files(str(tmp_path))) == ["story_1_word_time.mat"]
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "story_1_word_time.mat").write_bytes(b"")
    with pytest.raises(ValueError, match="twice"):
        annotation_files(str(tmp_path))
