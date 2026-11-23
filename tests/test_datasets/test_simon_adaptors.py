"""
Simon-lab KIT adaptors: registry names of all six; configuration snapshot and parse/load on small synthetic
downloads of the four whose data are not on disk (presacco2016, brodbeck2022, karunathilake2023/2025), plus the
subject numbering of karunathilake2023_aging (full R-number).
"""
import json
import pickle
import sys
import types

import h5py
import numpy as np
import openpyxl
import pandas as pd
import pytest
from scipy.io import savemat

from cnsp_datasets.datasets.brodbeck2022 import adaptor as b22
from cnsp_datasets.datasets.karunathilake2023 import adaptor as k23
from cnsp_datasets.datasets.karunathilake2023_aging import adaptor as k23a
from cnsp_datasets.datasets.karunathilake2025 import adaptor as k25
from cnsp_datasets.datasets.presacco2016 import adaptor as p16
from cnsp_datasets.datasets.simon_base.common import meg_picks, read_raw
from cnsp_datasets.standardise.format_dataset import get_adaptor_class
from tests.test_datasets.simon_helpers import kit_raw, write_wav


@pytest.mark.parametrize("name, cls", [("presacco2016", "Presacco2016Adaptor"), ("brodbeck2022", "Brodbeck2022Adaptor"),
                                       ("karunathilake2023", "Karunathilake2023Adaptor"),
                                       ("karunathilake2025", "Karunathilake2025Adaptor"),
                                       ("brodbeck2018", "Brodbeck2018Adaptor"),
                                       ("kulasingham2021", "Kulasingham2021Adaptor")])
def test_registry_names(name, cls):
    assert get_adaptor_class(name).__name__ == cls


def test_configuration_snapshot():
    """Guard for the simon_base refactor (2026-11-23): constants as at that time; update when one changes."""
    assert (p16.FS, p16.AUDIO_FS, p16.N_EPOCH, p16.N_REP, p16.N_CH, p16.ONSET, p16.UNIT) == (
        1000, 44100, 60000, 3, 192, 1, 1e-15)
    assert {k: v[4] for k, v in p16.CONDITIONS.items()} == {
        "Q_H": 167, "Q_L": 172, "P3_H": 168, "Zero_H": 169, "M3_H": 170, "M6_H": 171, "P3_L": 173, "Zero_L": 174,
        "M3_L": 175, "M6_L": 176}
    assert {k: v[2] for k, v in p16.GROUPS.items()} == {"Younger": 0, "Older_Normal_Hearing": 0,
                                                        "Older_Hearing_Impaired": 100}
    assert (b22.FS, b22.TASK, b22.ONSET_CODE, b22.JITTER_MS, b22.DRIFT_PPM) == (1000, "Appleseed", 162, 10, 3.4)
    assert sorted(b22.FLAGS) == [(4, 6), (4, 7), (5, 6), (5, 7), (6, 6), (6, 7), (11, 6)]
    assert (k23.FS, k23.AUDIO_FS, k23.N_PASSAGES, k23.FLAT_RATIO) == (1000, 44100, 36, 20)
    assert k23.CONDITIONS == {"main": {164: "pre", 165: "clean", 166: "post"},
                              "control": {164: "control-pre1", 166: "control-pre2", 165: "control-clean"}}
    assert k23.RATING_COLUMN == {"main": {164: "PRE", 166: "POST"}, "control": {164: "PRE1", 166: "PRE2"}}
    assert (len(k23.AUTHORS_ALL), len(k23.AUTHORS_MAIN_ANALYSED)) == (36, 23)
    assert k23.AUTHORS_MAIN_ANALYSED < k23.AUTHORS_ALL
    assert (k25.FS, k25.AUDIO_FS, k25.FLAT_RATIO, k25.SATURATED_RATIO) == (1000, 22050, 20, 30)
    assert sorted(k25.CODES) == [c for c in range(164, 181) if c != 177]
    assert k25.CONDITIONS == {"ASN": "noise", "PH": "nonwords", "ASM": "scrambled", "AS": "narrative"}


# presacco2016 ----------------------------------------------------------------------------------------------------

def _presacco_mat(path, line, bads=(), n=100, zero=None):
    """MATLAB v7.3 file with the shipped `data_exported` layout, the onset edge of `line` at sample 1."""
    rng = np.random.default_rng(1)
    x = rng.standard_normal((3, 192, n))
    x[:, 160:] = 1.0  # idle trigger lines
    x[:, line - 1, 0], x[:, line - 1, 1:] = 5.0, 0.0
    if zero is not None:
        x[:, zero] = 0
    with h5py.File(path, "w") as f:
        d = f.create_group("data_exported")
        labels = d.create_dataset("labels", (1, 192), dtype=h5py.ref_dtype)
        for i in range(192):
            labels[0, i] = f.create_dataset(f"#refs#/{i}", data=np.array([ord(c) for c in str(i + 1)], np.uint16)).ref
        d.create_dataset("sampling_frequency", data=np.array([[1000.0]]))
        b = d.create_dataset("bad_channels", data=np.array([list(bads)], float) if bads else np.zeros(2, np.uint64))
        if not bads:
            b.attrs["MATLAB_empty"] = 1
        d.create_dataset("eeg_data_aligned", data=x)
    return x


def _presacco_download(root):
    for folder, names in (("High Context", ["Quiet_H", "Plus_3_H", "Zero_H", "Minus_3_H", "Minus_6_H", "English_F"]),
                          ("Low Context", ["Quiet_L", "Plus_3_L", "Zero_L", "Minus_3_L", "Minus_6_L", "Dutch_F"])):
        for name in names:
            write_wav(root / "stim" / folder / f"{name}.wav", 44100, np.arange(10) * 100)
    young, impaired = root / "S02_Younger_MEG", root / "S01_Older_Hearing_Impaired_MEG"
    young.mkdir()
    impaired.mkdir()
    for tag in p16.CONDITIONS:
        (young / f"S02_{tag}.mat").touch()
    variants = {"M3_H": "S01HL_M3H", "M6_L": "S01HL_M6L_II", "Zero_H": "S01_HL_ZeroH"}
    for tag in p16.CONDITIONS:
        (impaired / f"{variants.get(tag, 'S01HL_' + tag)}.mat").touch()
    return young, impaired


def test_presacco_parse(tmp_path):
    young, impaired = _presacco_download(tmp_path)
    records = list(p16.ADAPTOR(str(tmp_path)).parse())
    assert len(records) == 2 * 30
    by_subject = {}
    for r in records:
        by_subject.setdefault(r.subject, []).append(r)
    assert sorted(by_subject) == [2, 101]
    hi = by_subject[101]
    assert [r.trial for r in hi] == list(range(1, 31))
    assert [r.condition for r in hi[:6]] == ["quiet"] * 6
    assert hi[6].condition == "english_snr+3dB" and hi[-1].condition == "dutch_snr-6dB"
    assert [(s.name, s.is_attended) for s in hi[0].stimulus] == [("Quiet_H", True)]
    assert [(s.name, s.is_attended) for s in hi[-1].stimulus] == [("Minus_6_L", True), ("Dutch_F", False)]
    assert p16._find_mat(str(impaired), "M6_L").endswith("S01HL_M6L_II.mat")
    audio = hi[-1].stimulus[1].data_fn()
    assert audio["fs"] == 44100 and audio["data"].dtype == np.float32
    np.testing.assert_array_equal(audio["data"][0], (np.arange(10) * 100 / 32768.0).astype(np.float32))


def test_presacco_meg_loader(tmp_path, monkeypatch):
    monkeypatch.setattr(p16, "N_EPOCH", 100)
    mat = str(tmp_path / "S02_P3_H.mat")
    x = _presacco_mat(mat, line=168, bads=(5, 7), zero=10)
    raw = p16._meg_loader(mat, 1, 168, '{"a": 1}')()
    assert raw.ch_names == [f"MEG {i:03d}" for i in range(1, 161)]
    assert raw.get_channel_types() == ["mag"] * 157 + ["ref_meg"] * 3
    assert raw.info["bads"] == ["MEG 006", "MEG 008", "MEG 011"]
    assert raw.info["sfreq"] == 1000 and raw.info["description"] == '{"a": 1}'
    np.testing.assert_array_equal(raw.get_data(), x[1, :160, 1:] * 1e-15)
    with pytest.raises(ValueError, match="onset trigger edge"):
        p16._meg_loader(mat, 1, 167, "{}")()


# brodbeck2022 ----------------------------------------------------------------------------------------------------

def _ndvar_pickle(path, x, freqs, monkeypatch):
    """Pickle shaped like an eelbrain NDVar (classes from a stand-in eelbrain._data_obj module)."""
    mod = types.ModuleType("eelbrain._data_obj")
    for name in ("NDVar", "Scalar", "UTS"):
        cls = type(name, (), {"__module__": "eelbrain._data_obj",
                              "__getstate__": lambda self: self.s, "__setstate__": lambda self, s: None})
        setattr(mod, name, cls)
    monkeypatch.setitem(sys.modules, "eelbrain", types.ModuleType("eelbrain"))
    monkeypatch.setitem(sys.modules, "eelbrain._data_obj", mod)

    def obj(name, state):
        o = getattr(mod, name)()
        o.s = state
        return o

    dims = (obj("Scalar", {"values": freqs}), obj("UTS", {"tmin": 0.0, "tstep": 0.001, "nsamples": x.shape[1]}))
    with open(path, "wb") as f:
        pickle.dump(obj("NDVar", {"x": x, "dims": dims, "name": "gt", "info": {}}), f, protocol=4)


def test_brodbeck2022_parse_and_load(tmp_path, monkeypatch):
    meg = tmp_path / "sub-11" / "meg"
    meg.mkdir(parents=True)
    pd.DataFrame({"onset": [2.0, 3.5, 5.0, 7.0], "value": [162, 167, 162, 162], "stimulus": ["1", "1", "6", "6"]}) \
        .to_csv(meg / "sub-11_task-Appleseed_events.tsv", sep="\t", index=False)
    raw = kit_raw(10_000)
    raw.info["bads"] = ["MEG 003"]
    raw.save(meg / "sub-11_task-Appleseed_split-01_meg.fif", verbose="ERROR")
    (tmp_path / "stimuli").mkdir()
    x = np.array([[1.0, -2.0, 3.0], [0.5, 0.5, -1.0]])
    for stim in ("1", "6"):
        (tmp_path / "stimuli" / f"{stim}.TextGrid").write_text("File type\nxmin = 0\nxmax = 0.25\n", encoding="utf-8")
        _ndvar_pickle(tmp_path / "stimuli" / f"{stim}-gammatone1000.pickle", x, np.array([100.0, 200.0]), monkeypatch)
    records = list(b22.ADAPTOR(str(tmp_path)).parse())
    assert [(r.subject, r.trial, r.condition) for r in records] == [(11, 1, "appleseed"), (11, 2, "appleseed"),
                                                                    (11, 3, "appleseed")]
    assert [s.name for s in records[0].stimulus] == ["appleseed-01"] * 3
    env, spec, grid = (s.data_fn() for s in records[0].stimulus)
    np.testing.assert_array_equal(env["data"], np.array([[1.5, 0.5, 3.0]], np.float32))
    np.testing.assert_array_equal(spec["data"], np.maximum(x, 0).astype(np.float32))
    assert spec["frequencies_hz"].tolist() == [100.0, 200.0] and grid.startswith("File type")
    out = records[2].neural_data_fn()  # segment 3 (flags are for segment 6)
    assert out.ch_names == [f"MEG {i:03d}" for i in range(1, 8)] and out.info["bads"] == ["MEG 003"]
    assert out.n_times == 250
    src = read_raw(str(meg / "sub-11_task-Appleseed_split-01_meg.fif"), 1000)
    np.testing.assert_array_equal(out.get_data(), src.get_data(picks=meg_picks(src.info), start=7000, stop=7250))
    meta = json.loads(out.info["description"])
    assert meta["onset_s"] == 7.0 and meta["stimulus_file"] == "6" and meta["flagged"] is False
    assert (meta["units_as_shipped"], meta["reference"]) == ("T", "not applicable (MEG)")
    assert json.loads(records[1].neural_data_fn().info["description"])["alignment_method"] == "sw_trigger"


# karunathilake2023 / 2025 ------------------------------------------------------------------------------------------

def _save_recording(path, events, n_times=140_000):
    raw = kit_raw(n_times, events=events)
    raw._data[1] *= 1e-3  # MEG 002 flat
    raw._data[3] *= 100   # MEG 004 saturated
    path.parent.mkdir(parents=True, exist_ok=True)
    raw.save(path, verbose="ERROR")


def test_karunathilake2025_parse_and_load(tmp_path):
    names = list(k25.CODES.values())
    for name in names:
        write_wav(tmp_path / "stimuli" / f"{name}.wav", 22050, np.full(2205, 1000))
    order = [c for c in k25.CODES for _ in range(2)]
    events = [(1000 + 2000 * i, c) for i, c in enumerate(order)] + [(90_000, 177)]
    _save_recording(tmp_path / "meg" / "R2682" / "R2682_fif-raw.fif", events)
    records = list(k25.ADAPTOR(str(tmp_path)).parse())
    assert len(records) == 32 and {r.subject for r in records} == {2682}
    assert [r.trial for r in records] == list(range(1, 33))
    assert [r.condition for r in records[:2]] == ["noise", "noise"] and records[-1].condition == "narrative"
    meta = [json.loads(r.neural_data_fn().info["description"]) for r in records[:3]]
    assert [(m["repetition"], m["passage"], m["block"], m["trigger_code"]) for m in meta] == [
        (1, 1, 1, 164), (2, 1, 1, 164), (1, 2, 1, 165)]
    assert meta[2]["onset_s"] == 5.0 and meta[2]["stimulus_file"] == "ASN_M02.wav"
    assert {(m["units_as_shipped"], m["reference"]) for m in meta} == {("T", "not applicable (MEG)")}
    out = records[8].neural_data_fn()
    assert out.n_times == 100 and out.info["bads"] == ["MEG 002", "MEG 004"]
    assert json.loads(out.info["description"])["block"] == 2
    src = read_raw(str(tmp_path / "meg" / "R2682" / "R2682_fif-raw.fif"), 1000)
    np.testing.assert_array_equal(out.get_data(), src.get_data(picks=meg_picks(src.info), start=17_000, stop=17_100))
    assert records[0].stimulus[0].name == "ASN_M01" and records[0].stimulus[0].is_attended


def test_karunathilake2025_rejects_wrong_order(tmp_path):
    for name in k25.CODES.values():
        write_wav(tmp_path / "stimuli" / f"{name}.wav", 22050, np.zeros(10))
    order = list(k25.CODES) * 2  # each code twice, but not in a row
    _save_recording(tmp_path / "R2683" / "R2683_fif-raw.fif", [(1000 + 2000 * i, c) for i, c in enumerate(order)])
    with pytest.raises(ValueError, match="twice in a row"):
        list(k25.ADAPTOR(str(tmp_path)).parse())


def _ratings(path, pid, columns):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = pid
    ws.append(["Trial", *columns, "Q2"])
    for k in range(1, 37):
        ws.append([k, *[10 * k + j for j in range(len(columns))], f"q{k}"])
    wb.save(path)


def test_karunathilake2023_parse_and_load(tmp_path):
    for k in range(1, 37):
        for suffix in ("", "_vocoded"):
            write_wav(tmp_path / "stimuli" / f"split{k}{suffix}.wav", 44100, np.zeros(4410))
    _ratings(tmp_path / "Ratings_main.xlsx", "R2684", ["PRE", "POST"])
    _ratings(tmp_path / "Ratings_control.xlsx", "R2963", ["PRE1", "PRE2"])
    main = [(1000 + 500 * i, c) for i, c in enumerate([164, 165, 166] * 36)]
    control = [(1000 + 500 * i, c) for i, c in enumerate([164, 166, 165] * 36)]
    _save_recording(tmp_path / "meg_main1" / "R2684" / "R2684_voc-raw.fif", main)
    _save_recording(tmp_path / "meg_control" / "R2963" / "R2963_voc-raw.fif", control)
    records = list(k23.ADAPTOR(str(tmp_path)).parse())
    assert len(records) == 216
    by_subject = {s: [r for r in records if r.subject == s] for s in (2684, 2963)}
    assert [r.condition for r in by_subject[2684][:3]] == ["pre", "clean", "post"]
    assert [r.condition for r in by_subject[2963][:3]] == ["control-pre1", "control-pre2", "control-clean"]
    assert [s.name for r in by_subject[2684][3:6] for s in r.stimulus] == ["split2_vocoded", "split2",
                                                                         "split2_vocoded"]
    out = by_subject[2684][4].neural_data_fn()
    meta = json.loads(out.info["description"])
    assert (meta["passage"], meta["presentation"], meta["clarity_rating"], meta["q2_as_shipped"]) == (
        2, "clean", None, "q2")
    assert meta["in_authors_pool"] and meta["in_authors_main_analysis"] and meta["onset_s"] == 3.0
    assert (meta["units_as_shipped"], meta["reference"]) == ("T", "not applicable (MEG)")
    assert out.n_times == 100 and out.info["bads"] == ["MEG 002"]  # flat only: no saturation rule here
    post = json.loads(by_subject[2684][5].neural_data_fn().info["description"])
    assert (post["clarity_rating"], post["vocoded"]) == (21, True)
    pre2 = json.loads(by_subject[2963][1].neural_data_fn().info["description"])
    assert (pre2["study"], pre2["clarity_rating"], pre2["in_authors_main_analysis"]) == ("control", 11, None)


def test_karunathilake2023_aging_subjects(tmp_path, monkeypatch):
    """Full R-numbers; junk-row (R2509) and auditory-component (R2594) tables keyed by them."""
    monkeypatch.setattr(k23a, "N_ARRAY", k23a.DELAY + 5)
    for group, pid, n_solo in (("Younger", "R2509", 9), ("Older", "R2594", 8)):
        arrays = {k: np.zeros((n, k23a.N_ARRAY, k23a.N_COMP)) for k, n in
                  (("dss_solo", n_solo), ("dss_mix", 12), ("dss_babble", 3))}
        path = tmp_path / "Data" / "MEG" / group / f"{pid}_todss_250hz.mat"
        path.parent.mkdir(parents=True, exist_ok=True)
        savemat(path, arrays)
    records = list(k23a.ADAPTOR(str(tmp_path)).parse())
    assert [r.subject for r in records] == [2509] * 23 + [2594] * 23
    raws = [r.neural_data_fn() for r in (records[0], records[23])]
    assert [raw.n_times for raw in raws] == [5, 5]
    meta = [json.loads(raw.info["description"]) for raw in raws]
    assert [(m["participant"], m["auditory_component"]) for m in meta] == [("R2509", "dss1"), ("R2594", "dss2")]
