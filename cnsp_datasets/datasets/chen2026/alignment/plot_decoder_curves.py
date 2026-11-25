"""Held-out (LOCO, pass 2) decoder r vs sound latency, one panel per chapter. usage: plot_decoder_curves.py <sub> ..."""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 1)
import csv, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
C = settings.ALIGN
for sub in sys.argv[1:]:
    z = np.load(f'{C}/decoder/sub-{sub}.npz'); rows = list(csv.DictReader(open(f'{C}/decoder/sub-{sub}.csv')))
    fig, axs = plt.subplots(6, 6, figsize=(22, 15), sharex=True); axs = axs.ravel()
    for ax, r in zip(axs, rows):
        k = r['key']; off = float(r['off_ms']) / 1e3
        strong = float(r['z']) >= 5 and float(r['se_ms']) <= 25
        ax.plot((z['shifts'] + off) * 1e3, z[f'curve_{k}'], lw=.8, color='C0' if strong else '0.5')
        ax.axvline(float(r['L_ms']), color='r', lw=.5)
        ax.set_title(f"{'GD' if k.startswith('garnett') else 'LP'}{int(k[-2:])} L {float(r['L_ms']):.0f} ms z {float(r['z']):.1f} SE {float(r['se_ms']):.0f}", fontsize=8)
    for ax in axs[len(rows):]:
        ax.axis('off')
    for ax in axs[-6:]:
        ax.set_xlabel('latency after t0 (ms)')
    fig.suptitle(f'sub-{sub}: held-out (LOCO) decoder r vs sound latency (grey = weak)'); fig.tight_layout()
    fig.savefig(f'{C}/summary/sub-{sub}_decoder_curves.png', dpi=60); plt.close(fig)
