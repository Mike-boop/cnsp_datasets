"""Timing proposal v2 (user, 2026-11-23: z >= 2 threshold, extended search for the rest). Nothing is applied.

Rule per chapter (first that applies):
 1. 'decoder z>=5'    decoder (0-4 s scan) z >= 5, SE <= 25 ms (as v1)
 2. 'decoder z>=2'    decoder z >= 2, SE <= 25 ms, peak not at the scan edge, not inconsistent
 3. extended search (-1..+8 s, ext_scan.py), decoder first, then DNN (DNN - listener offset):
      decoder: z >= 2, SE <= 25 ms; DNN: z >= 2, SE <= 40 ms; peak not within 20 ms of the -1/+8 s edges,
      latency >= 0 (sound cannot precede the playback request), and consistent (not > 3 robust SD from the
      listener median with a peak ratio >= 0.75). Label 'extended-range decoder' / 'extended-range dnn' when the peak
      lies outside the original window (decoder 0-4 s, DNN -0.5-4 s), else 'rescan decoder z>=2' / 'dnn z>=2'.
 4. 'listener median' (median of the rule-1/2 latencies of the listener).
Option B (v2): listener median unless the chapter deviates by > max(40 ms, 3 SE).
Outputs: <WORK>/timing_table_v2.csv, timing_v2_overview.png, align/z2/sub-XX_ext_curves.png."""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 0)
import csv, json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
C = settings.WORK
A = f'{C}/align'
SUBS = ['01', '02', '03', '04', '05', '06', '07', '08']
RC = {(d['sub'], d['key']): d for d in csv.DictReader(open(f'{A}/z2/reclass.csv'))}
FAIL = {(d['sub'], d['key']): d['why'] for d in csv.DictReader(open(f'{A}/z2/fail_z2.csv'))}
OLD = {(r['sub'], r['story'], int(r['chapter'])): r for r in csv.DictReader(open(f'{C}/timing_table_proposal.csv'))}
# DNN offset (DNN - decoder): listener value if >= 3 chapters strong in both (v1 analysis), else pooled over listeners
pooled = []
OFF = {}
for s in SUBS:
    j = json.load(open(f'{A}/summary/sub-{s}.json'))
    for r in csv.DictReader(open(f'{A}/summary/sub-{s}_chapters.csv')):
        if r['source'] == 'decoder' and r['dnn_z'] != 'nan' and float(r['dnn_z']) >= 4 and float(r['dnn_se_ms']) <= 40:
            pooled.append(float(r['L_dnn_ms']) - float(r['L_dec_ms']))
    OFF[s] = j['dnn_minus_decoder_ms'] if j['n_both'] >= 3 else None
POOLED_OFF = float(np.median(pooled))
OFF = {s: (v if v is not None else POOLED_OFF) for s, v in OFF.items()}


def peak(c):
    i = int(np.argmax(c))
    if 0 < i < len(c) - 1:
        den = c[i - 1] - 2 * c[i] + c[i + 1]
        return i + (0.5 * (c[i - 1] - c[i + 1]) / den if den < 0 else 0.0)
    return float(i)


def ratio(lat, c):
    i = int(np.argmax(c))
    loc = [j for j in range(1, len(c) - 1) if c[j] >= c[j - 1] and c[j] >= c[j + 1] and abs(lat[j] - lat[i]) > 0.15]
    cc = c - np.median(c)
    return float(max(cc[j] for j in loc) / cc[i]) if loc and cc[i] > 0 else 0.0


def dnn_ext(e):
    lat = e['dnn_lat']; o = np.argsort(lat); lat = lat[o]
    S = gaussian_filter1d(e['dnn_scores'][o], 3, axis=0); c = S.mean(1)
    nl = gaussian_filter1d(e['dnn_null'][o], 3, axis=0)
    nprom = nl.max(0) - np.median(nl, 0)
    z = (c.max() - np.median(c) - nprom.mean()) / (nprom.std(ddof=1) + 1e-9)
    n = S.shape[1]; ch = np.minimum(np.arange(n) * 10 // n, 9)
    sums = np.stack([S[:, ch == q].sum(1) for q in range(10)])
    loo = np.array([lat[0] + peak(sums.sum(0) - sums[q]) / 128 for q in range(10)])
    se = np.sqrt(0.9 * ((loo - loo.mean()) ** 2).sum())
    return dict(L=lat[0] + peak(c) / 128, z=z, se=se, lat=lat, c=c - np.median(c), ratio=ratio(lat, c))


rows_out, ext_log = [], []
for s in SUBS:
    recs = [d for (ss, k), d in RC.items() if ss == s]
    passed = [d for d in recs if (s, d['key']) not in FAIL]
    med = float(np.median([float(d['L_ms']) for d in passed]))
    rsd = float(1.4826 * np.median([abs(float(d['L_ms']) - med) for d in passed]))
    fails = [d for d in recs if (s, d['key']) in FAIL]
    ncol = 6; nrow = max(1, int(np.ceil(len(fails) / ncol)))
    fig, axs = plt.subplots(nrow, ncol, figsize=(22, 3.2 * nrow), squeeze=False); axs = axs.ravel()
    for d in recs:
        k = d['key']; L, se, rule, extra = float(d['L_ms']), float(d['se_ms']), None, ''
        if (s, k) not in FAIL:
            rule = 'decoder z>=5' if d['old'] == 'True' else 'decoder z>=2'
        else:
            f = f'{A}/ext/sub-{s}_{k}.npz'
            ax = axs[fails.index(d)]
            if os.path.exists(f):
                e = np.load(f)
                dl, dc = e['dec_lat'], e['dec_curve']
                DE = dict(L=float(e['dec_L']), z=float(e['dec_z']), se=float(e['dec_se']), ratio=ratio(dl, dc))
                DN = dnn_ext(e); DN['L'] -= OFF[s] / 1e3
                cands = []
                for nm, X, semax, lo, win in (('decoder', DE, 0.025, -1.0, (0, 4)), ('dnn', DN, 0.040, -1.0, (-0.5, 4))):
                    ok_edge = lo + 0.02 < X['L'] + (OFF[s] / 1e3 if nm == 'dnn' else 0) < 8 - 0.02
                    far = abs(X['L'] * 1e3 - med) > 3 * rsd
                    ok = X['z'] >= 2 and X['se'] <= semax and ok_edge and X['L'] >= 0 and not (far and X['ratio'] >= 0.75)
                    why = [] if ok else [w for w, b in (('z<2', X['z'] < 2), (f'SE>{semax * 1e3:.0f}', X['se'] > semax), ('edge', not ok_edge),
                                                        ('negative', X['L'] < 0), ('inconsistent', far and X['ratio'] >= 0.75)) if b]
                    outside = not (win[0] <= X['L'] + (OFF[s] / 1e3 if nm == 'dnn' else 0) <= win[1])
                    cands.append((nm, X, ok, outside, why))
                    ext_log.append(dict(sub=s, chapter=d['chapter'], why_failed=FAIL[(s, k)], est=nm, L_ms=round(X['L'] * 1e3), z=round(X['z'], 1),
                                        se_ms=round(X['se'] * 1e3), peak_ratio=round(X['ratio'], 2), accepted=ok, outside_original=outside,
                                        reject=','.join(why)))
                acc = [c for c in cands if c[2]]
                if acc:
                    nm, X, _, outside, _ = acc[0]
                    L, se = X['L'] * 1e3, X['se'] * 1e3
                    rule = (f'extended-range {nm}' if outside else ('rescan decoder z>=2' if nm == 'decoder' else 'dnn z>=2'))
                ax.plot(dl * 1e3, dc / max(dc.max(), 1e-9), color='C0', lw=.8, label=f"decoder z {DE['z']:.1f} SE {DE['se'] * 1e3:.0f}")
                ax.plot((DN['lat'] - OFF[s] / 1e3) * 1e3, DN['c'] / max(DN['c'].max(), 1e-9), color='C3', lw=.6, alpha=.7,
                        label=f"DNN-off z {DN['z']:.1f} SE {DN['se'] * 1e3:.0f}")
                ax.axvspan(0, 4000, color='0.93', zorder=0)
                ax.axvline(med, color='k', ls='--', lw=1)
                if rule:
                    ax.axvline(L, color='g', lw=2, alpha=.6)
                ax.set_xlim(-1000, 8000); ax.legend(fontsize=6, loc='upper right')
            ax.set_title(f"{d['chapter']} ({FAIL[(s, k)]}) -> {rule or 'listener median'}", fontsize=8)
            if rule is None:
                rule, L, se = 'listener median', med, np.nan
        rows_out.append(dict(sub=s, key=k, chapter=d['chapter'], L=L, se=se, rule=rule, med=med))
    for ax in axs[len(fails):]:
        ax.axis('off')
    for ax in axs[:len(fails)]:
        ax.set_xlabel('latency after t0 (ms)', fontsize=7)
    fig.suptitle(f'sub-{s}: extended search (-1..+8 s) for chapters failing the z >= 2 rule; curves scaled to their max; '
                 f'grey = original 0-4 s window; dashed = listener median {med:.0f} ms; green = accepted peak', fontsize=10)
    fig.tight_layout(); fig.savefig(f'{A}/z2/sub-{s}_ext_curves.png', dpi=65); plt.close(fig)
# table: same columns as v1 + rule + old values
T = []
for r in rows_out:
    story = 'garnettdream' if r['chapter'].startswith('GD') else 'littleprince'
    o = OLD[(r['sub'], story, int(r['chapter'][2:]))]
    t0 = float(o['t0_s']); L = r['L'] / 1e3
    dev = r['rule'] != 'listener median' and abs(r['L'] - r['med']) > max(40, 3 * (r['se'] if np.isfinite(r['se']) else np.inf))
    LB = L if dev else r['med'] / 1e3
    row = {k: o[k] for k in o}
    row.update(latency_s=round(L, 4), onset_s=round(t0 + L, 4), source=r['rule'].split(' ')[0] if r['rule'] != 'listener median' else 'listener median',
               latency_optionB_s=round(LB, 4), onset_optionB_s=round(t0 + LB, 4), rule=r['rule'],
               latency_se_ms=round(r['se'], 1) if np.isfinite(r['se']) else '', listener_median_ms=round(r['med'], 1),
               v1_latency_s=o['latency_s'], v1_source=o['source'])
    T.append(row)
with open(f'{C}/timing_table_v2.csv', 'w') as f:
    w = csv.DictWriter(f, fieldnames=list(T[0])); w.writeheader(); w.writerows(T)
with open(f'{A}/z2/ext_results.csv', 'w') as f:
    w = csv.DictWriter(f, fieldnames=list(ext_log[0])); w.writeheader(); w.writerows(ext_log)
# overview: old vs new per chapter
fig, axs = plt.subplots(4, 2, figsize=(22, 16), layout='constrained'); axs = axs.ravel()
cols = {'decoder z>=5': 'C0', 'decoder z>=2': 'C1', 'rescan decoder z>=2': 'C4', 'dnn z>=2': 'C3',
        'extended-range decoder': 'C2', 'extended-range dnn': 'C6', 'listener median': '0.5'}
for ax, s in zip(axs, SUBS):
    rr = [t for t in T if t['sub'] == s]
    for i, t in enumerate(rr):
        ax.plot(i - .15, float(t['v1_latency_s']) * 1e3, 's', mfc='none', color='k', ms=5, label='v1 proposal' if i == 0 else None)
        se = float(t['latency_se_ms']) if t['latency_se_ms'] != '' else 0
        ax.errorbar(i + .15, float(t['latency_s']) * 1e3, yerr=min(se, 300), fmt='o', ms=5, capsize=2, color=cols[t['rule']])
    ax.axhline(float(rr[0]['listener_median_ms']), color='k', lw=.6, ls='--')
    ax.set_xticks(range(len(rr)), [('GD' if t['story'] == 'garnettdream' else 'LP') + t['chapter'] for t in rr], rotation=90, fontsize=7)
    ax.set_ylim(350, 1700); ax.set_ylabel('latency after t0 (ms)')
    cnt = {k: sum(t['rule'] == k for t in rr) for k in cols}
    ax.set_title(f'sub-{s}: ' + ', '.join(f'{k} {v}' for k, v in cnt.items() if v), fontsize=8)
for k, c in cols.items():
    axs[0].plot([], [], 'o', color=c, label=f'v2: {k}')
axs[0].legend(fontsize=7, ncol=2)
fig.suptitle('chen2026 timing proposal v2 (circles, +-SE, colour = rule) vs v1 (open squares); dashed = listener median (v2)')
fig.savefig(f'{C}/timing_v2_overview.png', dpi=75)
cnt = {}
for t in T:
    cnt.setdefault(t['sub'], {}).setdefault(t['rule'], 0); cnt[t['sub']][t['rule']] += 1
for s in SUBS:
    print(s, cnt[s])
print('total', {k: sum(t['rule'] == k for t in T) for k in cols})
print('DNN offsets', {s: round(v) for s, v in OFF.items()}, 'pooled', round(POOLED_OFF), 'n', len(pooled))
changed = [(t['sub'], t['story'][:2] + t['chapter'], t['v1_latency_s'], t['latency_s'], t['rule']) for t in T
           if abs(float(t['v1_latency_s']) - float(t['latency_s'])) > 0.1]
print('changed by > 100 ms vs v1:', changed)
