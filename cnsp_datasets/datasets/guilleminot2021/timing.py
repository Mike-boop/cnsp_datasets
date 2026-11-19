"""
Trial timing for guilleminot2021 from the EEG 'Sound' channel, which records both the speech and the vibrotactile
signal. Writes trial_timing.csv (shipped next to the adaptor), which the adaptor reads.

What was played (established from the Sound channel, see the review notes):
  - Each trial plays one stimulus buffer at 39062.5 Hz: 1 s of silence, the story part (Odin_X.wav), 1 s of silence.
    Stimuli/Odin_X_audio.npy is the speech buffer and Stimuli/Odin_X_phone_.npy the zero-delay tactile buffer.
  - Audio-tactile trials: the tactile buffer starts `Delay` ms after the speech buffer (negative: tactile first).
  - Mismatched trials (Correlated = 0): the trial's own tactile buffer, circularly shifted by a quarter of its length.
  - The buffer starts 1-3 ms after the R3 marker in all but one trial (zartan session 2, row 0: 2.39 s before it).

For every row of each session's csv this finds the buffer onset by cross-correlating the Sound channel (1 kHz,
high-passed at 20 Hz) with the expected tactile buffer (or the speech buffer in audio-only trials) within 5 s of each
R3 marker (method "stimtrack"). A row matching no marker is searched for over the whole recording ("no_marker").
Rows whose Sound is unusable (saturated) take the one unused marker between their neighbours' markers, + 2 ms
("marker"); otherwise "missing". Column `issue` flags trials that run past the end of their recording ("past_end") or
contain a recording pause ("segment_break": MNE joins the segments without a gap; both naga "no_marker" trials
started during a pause, so their marker was never recorded). The adaptor uses stimtrack and marker rows without an
issue.

    python -m cnsp_datasets.datasets.guilleminot2021.timing <download_dir>
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache

import mne
import numpy as np
import pandas as pd
from scipy.signal import butter, fftconvolve, resample_poly, sosfiltfilt

BUFFER_FS = 39062.5
PAD_S = 1.0                          # silence before the story part in each buffer
MARKER = "Response/R  3"
MARKER_LATENCY_S = 0.002             # typical buffer onset after the marker
MIN_R = {"audio": 0.1, "tactile": 0.3}
SEARCH_S = 5.0
OUT = os.path.join(os.path.dirname(__file__), "trial_timing.csv")
_SOS = butter(4, 20, "hp", fs=1000, output="sos")


def tactile_buffer(stimuli_dir: str, file: str, correlated: bool) -> np.ndarray:
    """Zero-delay tactile buffer of a story part (39062.5 Hz); mismatched trials roll it by a quarter."""
    x = np.load(os.path.join(stimuli_dir, f"Odin_{file}_phone_.npy"))
    return x if correlated else np.roll(x, len(x) // 4)


@lru_cache(maxsize=64)
def _template(stimuli_dir: str, file: str, kind: str, correlated: bool) -> np.ndarray:
    x = (np.load(os.path.join(stimuli_dir, f"Odin_{file}_audio.npy")) if kind == "audio"
         else tactile_buffer(stimuli_dir, file, correlated))
    return sosfiltfilt(_SOS, resample_poly(x, 128, 5000)).astype(np.float32)  # -> 1 kHz


def _match(sound: np.ndarray, template: np.ndarray) -> tuple[int, float]:
    c = fftconvolve(sound, template[::-1], "valid")
    k = int(np.argmax(np.abs(c)))
    energy = float((sound[k:k + len(template)] ** 2).sum())
    return k, float(np.abs(c[k]) / np.sqrt((template ** 2).sum() * energy + 1e-30))


def session_timing(root: str, participant: str, session: int, vhdrs: list[str]) -> pd.DataFrame:
    stim_dir = os.path.join(root, "Stimuli")
    info = pd.read_csv(os.path.join(root, participant, f"{participant}_EEG_{session}", f"{participant}_EEG_{session}.csv"))
    raws = [mne.io.read_raw_brainvision(v, preload=False, verbose="ERROR") for v in vhdrs]
    sounds = [sosfiltfilt(_SOS, r.get_data(picks=["Sound"])[0]).astype(np.float32) for r in raws]
    marks = [(f, a["onset"]) for f, r in enumerate(raws) for a in r.annotations if a["description"] == MARKER]
    found = {}                                   # row -> (r, marker, recording index, buffer onset s, method)
    templates = {}
    # pass 1: each row against the markers (best match within SEARCH_S of a marker)
    for row, t in info.iterrows():
        kind = "audio" if t.Type == "audio" else "tactile"
        tpl = _template(stim_dir, str(t.File), kind, bool(t.Correlated))
        shift = t.Delay / 1000 if kind == "tactile" and t.Correlated else 0.0  # tactile buffer onset - buffer onset
        templates[row] = (kind, tpl, shift)
        best = (-1.0, None, None, None, "stimtrack")
        for m, (f, onset) in enumerate(marks):
            a = max(0, int((onset - SEARCH_S) * 1000))
            seg = sounds[f][a:int((onset + SEARCH_S) * 1000) + len(tpl)]
            if len(seg) > len(tpl):
                k, r = _match(seg, tpl)
                if r > best[0]:
                    best = (r, m, f, (a + k) / 1000 - shift, "stimtrack")
        found[row] = best
    ok = lambda row: found[row][0] >= MIN_R[templates[row][0]]  # noqa: E731
    # pass 2: rows matching no marker: search each whole recording
    for row in [r for r in found if not ok(r)]:
        kind, tpl, shift = templates[row]
        for f, s in enumerate(sounds):
            if len(s) > len(tpl):
                k, r = _match(s, tpl)
                if r >= MIN_R[kind] and r > found[row][0]:
                    found[row] = (r, None, f, k / 1000 - shift, "no_marker")
    # pass 3: Sound unusable (saturated, absent): the one unused marker between the neighbouring matched rows' markers
    used = {found[r][1] for r in found if ok(r) and found[r][1] is not None}
    for row in [r for r in found if not ok(r) and found[r][4] != "no_marker"]:
        before = [found[r][1] for r in found if r < row and ok(r) and found[r][1] is not None]
        after = [found[r][1] for r in found if r > row and ok(r) and found[r][1] is not None]
        lo, hi = max(before, default=-1), min(after, default=len(marks))
        free = [m for m in range(lo + 1, hi) if m not in used]
        if len(free) == 1:
            f, onset = marks[free[0]]
            found[row] = (found[row][0], free[0], f, onset + MARKER_LATENCY_S, "marker")
            used.add(free[0])
        else:
            found[row] = (found[row][0], None, None, None, "missing")
    rows = []
    for row, t in info.iterrows():
        r, m, f, onset, method = found[row]
        rows.append(dict(participant=participant, session=session, row=row, file=t.File, type=t.Type, delay=t.Delay,
                         correlated=int(t.Correlated), method=method, r=round(r, 3), marker=m,
                         recording=None if f is None else os.path.basename(vhdrs[f]),
                         buffer_onset_s=None if onset is None else round(onset, 4),
                         marker_minus_onset_ms=None if m is None or onset is None
                         else round(1000 * (marks[m][1] - onset), 1)))
    return pd.DataFrame(rows)


def main(root: str) -> None:
    from cnsp_datasets.datasets.guilleminot2021.adaptor import EEG_FNAME_DICT, PARTICIPANTS, SESSIONS
    frames = []
    for p in PARTICIPANTS:
        for ses in SESSIONS:
            names = [EEG_FNAME_DICT[p][str(ses)], EEG_FNAME_DICT[p][f"{ses}_2"]]
            vhdrs = [os.path.join(root, p, f"{p}_EEG_{ses}", n) for n in names if n]
            if all(os.path.exists(v) for v in vhdrs):
                frames.append(session_timing(root, p, ses, vhdrs))
    flag_issues(pd.concat(frames), root).to_csv(OUT, index=False)
    print(f"wrote {OUT}")


def flag_issues(timing: pd.DataFrame, root: str) -> pd.DataFrame:
    """Add column `issue`: "past_end" (buffer ends after the recording) or "segment_break" (recording paused)."""
    issues = []
    for t in timing.itertuples():
        issue = ""
        if isinstance(t.recording, str):
            raw = mne.io.read_raw_brainvision(os.path.join(root, t.participant, f"{t.participant}_EEG_{t.session}",
                                                           t.recording), preload=False, verbose="ERROR")
            buffer = np.load(os.path.join(root, "Stimuli", f"Odin_{t.file}_audio.npy"), mmap_mode="r")
            end = t.buffer_onset_s + len(buffer) / BUFFER_FS
            if any(t.buffer_onset_s < a["onset"] < end for a in raw.annotations
                   if a["description"].startswith("New Segment")):
                issue = "segment_break"
            elif end > raw.times[-1]:
                issue = "past_end"
        issues.append(issue)
    return timing.assign(issue=issues)


if __name__ == "__main__":
    main(sys.argv[1])
