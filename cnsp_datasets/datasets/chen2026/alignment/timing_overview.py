"""Cross-listener overview figure and the PROPOSED timing table (nothing applied).
onset_s = t0 (trigger fit, file clock) + L_proposed (decoder if strong, else DNN - listener offset if DNN strong, else
listener median; see analyse_timing.py).
usage: timing_overview.py -> align/summary/overview.png, <WORK>/timing_table_proposal.csv"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 0)
import csv, glob, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
C = settings.WORK
S = f'{C}/align/summary'
subs = sorted(f[-7:-5] for f in glob.glob(f'{S}/sub-??.json'))
J = {s: json.load(open(f'{S}/sub-{s}.json')) for s in subs}
CH = {s: list(csv.DictReader(open(f'{S}/sub-{s}_chapters.csv'))) for s in subs}
t0 = {(r['sub'], ('GD' if r['story'] == 'garnettdream' else 'LP') + r['chapter']): r for r in csv.DictReader(open(f'{C}/t0_table.csv'))}
out = []
for s in subs:
    for r in CH[s]:
        t = t0[(s, r['chapter'])]
        L = float(r['L_proposed_ms']) / 1e3
        out.append(dict(sub=s, story=t['story'], chapter=int(t['chapter']), file=t['file'], t0_s=float(t['t0']),
                        latency_s=round(L, 4), onset_s=round(float(t['t0']) + L, 4), source=r['source'],
                        latency_optionB_s=round(float(r['L_optionB_ms']) / 1e3, 4), onset_optionB_s=round(float(t['t0']) + float(r['L_optionB_ms']) / 1e3, 4),
                        latency_decoder_ms=r['L_dec_ms'], decoder_se_ms=r['dec_se_ms'], decoder_z=r['dec_z'],
                        latency_dnn_ms=r['L_dnn_ms'], dnn_se_ms=r['dnn_se_ms'], dnn_z=r['dnn_z'], wav_s=t['wav_s'],
                        trig_res_sd_ms=t['res_sd_ms']))
with open(f'{C}/timing_table_proposal.csv', 'w') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
fig, ax = plt.subplots(1, 3, figsize=(19, 5.5), layout='constrained')
for i, s in enumerate(subs):
    rr = CH[s]
    Ls = np.array([float(r['L_proposed_ms']) for r in rr]); st = np.array([r['source'] != 'listener median' for r in rr])
    gd = np.array([r['chapter'].startswith('GD') for r in rr])
    jit = (np.random.default_rng(i).random(len(rr)) - .5) * .5
    ax[0].scatter(i + jit[st & gd], Ls[st & gd], s=14, c='C0', label='GD, strong' if i == 0 else None)
    ax[0].scatter(i + jit[st & ~gd], Ls[st & ~gd], s=14, c='C1', label='LP, strong' if i == 0 else None)
    ax[0].scatter(i + jit[~st], np.clip(Ls[~st], 0, 1500), s=14, marker='x', c='0.5', label='fallback = median' if i == 0 else None)
    ax[0].plot([i - .3, i + .3], [J[s]['median_L_ms']] * 2, 'k', lw=2)
    if 'drift_pooled_ppm' not in J[s]:
        continue
    ax[1].errorbar(i - .1, J[s]['drift_pooled_ppm'], yerr=J[s]['drift_pooled_se'], fmt='o', c='C3', capsize=3,
                   label='pooled joint_fit (lag axis x10), +-SE' if i == 0 else None)
    lo, hi = J[s]['drift_theilsen_ci95']; d = J[s]['drift_theilsen_ppm']
    ax[1].errorbar(i + .1, d, yerr=[[d - lo], [hi - d]], fmt='s', c='C2', capsize=3, label='pooled Theil-Sen, 95% CI' if i == 0 else None)
    if 'heldout_r_own' not in J[s]:
        continue
    ax[2].bar(i - .25, J[s]['heldout_r_own'], .25, color='C0', label='latency from the other half' if i == 0 else None)
    ax[2].bar(i, J[s]['heldout_r_median'], .25, color='C1', label='listener median' if i == 0 else None)
    ax[2].bar(i + .25, J[s]['heldout_r_500'], .25, color='0.6', label='constant 500 ms' if i == 0 else None)
for a in ax:
    a.set_xticks(range(len(subs)), [f'sub-{s}' for s in subs])
ax[0].set_ylabel('sound latency after trigger t0 (ms)'); ax[0].set_title('proposed per-chapter latency (decoder / DNN); bar = listener median')
ax[0].legend(fontsize=8); ax[0].set_yscale('log'); ax[0].set_ylim(300, 4100)
ax[1].axhline(0, c='k', lw=.5); ax[1].set_ylabel('drift (ppm, + = sound later at chapter end)'); ax[1].legend(fontsize=8)
ax[1].set_title('drift pooled over strong chapters per listener')
ax[2].set_ylabel('held-out decoder r (other half of the chapter)'); ax[2].legend(fontsize=8)
ax[2].set_title('held-out validation (odd/even 30-s blocks)')
fig.savefig(f'{S}/overview.png', dpi=90)
for s in subs:
    j = J[s]
    print(f"sub-{s}: dec strong {j['n_decoder_strong']}, dnn {j['n_from_dnn']}, fallback {j['n_fallback']} of {j['n_chapters']}; S0 {j['S0']:.2f}; "
          f"median L {j['median_L_ms']:.0f} IQR {j['L_iqr_ms'][0]:.0f}-{j['L_iqr_ms'][1]:.0f} range {j['L_range_ms'][0]:.0f}-{j['L_range_ms'][1]:.0f}, "
          f"late>+200ms {j['n_late_gt_200ms']} | halves r_core {j.get('halves_r_core', np.nan):.2f} |A-B| {j.get('halves_absdiff_med_ms', np.nan):.0f} core SD {j.get('core_sd_ms', np.nan):.0f} | "
          f"drift jf {j.get('drift_pooled_ppm', np.nan):+.0f}+-{j.get('drift_pooled_se', np.nan):.0f} TS {j.get('drift_theilsen_ppm', np.nan):+.0f} {np.round(j.get('drift_theilsen_ci95', [np.nan] * 2)).tolist()} | "
          f"heldout own/med/500 {j.get('heldout_r_own', np.nan):.3f}/{j.get('heldout_r_median', np.nan):.3f}/{j.get('heldout_r_500', np.nan):.3f} | "
          f"DNN-dec {j['dnn_minus_decoder_ms']:+.0f} (MAD {j['dnn_minus_decoder_mad_ms']:.0f}, n {j['n_both']}, r {j['dnn_decoder_r']:.2f})")
