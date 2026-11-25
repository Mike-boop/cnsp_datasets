"""
Shared readers and helpers for adaptors.

Stimulus loaders return {"fs": int, "data": float32 array (n_channels, n_times)} (the stimulus dict saved by the
sinks). Neural data stays in SI units; bad channels are kept in the data and listed in info["bads"].
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, Iterable, List, Mapping, Sequence, Tuple

import mne
import numpy as np

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------------------------------------------
# audio
# ---------------------------------------------------------------------------------------------------------------

def to_float32(x: np.ndarray) -> np.ndarray:
    """PCM samples as float32 in [-1, 1): integers scaled by their full range (uint8 centred), floats kept."""
    x = np.asarray(x)
    if x.dtype.kind == "f":
        return x.astype(np.float32, copy=False)
    if x.dtype == np.uint8:
        return ((x.astype(np.float32) - 128.0) / 128.0)
    if x.dtype.kind == "i":
        return (x / float(-np.iinfo(x.dtype).min)).astype(np.float32)
    raise TypeError(f"unsupported sample type {x.dtype}")


def read_wav(path: str, channel: int | None = None, collapse_identical: bool = False,
             expect_fs: float | None = None) -> Tuple[np.ndarray, int]:
    """
    A wav (or any file soundfile reads: flac, ogg, aiff) as float32 (n_channels, n_times) in [-1, 1), and its
    rate. Integer PCM of any width is scaled by its full range; float files are kept as stored.

    channel: keep only this channel (e.g. li2022 stores the two talkers as left/right). collapse_identical: a
    multichannel file whose channels are all identical (mono stored as stereo) becomes one channel; differing
    channels are kept (and logged), never averaged. expect_fs: raise if the file's rate differs.
    """
    import soundfile  # imported here: only audio adaptors need it

    data, fs = soundfile.read(path, dtype="float32", always_2d=True)  # (n_times, n_channels)
    data = data.T
    if expect_fs is not None and fs != expect_fs:
        raise ValueError(f"{path}: {fs} Hz, expected {expect_fs} Hz")
    if channel is not None:
        if not 0 <= channel < data.shape[0]:
            raise ValueError(f"{path}: has {data.shape[0]} channels, asked for channel {channel}")
        data = data[channel:channel + 1]
    elif collapse_identical and data.shape[0] > 1:
        if all(np.array_equal(data[0], d) for d in data[1:]):
            data = data[:1]
        else:
            log.info("%s: channels differ, kept all %d", path, data.shape[0])
    return np.ascontiguousarray(data), int(fs)


def audio_loader(path: str, mute: int = 0, **read_kwargs) -> Callable[[], Dict]:
    """Stimulus loader of read_wav(path, **read_kwargs); samples before `mute` set to 0."""
    def _load() -> Dict:
        data, fs = read_wav(path, **read_kwargs)
        if mute:
            data = data.copy()
            data[:, :mute] = 0
        return {"fs": fs, "data": data}

    return _load


def array_loader(data: np.ndarray, fs: float) -> Callable[[], Dict]:
    """Stimulus loader of an array already in memory (e.g. a shipped envelope), as float32 (n_channels, n)."""
    data = np.atleast_2d(np.asarray(data, dtype=np.float32))
    fs = int(fs) if float(fs).is_integer() else float(fs)
    return lambda: {"fs": fs, "data": data}


# ---------------------------------------------------------------------------------------------------------------
# triggers
# ---------------------------------------------------------------------------------------------------------------

def status_codes(status: np.ndarray, mask: int = 0xFFFF) -> np.ndarray:
    """Trigger codes of a BioSemi 'Status' channel (as read by MNE, any float/int type), masked."""
    return np.asarray(np.rint(status), dtype=np.int64).ravel() & mask


def status_edges(status: np.ndarray, mask: int = 0xFFFF, kind: str = "rise",
                 idle: int | None = 0) -> np.ndarray:
    """
    Sample indices where the masked Status code changes. kind: "rise" (code leaves `idle`), "fall" (returns to
    `idle`) or "change" (any change). idle=None: the most common code is taken as idle (BioSemi devices whose
    upper trigger bits idle high).
    """
    codes = status_codes(status, mask)
    if idle is None:
        values, counts = np.unique(codes, return_counts=True)
        idle = int(values[np.argmax(counts)])
    active = codes != idle
    if kind == "change":
        return np.flatnonzero(np.diff(codes) != 0) + 1
    if kind == "rise":
        return np.flatnonzero(~active[:-1] & active[1:]) + 1
    if kind == "fall":
        return np.flatnonzero(active[:-1] & ~active[1:]) + 1
    raise ValueError(f"kind {kind!r} not in rise/fall/change")


# ---------------------------------------------------------------------------------------------------------------
# channels
# ---------------------------------------------------------------------------------------------------------------

def mark_bads(raw: mne.io.BaseRaw, bads: Iterable[str], strict: bool = True) -> mne.io.BaseRaw:
    """
    Add `bads` to raw.info["bads"] (kept in the data). strict: raise on a name that is not a channel (a stale
    list); otherwise log it and skip it.
    """
    bads = list(dict.fromkeys(bads))
    unknown = [b for b in bads if b not in raw.ch_names]
    if unknown:
        if strict:
            raise ValueError(f"bad channels {unknown} are not in the recording")
        log.warning("bad channels %s are not in the recording; ignored", unknown)
    raw.info["bads"] = list(dict.fromkeys([*raw.info["bads"], *[b for b in bads if b in raw.ch_names]]))
    return raw


def flat_channels(raw_or_data, ch_names: Sequence[str] | None = None, tol: float = 0.0) -> List[str]:
    """Channels whose samples vary by at most `tol` (zero-filled or disconnected), from a Raw or an array."""
    if isinstance(raw_or_data, mne.io.BaseRaw):
        data, ch_names = raw_or_data.get_data(), raw_or_data.ch_names
    else:
        data = np.asarray(raw_or_data)
    if ch_names is None:
        raise ValueError("ch_names is needed with an array")
    spread = np.ptp(data, axis=1)
    return [name for name, s in zip(ch_names, spread) if s <= tol]


def bads_for(bads: Mapping, *keys) -> List[str]:
    """
    Bad channels of one recording from a dataset's BADS table. The table maps keys from the most to the least
    specific, e.g. BADS[(subject, session, ns_type)], BADS[(subject, session)] or BADS[subject]: every matching
    level is merged. keys: (subject, session, ns_type) or a prefix of it.
    """
    out: List[str] = []
    for n in range(len(keys), 0, -1):
        key = keys[:n] if n > 1 else keys[0]
        out.extend(bads.get(key, []))
    return list(dict.fromkeys(out))


MASTOID_NAMES = {"M1", "M2"}


def rename_channels(raw: mne.io.BaseRaw, mapping: Mapping[str, str],
                    types: Mapping[str, str] | None = None) -> mne.io.BaseRaw:
    """
    Rename (e.g. {"EXG1": "M1", "EXG2": "M2", "EXG3": "VEOG"}) and retype channels in one place. Renamed
    mastoids default to type "misc" and EOG names (VEOG, HEOG, EOG*) to "eog" unless `types` says otherwise.
    """
    mapping = {k: v for k, v in mapping.items() if k in raw.ch_names}
    raw.rename_channels(mapping)
    default = {v: ("misc" if v in MASTOID_NAMES else "eog") for v in mapping.values()
               if v in MASTOID_NAMES or v in ("VEOG", "HEOG") or v.startswith("EOG")}
    types = {**default, **(types or {})}
    if types:
        raw.set_channel_types({k: v for k, v in types.items() if k in raw.ch_names}, verbose="ERROR")
    return raw


# ---------------------------------------------------------------------------------------------------------------
# TextGrid
# ---------------------------------------------------------------------------------------------------------------

def _quote(text: str) -> str:
    return '"' + str(text).replace('"', '""') + '"'


def textgrid(tiers: Mapping[str, Sequence[Tuple[float, float, str]]], xmax: float | None = None,
             xmin: float = 0.0, fill_gaps: bool = True) -> str:
    """
    A Praat TextGrid (long text format) of interval tiers {name: [(onset_s, offset_s, label), ...]}. Gaps between
    intervals (and before the first / after the last, up to xmin / xmax) are filled with empty intervals, as
    Praat requires; overlapping intervals raise. xmax defaults to the latest offset.
    """
    xmax = max(off for ivs in tiers.values() for _, off, _ in ivs) if xmax is None else xmax
    lines = ['File type = "ooTextFile"', 'Object class = "TextGrid"', "", f"xmin = {xmin}", f"xmax = {xmax}",
             "tiers? <exists>", f"size = {len(tiers)}", "item []:"]
    for i, (name, intervals) in enumerate(tiers.items(), 1):
        ivs = sorted((float(a), float(b), str(t)) for a, b, t in intervals)
        filled: List[Tuple[float, float, str]] = []
        t = xmin
        for a, b, label in ivs:
            if a < t - 1e-9:
                raise ValueError(f"tier {name!r}: interval ({a}, {b}) overlaps the previous one")
            if fill_gaps and a > t + 1e-9:
                filled.append((t, a, ""))
            filled.append((a, b, label))
            t = b
        if fill_gaps and xmax > t + 1e-9:
            filled.append((t, xmax, ""))
        lines += [f"    item [{i}]:", '        class = "IntervalTier"', f"        name = {_quote(name)}",
                  f"        xmin = {xmin}", f"        xmax = {xmax}", f"        intervals: size = {len(filled)}"]
        for j, (a, b, label) in enumerate(filled, 1):
            lines += [f"        intervals [{j}]:", f"            xmin = {a}", f"            xmax = {b}",
                      f"            text = {_quote(label)}"]
    return "\n".join(lines) + "\n"
