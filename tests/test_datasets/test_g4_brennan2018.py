"""brennan2018: segments starting before the recording are skipped, not clipped (synthetic)."""
import logging

import numpy as np
import pandas as pd
import soundfile

from cnsp_datasets.datasets.brennan2018.adaptor import Brennan2018Adaptor


def _download(root):
    (root / "stimuli").mkdir()
    (root / "sourcedata").mkdir()
    for seg in range(1, 13):
        soundfile.write(root / "stimuli" / f"DownTheRabbitHoleFinal_SoundFile{seg}.wav",
                        np.random.default_rng(seg).uniform(-0.5, 0.5, 4410), 44100, subtype="PCM_16")
    pd.DataFrame(dict(Word=["Alice", "was"], Segment=[1, 1], onset=[0.0, 0.05], offset=[0.04, 0.09],
                      Order=[1, 2])).to_csv(root / "sourcedata" / "AliceChapterOne-EEG.csv", index=False)
    (root / "sub-001" / "eeg").mkdir(parents=True)
    (root / "sub-001" / "eeg" / "sub-001_task-alice_eeg.vhdr").write_text("")


def test_negative_onset_skipped(tmp_path, monkeypatch, caplog):
    _download(tmp_path)
    adaptor = Brennan2018Adaptor(tmp_path)
    monkeypatch.setattr(adaptor, "_segment_onsets", lambda vhdr: {1: (-0.2, "software (events.tsv)", None),
                                                                  2: (3.0, "stimtrack (xcorr quality 40)", 40.0)})
    with caplog.at_level(logging.WARNING):
        trials = list(adaptor.parse())
    assert [t.trial for t in trials] == [2] and "before the recording starts" in caplog.text
    audio = trials[0].stimulus[0].data_fn()
    assert audio["data"].dtype == np.float32 and audio["data"].shape == (1, 4410)
    tg = trials[0].stimulus[1].data_fn()
    assert 'text = ""' in tg  # Segment 2 has no words in the table: tier empty except the filled gap
