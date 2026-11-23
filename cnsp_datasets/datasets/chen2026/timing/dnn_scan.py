"""Unanchored DNN lag scan per chapter (align/scan.py:lag_scores, fs128_1020-64 broadband classifier).
EEG from floor(t0 * 128) (cache eeg128), envelope from audio sample 0 (env128), both z-scored; lags -4.0..+0.5 s
(lag_scores convention: lag -L means the sound sits L s after EEG sample 0), 5 s windows, 1 s hop. Also NNULL
mismatched-stimulus nulls: the same EEG against other chapters' envelopes (mean curves, n_lags x NNULL).
Saves per-window scores. usage: dnn_scan.py <sub> ...   (cache -> align/scans/)"""
import os, sys  # noqa: E401
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
settings.usage(__doc__, 1)
import glob, os, sys
import numpy as np
import torch
from scipy.stats import zscore
from cnsp_datasets.align.scan import lag_scores
from cnsp_datasets.align.specs import load_classifier
torch.set_num_threads(4)
C = settings.ALIGN
MODEL = settings.MODEL
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
model, spec, _ = load_classifier(MODEL, dev)
FS, SEG, HOP = 128, 640, 128
LAGS = np.arange(-round(4.0 * FS), round(0.5 * FS) + 1)
NNULL = 5
os.makedirs(f'{C}/scans', exist_ok=True)
for sub in sys.argv[1:]:
    files = sorted(glob.glob(f'{C}/cache/sub-{sub}_*.npz'))
    for i, f in enumerate(files):
        out = f'{C}/scans/{os.path.basename(f)}'
        if os.path.exists(out):
            continue
        d = np.load(f)
        eeg, env = d['eeg128'], d['env128'].mean(0, keepdims=True)
        n = min(eeg.shape[1], env.shape[1] + LAGS.max() + SEG)  # EEG beyond the sound is not needed
        eeg = zscore(eeg[:, :n], axis=-1).astype(np.float32)
        env_z = zscore(env, axis=-1).astype(np.float32)
        pad = np.zeros((1, max(0, n - env.shape[1])), np.float32)
        stim = np.concatenate([env_z, pad], 1)[:, :n]
        # windows must lie inside the sound: restrict EEG to the sound span plus the lag range
        m = min(n, env.shape[1] - LAGS.min())
        scores, starts = lag_scores(model, eeg[:, :m], stim[:, :m], LAGS, SEG, HOP, device=dev)
        # nulls: NNULL other chapters' envelopes (wrap-around) over the same EEG; mean curves only
        null = []
        for j in range(1, NNULL + 1):
            g = np.load(files[(i + j) % len(files)])['env128'].mean(0, keepdims=True)
            g = zscore(np.resize(g, (1, m)), axis=-1).astype(np.float32)
            null.append(lag_scores(model, eeg[:, :m], g, LAGS, SEG, HOP, device=dev)[0].mean(1))
        null = np.stack(null, 1)
        np.savez(out, scores=scores.astype(np.float32), null=null.astype(np.float32), starts=starts, lags=LAGS,
                 t0=d['t0'], te128=d['te128'], wav_s=d['wav_s'], bads=d['bads'])
        c = scores.mean(1)
        print(f'{os.path.basename(f)}: peak lag {LAGS[c.argmax()] / FS:+.3f} s, mean-curve max {c.max():.3f} '
              f'(null max {null.max():.3f}), {len(starts)} windows', flush=True)
