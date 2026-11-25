"""armeni2022: CTF bad-channel names and the TextGrid from events.tsv (synthetic)."""
import pandas as pd
import pytest

from cnsp_datasets.datasets.armeni2022.adaptor import _textgrid_text, bad_channels


def test_bad_channels():
    names = ["MRC23-4304", "MLO22-4304", "UADC003-4302"]
    assert bad_channels(names, ["MRC23"]) == ["MRC23-4304"]
    with pytest.raises(ValueError, match="MRP55"):
        bad_channels(names, ["MRC23", "MRP55"])


def test_textgrid_text():
    ev = pd.DataFrame(dict(type=["wav_onset", "word_onset_01", "word_onset_01", "phoneme_onset_01"],
                           value=["10", '"To"', '"Sherlock"', '"t"'], onset=[100.0, 100.5, 100.8, 100.5],
                           duration=["n/a", "0.2", "0.5", "0.1"]))
    tg = _textgrid_text(ev[ev.type != "wav_onset"], 1, 100.0)
    words = tg.split('name = "phones"')[0]
    assert 'text = "Sherlock"' in words and words.count("intervals [") == 4  # gaps 0-0.5, 0.7-0.8 filled
    assert "xmax = 1.3" in tg
