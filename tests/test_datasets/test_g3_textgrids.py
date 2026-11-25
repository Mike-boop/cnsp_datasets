"""Word-timing TextGrids of group-3 adaptors, now written by iohelpers.textgrid."""
from cnsp_datasets.datasets.nguyen2025.adaptor import _textgrid_loader


def test_nguyen2025_textgrid(tmp_path):
    path = tmp_path / "trigger_1.txt"
    rows = ["0\t500\t0\t900\tHej", "1\t1000\t0\t1400\tAnna", "0\t1600\t0\t1500\t-", "5\t2000\t0\t2300\tr\xf8d"]
    path.write_bytes(("\r\n".join(rows) + "\r\n").encode("latin-1"))
    tg = _textgrid_loader(str(path))()
    assert 'name = "words"' in tg and 'name = "targets"' in tg and "size = 2" in tg
    words = tg.split('name = "targets"')[0]
    # gaps filled from 0 s: "", Hej, "", Anna, "", rød (the reversed "-" row dropped)
    assert "intervals: size = 6" in words and 'text = "r\xf8d"' in words and 'text = "-"' not in words
    targets = tg.split('name = "targets"')[1]
    assert 'text = "human_name"' in targets and 'text = "color"' in targets and "xmax = 2.3" in targets


SPEECH_TG = """File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 4
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "words"
        xmin = 0
        xmax = 4
        intervals: size = 3
        intervals [1]:
            xmin = 0
            xmax = 0.5
            text = ""
        intervals [2]:
            xmin = 0.5
            xmax = 1.5
            text = "hej"
        intervals [3]:
            xmin = 1.5
            xmax = 4
            text = "da"
"""


def test_guilleminot2021_tactile_textgrid_and_audio(tmp_path):
    import numpy as np
    import soundfile

    from cnsp_datasets.datasets.guilleminot2021.adaptor import Guilleminot2021Adaptor
    stim = tmp_path / "Stimuli"
    stim.mkdir()
    soundfile.write(stim / "Odin_1.wav", np.full(44100 * 4, 16384, np.int16), 44100, subtype="PCM_16")
    np.save(stim / "Odin_1_phone_.npy", np.zeros(int(39062.5 * 6)))
    (stim / "Odin_1.TextGrid").write_text(SPEECH_TG)
    adaptor = Guilleminot2021Adaptor.__new__(Guilleminot2021Adaptor)
    adaptor.root = str(tmp_path)
    tg = adaptor._make_tactile_tg_loader("1", str(stim / "Odin_1.wav"), 300, True)()
    # shifted by +0.3 s, clipped at the wav's 4 s, gap before the first word filled
    assert "intervals: size = 3" in tg and "xmin = 0.8" in tg and 'text = "hej"' in tg and "xmax = 4.0" in tg
    audio = adaptor._make_audio_loader(str(stim / "Odin_1.wav"))()
    assert audio["data"].dtype == np.float32 and audio["data"].shape == (1, 44100 * 4)
    assert audio["data"].max() == 0.5  # scaled by 32768 (was the raw int16 values)
    tactile = adaptor._make_tactile_loader("1", str(stim / "Odin_1.wav"), 300, True)()
    assert tactile["data"].dtype == np.float32 and tactile["data"].shape == (1, 44100 * 4)
