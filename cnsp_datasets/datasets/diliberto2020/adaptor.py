from __future__ import annotations

import os
from functools import lru_cache
from typing import Callable, Iterable

import numpy as np
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray
from pymatreader import read_mat
from scipy.io import wavfile

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

ROOT = "diliBach_4dryad_CND"
WAV = os.path.join("donders", "MusicData", "MusicEEG", "wav", "audio{:02d}.wav")  # registry `diliberto2020_audio`
AUDIO_FS = 44100
EEG_FS = 512
STIM_FS = 64
PAD = 512  # leading padding samples; the stimulus starts at EEG sample PAD + 1 (readme)
LSB = 31.25e-9  # shipped values are BioSemi ADC counts (notes section 5)
FEATURES = {0: "envelope", 1: "note_onsets", 2: "note_pitch"}  # rows of stim.data
RENAME = {"T7 (T3)": "T7", "T8 (T4)": "T8", "Iz (inion)": "Iz", "Afz": "AFz"}
MASTOIDS = ["M1", "M2"]  # extChan columns: left, right (readme)
BADS = {8: ["C4"], 12: ["Fpz"]}  # noise without EEG, notes section 5
TRIGGER = "unknown (Presentation; trigger route not documented, triggers not shared)"
NOTES = ("CND release: raw BioSemi EEG at 512 Hz (ADC counts scaled by 31.25 nV to V; CMS/DRL, no reference, no "
         "filter). Trials cut by the authors; onset = EEG sample 513 as documented, the leading 1 s padding is "
         "dropped and ~1 s of EEG after the stimulus kept. Presentation order not shipped: trial = shipped index. "
         "Drift not measurable.")
STIM_NOTES = {
    "audio": "Stimulus = the played wav (stereo, 44.1 kHz) from the Kern et al. 2022 Donders collection; its 64 Hz "
             "Hilbert envelope matches the shipped envelope (r >= 0.9995, lag 0, same length; notes section 4).",
    "envelope": "Stimulus = the authors' shipped 64 Hz envelope (Dryad).",
}
TIERS = {"audio": "mlr", "envelope": "low"}  # audio: MLR peaks 22-47 ms, brainstem nominal only; 64 Hz: low only


class DiLiberto2020Adaptor:
    """
    Di Liberto et al. 2020 (Dryad g1jwstqmh, CND): 20 subjects (1-10 non-musicians, 11-20 pianists) x 30 trials =
    10 MIDI-synthesised Bach piano pieces x 3 repetitions. 64 BioSemi channels + mastoids at 512 Hz. Stimulus
    `piece<kk>` starts at trial sample 0: `stimulus="audio"` (default) = the played wav from the Kern et al. 2022
    Donders collection (registry `diliberto2020_audio`), "envelope" = the authors' 64 Hz envelope (Dryad);
    `note_features=True` adds the shipped 64 Hz note-onset features. Trial = shipped index + 1 (presentation order
    not shipped). See notes.md.
    """

    def __init__(self, download_dir: str, stimulus: str = "audio", note_features: bool = False):
        if stimulus not in STIM_NOTES:
            raise ValueError(f"stimulus must be one of {sorted(STIM_NOTES)}")
        self.stimulus, self.wav = stimulus, os.path.join(download_dir, WAV)
        if stimulus == "audio" and not os.path.exists(self.wav.format(1)):
            raise FileNotFoundError(f"{self.wav.format(1)} missing: download registry entry diliberto2020_audio")
        self.root = os.path.join(download_dir, ROOT)
        rows = [0] if stimulus == "envelope" else []
        if note_features:
            rows += [1, 2]
        self.features = {row: FEATURES[row] for row in rows}
        self.subjects = [s for s in range(1, 21) if os.path.exists(self._path(f"Sub{s}"))]

    def parse(self) -> Iterable[TrialRecord]:
        stim = read_mat(self._path("Stim"))["stim"]
        if stim["fs"] != STIM_FS:
            raise ValueError(f"stimuli at {stim['fs']} Hz, expected {STIM_FS}")
        pieces = np.asarray(stim["stimIdxs"], int)
        reps = np.asarray(stim["repIdxs"], int)
        for sub in self.subjects:
            for idx, (piece, rep) in enumerate(zip(pieces, reps)):
                name, n_stim = f"piece{piece:02d}", len(stim["data"][0][idx])
                description = provenance(
                    "onset_only", TRIGGER, f"{NOTES} {STIM_NOTES[self.stimulus]}", validation_tier=TIERS[self.stimulus],
                    piece=int(piece), repetition=int(rep),
                    group="musician" if sub > 10 else "non-musician", shipped_trial_index=idx,
                    feature_samples_64hz=n_stim,
                )
                stimuli = [StimulusRecord("audio", name, _feature_loader(stim["data"][row][idx]), is_attended=True,
                                          feature_name=feature) for row, feature in self.features.items()]
                if self.stimulus == "audio":
                    loader = _wav_loader(self.wav.format(piece), n_stim)
                    stimuli.insert(0, StimulusRecord("audio", name, loader, is_attended=True, feature_name="audio"))
                yield TrialRecord(
                    subject=sub, session=1, trial=idx + 1, condition="listening", ns_type="eeg", stimulus=stimuli,
                    neural_data_fn=self._eeg_loader(sub, idx, n_stim, description),
                )

    def _path(self, kind: str) -> str:
        return os.path.join(self.root, f"data{kind}.mat")

    def _eeg_loader(self, sub: int, idx: int, stim_len: int, description: str) -> Callable[[], BaseRaw]:
        """
        Loader of one trial from the stimulus onset: 64 EEG channels + mastoids in V, original reference. Checks fs,
        padding and that the cropped EEG covers the stimulus (the only guard on the crop).
        """
        path = self._path(f"Sub{sub}")

        def _loader() -> BaseRaw:
            eeg = _read_eeg(path)
            if eeg["fs"] != EEG_FS or eeg["paddingStartSample"] != PAD:
                raise ValueError(f"subject {sub}: fs {eeg['fs']}, padding {eeg['paddingStartSample']}")
            data = np.concatenate([eeg["data"][idx], eeg["extChan"]["data"][idx]], axis=1)[PAD:].T
            if data.shape[1] < stim_len * EEG_FS // STIM_FS:
                raise ValueError(f"subject {sub}, trial {idx}: EEG shorter than the stimulus")
            labels = [RENAME.get(ch, ch) for ch in eeg["chanlocs"]["labels"]]
            info = create_info(labels + MASTOIDS, float(EEG_FS), ["eeg"] * len(labels) + ["misc"] * 2)
            raw = RawArray(LSB * data, info, verbose="ERROR")
            raw.set_montage(make_standard_montage("biosemi64"))  # template positions
            raw.info["bads"] = list(BADS.get(sub, []))
            raw.info["description"] = description
            return raw
        return _loader


def _feature_loader(x) -> Callable[[], dict]:
    """Loader of one 64 Hz feature as a 1 x n float32 array."""
    data = np.asarray(x, dtype=np.float32)[None, :]
    return lambda: {"fs": STIM_FS, "data": data}


def _wav_loader(path: str, n_stim: int) -> Callable[[], dict]:
    return lambda: {"fs": AUDIO_FS, "data": _read_wav(path, n_stim)}


@lru_cache(maxsize=10)
def _read_wav(path: str, n_stim: int) -> np.ndarray:
    """44.1 kHz stereo int16 wav as 2 x n float32 in +-1; checks ceil(n * 64 / fs) == n_stim (notes section 4)."""
    fs, x = wavfile.read(path)
    if fs != AUDIO_FS or x.dtype != np.int16 or x.ndim != 2:
        raise ValueError(f"{path}: expected 44.1 kHz stereo int16")
    if int(np.ceil(len(x) * STIM_FS / fs)) != n_stim:
        raise ValueError(f"{path}: length does not match the shipped {STIM_FS} Hz features")
    return (x.T / 32768.0).astype(np.float32)


@lru_cache(maxsize=1)
def _read_eeg(path: str) -> dict:
    """One subject's CND `eeg` struct; cached because a subject's trials are loaded one after another."""
    return read_mat(path)["eeg"]


ADAPTOR = DiLiberto2020Adaptor
