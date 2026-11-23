from __future__ import annotations

import os
from functools import lru_cache
from typing import Callable, Iterable

import numpy as np
from mne import create_info
from mne.channels import make_standard_montage
from mne.io import BaseRaw, RawArray
from pymatreader import read_mat

from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 64
FEATURE = "envelope"  # the authors' 64 Hz envelope of the degraded audio as played (no audio shared)
ROOT = os.path.join("spectrotemporalModulationsEEG", "dataCND")
MONTAGE = "biosemi64"  # channel names not shipped; BioSemi default order assumed (notes section 5)
MASTOIDS = ["M1", "M2"]  # extChan columns; left/right assumed
BADS = {3: ["P2"]}  # electrical noise only (aliased mains), notes section 5
TRIGGER = "software (Presentation via parallel port, recorded by the amplifier; paper). Triggers not shared"
NOTES = ("CND release: EEG downsampled by the authors from 1024 to 64 Hz, otherwise raw (CMS/DRL, no reference, "
         "no filtering), microvolts scaled to V. Trials cut by the authors from the onset trigger; the EEG runs "
         "0.5 s past the stimulus end. Stimulus = authors' 64 Hz envelope of the degraded audio as played; "
         "channel names and mastoid sides inferred (BioSemi 64 order).")


class CalderonDePalma2023Adaptor:
    """
    Calderon De Palma et al. 2023 (OSF gx6rm, CND): 13 subjects x 25 audiobook snippets (~3 min), each in one of
    five conditions (Clean, Temporal60/80, Spectral60/80 modulation low-pass). 64 BioSemi channels + mastoids at
    64 Hz. Stimulus `s<kk>_<condition>` = the authors' envelope of snippet kk in that condition, starting at trial
    sample 0. Trial number = presentation position. See notes.md.
    """

    def __init__(self, download_dir: str):
        self.root = os.path.join(download_dir, ROOT)
        self.subjects = [s for s in range(1, 30) if os.path.exists(self._path("Sub", s))]

    def parse(self) -> Iterable[TrialRecord]:
        sources = self._stimulus_sources()
        for sub in self.subjects:
            stim = _read_stim(self._path("Stim", sub))
            eeg = _read_eeg(self._path("Sub", sub))
            if eeg["fs"] != FS:
                raise ValueError(f"subject {sub}: EEG at {eeg['fs']} Hz, expected {FS}")
            order = np.asarray(eeg["origTrialPosition"])
            if sorted(order) != list(range(1, len(order) + 1)):
                raise ValueError(f"subject {sub}: origTrialPosition is not a permutation")
            for idx, name in enumerate(_names(stim)):
                source, env = sources[name]
                description = provenance(
                    "sw_trigger", TRIGGER, NOTES, validation_tier="low", snippet=int(stim["stimIdxs"][idx]),
                    temporal_cutoff_hz=float(stim["addinfo"]["Hz"][idx]),
                    spectral_cutoff_cyc_per_khz=float(stim["addinfo"]["scale"][idx]),
                    stimulus_source_subject=source, shipped_trial_index=idx,
                    channel_names="inferred (biosemi64 order)",
                )
                yield TrialRecord(
                    subject=sub, session=1, trial=int(order[idx]), condition=name.split("_", 1)[1], ns_type="eeg",
                    stimulus=StimulusRecord("audio", name, _env_loader(env), is_attended=True, feature_name=FEATURE),
                    neural_data_fn=self._eeg_loader(sub, idx, description),
                )

    def _path(self, kind: str, sub: int) -> str:
        return os.path.join(self.root, f"data{kind}{sub}.mat")

    def _stimulus_sources(self) -> dict[str, tuple[int, np.ndarray]]:
        """
        Stimulus name -> (subject, envelope) of its first occurrence. The other subjects' copies must match it up to
        an affine scale (same length, r >= 0.9999).
        """
        sources = {}
        for sub in self.subjects:
            stim = _read_stim(self._path("Stim", sub))
            if stim["fs"] != FS:
                raise ValueError(f"subject {sub}: stimuli at {stim['fs']} Hz, expected {FS}")
            for idx, name in enumerate(_names(stim)):
                env = np.asarray(stim["data"][0][idx], dtype=np.float32)
                if name not in sources:
                    sources[name] = (sub, env)
                elif len(env) != len(sources[name][1]) or np.corrcoef(env, sources[name][1])[0, 1] < 0.9999:
                    raise ValueError(f"subject {sub}: envelope of {name} differs from subject {sources[name][0]}")
        return sources

    def _eeg_loader(self, sub: int, idx: int, description: str) -> Callable[[], BaseRaw]:
        """Loader of one trial: 64 EEG channels + mastoids at 64 Hz in V, without reference."""
        path = self._path("Sub", sub)

        def _loader() -> BaseRaw:
            eeg = _read_eeg(path)
            data = np.concatenate([eeg["data"][idx], eeg["extChan"]["data"][idx]], axis=1).T
            montage = make_standard_montage(MONTAGE)
            types = ["eeg"] * len(montage.ch_names) + ["misc"] * len(MASTOIDS)
            info = create_info(montage.ch_names + MASTOIDS, float(FS), types)
            raw = RawArray(1e-6 * data, info, verbose="ERROR")  # shipped in µV
            raw.set_montage(montage)  # template positions
            raw.info["bads"] = list(BADS.get(sub, []))
            raw.info["description"] = description
            return raw
        return _loader


def _names(stim: dict) -> list[str]:
    """Stimulus names `s<kk>_<condition>` of a subject's trials, in shipped order."""
    return [f"s{int(k):02d}_{stim['condNames'][c - 1]}" for k, c in zip(stim["stimIdxs"], stim["condIdxs"])]


def _env_loader(env: np.ndarray) -> Callable[[], dict]:
    return lambda: {"fs": FS, "data": env[None, :]}


@lru_cache(maxsize=1)
def _read_stim(path: str) -> dict:
    return read_mat(path)["stim"]


@lru_cache(maxsize=1)
def _read_eeg(path: str) -> dict:
    return read_mat(path)["eeg"]


ADAPTOR = CalderonDePalma2023Adaptor
