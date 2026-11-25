"""wang2025: patched BrainVision header outlives the call (synthetic)."""
import os

from cnsp_datasets.datasets.wang2025.adaptor import patched_header


def test_patched_header(tmp_path):
    vhdr = tmp_path / "sub-26_task-multitalker_eeg.vhdr"
    vhdr.write_text("[Common Infos]\nDataFile=lab_name.eeg\nMarkerFile=lab_name.vmrk\n", encoding="utf-8")
    path = patched_header(str(vhdr))
    assert patched_header(str(vhdr)) == path and os.path.exists(path)
    text = open(path, encoding="utf-8").read()
    stem = str(tmp_path / "sub-26_task-multitalker_eeg")
    assert f"DataFile={stem}.eeg" in text and f"MarkerFile={stem}.vmrk" in text
