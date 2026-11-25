"""yang2026 TextGrid from the MFA start-time tables (synthetic)."""
import numpy as np

from cnsp_datasets.datasets.yang2026_en.adaptor import Yang2026ENAdaptor


def test_textgrid(tmp_path):
    adaptor = Yang2026ENAdaptor(tmp_path)
    audio = tmp_path / adaptor.cfg["folder"] / "stimuli" / "audio"
    audio.mkdir(parents=True)
    for stem, labels, starts in (("mfa_word", ["<sp>", "ice", "cream"], [0.0, 0.5, 1.0]),
                                 ("mfa_phoneme", ["AY", "S"], [0.5, 0.7])):
        (audio / f"{stem}.txt").write_text("\n".join(labels) + "\n", encoding="utf-8")
        np.savetxt(audio / f"{stem}_stime.txt", starts)
    tg = adaptor._textgrid_loader(2.0)()
    assert 'name = "words"' in tg and 'name = "phones"' in tg
    words = tg.split('name = "phones"')[0]
    assert words.count("intervals [") == 3 and 'text = ""' in words and 'text = "cream"' in words
    phones = tg.split('name = "phones"')[1]
    assert phones.count("intervals [") == 3  # leading gap 0-0.5 filled
