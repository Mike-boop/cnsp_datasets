"""
Reader for the MATLAB `table` / `string` objects in the zhang2023 .mat files (v7.3), which h5py exposes only as
the raw MCOS subsystem (`#subsystem#/MCOS`) and pymatreader cannot read.

MCOS layout used here: cell 0 of the FileWrapper is a uint8 metadata blob with a header (version, number of names,
8 region offsets), the property names, region 2 (property blocks of plain objects such as `string`), region 3 (one
6-uint32 record per object: class, 0, 0, region-2 block, region-4 block, dependency) and region 4 (property blocks
of objects with saved properties such as `table`). A property block is n, then n (name index, flag, value) triples,
padded to 8 bytes; the value is a FileWrapper cell index minus 2. A `string` array is a uint64 vector [version,
ndims, dims..., lengths..., UTF-16 code units packed 4 per uint64].
"""
from __future__ import annotations

import h5py
import numpy as np


def _strings(v) -> list[str]:
    v = np.asarray(v).ravel().astype(np.uint64)
    nd = int(v[1])
    n = int(np.prod(v[2:2 + nd]))
    lengths = v[2 + nd:2 + nd + n].astype(int)
    chars = v[2 + nd + n:].view(np.uint16)
    ends = np.cumsum(lengths)
    return [chars[e - n:e].tobytes().decode("utf-16-le") for e, n in zip(ends, lengths)]


def _blocks(seg: np.ndarray) -> list[dict[int, int]]:
    """Property blocks of a region; each region starts with an empty block 0 (n = 0 plus padding)."""
    out, i = [], 0
    while i < len(seg):
        n = int(seg[i])
        out.append({int(seg[i + 1 + 3 * k]): int(seg[i + 3 + 3 * k]) for k in range(n)})
        i += 1 + 3 * n
        i += i % 2
    return out


class _MCOS:
    def __init__(self, f: h5py.File):
        self.f = f
        self.cells = [f[r] for r in np.asarray(f["#subsystem#/MCOS"]).ravel()]
        b = np.asarray(self.cells[0]).ravel().astype(np.uint8).tobytes()
        u32 = lambda o: int.from_bytes(b[o:o + 4], "little")  # noqa: E731
        offs = [u32(8 + 4 * i) for i in range(8)]
        self.names = [x.decode() for x in b[40:offs[0]].split(b"\0")[:u32(4)]]
        region = lambda k: np.frombuffer(b[offs[k - 1]:offs[k]], dtype="<u4")  # noqa: E731
        self.plain, self.objects, self.saved = _blocks(region(2)), region(3).reshape(-1, 6), _blocks(region(4))

    def props(self, object_id: int) -> dict[str, h5py.Dataset]:
        o = self.objects[object_id]
        block = self.plain[o[3]] if o[3] else self.saved[o[4]]
        return {self.names[k - 1]: self.cells[v + 2] for k, v in block.items()}

    def leaf(self, x):
        a = np.asarray(x)
        if a.dtype == object:
            return [self.leaf(self.f[r]) for r in a.ravel()]
        return a.ravel().tolist()


def read_expinfo(f: h5py.File) -> dict[str, list]:
    """
    `expinfo` table of one subject file: attended_lr, l_audio, r_audio (lists of str) and azimuth (list of
    [l, r] or 5-point trajectories), one entry per table row (rows may outnumber the trials; extra rows are
    empty). An MCOS reference is uint32 [0xDD000000, 2, 1, 1, object id, class id].
    """
    m = _MCOS(f)
    table = m.props(int(np.asarray(f["expinfo"]).ravel()[4]))
    varnames = ["".join(map(chr, v)) for v in m.leaf(table["varnames"])]
    out = {}
    for name, ref in zip(varnames, np.asarray(table["data"]).ravel()):
        a = np.asarray(f[ref]).ravel()
        if a.dtype == np.uint32:
            out[name] = _strings(m.props(int(a[4]))["any"])
        else:
            out[name] = [_squeeze(x) for x in m.leaf(f[ref])]
    return out


def _squeeze(a):
    while isinstance(a, list) and len(a) == 1 and isinstance(a[0], list):
        a = a[0]
    return a


def channel_names(f: h5py.File) -> list[str]:
    """
    EEG channel names (data.dim.chan.eeg: one cell per trial, each a cell of names, the same in every file; empty
    for S06 trials 1-10, so the first non-empty one is used).
    """
    for ref in np.asarray(f["data/dim/chan/eeg"]).ravel():
        cell = np.asarray(f[ref])
        if cell.dtype == object:
            return ["".join(map(chr, np.asarray(f[r]).ravel())) for r in cell.ravel()]
    raise ValueError(f"{f.filename}: no channel names")
