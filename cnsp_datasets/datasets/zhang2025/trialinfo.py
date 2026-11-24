"""Reader for the `this_trial_info` MATLAB object (MCOS, class task<k>info) in the zhang2025 trialinfo .mat files.

scipy loads MATLAB class objects only as opaque bytes (`__function_workspace__`). That workspace is a small MAT-file
whose single cell array holds a metadata blob (names, classes, objects, property tables) followed by the property
values. This reads the properties of object 1 (the trial info); nested `string` objects become lists of str.
"""
from __future__ import annotations

import io
import struct
from pathlib import PureWindowsPath

import numpy as np
from scipy.io import loadmat
from scipy.io.matlab._mio5 import MatFile5Reader  # private, but scipy has no public MCOS reader

REF = 0xDD000000  # first word of an object reference


def read_trial_info(path: str) -> dict:
    """Properties of the trial-info object (subject_id, speaker_directions, audio_paths, switch_time, ...)."""
    fw = loadmat(path, variable_names=["__function_workspace__"])["__function_workspace__"].tobytes()
    # fake 128-byte MAT header: 124 bytes of text, then version + endian from the workspace (skip its 4 padding bytes)
    reader = MatFile5Reader(io.BytesIO(b" " * 124 + fw[:4] + fw[8:]), squeeze_me=False)
    reader.mat_stream.seek(128)
    reader.initialize_read()
    cells = np.ravel(reader.read_var_array(reader.read_var_header()[0])[0, 0]["MCOS"][0]["arr"])
    meta = cells[0].tobytes()
    n_names = struct.unpack("<i", meta[4:8])[0]
    off = struct.unpack("<8i", meta[8:40])
    names = [n.decode() for n in meta[40:off[0]].split(b"\0")[:n_names]]
    classes = np.frombuffer(meta[off[0]:off[1]], "<i4").reshape(-1, 4)
    objects = np.frombuffer(meta[off[2]:off[3]], "<i4").reshape(-1, 6)
    tables = {1: _tables(meta[off[1]:off[2]]), 2: _tables(meta[off[3]:off[4]])}

    def obj(oid: int) -> dict:
        cls, _, _, t1, t2, _ = objects[oid]
        out = {"class": names[classes[cls][1] - 1]}
        for name, flag, value in (tables[1][t1] if t1 else tables[2][t2]):
            if flag != 1:  # inline values (enumerations, logicals) do not occur in these files
                raise ValueError(f"{path}: unsupported property flag {flag}")
            v = cells[value + 2]
            if v.dtype == np.uint32 and v.size == 6 and v.ravel()[0] == REF:
                v = obj(int(v.ravel()[4]))
                v = v["any"] if v["class"] == "string" else v
            elif v.dtype == np.uint64 and out["class"] == "string":
                v = _string(v)
            out[names[name - 1]] = v
        return out

    return obj(1)


def stem(path: str) -> str:
    """File stem of a Windows audio path stored in the trial info (e.g. speaker_1_segment_10)."""
    return PureWindowsPath(path).stem


def _tables(b: bytes) -> list:
    """Property tables: per object, (name index, flag, value) triples; each table padded to 8 bytes."""
    a = np.frombuffer(b, "<i4")
    tables, i = [None], 2  # skip two header words
    while i < len(a):
        n = int(a[i])
        tables.append([tuple(int(v) for v in a[i + 1 + 3 * k:i + 4 + 3 * k]) for k in range(n)])
        i += 1 + 3 * n + (1 + 3 * n) % 2
    return tables


def _string(u: np.ndarray) -> list[str]:
    """MATLAB string array saved as uint64: version, ndims, dims, lengths, then UTF-16 characters."""
    u = u.ravel()
    nd = int(u[1])
    n = int(np.prod(u[2:2 + nd]))
    edges = np.concatenate([[0], np.cumsum(u[2 + nd:2 + nd + n].astype(int))])
    chars = u[2 + nd + n:].view(np.uint16)
    return [chars[a:b].tobytes().decode("utf-16-le") for a, b in zip(edges[:-1], edges[1:])]
