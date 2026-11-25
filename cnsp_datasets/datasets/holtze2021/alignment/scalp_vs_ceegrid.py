"""Lag and drift between the ds003516 scalp file and the ds004015 cEEGrid file of the same Holtze session.

For block b: scalp sample t16 (ds003516 time) is predicted at t15 = ST15_b + (t16 - ST16_b) in the cEEGrid file; we
measure L such that cEEGrid(t15 + L) matches scalp(t16) (L > 0: cEEGrid content later than predicted).
Coarse: sum over all scalp x cEEGrid channel pairs of squared normalised xcorr (1-40 Hz), +-3 s, whole block
(z < 20: peak searched in -100..0 ms only). Block lag = median of the window lags (robust to artefacts).
Windows: the same in 60-s windows within +-60 ms of the block peak, parabolic peak -> Theil-Sen slope (ppm).
Line noise: 50 Hz phase difference (best scalp vs best cEEGrid channel) in 2-s windows -> slope (ppm).

    python -m cnsp_datasets.datasets.holtze2021.alignment.scalp_vs_ceegrid <ds003516 dir> <ds004015 dir> <work dir> \
        <bjh number> [...]

Cache per subject in <work dir>/scalp_vs_ceegrid/bjh<NN>.json; then scalp_vs_ceegrid_summary.py writes
alignment/ceegrid_onsets.csv (read by the adaptor). Moved here from the review scripts on 2026-11-25 (paths made
arguments, otherwise unchanged; notes.md section 13).
"""
import json
import os
import sys

import mne
import numpy as np
from scipy.fft import irfft, next_fast_len, rfft
from scipy.signal import hilbert
from scipy.stats import theilslopes

FS = 500
BJH15 = [1, 2, 3, 5, 6, 8, 9, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25]  # ds004015 sub-016.. order
MAXLAG = 3 * FS


def load(path):
    raw = mne.io.read_raw_eeglab(path, preload=True, verbose="ERROR")
    st = raw.annotations.onset[raw.annotations.description == "StartTrigger"]
    return raw.get_data(), st


def zs(x):
    x = x - x.mean(1, keepdims=True)
    return x / (x.std(1, keepdims=True) + 1e-20)


def xcorr_sum(a, b, maxlag):
    """sum_ij xcorr(a_i, b_j)[lag]^2 for lags -maxlag..maxlag; b is longer by 2*maxlag (b[k] ~ a[k - maxlag + lag])."""
    n = next_fast_len(b.shape[1] + a.shape[1])
    fa, fb = rfft(a, n, axis=1), rfft(b, n, axis=1)
    tot = np.zeros(2 * maxlag + 1)
    for j in range(b.shape[0]):
        c = irfft(np.conj(fa) * fb[j], n, axis=1)[:, :2 * maxlag + 1] / a.shape[1]
        tot += (c ** 2).sum(0)
    return tot


def parabolic(y, i):
    if 0 < i < len(y) - 1:
        d = (y[i - 1] - y[i + 1]) / (2 * (y[i - 1] - 2 * y[i] + y[i + 1]))
        return i + d
    return float(i)


def run(bjh, ds003516, ds004015, work):
    j = 16 + BJH15.index(bjh)
    out = f"{work}/scalp_vs_ceegrid"
    cf = f"{out}/bjh{bjh:02d}.json"
    if os.path.exists(cf):
        return
    s, st16 = load(f"{ds003516}/sub-{bjh:03d}/eeg/sub-{bjh:03d}_task-AttendedSpeakerParadigmOwnName_eeg.set")
    c, st15 = load(f"{ds004015}/sub-{j:03d}/eeg/sub-{j:03d}_task-AttendedSpeakerParadigmcEEGridAttention_eeg.set")
    sf = mne.filter.filter_data(s, FS, 1, 40, verbose="ERROR")
    cf_ = mne.filter.filter_data(c, FS, 1, 40, verbose="ERROR")
    sl = mne.filter.filter_data(s, FS, 48, 52, verbose="ERROR")
    cl = mne.filter.filter_data(c, FS, 48, 52, verbose="ERROR")
    res = dict(bjh=bjh, ds004015=f"sub-{j:03d}", st16=st16.tolist(), st15=st15.tolist(), blocks=[])
    for b in range(5):
        i16 = int(round(st16[b] * FS))
        a0, a1 = i16 - 25, i16 + 629 * FS  # stay inside the true block (splice at -0.1 s)
        i15 = int(round(st15[b] * FS)) + (a0 - i16)
        a = zs(sf[:, a0:a1])
        bb = zs(cf_[:, i15 - MAXLAG:i15 + (a1 - a0) + MAXLAG])
        tot = xcorr_sum(a, bb, MAXLAG)
        k = int(np.argmax(tot))
        lag = (parabolic(tot, k) - MAXLAG) / FS
        z = (tot[k] - np.median(tot)) / (np.median(np.abs(tot - np.median(tot))) * 1.4826)
        if z < 20:  # weak whole-block peak (artefact-dominated, bjh08 block 4): search the population range only
            pop = slice(MAXLAG - 50, MAXLAG + 1)  # -100..0 ms
            k = pop.start + int(np.argmax(tot[pop]))
        # windows
        W, wl = 60 * FS, 30  # 60 ms search around the block peak
        wl_s, wt = [], []
        for w0 in range(0, (a1 - a0) - W, W // 2):
            aw = zs(sf[:, a0 + w0:a0 + w0 + W])
            off = k - MAXLAG
            bw = zs(cf_[:, i15 + w0 + off - wl:i15 + w0 + off + W + wl])
            t = xcorr_sum(aw, bw, wl)
            kk = int(np.argmax(t))
            wl_s.append((off + parabolic(t, kk) - wl) / FS)
            wt.append((w0 + W / 2) / FS)
        wl_s, wt = np.array(wl_s), np.array(wt)
        slope = theilslopes(wl_s, wt)
        # line noise phase difference
        pi_s = int(np.argmax((sl[:, a0:a1] ** 2).mean(1)))
        pi_c = int(np.argmax((cl[:, i15:i15 + a1 - a0] ** 2).mean(1)))
        off = int(round(lag * FS))
        za = hilbert(sl[pi_s, a0:a1])
        zb = hilbert(cl[pi_c, i15 + off:i15 + off + a1 - a0])
        n2 = 2 * FS
        ph = np.array([np.angle(np.sum(za[q:q + n2] * np.conj(zb[q:q + n2]))) for q in range(0, len(za) - n2, n2)])
        coh = float(np.abs(np.sum(za * np.conj(zb))) / np.sqrt(np.sum(np.abs(za) ** 2) * np.sum(np.abs(zb) ** 2)))
        pu = np.unwrap(ph)
        tq = np.arange(len(pu)) * 2 + 1
        ls = theilslopes(pu, tq)[0] / (2 * np.pi * 50) * 1e6  # ppm (+: cEEGrid phase lags more over time)
        res["blocks"].append(dict(block=b + 1, lag_ms=float(np.median(wl_s)) * 1e3, block_xcorr_lag_ms=lag * 1e3,
                                  peak_z=float(z), peak_rel=float(tot[k] / np.median(tot)),
                                  win_t=wt.tolist(), win_lag_ms=(wl_s * 1e3).tolist(),
                                  drift_ppm=slope[0] * 1e6, drift_ci=[slope[2] * 1e6, slope[3] * 1e6],
                                  line_ppm=float(ls), line_coh=coh, line_phase_sd=float(np.std(pu - np.polyval(np.polyfit(tq, pu, 1), tq)))))
        print(bjh, res["blocks"][-1]["block"], {k_: (round(v, 3) if isinstance(v, float) else v) for k_, v in res["blocks"][-1].items() if not k_.startswith("win")}, flush=True)
    os.makedirs(out, exist_ok=True)
    with open(cf + ".tmp", "w") as f:
        json.dump(res, f)
    os.replace(cf + ".tmp", cf)


if __name__ == "__main__":
    for x in sys.argv[4:]:
        run(int(x), *sys.argv[1:4])
