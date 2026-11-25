from __future__ import annotations

import os
import unicodedata
from datetime import datetime
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
from mne.channels import make_standard_montage
from pymatreader import read_mat

from cnsp_datasets.datasets.accou2023.adaptor import _load_npz
from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import mark_bads
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 128  # authors' preprocessed EEG and envelopes
TRIGGER_FS = 8192  # raw BDF rate of the trigger positions in metadata
SWITCH = 300.0  # s: both talkers swap sides (the attended talker stays the same)
EOG = {"EXG3": "VEOG_high", "EXG4": "VEOG_low", "EXG5": "HEOG_right", "EXG6": "HEOG_left"}  # notes.md 5
BADS = {3: ["P1", "PO3"], 16: ["P1"]}  # near-flat (< 0.1 x median SD), notes.md 5
# podcast (shipped name without "_10min") -> (SparrKULee stimulus, start in it (s)); envelope match, notes.md 4
SPARRKULEE = {
    "Heeft_het_zin_om_fair_trade_te_kopen": ("podcast_24", 18.0),
    "Hoe_groot_is_de_kans_dat_je_niet_de_vader_van_je_kind_bent": ("podcast_15", 17.964),
    "Hoe_moeilijk_is_het_om_de_trein_stipt_te_laten_rijden": ("podcast_1", 17.964),
    "Hoe_onterf_je_je_kind": ("podcast_23", 18.0),
    "Hoe_word_ik_fit_vanuit_mijn_luie_zetel": ("podcast_28", 18.0),
    "Waarom_gebruiken_we_drugs_niet_meer_als_medicijn": ("podcast_32", 17.964),
    "Waarom_herinneren_mensen_met_dementie_zich_enkel_hun_jeugd": ("podcast_20", 18.0),
    "Wat_kan_je_terugvinden_in_een_druppel_bloed": ("podcast_25", 18.0),
    "Zijn_led-schermen_gevaarlijk": ("podcast_19", 18.0),
    "Zorgt_Waze_voor_meer_sluipverkeer": ("podcast_35", 17.964),
}
# timing problems seen in the EEG only (backward decoder, alignment/decoder_lags.csv; documented, not corrected)
LATE_CUT = {(4, "MovingTargetNoise2"): "epoch starts ~1 s into the audio (decoder lag -994 ms, z 6.4)"}
TRIGGER_TYPE = ("hardware (inferred: 1-s square pulses recorded by the EEG (paper 2.3), quantisation-level jitter; "
                "the pulse grid does not follow the audio after a first-buffer stall, notes.md 6)")
NOTES = ("Authors' preprocessed trials (README): BioSemi 8192 Hz -> 256 Hz, 1-40 Hz zero-phase Chebyshev II, 128 Hz, "
         "cut by the authors to 600 s from the trial start; microvolts scaled to V; no reference (CMS/DRL). Shipped "
         "timing kept: no onset or drift correction. Stimuli: the authors' 128 Hz envelopes of the dry podcasts "
         "(gammatone, |.|^0.6, 1-40 Hz; 'envelope') for all 30 podcasts, and for the 10 that are SparrKULee podcasts "
         "the matching 600-s excerpt of the SparrKULee audio ('audio', 48 kHz, envelope-matched to ~1 ms). Played "
         "after HRIR convolution (+-90 deg) over insert phones; MovingTargetNoise added babble noise at -1 dB SNR "
         "(not shipped). Attention: the attended talker is fixed; both talkers swap sides at 300 s "
         "(attend/left, attend/right annotations). Visual stimuli are not standardised.")


class Rotaru2024Adaptor(BaseAdaptor):
    """
    Rotaru et al. 2024 AV-GC-AAD (Zenodo 11058711): 13 participants (sub01, 03, 04, 07-16), two competing Flemish
    podcasts over insert phones, conditions MovingVideo, MovingTargetNoise (not sub01, 03), NoVisuals and FixedVideo
    (= StaticVideo), two 10-min trials per condition (sub14: one FixedVideo). BioSemi 64 + 4 EOG, authors'
    preprocessed data at 128 Hz. Stimulus names are the podcast titles. `sparrkulee_dir`: a SparrKULee (accou2023)
    download, for the audio of the 10 podcasts it shares; without it only the envelopes are written. See notes.md.
    """

    def __init__(self, download_dir: str, sparrkulee_dir: str | None = None):
        super().__init__(download_dir)
        self.files = self.sorted_glob(download_dir, "2024-AV-GC-AAD-sub*_preprocessed.mat")
        self.sparrkulee_dir = sparrkulee_dir

    def parse(self) -> Iterable[TrialRecord]:
        for path in self.files:
            d = _read(path)
            participant = d["subjID"].rsplit("-", 1)[1]
            sub = int(participant[3:])
            rows = {r["conditionID"]: r for r in d["randomization"]}  # not in trial order (notes.md 3)
            times = [_start_time(m) for m in d["metadata"]]
            order = np.argsort(np.argsort(times)) + 1  # trial number = recording position
            for idx, cid in enumerate(d["conditionID"]):
                r = rows[cid]
                if d["initAttention"][idx][0].upper() != r["first_attended_side"] or r["switch_times"] != SWITCH:
                    raise ValueError(f"{path} trial {idx}: attention labels disagree")
                first = r["first_attended_side"]
                att, una = (r["left"], r["right"]) if first == "L" else (r["right"], r["left"])
                stimuli = [s for wav, key, attended in ((att, "attendedEnvelopes", True),
                                                        (una, "unattendedEnvelopes", False))
                           for s in self._stimuli(_name(wav), d["stimulus"][key][idx], attended)]
                condition = cid.rstrip("12")
                pulses = _pulse_summary(d["metadata"][idx]["RawData"]["Triggers"])
                extra = dict(participant=participant, condition_id=cid, block=int(cid[-1]), shipped_trial_index=idx,
                             recording_start=times[idx].isoformat(), attended_stimulus=_name(att),
                             unattended_stimulus=_name(una), initial_attended_side=first, switch_time_s=SWITCH,
                             visual_stimulus=None if condition == "NoVisuals" else r.get("visuals"),  # notes.md 3
                             bad_channels=BADS.get(sub, []), reference="BioSemi CMS/DRL (not re-referenced)",
                             units_as_shipped="uV", montage="biosemi64 template (no digitisation)",
                             eog=EOG,
                             **pulses, timing_flag=_timing_flag(sub, cid, pulses["first_pulse_interval_dev_ms"]))
                yield TrialRecord(subject=sub, session=1, trial=int(order[idx]), condition=condition, ns_type="eeg",
                                  stimulus=stimuli, neural_data_fn=_eeg_loader(path, idx, sub, first, extra))

    def _stimuli(self, name: str, env: np.ndarray, attended: bool) -> list[StimulusRecord]:
        """The shipped envelope, plus the SparrKULee audio excerpt when the podcast is one of SparrKULee's."""
        env = np.asarray(env, dtype=np.float32)
        out = [StimulusRecord("audio", name, lambda: {"fs": FS, "data": env[None, :]}, is_attended=attended,
                              feature_name="envelope")]
        if self.sparrkulee_dir is not None and name in SPARRKULEE:
            stem, start = SPARRKULEE[name]
            path = os.path.join(self.sparrkulee_dir, "stimuli", "eeg", f"{stem}.npz")
            path = path if os.path.exists(path) else path + ".gz"  # as shipped by accou2023
            out.append(StimulusRecord("audio", name, _excerpt_loader(path, start, len(env) / FS),
                                      is_attended=attended, feature_name="audio"))
        return out


def _name(wav: str) -> str:
    """Stimulus name: the podcast title as shipped, without '_10min.wav', in ASCII ('België' -> 'Belgie')."""
    stem = wav.removesuffix(".wav").removesuffix("_10min")
    return unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()


def _start_time(metadata: dict) -> datetime:
    """BDF start time of a trial (gives the recording order)."""
    return datetime.fromisoformat(metadata["FileHeader"]["DateTime"])


def _chain(triggers) -> np.ndarray:
    """
    The 1-s pulse train: the first trigger (pulse 0; spurious events come later, notes.md 6), then each trigger
    0.5-1.5 s after the last kept one.
    """
    t = np.asarray(triggers, dtype=np.int64)
    keep = [t[0]]
    for x in t[1:]:
        if 0.5 * TRIGGER_FS < x - keep[-1] < 1.5 * TRIGGER_FS:
            keep.append(x)
    return np.array(keep)


def _pulse_summary(triggers) -> dict:
    """First pulse-interval deviation (first-buffer stall) and the pulse-grid drift, measured, not applied."""
    c = _chain(triggers)
    k = np.round((c - c[0]) / TRIGGER_FS)
    slope = np.polyfit(k[1:], c[1:], 1)[0]  # from pulse 1 on: the first interval may be stalled
    return dict(n_pulses=len(c), first_pulse_interval_dev_ms=round((c[1] - c[0] - TRIGGER_FS) / TRIGGER_FS * 1e3, 2),
                pulse_grid_drift_ppm=round((slope / TRIGGER_FS - 1) * 1e6, 2))


def _timing_flag(sub: int, cid: str, dev: float) -> str | None:
    """
    Known timing problems of the shipped epoch (notes.md 6), or None. dev: first pulse-interval deviation (ms);
    positive stalls are >= +46 ms, negative deviations decode as aligned.
    """
    if (sub, cid) in LATE_CUT:
        return LATE_CUT[(sub, cid)]
    if dev > 1:
        return (f"first-buffer stall ({dev:.0f} ms): the EEG lags the envelope by ~20-130 ms, more early in the "
                f"trial (decoder; notes.md 6)")
    return None


def _eeg_loader(path: str, idx: int, sub: int, first: str, extra: dict) -> Callable[[], mne.io.BaseRaw]:
    """One trial: EEG (64; sub16 63, no P9) + 4 EOG at 128 Hz in V, with attend/left|right annotations."""
    def _loader() -> mne.io.BaseRaw:
        d = _read(path)
        data = np.asarray(d["data"][idx], dtype=np.float64).T * 1e-6
        labels = list(d["metadata"][idx]["FileHeader"]["Channels"]["Label"])
        if len(labels) != data.shape[0]:
            raise ValueError(f"{path} trial {idx}: {len(labels)} labels for {data.shape[0]} channels")
        if labels[-4:] != list(EOG):
            raise ValueError(f"{path} trial {idx}: last labels {labels[-4:]}, expected {list(EOG)}")
        info = mne.create_info(labels[:-4] + list(EOG.values()), float(FS),
                               ["eeg"] * (len(labels) - 4) + ["eog"] * 4)
        raw = mne.io.RawArray(data, info, verbose="ERROR")
        raw.set_montage(make_standard_montage("biosemi64"))
        mark_bads(raw, BADS.get(sub, []))
        side = {"L": "attend/left", "R": "attend/right"}
        raw.set_annotations(mne.Annotations([0.0, SWITCH], [SWITCH, raw.n_times / FS - SWITCH],
                                            [side[first], side["R" if first == "L" else "L"]]))
        raw.info["description"] = provenance("onset_only", TRIGGER_TYPE, NOTES, validation_tier="low", **extra)
        return raw
    return _loader


def _excerpt_loader(path: str, start: float, duration: float) -> Callable[[], dict]:
    """The excerpt [start, start + duration) s of a SparrKULee stimulus (48 kHz), as played in this dataset."""
    def _loader() -> dict:
        d = _load_npz(path)
        fs = int(d["fs"])
        a = int(round(start * fs))
        return {"fs": fs, "data": d["audio"][a:a + int(round(duration * fs))].astype(np.float32)[None, :]}
    return _loader


@lru_cache(maxsize=1)  # one ~150 MB file per participant; trials are read participant by participant
def _read(path: str) -> dict:
    """A participant's .mat."""
    return read_mat(path)


ADAPTOR = Rotaru2024Adaptor
