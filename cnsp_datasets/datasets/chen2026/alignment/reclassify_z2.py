"""Re-classify decoder latencies at z >= 2 (user request 2026-11-23) and check the passes for consistency.

Per chapter (decoder pass 2, held-out LOCO; align/decoder/sub-XX.{csv,npz}):
  z, SE (jackknife), L, odd/even-block halves LA/LB;
  peak ratio = second-highest local maximum of the r-vs-latency curve outside +-150 ms of the peak / the peak
  (clean single peak: ratio < 0.75);
  halves replicate: |LA - LB| <= 50 ms.
Rules compared: old (z >= 5 and SE <= 25 ms), z2 (z >= 2), z2se (z >= 2 and SE <= 25 ms).
Listener distribution over z2 passes: median and robust SD (1.4826 MAD); a pass is "inconsistent" if
|L - median| > 3 robust SD and its peak is not clean; "late, clean" if beyond 3 robust SD with a clean peak.
Writes align/z2/reclass.csv, align/z2/fail_z2.csv (chapters failing the full decoder rule, with the reason: input of
ext_scan.py and timing_v2.py), align/z2/sub-XX_passes.png.
usage: reclassify_z2.py"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 0)
import csv, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
A = settings.ALIGN
O = f'{A}/z2'; os.makedirs(O, exist_ok=True)
SUBS = ['01', '02', '03', '04', '05', '06', '07', '08']


def label(k):
    return ('GD' if k.startswith('garnett') else 'LP') + str(int(k[-2:]))


def peak_ratio(lat_ms, c):
    i = int(np.argmax(c))
    loc = [j for j in range(1, len(c) - 1) if c[j] >= c[j - 1] and c[j] >= c[j + 1] and abs(lat_ms[j] - lat_ms[i]) > 150]
    return float(max(c[j] for j in loc) / c[i]) if loc and c[i] > 0 else 0.0


out, summary = [], []
for sub in SUBS:
    rows = list(csv.DictReader(open(f'{A}/decoder/sub-{sub}.csv')))
    z = np.load(f'{A}/decoder/sub-{sub}.npz')
    recs = []
    for r in rows:
        k = r['key']; off = float(r['off_ms'])
        lat = z['shifts'] * 1e3 + off
        d = dict(sub=sub, key=k, chapter=label(k), L_ms=float(r['L_ms']), se_ms=float(r['se_ms']), z=float(r['z']),
                 edge=not 10 <= float(r['L_ms']) - off <= 3990,  # peak at the 0-4 s scan boundary
                 r=float(r['r']), LA_ms=float(r['LA_ms']), LB_ms=float(r['LB_ms']),
                 peak_ratio=round(peak_ratio(lat, z[f'curve_{k}']), 3))
        d['halves_ok'] = abs(d['LA_ms'] - d['LB_ms']) <= 50
        d['old'] = d['z'] >= 5 and d['se_ms'] <= 25
        d['z2'] = d['z'] >= 2
        d['z2se'] = d['z2'] and d['se_ms'] <= 25
        d['new'] = d['z2'] and not d['old']
        recs.append(d)
    P = np.array([d['L_ms'] for d in recs if d['z2']])
    med = float(np.median(P)); rsd = float(1.4826 * np.median(np.abs(P - med)))
    for d in recs:
        far = d['z2'] and abs(d['L_ms'] - med) > 3 * rsd
        d['clean'] = d['peak_ratio'] < 0.75
        d['flag'] = ('inconsistent' if far and not d['clean'] else 'late, clean' if far else '') if d['z2'] else ''
        d['median_ms'] = round(med, 1); d['robust_sd_ms'] = round(rsd, 1)
    out += recs
    n = lambda f: sum(f(d) for d in recs)
    summary.append(dict(sub=sub, n=len(recs), old=n(lambda d: d['old']), z2=n(lambda d: d['z2']), z2se=n(lambda d: d['z2se']),
                        new=n(lambda d: d['new']), new_halves_ok=n(lambda d: d['new'] and d['halves_ok']),
                        old_halves_ok=n(lambda d: d['old'] and d['halves_ok']),
                        z2_se_gt25=n(lambda d: d['z2'] and not d['z2se']),
                        z2_se_gt25_halves_ok=n(lambda d: d['z2'] and not d['z2se'] and d['halves_ok']),
                        inconsistent=n(lambda d: d['flag'] == 'inconsistent'), late_clean=n(lambda d: d['flag'] == 'late, clean'),
                        median=round(med), robust_sd=round(rsd, 1)))
    # figure: passing latencies with SE, chapter on x
    fig, ax = plt.subplots(figsize=(15, 5), layout='constrained')
    x = np.arange(len(recs))
    ax.axhspan(med - 3 * rsd, med + 3 * rsd, color='0.9', label=f'median {med:.0f} +- 3 robust SD ({rsd:.0f} ms)')
    ax.axhline(med, color='k', lw=1)
    lab = set()
    for i, d in enumerate(recs):
        if not d['z2']:
            ax.plot(i, med, 'x', color='0.6', label=None if 'f' in lab else 'fails z >= 2 (-> extended search)'); lab.add('f')
            continue
        col = 'C0' if d['old'] else 'C1'
        nm = 'admitted before (z >= 5, SE <= 25)' if d['old'] else 'newly admitted (2 <= z, or SE > 25)'
        ax.errorbar(i, d['L_ms'], yerr=min(d['se_ms'], 300), fmt='o', color=col, capsize=2, ms=5, label=None if nm in lab else nm); lab.add(nm)
        ax.plot([i + .25] * 2, [d['LA_ms'], d['LB_ms']], 'x', color='C2' if d['halves_ok'] else 'C3', ms=4,
                label=None if ('h' + str(d['halves_ok'])) in lab else ('odd/even halves (agree <= 50 ms)' if d['halves_ok'] else 'odd/even halves (disagree)'))
        lab.add('h' + str(d['halves_ok']))
        if d['flag']:
            ax.plot(i, d['L_ms'], 's', ms=12, mfc='none', color='r' if d['flag'] == 'inconsistent' else 'm',
                    label=None if d['flag'] in lab else ('inconsistent: > 3 robust SD, no clean peak' if d['flag'] == 'inconsistent' else '> 3 robust SD, clean single peak'))
            lab.add(d['flag'])
    hi = max([d['L_ms'] for d in recs if d['z2']] + [med + 200])
    ax.set_ylim(max(0, min([d['L_ms'] for d in recs if d['z2']] + [med]) - 100), min(hi + 100, 4100))
    ax.set_xticks(x, [d['chapter'] for d in recs], rotation=90, fontsize=8)
    ax.set_ylabel('sound latency after t0 (ms), decoder +- SE')
    ax.set_title(f'sub-{sub}: decoder passes at z >= 2 ({summary[-1]["z2"]} of {len(recs)}; before {summary[-1]["old"]})')
    ax.legend(fontsize=7, ncol=2)
    fig.savefig(f'{O}/sub-{sub}_passes.png', dpi=85); plt.close(fig)
keys = list(out[0])
with open(f'{O}/reclass.csv', 'w') as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
with open(f'{O}/fail_z2.csv', 'w') as f:
    # every chapter failing the full decoder rule (z >= 2, SE <= 25 ms, not at the edge, not inconsistent)
    w = csv.writer(f); w.writerow(['sub', 'key', 'chapter', 'median_ms', 'why'])
    for d in out:
        why = ('z<2' if not d['z2'] else 'SE>25' if not d['z2se'] else 'edge' if d['edge']
               else 'inconsistent' if d['flag'] == 'inconsistent' else '')
        if why:
            w.writerow([d['sub'], d['key'], d['chapter'], d['median_ms'], why])
for s in summary:
    print(s)
print('total', {k: sum(s[k] for s in summary) for k in summary[0] if k not in ('sub', 'median', 'robust_sd')})
for d in out:
    if d['flag'] or (d['new'] and not d['halves_ok']):
        print(f"sub-{d['sub']} {d['chapter']}: L {d['L_ms']:.0f} z {d['z']:.1f} SE {d['se_ms']:.0f} halves {d['LA_ms']:.0f}/{d['LB_ms']:.0f} "
              f"peak ratio {d['peak_ratio']:.2f} new {d['new']} flag '{d['flag']}' (median {d['median_ms']:.0f}, rSD {d['robust_sd_ms']:.0f})")
