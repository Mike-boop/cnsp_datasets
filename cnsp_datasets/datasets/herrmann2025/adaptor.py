from __future__ import annotations

import glob
import os
import re
from typing import Callable, Iterable, List

import mne
import numpy as np
import pandas as pd
from mne.channels import make_standard_montage
from mne.io import BaseRaw
from scipy.io import loadmat, wavfile

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

# Validation 2026-11-22 (notes): mlr tier for clear and babble >= 15 dB SNR, low tier at <= 10.8 dB.
LOW_TIER_MAX_SNR = 10.8
# No clear speech tracking under the logged mapping (notes 3); kept and flagged.
WEAK_TRACKING = {"na10", "na21", "na55", "na61", "na64", "na65"}
MASTOIDS = {"EXG1": "left mastoid", "EXG2": "right mastoid"}  # BioSemi convention, unverified (notes 5)
MARKER_BASE, MARKER_ON = 254, 255  # Status & 0xFF; one rising edge per story (notes 6)
PTA_HZ = (500, 1000, 2000, 4000)  # pure-tone average, both ears
AUDIO_FS = 44100
NOTES = ("Onset = Status marker rising edge (254 -> 255), inferred software marker from MATLAB/Psychtoolbox; "
         "marker vs sound onset agrees to within a few tens of ms (ERP), no stimtrack, no drift estimate. "
         "Original CMS/DRL reference; EXG1/EXG2 = left/right mastoid (convention, unverified).")
WEAK_NOTE = "No clear speech tracking under the logged story mapping (cause unknown; notes 3)."


class Herrmann2025Adaptor:
    """
    Herrmann 2025 (OSF p8nxq): younger (na01-na26) and older (na40-na65) adults listen to 20 stories (~1.7 min),
    4 in clear and one at each of 16 SNRs (57 to -6 dB) in 12-talker babble; 5 BioSemi blocks of 4 stories.
    16 scalp channels + EXG1/EXG2 (mastoids, `misc`) at 1024 Hz, as recorded (CMS/DRL, no re-referencing).

    Only blocks with a MATLAB log are used (146 of 260): the log names the wav of each story; unlogged blocks have
    unknown story and SNR (18 participants have none). Trial = 4 * (block - 1) + position (1-20).
    Onset = the block's i-th marker; the EEG lasts as long as the story. Conditions `clear` and `babble` (SNR in
    the trial metadata, raw.info["description"], JSON). Stimuli (44.1 kHz, as shipped): `<Title>` clean speech
    (the LInf wav, attended); babble trials add `<Title>_L<SNR>` (mixture as played) and the derived
    `<Title>_L<SNR>_babble` = mixture - a * clean (least-squares a). See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = download_dir
        self.demographics = _table(os.path.join(download_dir, "demographics.xlsx"), "ParticipantID")
        self.audiometry = _table(os.path.join(download_dir, "audiometry.xlsx"), "PID")

    def parse(self) -> Iterable[TrialRecord]:
        for log in sorted(glob.glob(os.path.join(self.root, "logfiles", "na*a[1-5].mat"))):
            stem = os.path.basename(log)[:-4]  # naNNa<block>
            pid, block = stem[:4], int(stem[5])
            bdf = os.path.join(self.root, "rawdata", stem + ".bdf")
            onsets = _marker_onsets(bdf)
            lists = loadmat(log, squeeze_me=True)["lists"]
            if len(onsets) != len(lists):
                raise ValueError(f"{bdf}: {len(onsets)} markers for {len(lists)} logged stories")
            for pos, (entry, onset) in enumerate(zip(lists, onsets)):
                wav = str(entry["story"])
                title, snr = re.fullmatch(r"(.+)_sil_L(.+)\.wav", wav).groups()
                clear = snr == "Inf"
                trial = 4 * (block - 1) + pos + 1
                babble = {} if clear else {"babble_stimulus": f"{title}_L{snr}_babble: derived, mixture minus "
                                                              "the least-squares scaled clean speech (not shipped)"}
                description = provenance(
                    "sw_trigger", "software (inferred; not documented)",
                    NOTES + (" " + WEAK_NOTE if pid in WEAK_TRACKING else ""),
                    story=title, wav=wav, snr_db=None if clear else float(snr),
                    block=block, position_in_block=pos + 1, marker_sample=int(onset),
                    reference="CMS/DRL (as recorded)", external_sensors=MASTOIDS,
                    weak_tracking=pid in WEAK_TRACKING, **self._subject_info(pid), **babble,
                    validation_tier="low" if not clear and float(snr) <= LOW_TIER_MAX_SNR else "mlr",
                )
                yield TrialRecord(
                    subject=int(pid[2:]), session=1, trial=trial, condition="clear" if clear else "babble",
                    ns_type="eeg", stimulus=self._stimuli(title, snr),
                    neural_data_fn=self._eeg_loader(bdf, onset, _wav_duration(self._wav(title, "Inf")), description),
                )

    def _stimuli(self, title: str, snr: str) -> List[StimulusRecord]:
        clean = self._wav(title, "Inf")
        stims = [StimulusRecord("audio", title, _audio_loader(clean), is_attended=True, feature_name="audio")]
        if snr != "Inf":
            mix = self._wav(title, snr)
            if _wav_duration(mix) != _wav_duration(clean):
                raise ValueError(f"{mix}: length differs from the clean speech")
            stims += [StimulusRecord("audio", f"{title}_L{snr}", _audio_loader(mix), feature_name="audio"),
                      StimulusRecord("audio", f"{title}_L{snr}_babble", _babble_loader(mix, clean),
                                     feature_name="audio")]
        return stims

    def _wav(self, title: str, snr: str) -> str:
        return os.path.join(self.root, "stories", f"{title}_sil_L{snr}.wav")

    def _subject_info(self, pid: str) -> dict:
        d, a = self.demographics[pid], self.audiometry[pid]
        pta = np.mean([float(a[f"{ear}E: {f} Hz"]) for ear in "RL" for f in PTA_HZ])
        return {"participant": pid, "age_group": {"YA": "younger", "OA": "older"}[d["Age Group"]],
                "age": int(d["Age"]), "sex": d["Gender"], "pta_db_hl": round(float(pta), 2)}

    def _eeg_loader(self, bdf: str, onset: int, duration: float, description: str) -> Callable[[], BaseRaw]:
        def _loader() -> BaseRaw:
            raw = mne.io.read_raw_bdf(bdf, preload=False, verbose="ERROR")
            raw.drop_channels(["Status"])
            start = onset / raw.info["sfreq"]
            raw.crop(start, start + duration, include_tmax=False).load_data(verbose="ERROR")
            raw.set_channel_types({c: "misc" for c in MASTOIDS}, verbose="ERROR")
            raw.set_montage(make_standard_montage("standard_1020"))
            raw.info["description"] = description
            return raw
        return _loader


def _marker_onsets(bdf: str) -> np.ndarray:
    """Samples of the 254 -> 255 rising edges of the Status low byte (bit 16 at file start is masked out)."""
    raw = mne.io.read_raw_bdf(bdf, preload=False, verbose="ERROR")
    status = raw.get_data(picks=["Status"])[0].astype(np.int64) & 0xFF
    return np.flatnonzero((status[:-1] == MARKER_BASE) & (status[1:] == MARKER_ON)) + 1


def _wav_duration(path: str) -> float:
    fs, x = wavfile.read(path, mmap=True)
    return len(x) / fs


def _read_wav(path: str) -> np.ndarray:
    fs, x = wavfile.read(path)
    if fs != AUDIO_FS or x.dtype != np.int16 or x.ndim != 1:
        raise ValueError(f"{path}: expected 44.1 kHz mono int16")
    return x / 32768.0


def _audio_loader(path: str) -> Callable[[], dict]:
    return lambda: {"fs": AUDIO_FS, "data": _read_wav(path).astype(np.float32)[None, :]}


def _babble_loader(mix_path: str, clean_path: str) -> Callable[[], dict]:
    def _loader() -> dict:
        mix, clean = _read_wav(mix_path), _read_wav(clean_path)
        babble = mix - np.dot(mix, clean) / np.dot(clean, clean) * clean
        return {"fs": AUDIO_FS, "data": babble.astype(np.float32)[None, :]}
    return _loader


def _table(path: str, id_column: str) -> dict:
    """Spreadsheet rows keyed by participant (naNN); headers stripped (audiometry has trailing spaces)."""
    rows = pd.read_excel(path).rename(columns=str.strip).dropna(subset=[id_column]).to_dict("records")
    return {r[id_column][:4]: r for r in rows}


ADAPTOR = Herrmann2025Adaptor
