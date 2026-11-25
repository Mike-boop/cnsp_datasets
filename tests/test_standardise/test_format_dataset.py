import argparse

import pytest

from cnsp_datasets.standardise import format_dataset as fd


@pytest.mark.parametrize("opt, expected", [("onset=None", None), ("drift_correction=False", False), ("n=3", 3),
                                           ("subjects=['01', '02']", ["01", "02"]), ("onset=none", "none"),
                                           ("subject=02", "02"), ("path=/a/b", "/a/b"), ("x={[1]: 2}", "{[1]: 2}")])
def test_parse_adaptor_opt_reads_literals_and_falls_back_to_strings(opt, expected):
    assert fd.parse_adaptor_opt(opt) == (opt.split("=")[0], expected)


@pytest.mark.parametrize("opt", ["onset", "=none"])
def test_parse_adaptor_opt_rejects_malformed(opt):
    with pytest.raises(argparse.ArgumentTypeError):
        fd.parse_adaptor_opt(opt)


def test_format_dataset_passes_adaptor_kwargs_to_the_constructor(monkeypatch, tmp_path):
    seen = {}

    class Adaptor:
        def __init__(self, download_dir, **kwargs):
            seen.update(download_dir=download_dir, **kwargs)

        def parse(self):
            yield "record"

    class Sink:
        def __init__(self, save_directory):
            seen["save_directory"] = save_directory

        def save_record(self, record):
            seen["record"] = record

    monkeypatch.setattr(fd, "get_adaptor_class", lambda name: Adaptor)
    out = str(tmp_path / "out")
    fd.format_dataset("x", "dl", out, sinker_handle=Sink, adaptor_kwargs={"onset": None})
    assert seen == {"download_dir": "dl", "onset": None, "save_directory": out, "record": "record"}


def test_main_parses_repeated_adaptor_opts(monkeypatch):
    calls = []
    monkeypatch.setattr(fd, "format_dataset", lambda *args, **kwargs: calls.append((args, kwargs)))
    fd.main(["x", "dl", "out", "--adaptor-opt", "onset=none", "--adaptor-opt", "drift_correction=False"])
    assert calls == [(("x", "dl", "out"), {"adaptor_kwargs": {"onset": "none", "drift_correction": False}})]


def test_main_reports_malformed_adaptor_opt_as_usage_error():
    with pytest.raises(SystemExit) as e:
        fd.main(["x", "dl", "out", "--adaptor-opt", "onset"])
    assert e.value.code == 2


def test_failed_trials_are_logged_and_raise(tmp_path, monkeypatch):
    import mne
    import numpy as np
    import pytest
    from cnsp_datasets.standardise import format_dataset as fd
    from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

    def broken():
        raise OSError("disk on fire")

    def good():
        return mne.io.RawArray(np.zeros((1, 10)), mne.create_info(1, 100.0, "eeg"), verbose="ERROR")

    stim = StimulusRecord("audio", "s1", lambda: {"fs": 100, "data": np.zeros(10)})

    class Adaptor:
        def __init__(self, download_dir):
            pass

        def parse(self):
            yield TrialRecord(1, 1, 1, "c", "eeg", stim, good)
            yield TrialRecord(1, 1, 2, "c", "eeg", stim, broken)

    monkeypatch.setattr(fd, "get_adaptor_class", lambda name: Adaptor)
    with pytest.raises(RuntimeError, match="1 trials could not be saved"):
        fd.format_dataset("x", str(tmp_path), str(tmp_path / "out"))
    text = (tmp_path / "out" / "standardise.log").read_text()
    assert "disk on fire" in text and "trial=2" in text and "1 trials saved, 1 failed" in text
