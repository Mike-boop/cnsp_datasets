from __future__ import annotations

import glob
import io
import math
import os
import re
from functools import lru_cache
from typing import Iterable

import mne
import numpy as np
import pandas as pd
import textgrid
from scipy.io import wavfile

from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

DRIFT_CSV = os.path.join(os.path.dirname(__file__), "drift.csv")  # from drift.py (audio copy vs wav, per presentation)
ACOUSTIC_DELAY_MS = 7.3  # assumed: 2.5 m ER3 tubes at 343 m/s; not in the (electrical) audio copy (notes.md, 9.4)
FIT_END_S = {("sub-E12_task-en_run-1_meg.fif", 2): 351.0}  # playback glitch (+15 ms) at wav ~352 s (notes.md, 9.6)
SITES = {
    "en": dict(folder="english-native-english-conversation", task="en", phones="mfa_phoneme",
               audio_copy={"MISC006": "audio copy (V), identical to MISC007",
                           "MISC007": "audio copy (V), identical to MISC006"},
               system="MEGIN TRIUX (MRC CBU Cambridge), 2023-2024", sss=("sss_cal_triux.dat", "ct_sparse_triux.fif"),
               jitter_ms=0.014, trigger="software (inferred: Psychtoolbox, paper; code 3 jitters by 0.90 ms sd)"),
    "ru": dict(folder="russian-native-russian-conversation", task="ru", phones="mfa_phone",
               audio_copy={"MISC005": "audio copy (V)"},
               system="Elekta Neuromag VectorView (MRC CBU Cambridge), 2015",
               sss=("sss_cal_vectorview.dat", "ct_sparse_vectorview.fif"), jitter_ms=0.024,
               trigger="software (inferred: Psychtoolbox, paper; code 3 jitters by 0.35 ms sd)"),
}
DROP = {"recordedinerror"}  # R1, R2: a second channel typed ECG, recorded in error
NOTES = ("Raw MEG as shipped: no SSS/MaxFilter (fine-calibration and cross-talk files in the dataset root); FIF bads "
         "kept. The simultaneous EEG is not included. Onset = audio-copy onset fitted against the wav (10 s windows, "
         "Theil-Sen; code 3 of STI101 & 0xFF only locates the presentation) + 7.3 ms assumed tube delay (2.5 m ER3 "
         "tubes; the authors' delay configuration is not shared). Clock drift (English ~+538 ppm, Russian ~-0.7 ppm) "
         "corrected by resampling onto the audio clock. cHPI lines (293-328 Hz) remain in the data. Visual dots ran "
         "from the audio onset (possible visual onset responses).")
VALIDATION_NOTE = ("brainstem tier with tSSS (Maxwell filtering with the site's shipped sss_cal/ct_sparse files, "
                   "applied by the user; standardised data are raw); raw data reach no tier (low forward tier fails)")


class Yang2026Adaptor:
    """
    Kymata SOTO language dataset (Yang et al. 2026, OSF qdzgh): native listeners hear one ~400 s BBC podcast excerpt
    in runs of 2 presentations (English 8, sub-E1 4, sub-E8 6; Russian 4), MEG at 1000 Hz, raw. site "en": 20 English
    listeners on a MEGIN TRIUX (sub-E3b = subject 3, session 2); site "ru": 15 Russian listeners on a VectorView.
    download_dir: the shared `yang2026` download holding both BIDS folders.

    One condition `conversation`; trial = (run - 1) * 2 + presentation, starting at the audio onset (drift.csv + 7.3 ms
    tube delay) and as long as the wav (shorter for 13 Russian presentations whose recording stopped early; sub-E12
    run-1 presentation 2 ends at wav 351 s, before a playback glitch). drift_correction: "presentation" (default,
    drift.csv), "site" (median over the site) or None. Channels: MEG, EOG, ECG, audio copy (misc). Stimuli: the wav
    (first channel; L = R) and a TextGrid (words, phones) from the MFA tables. See notes.md.
    """

    def __init__(self, download_dir: str, site: str, drift_correction: str | None = "presentation"):
        if drift_correction not in ("presentation", "site", None):
            raise ValueError(f"drift_correction must be 'presentation', 'site' or None, not {drift_correction!r}")
        self.cfg = SITES[site]
        self.site = site
        self.root = os.path.join(download_dir, self.cfg["folder"])
        self.drift_correction = drift_correction
        d = pd.read_csv(DRIFT_CSV)
        self.table = d[d.site == site].set_index(["file", "pres"])
        self.wav = os.path.join(self.root, "stimuli", "audio", "stimulus.wav")

    def parse(self) -> Iterable[TrialRecord]:
        name = f"conversation_{self.site}"
        fs, x = wavfile.read(self.wav, mmap=True)
        n_wav = math.ceil(len(x) * 1000 / fs)
        stimulus = [StimulusRecord("audio", name, _audio_loader(self.wav), True, "audio"),
                    StimulusRecord("audio", name, self._textgrid_loader(len(x) / fs), True, "textgrid")]
        site_drift = self.table.drift_ppm.median()
        for (fname, pres), m in self.table.iterrows():
            sub, run = re.match(rf"sub-(\w+?)_task-{self.cfg['task']}_run-(\d)_meg.fif", fname).groups()
            fif = _find(self.root, sub, fname)
            drift = {"presentation": m.drift_ppm, "site": site_drift, None: 0.0}[self.drift_correction]
            fit_end = FIT_END_S.get((fname, pres))
            n_out = n_wav if fit_end is None else round(fit_end * 1000)
            onset = m.onset_samp + ACOUSTIC_DELAY_MS * (1 + m.drift_ppm * 1e-6)  # MEG samples from first stored
            extra = dict(
                drift_ppm=round(float(m.drift_ppm), 3), jitter_ms=self.cfg["jitter_ms"],
                drift_corrected_ppm=round(float(drift), 3), site=self.site, system=self.cfg["system"],
                file=fname, run=int(run), presentation=int(pres), code3_sample=int(m.code3),
                audio_onset_after_code3_ms=round(float(m.onset_samp - m.code3), 4),
                acoustic_delay_ms=ACOUSTIC_DELAY_MS, onset_sample=round(float(onset), 4),
                fit_windows=int(m.n_windows), fit_end_s=fit_end,
                sss=f"none (raw as shipped; {', '.join(self.cfg['sss'])} in the dataset root)",
                reference="none (MEG)", external_sensors=self.cfg["audio_copy"],
                chpi="continuous HPI, 5 coils at 293, 307, 314, 321, 328 Hz, not removed")
            if fit_end is not None:
                extra["glitch"] = f"playback paused ~15 ms at wav ~352 s; trial ends at wav {fit_end} s"
            yield TrialRecord(
                subject=int(sub.rstrip("b")[1:]), session=2 if sub.endswith("b") else 1,
                trial=(int(run) - 1) * 2 + int(pres), condition="conversation", ns_type="meg", stimulus=stimulus,
                neural_data_fn=_meg_loader(fif, onset, n_out, drift * 1e-6, self.cfg, extra))

    def _textgrid_loader(self, xmax: float):
        """words and phones tiers from the MFA start-time tables; `<sp>` (pause) intervals left empty."""
        audio = os.path.join(self.root, "stimuli", "audio")

        def _loader() -> str:
            tg = textgrid.TextGrid(maxTime=xmax)
            for tier, stem in (("words", "mfa_word"), ("phones", self.cfg["phones"])):
                with open(os.path.join(audio, f"{stem}.txt"), encoding="utf-8") as f:
                    labels = f.read().splitlines()
                starts = np.loadtxt(os.path.join(audio, f"{stem}_stime.txt"))
                if len(labels) != len(starts):
                    raise ValueError(f"{stem}: {len(labels)} labels, {len(starts)} start times")
                t = textgrid.IntervalTier(tier, 0, xmax)
                for a, b, mark in zip(starts, np.r_[starts[1:], xmax], labels):
                    t.add(float(a), float(b), "" if mark == "<sp>" else mark)
                tg.append(t)
            f = _Buffer()
            tg.write(f)
            return f.getvalue()

        return _loader


def _find(root: str, sub: str, fname: str) -> str:
    """The run file in sub-X/meg/ or, for sub-R6, sub-X/."""
    paths = glob.glob(os.path.join(root, f"sub-{sub}", fname)) + \
        glob.glob(os.path.join(root, f"sub-{sub}", "meg", fname))
    if len(paths) != 1:
        raise FileNotFoundError(f"{fname}: found {paths}")
    return paths[0]


def run_files(root: str, task: str) -> list[str]:
    """All task runs of a site (sub-R6 has no meg/ folder)."""
    return sorted(glob.glob(os.path.join(root, "sub-*", "meg", f"sub-*_task-{task}_run-*_meg.fif")) +
                  glob.glob(os.path.join(root, "sub-*", f"sub-*_task-{task}_run-*_meg.fif")))


def code3_samples(raw: mne.io.BaseRaw) -> np.ndarray:
    """Rising edges to code 3 (presentation onset) in STI101 & 0xFF (bit 16 corrupts the int16 codes)."""
    sti = raw.get_data(picks="STI101")[0].astype(int) & 0xFF
    edges = np.flatnonzero(np.diff(np.r_[0, sti]) != 0)
    return edges[sti[edges] == 3]


@lru_cache(maxsize=1)
def _read(fif: str) -> mne.io.BaseRaw:
    return mne.io.read_raw_fif(fif, preload=False, verbose="ERROR")


def _meg_loader(fif: str, onset: float, n_out: int, drift: float, cfg: dict, extra: dict):
    def _loader():
        raw = _read(fif)
        picks = [c for c, t in zip(raw.ch_names, raw.get_channel_types())
                 if (t in ("mag", "grad", "eog", "ecg") and c not in DROP) or c in cfg["audio_copy"]]
        out = crop_on_audio_clock(raw, onset, n_out, drift, picks=picks, sfreq_out=1000)
        dead = []  # flat (constant) MEG channels the FIF does not mark (notes 12); the drift interpolation leaves
        for kind in ("mag", "grad"):  # ~1e-22 numerical ripple on them, so compare with the type's median std
            idx = mne.pick_types(out.info, meg=kind, exclude=[])
            sd = out._data[idx].std(axis=1)
            dead += [out.ch_names[i] for i, s in zip(idx, sd)
                     if s < 1e-6 * np.median(sd) and out.ch_names[i] not in out.info["bads"]]
        out.info["bads"] = out.info["bads"] + dead
        info = dict(extra, trial_s=out.n_times / 1000, truncated_s=round((n_out - out.n_times) / 1000, 3),
                    bads=out.info["bads"], bads_added_flat=dead)
        notes = NOTES + (" The recording stopped before the end of the wav (truncated_s)." if out.n_times < n_out
                         else "")
        out.info["description"] = provenance("stimtrack_xcorr", cfg["trigger"], notes, validation_tier="brainstem",
                                             validation_note=VALIDATION_NOTE, **info)
        return out

    return _loader


def _audio_loader(path: str):
    def _loader():
        fs, x = wavfile.read(path)
        return {"fs": fs, "data": x[None, :, 0]}

    return _loader


class _Buffer(io.StringIO):
    """StringIO that survives TextGrid.write closing it."""

    def close(self):
        pass
