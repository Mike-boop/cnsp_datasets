from __future__ import annotations

import glob
import math
import os
import re
from functools import lru_cache
from typing import Iterable

import h5py
import mne
import numpy as np
import pandas as pd
from scipy.io import wavfile
from scipy.signal import resample_poly

from cnsp_datasets.datasets.broderick2019_natural.utils import multi_tier_dict_to_textgrid
from cnsp_datasets.datasets.libribrain100 import wavmap
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

STEP = 0.004       # s: a jump in timemeg - source time larger than this starts a new segment
MIN_AUDIO = 60.0   # s: shorter verified stretches are not split off as a trial of their own
SOURCE = {"TheMoth": "timepodcast", "MOCHATIMIT": "timesentence", "TIMIT": "timesentence"}  # else timechapter
NO_AUDIO = {"TIMIT": "TIMIT audio not redistributed (LDC licence)", "Sherlock8": "no Sherlock8 audio released"}


class LibriBrain100Adaptor:
    """
    LibriBrain100 (pnpl/LibriBrain + pnpl/LibriBrain2, Hugging Face): MEGIN 306-channel MEG. sub-0: raw FIF
    (1000 Hz) of Sherlock1-9, TheMoth, TIMIT and MOCHA-TIMIT, one session per chapter/story block; sub-1 to sub-32:
    the authors' preprocessed 250 Hz h5 of Sherlock1 chapters 11-12 (no raw data released).

    The audio was played in sentence-sized segments with short gaps, so the stimulus is rebuilt per session: each
    segment of the source audio is placed at its MEG time (`timemeg`), zeros in between. Sherlock chapters come from
    the release's wavs through wavmap.csv (which wav, its 44.1/44 kHz scale k and offset c, and how far the match
    holds); a session whose match breaks is split there into trial 1 (audio) and trial 2 (MEG and TextGrid only).
    TheMoth audio comes from OpenNeuro ds003020 (`<download>/ds003020/stimuli`), MOCHA-TIMIT from its sentence wavs;
    TIMIT and Sherlock8 have no audio. Every trial has a words/phones TextGrid on the trial's time axis. See notes.md.
    """

    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self.wavmap = wavmap.read()

    def parse(self) -> Iterable[TrialRecord]:
        for events in sorted(glob.glob(os.path.join(self.download_dir, "LibriBrain*", "*", "derivatives", "events",
                                                    "sub-*_events.tsv"))):
            repo, task = events.split(os.sep)[-5:-3]
            sub, ses = (int(x) for x in re.search(r"sub-(\d+)_ses-(\d+)", events).groups())
            meg = self._meg_file(repo, task, sub, ses)
            if meg is None:
                continue
            ev = pd.read_csv(events, sep="\t")
            segs = segments(ev, SOURCE.get(task, "timechapter"))
            audio_until = self._audio_until(task, sub, ses, segs)
            parts = [segs[segs.src_start < audio_until], segs[segs.src_start >= audio_until]]
            for trial, part in enumerate((p for p in parts if len(p)), 1):
                with_audio = part.src_start.iloc[0] < audio_until
                name = f"{task.lower()}_sub-{sub}_ses-{ses}" + ("" if trial == 1 else f"_part-{trial}")
                t0, t1 = part.meg_start.iloc[0], (part.meg_start + part.src_end - part.src_start).iloc[-1]
                stimuli = [StimulusRecord("audio", name, _textgrid_loader(ev, part, t0), True, "textgrid")]
                if with_audio:
                    stimuli.insert(0, StimulusRecord("audio", name, self._audio_loader(task, ses, part, t0, t1),
                                                     True, "audio"))
                yield TrialRecord(subject=sub, session=ses, trial=trial, condition=task.lower(), ns_type="meg",
                                  stimulus=stimuli, neural_data_fn=_meg_loader(meg, t0, t1, self._reference_fif()))

    # ----------------------------------------------------------------------------------------------- files

    def _meg_file(self, repo: str, task: str, sub: int, ses: int) -> str | None:
        if sub == 0:
            fifs = sorted(glob.glob(os.path.join(self.download_dir, repo, task, "sub-0", f"ses-{ses}", "meg",
                                                 "*_meg.fif")))
            return fifs[0] if fifs else None  # split-01 (MNE reads the following splits itself)
        h5 = glob.glob(os.path.join(self.download_dir, repo, task, "derivatives", "serialised*",
                                    f"sub-{sub}_ses-{ses}_*.h5"))
        return h5[0] if h5 else None

    @lru_cache(maxsize=1)
    def _reference_fif(self) -> str:
        """A sub-0 raw FIF, for the channel geometry of the h5 files (same scanner)."""
        return sorted(glob.glob(os.path.join(self.download_dir, "LibriBrain", "Sherlock1", "sub-0", "ses-*", "meg",
                                             "*_meg.fif")))[0]

    def _audio_until(self, task: str, sub: int, ses: int, segs: pd.DataFrame) -> float:
        """Source time up to which the session has verified audio (-inf: none)."""
        if task in NO_AUDIO:
            return -np.inf
        if task not in ("TheMoth", "MOCHATIMIT"):
            if (task, ses) not in self.wavmap.index:
                return -np.inf
            until = self.wavmap.loc[(task, ses), "valid_until_s"]
            if until < self.wavmap.loc[(task, ses), "source_end_s"] and until - segs.src_start.iloc[0] < MIN_AUDIO:
                return -np.inf
            return until
        return np.inf

    # ----------------------------------------------------------------------------------------------- audio

    def _source_wav(self, task: str, ses: int, seg) -> tuple[str, float, float]:
        """(wav path, k, c) for one segment: wav_time = k * source_time + c."""
        if task == "TheMoth":
            story = seg.wavile.split("/")[1]
            return os.path.join(self.download_dir, "ds003020", "stimuli", f"{story}.wav"), 1.0, 0.0
        if task == "MOCHATIMIT":
            return os.path.join(self.download_dir, "LibriBrain2", task, "stimuli", "audio",
                                os.path.basename(seg.wavile)), 1.0, 0.0
        row = self.wavmap.loc[(task, ses)]
        repo = "LibriBrain2" if task in ("Sherlock8", "Sherlock9") else "LibriBrain"
        return os.path.join(self.download_dir, repo, task, "stimuli", "audio", row.wav), row.k, row.c_s

    def _audio_loader(self, task: str, ses: int, part: pd.DataFrame, t0: float, t1: float):
        def _loader():
            out, fs_out = None, None
            for seg in part.itertuples():
                path, k, c = self._source_wav(task, ses, seg)
                fs, x = _wav_on_source_clock(path, round(k, 8))
                if out is None:
                    fs_out, out = fs, np.zeros(math.ceil((t1 - t0) * fs), dtype=x.dtype)
                a = int(round((seg.src_start + c / k) * fs))
                b = len(x) if task == "MOCHATIMIT" else int(round((seg.src_end + c / k) * fs))
                o = int(round((seg.meg_start - t0) * fs))
                chunk = x[max(a, 0):b][:len(out) - o]
                out[o:o + len(chunk)] = chunk
            return {"fs": fs_out, "data": out[None, :]}

        return _loader


def segments(ev: pd.DataFrame, src: str) -> pd.DataFrame:
    """
    Playback segments of one session: rows sharing a constant timemeg - source time (and segment file).
    Columns: src_start / src_end (source time), meg_start (s on the recording), wavile (first row's). A segment ends
    where the next one of the same source (chapter, story) starts; sentence wavs are played whole.
    """
    ev = ev.dropna(subset=[src]).sort_values("timemeg").reset_index(drop=True)
    offset = ev.timemeg - ev[src]
    new = (offset.diff().abs() > STEP) | (ev.wavile != ev.wavile.shift())
    source = ev.wavile.str.split("/").str[1] if src == "timepodcast" else pd.Series("", index=ev.index)
    seg = new.cumsum()
    g = ev.groupby(seg)
    out = pd.DataFrame(dict(src_first=g[src].first(), meg_first=g.timemeg.first(), wavile=g.wavile.first(),
                            source=source.groupby(seg).first(), src_last=(ev[src] + ev.duration).groupby(seg).max()))
    sentence = src == "timesentence"
    out["src_start"] = 0.0 if sentence else out.src_first
    out["meg_start"] = out.meg_first - (out.src_first - out.src_start)
    nxt = out.src_start.shift(-1)
    same_source = out.source == out.source.shift(-1)
    out["src_end"] = out.src_last if sentence else np.where(same_source & (nxt > out.src_start), nxt, out.src_last)
    out["src_end"] = np.maximum(out.src_end, out.src_last)
    return out.reset_index(drop=True)


def _textgrid_loader(ev: pd.DataFrame, part: pd.DataFrame, t0: float):
    def _loader():
        ev_ = ev.sort_values("timemeg").reset_index(drop=True)
        rows = ev_.loc[ev_.timemeg.between(part.meg_start.iloc[0] - 1e-3,
                                           (part.meg_start + part.src_end - part.src_start).iloc[-1])]
        tiers = {}
        for kind, tier in (("word", "words"), ("phoneme", "phones")):
            r = rows[rows.kind == kind]
            tiers[tier] = dict(item=r.segment.astype(str).tolist(), onset_s=(r.timemeg - t0).round(4).tolist(),
                               offset_s=(r.timemeg - t0 + r.duration).round(4).tolist())
        return multi_tier_dict_to_textgrid(tiers)

    return _loader


@lru_cache(maxsize=2)
def _wav_on_source_clock(path: str, k: float):
    """The wav resampled so that one second of it is one second of source time (k = wav s per source s)."""
    fs, x = wavfile.read(path)
    x = x[:, 0] if x.ndim == 2 else x
    if k != 1.0:
        up, down = (440, 441) if k > 1 else (441, 440)  # the two scales in wavmap.csv: 44100/44000 and its inverse
        if abs(k - down / up) > 1e-4:
            raise ValueError(f"{path}: scale {k} is not 44.1/44 kHz")
        x = resample_poly(x.astype(np.float32), up, down).astype(x.dtype)
    return fs, x


# --------------------------------------------------------------------------------------------------- MEG

@lru_cache(maxsize=1)
def _read(path: str, reference: str) -> mne.io.BaseRaw:
    if path.endswith(".fif"):
        raw = mne.io.read_raw_fif(path, preload=False, verbose="ERROR")
        return raw.pick(mne.pick_types(raw.info, meg=True, eog=True, ecg=True, emg=True))
    with h5py.File(path) as f:
        names = [c.strip() for c in f.attrs["channel_names"].split(",")]
        info = mne.pick_info(mne.io.read_info(reference, verbose="ERROR"),
                             mne.pick_channels(mne.io.read_info(reference, verbose="ERROR").ch_names, names,
                                               ordered=True))
        with info._unlock():
            info["sfreq"] = float(f.attrs["sample_frequency"])
            info["highpass"], info["lowpass"] = float(f.attrs["highpass_cutoff"]), float(f.attrs["lowpass_cutoff"])
            info["dev_head_t"], info["dig"], info["projs"], info["bads"] = None, None, [], []
            info["hpi_results"], info["hpi_meas"], info["hpi_subsystem"] = [], [], None
        return mne.io.RawArray(f["data"][:], info, verbose="ERROR")


def _meg_loader(path: str, t0: float, t1: float, reference: str):
    def _loader():
        raw = _read(path, reference)
        sf = raw.info["sfreq"]
        return crop_on_audio_clock(raw, round(t0 * sf), math.ceil((t1 - t0) * sf))

    return _loader


ADAPTOR = LibriBrain100Adaptor
