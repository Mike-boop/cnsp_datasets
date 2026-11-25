"""Group 1 restructure (2026-11-25): Simon-lab and Maddox-lab adaptors on BaseAdaptor, audio via iohelpers."""
import importlib

import numpy as np
import pytest
import soundfile

from cnsp_datasets.datasets.karunathilake2023_aging import adaptor as k23a
from cnsp_datasets.datasets.polonenko2021 import adaptor as p21
from cnsp_datasets.datasets.shan2024 import adaptor as shan
from cnsp_datasets.datasets.simon_base import common
from cnsp_datasets.datasets.stoll2025 import adaptor as stoll
from cnsp_datasets.datasets.stoll2025_cortex import adaptor as stoll_cortex
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from tests.test_datasets.simon_helpers import kit_raw, write_wav

GROUP = ["brodbeck2018", "brodbeck2022", "kulasingham2020", "kulasingham2021", "karunathilake2023",
         "karunathilake2023_aging", "karunathilake2025", "presacco2016", "miran2020", "miran2020b", "polonenko2021",
         "polonenko2024", "polonenko2025", "polonenko2026", "stoll2025", "stoll2025_cortex", "shan2024"]


@pytest.mark.parametrize("name", GROUP)
def test_adaptor_is_base_adaptor(name, tmp_path):
    cls = importlib.import_module(f"cnsp_datasets.datasets.{name}.adaptor").ADAPTOR
    assert isinstance(cls, type) and issubclass(cls, BaseAdaptor)
    assert cls(str(tmp_path)).download_dir == str(tmp_path)


def test_option_checks(tmp_path):
    from cnsp_datasets.datasets.kulasingham2020 import adaptor as k20

    assert k20.ADAPTOR(str(tmp_path), subjects="unique").subjects == "unique"
    with pytest.raises(ValueError, match="subjects="):
        k20.ADAPTOR(str(tmp_path), subjects="Unique")
    with pytest.raises(ValueError, match="montage="):
        stoll.ADAPTOR(str(tmp_path), montage="Cortex")


def test_stoll2025_cortex_is_a_fixed_variant(tmp_path):
    a = stoll_cortex.ADAPTOR(str(tmp_path), sfreq=None, drift_correction=False)
    assert isinstance(a, stoll.Stoll2025Adaptor)
    assert (a.montage, a.sfreq, a.drift_correction, a.save_anm) == ("cortex", None, False, False)
    with pytest.raises(TypeError):
        stoll_cortex.ADAPTOR(str(tmp_path), montage="subcortex")


# simon_base audio ---------------------------------------------------------------------------------------------

def test_simon_read_wav_any_pcm_width(tmp_path):
    x = np.array([0.0, 0.5, -1.0, 0.25, -0.125])
    for subtype in ("PCM_16", "PCM_24", "PCM_32"):
        path = str(tmp_path / f"{subtype}.wav")
        soundfile.write(path, x, 22050, subtype=subtype)
        out = common.read_wav(path, 22050)
        assert out.dtype == np.float32 and out.shape == (5,)
        np.testing.assert_allclose(out, x, atol=1e-4)
    path = write_wav(tmp_path / "int16.wav", 22050, np.array([16384, -32768, 32767]))
    np.testing.assert_array_equal(common.read_wav(path, 22050), np.array([16384, -32768, 32767]) / 32768.0)


def test_simon_wav_samples_header_only(tmp_path):
    path = str(tmp_path / "s.wav")
    soundfile.write(path, np.zeros(4410), 44100, subtype="PCM_24")
    assert common.wav_samples(path, 44100, 1000) == 100


def test_crop_meg_keeps_recording_bads(tmp_path):
    raw = kit_raw(5000)
    raw.info["bads"] = ["MEG 002"]
    out = common.crop_meg(raw, 100, 1000, "d", bads=["MEG 004"])
    assert out.info["bads"] == ["MEG 002", "MEG 004"]
    assert raw.info["bads"] == ["MEG 002"]  # the (cached) source is not modified
    assert common.crop_meg(raw, 100, 1000, "d").info["bads"] == ["MEG 002"]
    with pytest.raises(ValueError, match="not in the recording"):
        common.crop_meg(raw, 100, 1000, "d", bads=["MEG 999"])


def test_karunathilake2023_aging_audio_unchanged(tmp_path):
    """Loaders give the same float32 values as the former scipy reader (int16 / 32768, float64 difference)."""
    stim = tmp_path / "Data" / "stimuli"
    rng = np.random.default_rng(0)
    mix, babble = (rng.integers(-20000, 20000, 500).astype(np.int16) for _ in range(2))
    write_wav(stim / "babb_mix_F08_BF08.wav", k23a.AUDIO_FS, mix)
    write_wav(stim / "babb_singleQ_BF08.wav", k23a.AUDIO_FS, babble)
    a = k23a.ADAPTOR(str(tmp_path))
    out = a._audio("babb_mix_F08_BF08")()
    assert out["fs"] == k23a.AUDIO_FS and out["data"].dtype == np.float32
    np.testing.assert_array_equal(out["data"], (mix / 32768.0).astype(np.float32)[None])
    fg = a._foreground()["data"]
    np.testing.assert_array_equal(fg, (mix / 32768.0 - k23a.BABBLE_GAIN * (babble / 32768.0)).astype(np.float32)[None])


# Maddox family -------------------------------------------------------------------------------------------------

def test_stoll2025_dichotic_wav_channel_and_tdt_rate(tmp_path):
    x = np.stack([np.arange(6) * 1000, -np.arange(6) * 1000], axis=1).astype(np.int16)  # col 0 Wrinkle, 1 Alchemyst
    path = write_wav(tmp_path / "wrinkle_alchemyst001.wav", 24414, x)
    for col in (0, 1):
        out = stoll._wav_loader(path, col)()
        assert out["fs"] == stoll.FS_TDT == 24414.0625  # float rate kept, not the header's 24414
        assert out["data"].dtype == np.float32 and out["data"].shape == (1, 6)
        np.testing.assert_array_equal(out["data"][0], (x[:, col] / 32768.0).astype(np.float32))


def test_shan2024_audio_float_and_int16(tmp_path):
    (tmp_path / "stimuli" / "pop").mkdir(parents=True)
    x = np.array([0.01, -0.02, 0.005, 0.0])
    soundfile.write(str(tmp_path / "stimuli" / "pop" / "pop000.wav"), x, 48000, subtype="DOUBLE")
    write_wav(tmp_path / "stimuli" / "pop" / "pop001.wav", 48000, np.array([0, 3277, -3277]))
    a = shan.ADAPTOR(str(tmp_path))
    out = a._audio_loader("pop", "pop000")()
    assert out["fs"] == 48000 and out["data"].dtype == np.float32 and out["data"].shape == (1, 4)
    np.testing.assert_array_equal(out["data"][0], x.astype(np.float32))
    np.testing.assert_array_equal(a._audio_loader("pop", "pop001")()["data"][0],
                                  (np.array([0, 3277, -3277]) / 32768.0).astype(np.float32))


def test_polonenko2021_stimulus_files_sorted_and_unique(tmp_path):
    for folder, name in (("Exp2_Stimuli_Female_Narrator_2", "FemaleNarrator003_bands.hdf5"),
                         ("Exp2_Stimuli_Female_Narrator_1", "FemaleNarrator001_bands.hdf5"),
                         ("Exp1_Stimuli_Male_Narrator_1", "MaleNarrator000_bands.hdf5")):
        (tmp_path / folder).mkdir(exist_ok=True)
        (tmp_path / folder / name).touch()
    files = p21.ADAPTOR(str(tmp_path))._stimulus_files()
    assert list(files) == [("Exp1", "Male", 0), ("Exp2", "Female", 1), ("Exp2", "Female", 3)]
    (tmp_path / "Exp2_Stimuli_Female_Narrator_2" / "FemaleNarrator001_bands.hdf5").touch()
    with pytest.raises(ValueError, match="two stimulus files"):
        p21.ADAPTOR(str(tmp_path))._stimulus_files()
