import numpy as np
import pytest

from cnsp_datasets.standardise.default_sink import DefaultSinkv1, DefaultSourceV1
from cnsp_datasets.standardise.flat_sink import FlatSinkV1, FlatSourceV1
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


class TestSubjectNumbers:
    @pytest.mark.parametrize("subject, token", [(7, "sub-007"), (123, "sub-123"), (2522, "sub-2522")])
    def test_fname_padding(self, tmp_path, subject, token):
        assert FlatSinkV1(str(tmp_path))._build_fname(_record(subject)).split("_-_")[0] == token

    @pytest.mark.parametrize("subject", [7, 123, 2522])
    @pytest.mark.parametrize("sink_cls, source_cls", [(FlatSinkV1, FlatSourceV1), (DefaultSinkv1, DefaultSourceV1)])
    def test_round_trip(self, tmp_path, subject, sink_cls, source_cls):
        save_dir, fname = sink_cls(str(tmp_path))._get_ns_relative_path(_record(subject))
        save_dir.mkdir(parents=True)
        (save_dir / f"{fname}.fif").touch()
        [fif] = source_cls(tmp_path)._find_fif_files()
        assert source_cls(tmp_path)._parse_tokens_from_fname(fif.stem)["subject"] == subject

    @pytest.mark.parametrize("token", ["sub-07", "sub-1a3"])
    def test_rejects_malformed(self, tmp_path, token):
        with pytest.raises(ValueError):
            FlatSourceV1(tmp_path)._parse_tokens_from_fname(f"{token}_-_ses-001_-_trial-001_-_cond-c_-_eeg")
