"""Per-listener latency/drift summary, proposed per-chapter latency and figures, from decoder_scan.py and dnn_scan.py.

Latency L = seconds from the trigger-fit t0 to the sound in the EEG (scans cover 0..4 s).
Estimators per chapter:
 decoder (listener-specific, LOCO): strong if z >= 5 and jackknife SE <= 25 ms;
 DNN (accou2023 fs128 classifier): curve smoothed along lags (Gaussian, 3 samples = 23 ms), global peak; z of the
   peak prominence (max - median) against 5 mismatched-envelope nulls; jackknife SE over 10 window chunks; strong if
   z >= 4 and SE <= 40 ms.
Proposed L: decoder if strong; else DNN - offset if DNN strong (offset = listener median of DNN - decoder over chapters
strong in both, >= 3 of them, else the dataset median offset passed via OFFSETS json); else the listener median.
Drift delta (ppm, > 0 = the sound slides later through the chapter, i.e. audio stretched in EEG time), over chapters
with a strong decoder: (a) Theil-Sen through 30-s window peaks (within L +- 0.25 s), demeaned per chapter, pooled;
95% CI by bootstrapping chapters; (b) joint_fit per chapter on the window curves upsampled x10 along lags (cubic; the
linear interpolation in the old joint_fit biased drift towards 0; joint_fit is called with upsample=1 since the curves
are already upsampled here), pooled_drift per listener and per story.
Held-out check: latency from one half (odd/even 30-s blocks) vs r on the other half (decoder trained on other chapters).
usage: analyse_timing.py <sub> ...   -> align/summary/sub-<sub>{.json,_chapters.csv,_timing.png}"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 1)
import csv, json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d
from scipy.stats import theilslopes
from cnsp_datasets.align.scan import joint_fit, pooled_drift, peak_offset
C = settings.WORK
A = f'{C}/align'; os.makedirs(f'{A}/summary', exist_ok=True)
FS = 50; WIN = 30 * FS; UP = 10
GRID = np.arange(-150, 150.5, 0.5)
OFFSETS = json.load(open(os.environ['OFFSETS'])) if os.environ.get('OFFSETS') else {}
OLD = {'01': dict(GD1=474, GD2=476, GD3=519, GD4=542, GD5=474, GD8=617, LP1=495, LP2=511, LP3=489, LP10=471,
                  LP11=501, LP12=518, LP13=516, LP14=490)}


def label(k):
    return ('GD' if k.startswith('garnett') else 'LP') + str(int(k[-2:]))


def dnn_chapter(f):
    d = np.load(f)
    lat = -d['lags'] / 128 - (float(d['t0']) - float(d['te128']))
    o = np.argsort(lat); lat = lat[o]
    S = gaussian_filter1d(d['scores'][o], 3, axis=0)
    c = S.mean(1); prom = c.max() - np.median(c)
    nl = gaussian_filter1d(d['null'][o], 3, axis=0)
    nprom = nl.max(0) - np.median(nl, 0)
    z = (prom - nprom.mean()) / (nprom.std(ddof=1) + 1e-9)
    n = S.shape[1]; ch = np.minimum(np.arange(n) * 10 // n, 9)
    sums = np.stack([S[:, ch == q].sum(1) for q in range(10)])
    loo = np.array([lat[0] + peak_offset(sums.sum(0) - sums[q]) / 128 for q in range(10)])
    se = np.sqrt(9 / 10 * ((loo - loo.mean()) ** 2).sum())
    return dict(L=float(lat[0] + peak_offset(c) / 128), z=float(z), se=float(se), prom=float(prom), lat=lat, c=c - np.median(c), n=n)


for sub in sys.argv[1:]:
    rows = list(csv.DictReader(open(f'{A}/decoder/sub-{sub}.csv')))
    zf = np.load(f'{A}/decoder/sub-{sub}.npz')
    sh = zf['shifts']
    keys = [r['key'] for r in rows]
    R = {r['key']: r for r in rows}
    dec_strong = {k: float(R[k]['z']) >= 5 and float(R[k]['se_ms']) <= 25 for k in keys}
    D = {k: dnn_chapter(f'{A}/scans/sub-{sub}_{k}.npz') for k in keys if os.path.exists(f'{A}/scans/sub-{sub}_{k}.npz')}
    dnn_strong = {k: k in D and D[k]['z'] >= 4 and D[k]['se'] <= 0.040 for k in keys}
    both = [k for k in keys if dec_strong[k] and dnn_strong[k]]
    diffs = np.array([D[k]['L'] * 1e3 - float(R[k]['L_ms']) for k in both])
    offset = float(np.median(diffs)) if len(both) >= 3 else OFFSETS.get('dataset_median_ms', np.nan)
    prop, src = {}, {}
    for k in keys:
        if dec_strong[k]:
            prop[k], src[k] = float(R[k]['L_ms']), 'decoder'
        elif dnn_strong[k] and np.isfinite(offset):
            prop[k], src[k] = D[k]['L'] * 1e3 - offset, 'dnn'
    med = float(np.median(list(prop.values()))) if prop else np.nan
    for k in keys:
        if k not in prop:
            prop[k], src[k] = med, 'listener median'
    Ls = np.array([prop[k] for k in keys if src[k] != 'listener median'])
    # option B: listener median unless the chapter's estimate deviates by > max(40 ms, 3 SE)
    def se_of(k):
        return float(R[k]['se_ms']) if src[k] == 'decoder' else D[k]['se'] * 1e3 if src[k] == 'dnn' else np.inf
    hyb = {k: prop[k] if src[k] != 'listener median' and abs(prop[k] - med) > max(40, 3 * se_of(k)) else med for k in keys}
    # drift (decoder windows, strong decoder chapters)
    pts, fits, per, fkeys = [], [], {}, []
    for k in keys:
        if not dec_strong[k]:
            continue
        W = zf[f'W_{k}']; st = zf[f'wstarts_{k}']; off = float(R[k]['off_ms']) / 1e3
        if W.shape[1] < 3:
            continue
        cc = float(R[k]['L_ms']) / 1e3 - off
        sel = np.flatnonzero(np.abs(sh - cc) <= 0.25)
        pk = np.array([sh[sel[0]] + peak_offset(W[sel, j]) / FS for j in range(W.shape[1])])
        t = (st + WIN / 2) / FS
        pts.append((t - t.mean(), pk - np.median(pk)))
        Wu = CubicSpline(np.arange(len(sh)), W, axis=0)(np.arange((len(sh) - 1) * UP + 1) / UP)
        try:
            f = joint_fit(Wu, st * UP, np.arange(Wu.shape[0]), FS * UP, WIN * UP, drift_grid_ppm=GRID, n_chunks=min(10, W.shape[1]), upsample=1)
            fits.append(f); fkeys.append(k); per[k] = (f['drift_ppm'], f['drift_se'])
        except ValueError:
            pass
    res = dict(sub=sub, n_chapters=len(keys), n_decoder_strong=int(sum(dec_strong.values())),
               n_dnn_strong=int(sum(dnn_strong.values())), n_both=len(both), n_fallback=sum(v == 'listener median' for v in src.values()),
               n_from_dnn=sum(v == 'dnn' for v in src.values()),
               S0=float(zf['S0']) / FS, dnn_minus_decoder_ms=offset,
               dnn_minus_decoder_mad_ms=float(np.median(np.abs(diffs - np.median(diffs)))) if len(both) else np.nan,
               dnn_decoder_r=float(np.corrcoef([D[k]['L'] for k in both], [float(R[k]['L_ms']) for k in both])[0, 1]) if len(both) > 2 else np.nan,
               median_L_ms=med, L_iqr_ms=[float(np.percentile(Ls, 25)), float(np.percentile(Ls, 75))] if len(Ls) else None,
               L_range_ms=[float(Ls.min()), float(Ls.max())] if len(Ls) else None,
               n_late_gt_200ms=int(np.sum(Ls > med + 200)) if len(Ls) else 0,
               n_optionB_deviating=int(sum(hyb[k] != med for k in keys)))
    hs = [k for k in keys if dec_strong[k]]
    if len(hs) > 2:
        core = [k for k in hs if abs(float(R[k]['L_ms']) - med) < 150]
        res.update(halves_r_core=float(np.corrcoef([float(R[k]['LA_ms']) for k in core], [float(R[k]['LB_ms']) for k in core])[0, 1]) if len(core) > 2 else np.nan,
                   halves_absdiff_med_ms=float(np.median([abs(float(R[k]['LA_ms']) - float(R[k]['LB_ms'])) for k in hs])),
                   core_sd_ms=float(np.std([float(R[k]['L_ms']) for k in core])))
        hv, hc = [], []
        for k in hs:
            off = float(R[k]['off_ms']) / 1e3
            for est, other in (('LA_ms', 'cB'), ('LB_ms', 'cA')):
                c = zf[f'{other}_{k}']
                v = tuple(float(np.interp(L - off, sh, c)) for L in (float(R[k][est]) / 1e3, med / 1e3, 0.5))
                hv.append(v)
                if k in core:
                    hc.append(v)
        hv = np.array(hv)
        res.update(heldout_r_own=float(hv[:, 0].mean()), heldout_r_median=float(hv[:, 1].mean()), heldout_r_500=float(hv[:, 2].mean()),
                   heldout_frac_own_better=float(np.mean(hv[:, 0] > hv[:, 1])))
        if hc:
            hc = np.array(hc)  # core chapters only (|L - median| < 150 ms): does per-chapter help beyond the outliers?
            res.update(heldout_core_r_own=float(hc[:, 0].mean()), heldout_core_r_median=float(hc[:, 1].mean()),
                       heldout_core_frac_own_better=float(np.mean(hc[:, 0] > hc[:, 1])), n_outliers=len(hs) - len(core))
    if len(pts) > 1:
        tt = np.concatenate([p[0] for p in pts]); pp = np.concatenate([p[1] for p in pts])
        ts = theilslopes(pp, tt)[0] * 1e6
        rng = np.random.default_rng(0)
        boot = [theilslopes(np.concatenate([pts[i][1] for i in idx]), np.concatenate([pts[i][0] for i in idx]))[0] * 1e6
                for idx in (rng.integers(0, len(pts), len(pts)) for _ in range(500))]
        res.update(drift_theilsen_ppm=float(ts), drift_theilsen_ci95=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))])
    if len(fits) > 1:
        p = pooled_drift(fits, FS * UP)
        res.update(drift_pooled_ppm=p['drift_ppm'], drift_pooled_se=p['drift_se'], n_drift_chapters=len(fits))
        for story in ('garnettdream', 'littleprince'):
            fs_ = [f for f, k in zip(fits, fkeys) if k.startswith(story)]
            if len(fs_) > 1:
                q = pooled_drift(fs_, FS * UP); res[f'drift_{story}'] = [q['drift_ppm'], q['drift_se'], len(fs_)]
    json.dump(res, open(f'{A}/summary/sub-{sub}.json', 'w'), indent=1)
    with open(f'{A}/summary/sub-{sub}_chapters.csv', 'w') as fh:
        w = csv.writer(fh)
        w.writerow(['sub', 'chapter', 'L_proposed_ms', 'source', 'L_optionB_ms', 'L_dec_ms', 'dec_se_ms', 'dec_z', 'L_dnn_ms', 'dnn_se_ms', 'dnn_z',
                    'LA_ms', 'LB_ms', 'drift_ppm', 'drift_se'])
        for k in keys:
            r = R[k]; d = D.get(k, {}); dr = per.get(k, (np.nan, np.nan))
            w.writerow([sub, label(k), round(prop[k], 1), src[k], round(hyb[k], 1), r['L_ms'], r['se_ms'], r['z'],
                        round(d.get('L', np.nan) * 1e3, 1), round(d.get('se', np.nan) * 1e3, 1), round(d.get('z', np.nan), 2),
                        r['LA_ms'], r['LB_ms'], round(dr[0], 1), round(dr[1], 1)])
    print(json.dumps(res))
    # figure
    fig, ax = plt.subplots(1, 3, figsize=(21, 6), gridspec_kw=dict(width_ratios=[3, 1.2, 1.4]), layout='constrained')
    lab = set()

    def once(name):
        if name in lab:
            return None
        lab.add(name); return name
    for i, k in enumerate(keys):
        r = R[k]
        ax[0].errorbar(i - .12, float(r['L_ms']), yerr=min(float(r['se_ms']), 500), fmt='o', ms=5, capsize=2,
                       color='C0' if dec_strong[k] else '0.75', label=once('decoder (LOCO) +-SE; grey = weak'))
        if dec_strong[k]:
            ax[0].plot([i - .3, i - .3], [float(r['LA_ms']), float(r['LB_ms'])], 'x', color='C2', ms=4, label=once('decoder, odd / even halves'))
        if k in D:
            ax[0].errorbar(i + .12, D[k]['L'] * 1e3 - (offset if np.isfinite(offset) else 0), yerr=min(D[k]['se'] * 1e3, 500), fmt='s', ms=4,
                           capsize=2, mfc='none', color='C3' if dnn_strong[k] else '0.75', label=once(f'DNN - offset ({offset:+.0f} ms) +-SE; grey = weak'))
        if label(k) in OLD.get(sub, {}):
            ax[0].plot(i - .2, OLD[sub][label(k)], 'd', color='C1', ms=4, label=once('crossdec 2026-11-22'))
        ax[0].plot(i, prop[k], '_', color='k', ms=14, mew=2, label=once('proposed'))
    ax[0].axhline(med, color='C0', ls='--', lw=1, label=f'listener median {med:.0f} ms')
    ax[0].axhline(500, color='k', lw=.5, label='constant 500 ms (earlier proposal)')
    ax[0].set_xticks(range(len(keys)), [label(k) for k in keys], rotation=90, fontsize=8)
    ax[0].set_ylim(0, 4100); ax[0].set_ylabel('sound latency after trigger t0 (ms)'); ax[0].legend(fontsize=7, ncol=2)
    ax[0].set_title(f'sub-{sub}: per-chapter latency (decoder strong {res["n_decoder_strong"]}, DNN strong {res["n_dnn_strong"]}, fallback {res["n_fallback"]})')
    ks = list(per)
    ax[1].errorbar(range(len(ks)), [per[k][0] for k in ks], yerr=[per[k][1] for k in ks], fmt='o', ms=4, capsize=2)
    if 'drift_pooled_ppm' in res:
        ax[1].axhline(res['drift_pooled_ppm'], color='C3', label=f"pooled joint_fit {res['drift_pooled_ppm']:+.0f} +- {res['drift_pooled_se']:.0f}")
    if 'drift_theilsen_ppm' in res:
        ax[1].axhspan(*res['drift_theilsen_ci95'], color='C2', alpha=.2,
                      label=f"pooled Theil-Sen {res['drift_theilsen_ppm']:+.0f} [{res['drift_theilsen_ci95'][0]:+.0f}, {res['drift_theilsen_ci95'][1]:+.0f}]")
    ax[1].axhline(0, color='k', lw=.5); ax[1].set_ylim(-160, 160)
    ax[1].set_xticks(range(len(ks)), [label(k) for k in ks], rotation=90, fontsize=7)
    ax[1].set_ylabel('drift (ppm, + = sound later at chapter end)'); ax[1].legend(fontsize=7); ax[1].set_title('drift per strong chapter (decoder)')
    for k in keys:
        if k in D and dnn_strong[k]:
            ax[2].plot(D[k]['lat'] * 1e3, D[k]['c'], lw=.6, color='C3' if dec_strong[k] else 'C4', alpha=.6)
    ax[2].set_xlabel('latency after t0 (ms)'); ax[2].set_ylabel('DNN score - median (smoothed)')
    ax[2].set_title('DNN curves of DNN-strong chapters (red: decoder also strong)')
    fig.savefig(f'{A}/summary/sub-{sub}_timing.png', dpi=85); plt.close(fig)
