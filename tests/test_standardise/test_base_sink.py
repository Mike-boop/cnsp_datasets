import numpy as np
import pytest

from cnsp_datasets.standardise.default_sink import DefaultSinkv1
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord


def _record(subject=1, stimuli=()):
    return TrialRecord(subject=subject, session=1, trial=1, condition="c", ns_type="eeg", stimulus=list(stimuli),
                       neural_data_fn=None, anat=None, structural_data_fn=None, behavioural_data_fn=None)


class TestSaveStimuliLoadsOnlyWhenMissing:
    @pytest.mark.parametrize("feature, data, ext", [
        ("envelope", {"fs": 64, "data": np.zeros(4)}, "npz"),
        ("transcript", "some words", "txt"),
        ("textgrid", "File type = \"ooTextFile\"", "TextGrid"),
    ])
    def test_written_once_and_not_reloaded(self, tmp_path, feature, data, ext):
        calls = []

        def data_fn():
            calls.append(1)
            return data

        sink = DefaultSinkv1(str(tmp_path))
        record = _record(stimuli=[StimulusRecord("audio", "story", data_fn, feature_name=feature)])
        sink._save_stimuli(record)
        sink._save_stimuli(record)

        assert (tmp_path / "stimuli" / "audio" / f"story_-_{feature}.{ext}").exists()
        assert len(calls) == 1
