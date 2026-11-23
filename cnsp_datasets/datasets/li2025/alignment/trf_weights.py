"""
li2025: per-subject multichannel envelope TRFs (lags x channels), uncorrected and with the group delay applied.

usage: python -m cnsp_datasets.datasets.li2025.alignment.trf_weights <download dir> <out dir> [delay_A,delay_B s]
Writes <out>/sub-XX.npz: w_uncorrected, w_corrected (lags x channels, z units), lags_s, ch_names, ch_locs (MNE loc),
delay_s, group. Input of match_groups.py, butterfly.py and drift.py. Default delays: the adaptor's.
"""
import os
import sys

import numpy as np

from cnsp_datasets.datasets.li2025.adaptor import ONSET_DELAY_S
from cnsp_datasets.datasets.li2025.alignment.common import FS, LAGS, delayed, design, envelope, group, meg, regularised


def main(argv):
    src, out = argv[:2]
    delay = dict(zip("AB", [float(v) for v in argv[2].split(",")])) if len(argv) > 2 else ONSET_DELAY_S
    os.makedirs(out, exist_ok=True)
    env = envelope(src)
    Xu = design(env)
    Ru = regularised(Xu)
    Xc = {g: design(delayed(env, d)) for g, d in delay.items()}
    Rc = {g: regularised(X) for g, X in Xc.items()}
    for sub, info, Y in meg(src):
        g = group(sub)
        wu = np.linalg.solve(Ru, Xu.T @ Y)
        wc = np.linalg.solve(Rc[g], Xc[g].T @ Y)
        np.savez(os.path.join(out, f"sub-{sub:02d}.npz"), w_uncorrected=wu, w_corrected=wc, lags_s=LAGS / FS,
                 ch_names=np.array(info["ch_names"]), ch_locs=np.array([c["loc"] for c in info["chs"]]),
                 delay_s=delay[g], group=g)
        peak = [LAGS[np.argmax(np.sqrt((w ** 2).mean(1)))] / FS for w in (wu, wc)]
        print(sub, g, f"GFP peak uncorrected {peak[0]:+.3f} s, corrected {peak[1]:+.3f} s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
