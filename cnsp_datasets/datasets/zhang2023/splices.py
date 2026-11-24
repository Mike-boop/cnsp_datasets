"""
Splice maps of the zhang2023 trials and the unspliced 115 s sources, rebuilt from the shipped per-trial wavs.

The authors cut artefact segments out of each trial's EEG and both wavs together, on one grid: in trial and source
coordinates alike, block 0 is audio samples [0, 61) and block b >= 1 is [61 + 125 (b - 1), 61 + 125 b); EEG sample
j goes with trial block j + 1 (125 audio samples per EEG sample at 16 kHz / 128 Hz). The wavs are bit-exact 16-bit
copies of the sources, so every block is hashed (as integers) and the sources are rebuilt by chaining blocks with
successor votes across all occurrences of a source; zero or near-silent blocks repeat and are wildcards that take
the position of their run. A trial's EEG sample is mapped to a source position only where the rebuilds of its two
streams (cut together) agree.

Outputs (`write_maps`): pieces.csv (subject, trial, eeg_start, n, source_start: trial EEG samples
[eeg_start, eeg_start + n) go with source EEG-rate positions [source_start, source_start + n)) and
source_cover.csv (source, source_start, n, subject, trial, side, eeg_start: which shipped wav supplies each stretch).
"""
from __future__ import annotations

import collections
import contextlib
import csv
import glob
import os

import h5py
import numpy as np

from cnsp_datasets.datasets.zhang2023.expinfo import read_expinfo

FS_AUDIO, FS_EEG, BLOCK, PHASE = 16000, 128, 125, 61
SOURCE_LEN = 1840000  # 115 s
SILENT = 16  # blocks with max |sample| < SILENT / 32768 are wildcards
HERE = os.path.dirname(os.path.abspath(__file__))
SIDES = {"l": ("leftWav", "l_audio"), "r": ("rightWav", "r_audio")}


def mat_files(root: str) -> list[str]:
    return sorted(glob.glob(os.path.join(root, "NJUNCA_preprocessed_arte_removed", "S*.mat")))


def trial_lengths(f: h5py.File) -> list[int]:
    """EEG samples per trial (0 for the empty trials, e.g. S18 trials 9 and 22)."""
    cells = (f[r] for r in np.asarray(f["data/eeg"]).ravel())
    return [c.shape[1] if c.ndim == 2 else 0 for c in cells]


def read_wav(f: h5py.File, trial: int, side: str) -> np.ndarray:
    """Shipped wav of trial (0-based) and side 'l'/'r' as float64."""
    return np.asarray(f[f["data"][SIDES[side][0]][trial, 0]]).ravel()


def _hashes(w: np.ndarray, salt: np.ndarray) -> np.ndarray:
    """Hash per block b >= 1 (index b - 1); 0 for silent blocks."""
    n = (len(w) - PHASE) // BLOCK
    q = np.round(w[PHASE:PHASE + BLOCK * n].reshape(n, BLOCK) * 32768).astype(np.int64)
    u = q.view(np.uint64)
    h = (u * salt).sum(1) ^ ((u + np.uint64(7)) * salt[::-1]).sum(1)
    h[np.abs(q).max(1) < SILENT] = 0
    return h


def _chain(seqs: list[np.ndarray]) -> dict[int, int]:
    """Source block position of each hash from occurrence hash sequences (mutual-best successor votes)."""
    edges = collections.defaultdict(collections.Counter)
    first = collections.Counter()
    for h in seqs:
        nz = np.flatnonzero(h)
        if len(nz) and nz[0] == 0:
            first[h[0]] += 1
        for a, b in zip(nz[:-1], nz[1:]):
            edges[h[a]][(h[b], b - a - 1)] += 1
    pred = collections.defaultdict(collections.Counter)
    for a, c in edges.items():
        for (b, gap), k in c.items():
            pred[b][a] += k
    if not first:  # no occurrence starts with an audible block 1
        return {}
    a = first.most_common(1)[0][0]
    pos = {a: 1}
    while a in edges:
        b, gap = edges[a].most_common(1)[0][0]
        if pred[b].most_common(1)[0][0] != a or b in pos:
            break
        pos[b] = pos[a] + gap + 1
        a = b
    return pos


def _block_positions(h: np.ndarray, pos: dict[int, int]) -> np.ndarray:
    """Source block of each trial block b >= 1 (index b - 1), -1 if unknown; silent blocks inherit their run's shift."""
    out = np.full(len(h), -1)
    shift = None
    for i, x in enumerate(h):
        if x and x in pos:
            shift = pos[x] - (i + 1)
        elif x:
            shift = None
        if shift is not None:
            out[i] = i + 1 + shift
    return out


def rebuild(root: str) -> tuple[list[dict], list[dict]]:
    """Pieces and source cover rows (see module docstring) from the shipped files under root."""
    salt = np.random.default_rng(0).integers(1, 2 ** 63, BLOCK, dtype=np.uint64) | np.uint64(1)
    with contextlib.ExitStack() as stack:
        files = {os.path.basename(p)[:-4]: stack.enter_context(h5py.File(p, "r")) for p in mat_files(root)}
        return _rebuild(files, salt)


def _rebuild(files: dict[str, h5py.File], salt: np.ndarray) -> tuple[list[dict], list[dict]]:
    occ, lengths = collections.defaultdict(list), {}
    for s, f in files.items():
        info = read_expinfo(f)
        for t, n in enumerate(trial_lengths(f)):
            lengths[(s, t)] = n
            if n:
                for side, (_, col) in SIDES.items():
                    occ[info[col][t]].append((s, t, side))
    blockpos = {}
    for name, items in sorted(occ.items()):
        seqs = {o: _hashes(read_wav(files[o[0]], o[1], o[2]), salt) for o in items}
        pos = _chain(list(seqs.values()))
        blockpos.update({o: _block_positions(h, pos) for o, h in seqs.items()})
    pieces, cover = [], []
    sources = {o: n for n, items in occ.items() for o in items}
    covered = collections.defaultdict(lambda: np.zeros(SOURCE_LEN // BLOCK + 1, bool))
    for s, t in sorted({o[:2] for o in blockpos}):
        n_eeg = lengths[(s, t)]
        a, b = blockpos[(s, t, "l")], blockpos[(s, t, "r")]
        k = min(len(a), len(b), n_eeg)
        m = np.where((a[:k] >= 0) & (a[:k] == b[:k]), a[:k] - 1, -1)  # source EEG-rate position per EEG sample
        if k == n_eeg - 1:  # the last EEG sample goes with a partial block that has no hash: continue its piece
            m, k = np.r_[m, m[-1] + 1 if m[-1] >= 0 else -1], n_eeg
        brk = np.flatnonzero((np.diff(m) != 1) | (m[1:] < 0) | (m[:-1] < 0)) + 1
        for j0, j1 in zip(np.r_[0, brk], np.r_[brk, k]):
            if m[j0] < 0:
                continue
            row = dict(subject=s, trial=t + 1, eeg_start=int(j0), n=int(j1 - j0), source_start=int(m[j0]))
            pieces.append(row)
            for side in SIDES:
                name = sources[(s, t, side)].removesuffix(".wav")
                new = ~covered[name][m[j0]:m[j0] + (j1 - j0)]
                if new.any():
                    covered[name][m[j0]:m[j0] + (j1 - j0)] = True
                    cover.append(dict(source=name, source_start=row["source_start"], n=row["n"], subject=s,
                                      trial=t + 1, side=side, eeg_start=row["eeg_start"]))
    return pieces, cover


def write_maps(root: str, out_dir: str = HERE) -> None:
    pieces, cover = rebuild(root)
    for name, rows in (("pieces.csv", pieces), ("source_cover.csv", cover)):
        with open(os.path.join(out_dir, name), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def read_csv(name: str, text: tuple[str, ...] = ("subject", "source", "side")) -> list[dict]:
    """Rows of a CSV in this folder; columns not in `text` as int."""
    with open(os.path.join(HERE, name), newline="") as fh:
        return [{k: (v if k in text else int(v)) for k, v in r.items()} for r in csv.DictReader(fh)]


def _span(start: int, n: int) -> slice:
    """Audio samples of EEG-rate positions [start, start + n) (blocks start + 1 .. start + n)."""
    return slice(PHASE + BLOCK * start, PHASE + BLOCK * (start + n))


def source_audio(root: str, name: str, cover: list[dict]) -> np.ndarray:
    """Rebuilt 115 s source (float32; zeros where no agreed piece covers it)."""
    out = np.zeros(SOURCE_LEN, np.float32)
    rows = [r for r in cover if r["source"] == name]
    for s in sorted({r["subject"] for r in rows}):
        with h5py.File(os.path.join(root, "NJUNCA_preprocessed_arte_removed", f"{s}.mat"), "r") as f:
            for r in (r for r in rows if r["subject"] == s):
                w = read_wav(f, r["trial"] - 1, r["side"])
                if r["eeg_start"] == 0 and r["source_start"] == 0:
                    out[:PHASE] = w[:PHASE]  # block 0
                w = w[_span(r["eeg_start"], r["n"])]
                dst = _span(r["source_start"], r["n"])
                out[dst.start:dst.start + len(w)] = w[:SOURCE_LEN - dst.start]
    return out


def realigned(source: np.ndarray, pieces: list[dict], n_eeg: int, lag: int) -> np.ndarray:
    """
    Trial stimulus at 16 kHz built from the source: each piece's EEG samples get the source audio at their mapped
    position + lag (EEG samples); zeros where unmapped or outside the source. lag 0 reproduces the shipped wav on
    the mapped samples (block 0 / the first 61 samples follow the first piece).
    """
    out = np.zeros(BLOCK * n_eeg, np.float32)
    for p in pieces:
        dst = _span(p["eeg_start"], p["n"])
        src = _span(p["source_start"] + lag, p["n"])
        if p["eeg_start"] == 0:
            dst, src = slice(0, dst.stop), slice(src.start - PHASE, src.stop)
        lo = max(0, -src.start)
        hi = min(src.stop, len(source)) - src.start
        hi = min(hi, len(out) - dst.start)
        if hi > lo:
            out[dst.start + lo:dst.start + hi] = source[src.start + lo:src.start + hi]
    return out
