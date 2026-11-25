"""gwilliams2023: option check and TextGrid from the word/phoneme events (synthetic)."""
import pytest

from cnsp_datasets.datasets.gwilliams2023.adaptor import Gwilliams2023Adaptor


def test_onset_option(tmp_path):
    with pytest.raises(ValueError, match="onset"):
        Gwilliams2023Adaptor(tmp_path, onset="audioo")


def test_textgrid(tmp_path):
    words = [dict(kind="word", word="lw1", start=0.5, duration=0.2),
             dict(kind="phoneme", phoneme="l", start=0.5, duration=0.1),
             dict(kind="phoneme", phoneme="w", start=0.6, duration=0.1)]
    stimuli = Gwilliams2023Adaptor(tmp_path)._stimuli("lw1_0", words)
    assert [s.feature_name for s in stimuli] == ["audio", "textgrid"]
    tg = stimuli[1].data_fn()
    words_tier, phones_tier = tg.split('name = "phones"')
    assert 'text = "lw1"' in words_tier and words_tier.count("intervals [") == 2  # 0-0.5 gap filled
    assert phones_tier.count("intervals [") == 3
