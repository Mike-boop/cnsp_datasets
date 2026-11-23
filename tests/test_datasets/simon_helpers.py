"""Synthetic KIT-like inputs for the simon_base and Simon-lab adaptor tests."""
import mne
import numpy as np
from scipy.io import wavfile


def kit_raw(n_times, sfreq=1000.0, n_mag=6, events=(), seed=0):
    """Synthetic KIT-like recording: MEG 001..n_mag (`mag`), one `ref_meg`, MISC 001 and STI 014."""
    names = [f"MEG {i:03d}" for i in range(1, n_mag + 2)] + ["MISC 001", "STI 014"]
    info = mne.create_info(names, sfreq, ["mag"] * n_mag + ["ref_meg", "misc", "stim"])
    data = np.random.default_rng(seed).standard_normal((len(names), n_times)) * 1e-13
    data[-1] = 0
    for sample, code in events:
        data[-1, sample:sample + 5] = code
    return mne.io.RawArray(data, info, verbose="ERROR")


def write_wav(path, fs, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, fs, np.asarray(x, dtype=np.int16))
    return str(path)
