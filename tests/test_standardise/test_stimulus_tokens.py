import numpy as np

from cnsp_datasets.standardise.flat_sink import FlatSinkV1, FlatSourceV1
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord


def _stim(name, feature, attended):
    return StimulusRecord(modality="audio", name=name, feature_name=feature, is_attended=attended,
                          data_fn=lambda: {"fs": 64, "data": np.zeros(4)})


def _record(stimuli):
    return TrialRecord(subject=1, session=1, trial=1, condition="c", ns_type="eeg", stimulus=stimuli,
                       neural_data_fn=None, anat=None, structural_data_fn=None, behavioural_data_fn=None)


def test_one_token_per_stimulus_not_per_feature(tmp_path):
    record = _record([_stim("story_a", "envelope", True), _stim("story_a", "textgrid", True),
                      _stim("story_b", "envelope", False), _stim("story_b", "textgrid", False)])
    fname = FlatSinkV1(str(tmp_path))._build_fname(record)
    assert fname == "sub-001_-_ses-001_-_trial-001_-_cond-c_-_audio01-story_a_-_audio02-story_b_-_eeg"


def test_source_dedupes_old_filenames(tmp_path):
    (tmp_path / "eeg").mkdir()
    (tmp_path / "audio").mkdir()
    for name in ("story_a", "story_b"):
        for feature in ("envelope", "onsets"):
            np.savez(tmp_path / "audio" / f"{name}_-_{feature}.npz", fs=64, data=np.zeros(4))
    old = "sub-001_-_ses-001_-_trial-001_-_cond-c_-_audio01-story_a_-_audio02-story_a_-_audio03-story_b_-_audio04-story_b_-_eeg"
    (tmp_path / "eeg" / f"{old}.fif").touch()
    trial = FlatSourceV1(tmp_path, assume_first_attended=True)._trial_from_fif_path(tmp_path / "eeg" / f"{old}.fif")
    assert sorted((s.name, s.feature_name, s.is_attended) for s in trial.stimulus) == [
        ("story_a", "envelope", True), ("story_a", "onsets", True),
        ("story_b", "envelope", False), ("story_b", "onsets", False)]
