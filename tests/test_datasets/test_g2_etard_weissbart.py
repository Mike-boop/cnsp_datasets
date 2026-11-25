"""etard2019 (stimulus names unique per padded content, float32 sums) and weissbart2019 audio (synthetic BIDS)."""
import numpy as np
import pandas as pd
import soundfile

from cnsp_datasets.datasets.etard2019 import adaptor as etard
from cnsp_datasets.datasets.weissbart2019 import adaptor as weissbart

FS = 1000  # wav rate of the synthetic streams (1 sample = 1 ms)


def _run(root, sub, task, run, rows):
    d = root / f"sub-{sub}" / "ses-english" / "eeg"
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(d / f"sub-{sub}_ses-english_task-{task}_run-{run}_events.tsv", sep="\t", index=False)


def _wav(root, rel, x):
    (root / "stimuli" / rel).parent.mkdir(parents=True, exist_ok=True)
    soundfile.write(root / "stimuli" / rel, np.asarray(x, np.float32), FS, subtype="FLOAT")


def test_etard_names_and_padding(tmp_path):
    _wav(tmp_path, "english/lb/run-1_speech.wav", np.full(5, 0.5))
    _wav(tmp_path, "english/lb/run-1_babble.wav", np.full(8, 0.25))
    _wav(tmp_path, "english/clean/run-1_speech.wav", np.full(5, 0.5))
    babble = dict(trial_type="babble", stim_file="english/lb/run-1_babble.wav", duration=0.008)
    speech = dict(trial_type="speech", stim_file="english/lb/run-1_speech.wav", duration=0.005)
    _run(tmp_path, "00", "lb", 1, [dict(babble, onset=1.0, sample=1000), dict(speech, onset=1.002, sample=1002),
                                   dict(trial_type="trigger", onset=1.0, sample=1000, duration=0, stim_file=None)])
    _run(tmp_path, "01", "lb", 1, [dict(babble, onset=3.0, sample=3000), dict(speech, onset=3.003, sample=3003)])
    _run(tmp_path, "00", "clean", 1, [dict(speech, stim_file="english/clean/run-1_speech.wav", onset=1, sample=1000)])
    trials = list(etard.ADAPTOR(str(tmp_path)).parse())
    names = {(t.subject, t.condition): [s.name for s in t.stimulus] for t in trials}
    assert names == {(0, "natural"): ["natural_part_1_story"],
                     (0, "sin_highSNR"): ["sin_highSNR_part_1_story_at2ms", "sin_highSNR_part_1_babble"],
                     (1, "sin_highSNR"): ["sin_highSNR_part_1_story_at3ms", "sin_highSNR_part_1_babble"]}
    story = trials[1].stimulus[0].stim_data  # subject 0, lb
    assert story["fs"] == FS and story["data"].dtype == np.float32
    np.testing.assert_array_equal(story["data"], [[0, 0, 0.5, 0.5, 0.5, 0.5, 0.5]])
    np.testing.assert_array_equal(trials[1].stimulus[1].stim_data["data"], np.full((1, 8), 0.25, np.float32))


def test_weissbart_audio(tmp_path):
    (tmp_path / "participants.tsv").write_text("participant_id\nsub-00\n")
    d = tmp_path / "sub-00" / "eeg"
    d.mkdir(parents=True)
    pd.DataFrame([dict(trial_type="story", trial=1, sample=10, duration=0.004, stim_file="AUNP01/AUNP01.wav")]).to_csv(
        d / "sub-00_task-audiobook_events.tsv", sep="\t", index=False)
    pd.DataFrame([dict(name="Fp1", status="good"), dict(name="Sound", status="bad")]).to_csv(
        d / "sub-00_task-audiobook_channels.tsv", sep="\t", index=False)
    (tmp_path / "stimuli" / "AUNP01").mkdir(parents=True)
    soundfile.write(tmp_path / "stimuli" / "AUNP01" / "AUNP01.wav", np.array([[16384, 0]] * 4, np.int16), 44100,
                    subtype="PCM_16")
    (tmp_path / "stimuli" / "AUNP01" / "AUNP01.TextGrid").write_text("tg")
    (trial,) = weissbart.ADAPTOR(str(tmp_path)).parse()
    audio, tg = (s.stim_data for s in trial.stimulus)
    assert audio["data"].dtype == np.float32 and audio["data"].shape == (1, 4) and audio["data"][0, 0] == 0.5
    assert tg == "tg" and [s.name for s in trial.stimulus] == ["AUNP01", "AUNP01"]
