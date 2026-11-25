from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Callable, Iterable

import h5py
import numpy as np
from mne import create_info
from mne.io import BaseRaw, RawArray
from pymatreader import read_mat

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.iohelpers import array_loader, mark_bads
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

STIM_FS = 125
FEATURE = "envelope"  # the authors' 125 Hz Hilbert envelope of the wav (no audio shared)
ROOT = "dataCND"
MASTOIDS = ("M1", "M2")
BADS = {4: ["C4", "P3", "O2"]}  # flat in every trial (notes section 5)
TRIGGER = "software (Presentation -> Smarting; paper, route unknown). Triggers not shared"
NOTES = ("CND release: raw Smarting EEG epochs (no filter, no re-reference; reference not documented, Smarting "
         "default FCz) at 250 or 500 Hz, microvolts scaled to V. Epochs cut by the authors at the onset trigger; "
         "each runs to the next piece's onset (the last one to the end of the recording). Stimuli = authors' 125 Hz "
         "Hilbert envelopes of the wav as played and, for two-voice variants, of each voice. Drift not measurable.")


class Winchester2026Adaptor(BaseAdaptor):
    """
    Winchester et al. 2026 (OSF bjdh6, CND): 31 subjects x 32 MIDI-synthesised piano pieces, each in one of six
    variants (Original, Inverted, or one voice alone: <Original|Inverted>_Mono_<Left|Right>). 24 Smarting
    channels (incl. mastoids) at 250 or 500 Hz. Stimulus `<variant>_<kk>` = the authors' envelope of piece kk in
    that variant, starting at trial sample 0; two-voice trials add both voices. Trial = presentation position.
    See notes.md.
    """

    def __init__(self, download_dir: str):
        super().__init__(download_dir)
        self.root = os.path.join(download_dir, ROOT)
        self.subjects = [s for s in range(1, 41) if os.path.exists(self._path("Sub", s))]

    def parse(self) -> Iterable[TrialRecord]:
        envelopes, played = self._envelopes()
        for sub in self.subjects:
            eeg = _read_eeg(self._path("Sub", sub))
            positions = set()
            for idx, audio in enumerate(_strings(eeg["audioNames"])):
                # sub25: empty 33rd trial; sub16: 1-sample last trial (recording ended; pymatreader squeezes it to 1-D)
                if not audio or np.ndim(eeg["data"][idx]) < 2:
                    continue
                variant, piece = _variant_piece(audio, idx)
                names = [_name(variant, piece)] + [_name(v, piece) for v in _voices(variant)]
                if names[0] != played[sub][idx]:
                    raise ValueError(f"subject {sub}: EEG trial {idx} is {names[0]}, stimulus file {played[sub][idx]}")
                position = int(eeg["origTrialPosition"][idx])
                if position < 1 or position in positions:
                    raise ValueError(f"subject {sub}: presentation position {position} invalid or repeated")
                positions.add(position)
                description = provenance(
                    "sw_trigger", TRIGGER, NOTES, validation_tier="low", piece=piece, variant=variant,
                    shipped_trial_index=idx, stimulus_samples=len(envelopes[names[0]]),
                )
                stimuli = [StimulusRecord("audio", n, array_loader(envelopes[n], STIM_FS), is_attended=i == 0,
                                          feature_name=FEATURE) for i, n in enumerate(names)]
                yield TrialRecord(
                    subject=sub, session=1, trial=position, condition=variant, ns_type="eeg", stimulus=stimuli,
                    neural_data_fn=self._eeg_loader(sub, idx, description),
                )

    def _path(self, kind: str, sub: int) -> str:
        return os.path.join(self.root, f"data{kind}{sub}.mat")

    def _envelopes(self) -> tuple[dict[str, np.ndarray], dict[int, list[str]]]:
        """
        Stimulus name -> envelope (checked identical across subjects and between mono and two-voice trials), and
        subject -> name of the stimulus played in each shipped trial ('' for none), from the stimulus files.
        """
        envelopes, played = {}, {}
        for sub in self.subjects:
            with h5py.File(self._path("Stim", sub), "r") as f:  # read directly: cell {48 x trials} of v7.3
                stim = f["stim"]
                fs = stim["fs"][()].item()
                if fs != STIM_FS:
                    raise ValueError(f"subject {sub}: stimuli at {fs} Hz, expected {STIM_FS}")
                feature = {_h5str(f, r): i for i, r in enumerate(stim["names"][()].ravel())}
                variants = [_h5str(f, f[r][()].ravel()[0]) for r in stim["condNames"][()].ravel()]
                pieces = stim["stimIdxs"][()].ravel().astype(int)
                played[sub] = []
                for idx, cond in enumerate(stim["condIdxs"][()].ravel().astype(int)):
                    if cond == 0:
                        played[sub].append("")
                        continue  # sub25: empty 33rd trial
                    variant, piece = variants[cond - 1], int(pieces[idx])
                    played[sub].append(_name(variant, piece))
                    fields = {variant: "env"}
                    fields.update(zip(_voices(variant), ("env_left", "env_right")))
                    for v, field in fields.items():
                        env = f[stim["data"][idx, feature[field]]][()].ravel().astype(np.float32)
                        key = _name(v, piece)
                        if key not in envelopes:
                            envelopes[key] = env
                        elif not np.array_equal(env, envelopes[key]):
                            raise ValueError(f"subject {sub}: envelope {key} differs from an earlier copy")
        return envelopes, played

    def _eeg_loader(self, sub: int, idx: int, description: str) -> Callable[[], BaseRaw]:
        """Loader of one trial: 22 EEG channels + mastoids in V, original reference."""
        path = self._path("Sub", sub)

        def _loader() -> BaseRaw:
            eeg = _read_eeg(path)
            labels = _strings(eeg["chanlocs"]["labels"])
            types = ["misc" if ch in MASTOIDS else "eeg" for ch in labels]
            info = create_info(labels, float(eeg["fs"]), types)
            raw = RawArray(1e-6 * np.asarray(eeg["data"][idx]).T, info, verbose="ERROR")  # shipped in µV
            raw.set_montage("standard_1020")  # template positions
            mark_bads(raw, BADS.get(sub, []))
            raw.info["description"] = description
            return raw
        return _loader


def _strings(cells) -> list[str]:
    """MATLAB cellstr as a list of str; empty cells (sub25's extra trial) become ''."""
    return [c if isinstance(c, str) else "" for c in cells]


def _h5str(f: h5py.File, ref) -> str:
    """MATLAB char array behind an HDF5 object reference."""
    return "".join(map(chr, f[ref][()].ravel()))


def _variant_piece(audio: str, idx: int) -> tuple[str, int]:
    """`Original_Mono_Left7` -> ('Original_Mono_Left', 7); the piece must be the shipped index + 1."""
    variant, piece = re.fullmatch(r"(\D+)(\d+)", audio).groups()
    if int(piece) != idx + 1:
        raise ValueError(f"{audio} at index {idx}: piece is not index + 1")
    return variant, int(piece)


def _voices(variant: str) -> tuple[str, ...]:
    """The two single-voice variants making up a two-voice variant; none for a single voice."""
    return () if "_Mono_" in variant else (f"{variant}_Mono_Left", f"{variant}_Mono_Right")


def _name(variant: str, piece: int) -> str:
    """Stimulus name, e.g. `Original_Mono_Left_07`."""
    return f"{variant}_{piece:02d}"


@lru_cache(maxsize=1)
def _read_eeg(path: str) -> dict:
    """One subject's CND `eeg` struct; cached because trials of a subject are loaded one after another."""
    return read_mat(path)["eeg"]


ADAPTOR = Winchester2026Adaptor
