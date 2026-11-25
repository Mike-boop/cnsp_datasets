"""libribrain100: h5 lookup, TextGrid on the trial axis, rebuilt audio (synthetic)."""
import numpy as np
import pandas as pd
import pytest
import soundfile

from cnsp_datasets.datasets.libribrain100.adaptor import LibriBrain100Adaptor, _audio_loader, _textgrid_loader


def test_h5_lookup(tmp_path):
    d = tmp_path / "LibriBrain" / "Sherlock1" / "derivatives" / "serialised"
    d.mkdir(parents=True)
    adaptor = LibriBrain100Adaptor(tmp_path)
    assert adaptor._meg_file("LibriBrain", "Sherlock1", 1, 11) is None
    (d / "sub-1_ses-11_a.h5").write_bytes(b"")
    assert adaptor._meg_file("LibriBrain", "Sherlock1", 1, 11).endswith("sub-1_ses-11_a.h5")
    (d / "sub-1_ses-11_b.h5").write_bytes(b"")
    with pytest.raises(ValueError, match="several h5"):
        adaptor._meg_file("LibriBrain", "Sherlock1", 1, 11)


def test_textgrid_clipped():
    ev = pd.DataFrame(dict(kind=["word", "phoneme", "word"], segment=["the", "dh", "end"],
                           timemeg=[9.9995, 9.9995, 10.5], duration=[0.3, 0.1, 0.2]))
    part = pd.DataFrame(dict(meg_start=[10.0], src_start=[0.0], src_end=[1.0]))
    tg = _textgrid_loader(ev, part, 10.0)()
    words = tg.split('name = "phones"')[0]
    assert "xmin = 0.0\n" in words and 'text = "the"' in words and words.count("intervals [") == 3


def test_audio_rebuilt(tmp_path):
    wav = tmp_path / "a.wav"
    soundfile.write(wav, np.full((100, 2), 0.5), 100, subtype="PCM_16")
    part = pd.DataFrame(dict(wav=[str(wav)] * 2, wav_start=[0.0, 0.5], whole=[False, False], meg_start=[0.0, 1.0],
                             src_start=[0.0, 0.5], src_end=[0.25, 0.75]))
    out = _audio_loader(part, 0.0, 1.25)()
    assert out["fs"] == 100 and out["data"].dtype == np.float32 and out["data"].shape == (1, 125)
    assert np.allclose(out["data"][0, :25], 0.5) and not out["data"][0, 25:100].any()
