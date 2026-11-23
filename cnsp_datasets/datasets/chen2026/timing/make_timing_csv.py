"""Build the repo's chen2026/timing.csv from timing_table_v2.csv (+ halves from align/z2/reclass.csv, the accepted
extended-search estimate from align/z2/ext_results.csv, trigger-fit details from t0_table.csv).
usage: make_timing_csv.py [out.csv]   (default: ../timing.csv)"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 0)
import csv, sys
C = settings.WORK
T = list(csv.DictReader(open(f'{C}/timing_table_v2.csv')))
RC = {(d['sub'], d['chapter']): d for d in csv.DictReader(open(f'{C}/align/z2/reclass.csv'))}
EX = {(d['sub'], d['chapter']): d for d in csv.DictReader(open(f'{C}/align/z2/ext_results.csv')) if d['accepted'] == 'True'}
T0 = {(d['sub'], d['story'], d['chapter']): d for d in csv.DictReader(open(f'{C}/t0_table.csv'))}
import numpy as np
# one listener median per listener, exactly as used in latency_s for the fallback chapters (no double rounding)
MED = {t['sub']: t['latency_s'] for t in T if t['rule'] == 'listener median'}
# per-listener spread of the per-chapter latencies about the median (robust SD), used as jitter for median trials
RSD = {s: round(float(1.4826 * np.median([abs(float(t['latency_s']) - float(MED[s])) for t in T
                                           if t['sub'] == s and t['rule'] != 'listener median'])) * 1e3, 1) for s in MED}
out = []
for t in T:
    ch = ('GD' if t['story'] == 'garnettdream' else 'LP') + t['chapter']
    rc, ex, t0 = RC[(t['sub'], ch)], EX.get((t['sub'], ch)), T0[(t['sub'], t['story'], t['chapter'])]
    dec = t['rule'].startswith('decoder')
    out.append(dict(
        sub=t['sub'], story=t['story'], chapter=int(t['chapter']), file=t['file'], t0_s=t['t0_s'],
        trig_n_events=t0['n_events'], trig_rows_found=t0['rows_found'], trig_res_sd_ms=t0['res_sd_ms'], wav_s=t['wav_s'],
        latency_s=t['latency_s'], latency_optionB_s=t['latency_optionB_s'] if t['latency_optionB_s'] == t['latency_s'] else MED[t['sub']],
        listener_median_s=MED[t['sub']], listener_latency_rsd_ms=RSD[t['sub']], rule=t['rule'],
        optionB_per_chapter=(t['rule'] != 'listener median' and t['latency_optionB_s'] == t['latency_s']
                             and t['latency_s'] != MED[t['sub']]),
        rule_z=rc['z'] if dec else (ex['z'] if ex else ''), latency_se_ms=t['latency_se_ms'],
        halves_A_ms=rc['LA_ms'] if dec else '', halves_B_ms=rc['LB_ms'] if dec else '',
        halves_agree=(rc['halves_ok'] == 'True') if dec else '', peak_ratio=rc['peak_ratio'] if dec else (ex['peak_ratio'] if ex else ''),
        decoder_latency_ms=rc['L_ms'], decoder_z=rc['z'], decoder_se_ms=rc['se_ms']))
with open(sys.argv[1] if len(sys.argv) > 1 else settings.TIMING_CSV, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(len(out), 'rows')
