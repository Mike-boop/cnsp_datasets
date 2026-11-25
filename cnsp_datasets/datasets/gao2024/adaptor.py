from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Callable, Iterable

import mne
import numpy as np
import scipy.io as sio

from cnsp_datasets.standardise.adaptor import BaseAdaptor
from cnsp_datasets.standardise.clock import crop_on_audio_clock
from cnsp_datasets.standardise.iohelpers import audio_loader, mark_bads
from cnsp_datasets.standardise.provenance import provenance
from cnsp_datasets.standardise.trial_record import StimulusRecord, TrialRecord

FS = 100
AUDIO_FS = 48000
LINE_FREQ = 50.0
N_CHUNKS = 27  # per segment file: story chunks (3s-2..3s)-(1..9)
REFERENCE = "not applicable (MEG)"
DRIFT_PPM = 490  # trigger duration - wav = 2.5 ms + 490 ppm x length, 3888 chunks (notes.md, section 7)
# order_sub[s] = condition of segment s (notes.md, section 3)
CONDITIONS = {
    1: {1: "exp1-anechoic", 2: "exp1-echo125", 3: "exp1-echo250"},
    2: {1: "exp2-anechoic", 2: "exp2-echo125-6dB", 3: "exp2-echo250-6dB"},
    3: {1: "exp3-echo-attend", 2: "exp3-echo-movie", 3: "exp3-vocoded-echo-movie"},
}
# (experiment, condition) -> [(stimulus name prefix, wav path pattern)]: played sound, then direct sound and echo.
# Identical wavs share one name (exp1/2/3 clean, exp1/2 delays; md5-checked, notes.md section 3).
E12 = {1: "exp1_stimuli/new/{}", 2: "exp2_stimuli/Fir_half_Sti/{}"}
STIMULI = {
    **{(e, 1): [("clean", E12[1].format("{}-clean-1"))] for e in (1, 2)},
    **{(e, c): [(f"echo{d}" + ("-6dB" if e == 2 else ""), E12[e].format(f"{{}}-echo-{c}")),
                ("clean", E12[1].format("{}-clean-1")), (f"delay{d}", E12[1].format(f"{{}}-delay-{c}"))]
       for e in (1, 2) for c, d in ((2, 125), (3, 250))},
    **{(3, c): [("varecho", "exp3_stimuli/new/{}-echo"), ("clean", E12[1].format("{}-clean-1")),
                ("vardelay", "exp3_stimuli/new/{}-delay")] for c in (1, 2)},
    (3, 3): [(f"vocoded-{k}", f"exp3_stimuli/vocode/{{}}-{f}") for k, f in
             (("varecho", "echo"), ("clean", "clean"), ("vardelay", "delay"))],
}
TRIGGER_TYPE = ("unknown (onset/offset trigger per chunk, not documented; chunk start = the authors' start trigger, "
                "durations consistent to 1 ms across chunks)")
NOTES = ("Authors' preprocessed MEG (tSSS, downsampled to 100 Hz; paper Methods) as shipped, cut by the authors "
         "into story chunks of wav length starting at the chunk's start trigger; the gaps between chunks (0.2-5 s) "
         "are not shipped. Trigger-derived chunk durations exceed the wavs by 2.5 ms + 490 ppm x length "
         "(residual SD 1 ms): the MEG is resampled onto the audio clock (drift_correction=False keeps it as "
         "shipped); sw_trigger because onsets and drift come from the triggers, whose source is unknown. Channel "
         "names in Neuromag order (magnetometer first in each triplet, as the authors' code); the gradiometer order "
         "within a pair and sensor positions are not shipped. EOG (one channel, direction unknown) from the "
         "authors' continuous EOG trace, aligned within 1 sample. The played sound is the attended (first) "
         "stimulus, its direct-sound and echo components follow.")


class Gao2024Adaptor(BaseAdaptor):
    """
    Gao et al. 2024 (PLoS Biol, Zenodo 10472483): MEGIN TRIUX neo MEG at 100 Hz (authors' tSSS), a Chinese story
    with or without an echo in 3 experiments, one ~13 min segment per condition. One trial per story chunk
    (27 per segment); subject = 100 x experiment + subject number. See notes.md.
    """

    def __init__(self, download_dir: str, drift_correction: bool = True):
        super().__init__(download_dir)
        self.root = download_dir
        self.drift = DRIFT_PPM * 1e-6 if self.choice("drift_correction", drift_correction, (True, False)) else 0.0

    def parse(self) -> Iterable[TrialRecord]:
        stim_root = self._find_one("**/Experiment_Stimuli")
        names, types = _channels()
        for exp in CONDITIONS:
            behave = self._find_one(f"**/exp{exp}_behave_result")
            paths = sorted(self.sorted_glob(self.root, f"**/exp{exp}_PreData_*/sub*_*.mat"), key=_sub_seg)
            if len({_sub_seg(p) for p in paths}) != len(paths):
                raise ValueError(f"experiment {exp}: a subject-segment file appears twice under {self.root}")
            for path in paths:
                sub, seg = _sub_seg(path)
                cond = int(_order(os.path.join(behave, f"sub_{sub}.mat"))[seg - 1])
                for i in range(N_CHUNKS):
                    chunk = f"{3 * seg - 2 + i // 9}-{i % 9 + 1}"
                    stimuli = [StimulusRecord("audio", f"{prefix}_{chunk}",
                                              audio_loader(os.path.join(stim_root, pattern.format(chunk) + ".wav"),
                                                           expect_fs=AUDIO_FS), is_attended=j == 0)
                               for j, (prefix, pattern) in enumerate(STIMULI[exp, cond])]
                    description = provenance(
                        "sw_trigger", TRIGGER_TYPE, NOTES, drift_ppm=DRIFT_PPM, validation_tier="low",
                        drift_corrected=bool(self.drift),
                        experiment=exp, participant=f"sub{sub}", segment=seg, chunk=chunk, chunk_index=i + 1,
                        direct_gain=0.5 if exp == 2 and cond > 1 else 1.0,
                        task="movie" if exp == 3 and cond > 1 else "listen",
                        units_as_shipped="T, T/m (MEG), V (EOG)", reference=REFERENCE)
                    yield TrialRecord(
                        subject=100 * exp + sub, session=1, trial=(seg - 1) * N_CHUNKS + i + 1,
                        condition=CONDITIONS[exp][cond], ns_type="meg", stimulus=stimuli,
                        neural_data_fn=_meg_loader(path, i, names, types, self.drift, description))

    def _find_one(self, pattern: str) -> str:
        """The single match of a glob under the download."""
        hits = self.sorted_glob(self.root, pattern)
        if len(hits) != 1:
            raise FileNotFoundError(f"expected one match for {pattern} under {self.root}, found {hits}")
        return hits[0]


def _sub_seg(path: str) -> tuple[int, int]:
    """(subject, segment) from `sub<n>_<segment>.mat`."""
    return tuple(map(int, re.fullmatch(r"sub(\d+)_(\d)\.mat", os.path.basename(path)).groups()))


@lru_cache(maxsize=None)
def _order(path: str) -> np.ndarray:
    """`order_sub` of one subject: the condition of segments 1-3."""
    return sio.loadmat(path)["order_sub"].ravel()


def _channels() -> tuple[list[str], list[str]]:
    """Neuromag names in sorted order (MEG0111 mag, MEG0112, MEG0113 grad, MEG0121, ...) and their types."""
    names = sorted(n.replace(" ", "") for n in mne.channels.read_layout("Vectorview-all").names)
    return names, ["mag" if n.endswith("1") else "grad" for n in names]


@lru_cache(maxsize=1)
def _read(path: str) -> dict:
    """One subject-segment mat file (27 chunks, ~185 MB), kept for its consecutive trials."""
    return sio.loadmat(path)


def _meg_loader(path: str, i: int, names: list[str], types: list[str], drift: float,
                description: str) -> Callable[[], mne.io.BaseRaw]:
    """Chunk i (306 MEG + EOG if shipped) on the audio clock; zero-variance channels as bads."""
    def _loader() -> mne.io.BaseRaw:
        d = _read(path)
        data = np.array(d["sig_meg_sum"].ravel()[i].T)  # a copy, not a view into the cache
        ch_names, ch_types = names, types
        if "sig_eog" in d:
            start = round(d["st"].ravel()[i] / 1000 * FS)
            eog = d["sig_eog"][:, start:start + data.shape[1]]
            if eog.shape[1] != data.shape[1]:
                raise ValueError(f"{path} chunk {i + 1}: EOG ends before the chunk")
            data, ch_names, ch_types = np.vstack([data, eog]), ch_names + ["EOG"], ch_types + ["eog"]
        info = mne.create_info(ch_names, FS, ch_types)  # mag coil 3024, grad 3012 (Vectorview/TRIUX)
        with info._unlock():
            info["line_freq"] = LINE_FREQ
        raw = mne.io.RawArray(data, info, verbose="ERROR")
        mark_bads(raw, [n for n, s in zip(ch_names, data.std(1)) if s == 0])
        if drift:
            raw = crop_on_audio_clock(raw, 0, raw.n_times, drift)
        raw.info["description"] = description
        return raw

    return _loader


ADAPTOR = Gao2024Adaptor
