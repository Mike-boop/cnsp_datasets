"""chen2026: compare onset timing rules (user's z >= 2 per-chapter rule, option B, listener median, constant 0.5 s,
trigger only) per listener and over the dataset. Analysis only; nothing is applied.

usage: timing_compare.py <chen2026 review dir> <out dir>
1. passes.png: per listener and chapter, decoder z (0-4 s scan) and, for chapters failing the rule, the best z of the
   extended search (-1..+8 s; decoder and DNN), coloured by the rule finally used.
2. heldout.csv / heldout.png: held-out halves test. For every chapter the decoder (trained on the listener's other
   chapters) gives r vs shift curves for the odd (A) and even (B) 30-s blocks. Each rule picks a latency from one
   half (per-chapter values: that half's peak; median rules: the listener median) and is scored by the r of the other
   half at that latency (both directions averaged). Chapters on DNN timing use the DNN latency (an independent
   estimator, no decoder-half information). Leakage: the rule's per-chapter/median decision uses the full chapter.
3. trf.png / trf.npz: forward TRFs (envelope -> 129 ch, 1-8 Hz, 50 Hz, lags -0.5..+0.8 s, ridge alpha 1 x mean
   eigenvalue) per listener under each timing; butterfly + GFP, and the dataset mean GFP.
"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

root, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
tab = pd.read_csv(os.path.join(root, "timing_table_v2.csv"), dtype={"sub": str})
rec = pd.read_csv(os.path.join(root, "align/z2/reclass.csv"), dtype={"sub": str})
ext = pd.read_csv(os.path.join(root, "align/z2/ext_results.csv"), dtype={"sub": str})
tab["key"] = tab["story"] + "_ch" + tab["chapter"].astype(int).map("{:02d}".format)
tab = tab.merge(rec[["sub", "key", "chapter", "LA_ms", "LB_ms", "halves_ok"]].rename(columns={"chapter": "label"}),
                on=["sub", "key"], how="left")
subs = sorted(tab["sub"].unique())
PERCH = lambda rule: not str(rule).startswith("listener median")
RULES = ["your rule (z>=2)", "option B", "listener median", "constant 0.5 s", "trigger only (t0)"]
COL = {"decoder z>=5": "C0", "decoder z>=2": "C2", "rescan decoder z>=2": "C4", "dnn z>=2": "C3",
       "listener median": "0.6"}

# ---- 1. passes overview
fig, axs = plt.subplots(4, 2, figsize=(18, 14))
for ax, s in zip(axs.ravel(), subs):
    t = tab[tab["sub"] == s].reset_index(drop=True)
    for i, r in t.iterrows():
        c = next((v for k, v in COL.items() if str(r["rule"]).startswith(k)), "k")
        ax.plot(i, max(r["decoder_z"], 0.3), "o", color=c, ms=6)
        e = ext[(ext["sub"] == s) & (ext["chapter"] == r["label"])]
        if len(e):
            zb = e["z"].max()
            ax.plot(i, max(zb, 0.3), "^", mfc="none", mec="k" if e["accepted"].any() else "0.5", ms=7)
    ax.axhline(2, color="C1", ls="--", lw=1)
    ax.axhline(5, color="0.7", ls=":", lw=1)
    ax.set_yscale("log")
    ax.set_xticks(range(len(t)), t["label"], rotation=90, fontsize=7)
    n = t["rule"].map(lambda x: str(x).split(" (")[0]).value_counts().to_dict()
    ax.set_title(f"sub-{s}: " + ", ".join(f"{k} {v}" for k, v in n.items()), fontsize=9)
    ax.set_ylabel("decoder z (log)")
hs = [plt.Line2D([], [], marker="o", ls="", color=v, label=k) for k, v in COL.items()]
hs += [plt.Line2D([], [], marker="^", ls="", mfc="none", mec="k", label="extended search best z (black: accepted)")]
fig.legend(handles=hs, loc="upper center", ncol=6, fontsize=9)
fig.suptitle("chen2026: which chapters pass (z >= 2, dashed); colour = rule used for the onset", y=0.995)
fig.tight_layout(rect=(0, 0, 1, 0.97))
fig.savefig(os.path.join(out, "passes.png"), dpi=90)

# ---- 2. held-out halves
rows = []
for s in subs:
    z = np.load(os.path.join(root, f"align/decoder/sub-{s}.npz"), allow_pickle=True)
    sh = z["shifts"] * (1000 if z["shifts"].max() < 100 else 1)  # ms
    t = tab[tab["sub"] == s]
    med = t["listener_median_ms"].iloc[0]
    for _, r in t.iterrows():
        k = r["key"]
        if f"cA_{k}" not in z.files:
            continue
        cA, cB = z[f"cA_{k}"], z[f"cB_{k}"]
        at = lambda c, ms: float(np.interp(ms, sh, c))
        ob_per = abs(r["latency_optionB_s"] * 1000 - med) > 1.0
        perch, dnn = PERCH(r["rule"]), str(r["rule"]).startswith("dnn")
        res = {}
        for name, la, lb in (("your rule (z>=2)",
                              r["latency_s"] * 1000 if dnn else (r["LA_ms"] if perch else med),
                              r["latency_s"] * 1000 if dnn else (r["LB_ms"] if perch else med)),
                             ("option B", r["LA_ms"] if ob_per else med, r["LB_ms"] if ob_per else med),
                             ("listener median", med, med), ("constant 0.5 s", 500, 500),
                             ("trigger only (t0)", 0, 0)):
            res[name] = 0.5 * (at(cB, la) + at(cA, lb))  # latency from A scored on B, and vice versa
        rows.append(dict(sub=s, chapter=r["label"], rule=r["rule"], **res))
H = pd.DataFrame(rows)
H.to_csv(os.path.join(out, "heldout.csv"), index=False)
per = H.groupby("sub")[RULES].mean()
per.loc["all"] = H[RULES].mean()
print(per.round(4).to_string())
win = {k: int((H["your rule (z>=2)"] > H[k] + 1e-9).sum()) for k in RULES[1:]}
loss = {k: int((H["your rule (z>=2)"] < H[k] - 1e-9).sum()) for k in RULES[1:]}
print("chapters where your rule beats / loses to:", {k: (win[k], loss[k]) for k in win})
fig, ax = plt.subplots(1, 2, figsize=(16, 5))
x = np.arange(len(per))
for j, k in enumerate(RULES):
    ax[0].bar(x + (j - 2) * 0.16, per[k], 0.16, label=k)
ax[0].set_xticks(x, [f"sub-{i}" if i != "all" else "all" for i in per.index])
ax[0].set_ylabel("held-out r (decoder, other half)")
ax[0].legend(fontsize=8)
ax[0].set_title("held-out halves test per listener and over the dataset")
d = per.drop(columns=[RULES[0]]).rsub(per[RULES[0]], axis=0)
for j, k in enumerate(d.columns):
    ax[1].bar(x + (j - 1.5) * 0.2, d[k], 0.2, label=f"your rule - {k}")
ax[1].axhline(0, color="k", lw=0.6)
ax[1].set_xticks(x, [f"sub-{i}" if i != "all" else "all" for i in per.index])
ax[1].set_ylabel("difference in held-out r")
ax[1].legend(fontsize=8)
ax[1].set_title("your rule minus each alternative (> 0: your rule better)")
fig.tight_layout()
fig.savefig(os.path.join(out, "heldout.png"), dpi=100)

# ---- 3. forward TRFs per timing
FS = 50
LAGS = np.arange(round(-0.5 * FS), round(0.8 * FS) + 1)
lags_s = LAGS / FS
TIM = {"trigger only (t0)": lambda r: 0.0, "constant 0.5 s": lambda r: 0.5,
       "listener median": lambda r: r["listener_median_ms"] / 1000, "your rule (z>=2)": lambda r: r["latency_s"]}
W = {}
for s in subs:
    t = tab[tab["sub"] == s]
    acc = {k: [0, 0] for k in TIM}
    for _, r in t.iterrows():
        f = os.path.join(root, f"align/cache/sub-{s}_{r['key']}.npz")
        if not os.path.exists(f):
            continue
        c = np.load(f)
        eeg, env = c["eeg50"].T.astype(float), c["env50"].astype(float)
        eeg = (eeg - eeg.mean(0)) / eeg.std(0)
        env = (env - env.mean()) / env.std()
        for k, fn in TIM.items():
            i0 = int(round((float(c["t0"]) + fn(r) - float(c["te50"])) * FS))
            n = min(len(env), len(eeg) - i0)
            Y, e = eeg[i0:i0 + n], env[:n]
            X = np.zeros((n, len(LAGS)))
            for j, lag in enumerate(LAGS):
                if lag >= 0:
                    X[lag:, j] = e[:n - lag]
                else:
                    X[:lag, j] = e[-lag:]
            acc[k][0] = acc[k][0] + X.T @ X
            acc[k][1] = acc[k][1] + X.T @ Y
    W[s] = {}
    for k, (xx, xy) in acc.items():
        reg = xx + np.trace(xx) / len(LAGS) * np.eye(len(LAGS))
        W[s][k] = np.linalg.solve(reg, xy)
    print("TRF", s, flush=True)
np.savez(os.path.join(out, "trf.npz"), lags_s=lags_s, **{f"{s}|{k}": W[s][k] for s in W for k in W[s]})
fig, axs = plt.subplots(len(subs) + 1, len(TIM), figsize=(18, 2.3 * (len(subs) + 1)), sharex=True)
for i, s in enumerate(subs):
    for j, k in enumerate(TIM):
        w = W[s][k]
        g = np.sqrt((w ** 2).mean(1))
        axs[i, j].plot(lags_s, w, lw=0.3, alpha=0.5)
        axs[i, j].plot(lags_s, g, "k", lw=1.5)
        axs[i, j].axvline(0, color="r", lw=0.6)
        if i == 0:
            axs[i, j].set_title(k, fontsize=10)
        if j == 0:
            axs[i, j].set_ylabel(f"sub-{s}")
for j, k in enumerate(TIM):
    G = np.array([np.sqrt((W[s][k] ** 2).mean(1)) for s in subs])
    G = G / G.max(1, keepdims=True)
    axs[-1, j].plot(lags_s, G.T, lw=0.6, alpha=0.6)
    axs[-1, j].plot(lags_s, G.mean(0), "k", lw=2)
    axs[-1, j].axvline(0, color="r", lw=0.6)
    pk = lags_s[np.argmax(G.mean(0))]
    axs[-1, j].set_title(f"dataset: mean normalised GFP, peak {pk * 1000:+.0f} ms, max {G.mean(0).max():.2f}",
                         fontsize=9)
    axs[-1, j].set_xlabel("lag (s; > 0: EEG after the sound as placed)")
axs[-1, 0].set_ylabel("all (GFP / max)")
fig.suptitle("chen2026: forward 1-8 Hz envelope TRFs (129 ch) per listener under each onset timing; black = GFP",
             y=0.995)
fig.tight_layout(rect=(0, 0, 1, 0.985))
fig.savefig(os.path.join(out, "trf.png"), dpi=80)
print("done")
