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
