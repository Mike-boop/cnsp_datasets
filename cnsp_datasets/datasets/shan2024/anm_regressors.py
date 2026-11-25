"""
shan2024: auditory-nerve-model (ANM) regressors as in the authors' regressor_gen/IHC_ANM_regressor_gen.py `anm()`.

Zilany 2014 (cochlea package) HSR rates at 43 CFs (125 Hz - 16 kHz, 1/6 octave), stimulus resampled 48 -> 100
kHz and scaled to 65 dB SPL re rms 0.01, rates summed over CFs (M1 scale omitted: a constant), shifted by 1 ms,
resampled to 10 kHz; both polarities. One npz per clip: pos, neg (float32, 10 kHz, 12 s), fs.
Not used by the adaptor (audio only). Needs `cochlea` (pip; build with Cython<3 and --no-build-isolation)
in its own env; cochlea 2 uses removed numpy internals, hence the fftpack stub below.
Usage: python anm_regressors.py <stimuli_dir> <out_dir> <n_workers>
"""
import glob
import os
import sys
import types
from multiprocessing import get_context

import numpy as np

FS_IN, FS_UP, FS_OUT = 48000, 100000, 10000
DB, RMS_REF = 65, 0.01
CFS = 2 ** np.arange(np.log2(125), np.log2(16e3 + 1), 1 / 6)
N_OUT = 12 * FS_OUT


def anm(x):
    import cochlea
    from scipy.signal import resample_poly
    np.fft.fftpack = types.SimpleNamespace(_fft_cache={})
    up = resample_poly(x, 25, 12) * (20e-6 / RMS_REF) * 10 ** (DB / 20)
    rates = sum(np.asarray(cochlea.run_zilany2014_rate(up, FS_UP, anf_types="hsr", cf=cf, species="human",
                                                         cohc=1, cihc=1))[:, 0] for cf in CFS)
    shift = int(FS_UP * 0.001)
    rates = np.roll(rates, shift)
    rates[:shift] = rates[shift + 1]
    return resample_poly(rates, 1, 10)[:N_OUT].astype(np.float32)


def clip(args):
    wav, out = args
    from scipy.io import wavfile
    dest = os.path.join(out, os.path.basename(wav)[:-4] + ".npz")
    if os.path.exists(dest):
        return dest
    fs, x = wavfile.read(wav)
    if fs != FS_IN:
        raise ValueError(f"{wav}: {fs} Hz, expected {FS_IN} Hz")
    x = np.asarray(x, float)
    x = x[:, 0] if x.ndim > 1 else x
    np.savez(dest + ".part.npz", pos=anm(x), neg=anm(-x), fs=FS_OUT)
    os.replace(dest + ".part.npz", dest)
    return dest


if __name__ == "__main__":
    stim, out, workers = sys.argv[1], sys.argv[2], int(sys.argv[3])
    os.makedirs(out, exist_ok=True)
    wavs = sorted(w for w in glob.glob(os.path.join(stim, "*", "*.wav")) if "/click/" not in w)
    with get_context("spawn").Pool(workers, maxtasksperchild=20) as pool:
        for i, dest in enumerate(pool.imap_unordered(clip, [(w, out) for w in wavs])):
            print(i + 1, len(wavs), dest, flush=True)
    print("=== done")
