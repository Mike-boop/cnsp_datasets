"""
Classifier variants: sample rate, channel layout (montage and reference) and frequency band, and the
preprocessing that prepares any dataset for a given variant.

A ClassifierSpec is saved with the model weights (save_classifier), so a checkpoint carries everything needed to
prepare new data for it:

    model, spec, checkpoint = load_classifier("fs1024_1020-26_broadband.pt")
    session = SessionDataset(record, **spec.session_kwargs())                  # EEG on the model's channels
    session = SessionDataset(record, **spec.session_kwargs(mastoids=(None, "A2")))  # Cz-mastoids, bentum

Montages:
- "1020-64", "1020-32": the BioSemi 64 / 32 channel sets at standard 10-20 positions
- "1020-26": the 26 scalp channels of bentum2023
- "Cz-mastoids": Cz referenced to the linked mastoids (one channel)
The 10-20 montages are interpolated (spherical splines) from each recording's good EEG channels and re-referenced
to their average, so recordings with different caps and references end up comparable.

Reference (10-20 montages): "average" (default, over the montage's channels) or "linked-mastoids" (each channel minus
the mean of the two mastoids, before interpolation; needs the recording's mastoid channels). Average reference over a
cap that only covers the upper head removes most of the far-field brainstem response, which is near-uniform there;
linked mastoids keeps it.

Bands:
- "broadband": EEG high-passed at 0.5 Hz
- "hf": EEG and stimulus feature high-passed at hp_cutoff (default min(0.25 fs, 80) Hz), 50 Hz harmonics notched in
  the EEG

Stimulus feature: "envelope" (Hilbert envelope, default) or "rectified" (half-wave rectified waveform, anti-aliased to
fs), which keeps the waveform's fine timing for brainstem responses.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import mne
import numpy as np
import torch
from mne.io import BaseRaw
from scipy.signal import butter, sosfiltfilt

from cnsp_datasets.align.classifiers import SimilarityDetector
from cnsp_datasets.align.montage import InterpolateToMontage, montage_interpolation_matrix, pick_montage
from cnsp_datasets.preprocess.base import NeuralPreprocStep, StimulusPreprocStep, StimulusData, get_stim_array
from cnsp_datasets.preprocess.neural import MNERawMethod, ResampleNeural
from cnsp_datasets.preprocess.stimulus import HalfWaveRectify, HilbertEnvelope, ResampleStimulus


MONTAGES = {
    "1020-64": mne.channels.make_standard_montage("biosemi64").ch_names,
    "1020-32": mne.channels.make_standard_montage("biosemi32").ch_names,
    "1020-26": ["Fz", "F3", "F7", "FC5", "FC1", "C3", "T7", "CP5", "CP1", "Pz", "P3", "P7", "O1",
                "O2", "P4", "P8", "CP6", "CP2", "Cz", "C4", "T8", "FC6", "FC2", "F4", "F8", "Fp2"],
    "Cz-mastoids": ["Cz"],
}
BANDS = ("broadband", "hf")
REFERENCES = ("average", "linked-mastoids")
STIMULI = ("envelope", "rectified")
BROADBAND_L_FREQ = 0.5


# ------------------------------------------------------------------------------------------------------------
# Preprocessing steps used by the specs
# ------------------------------------------------------------------------------------------------------------

class HighPassStimulus(StimulusPreprocStep):
    """Zero-phase Butterworth high-pass of a stimulus feature (e.g. the envelope for high-frequency classifiers)."""

    def __init__(self, l_freq: float, order: int = 4):
        self.l_freq = l_freq
        self.order = order

    def run(self, data: StimulusData) -> StimulusData:
        sos = butter(self.order, self.l_freq, btype="highpass", fs=data["fs"], output="sos")
        return {"fs": data["fs"], "data": sosfiltfilt(sos, get_stim_array(data), axis=-1)}

    def __repr__(self) -> str:
        return f"HighPassStimulus(l_freq={self.l_freq:g})"


def _mastoid_reference(raw: BaseRaw, mastoids: tuple[str | None, str | None]) -> np.ndarray:
    """Mean of the two mastoid signals; a mastoid given as None is the recording reference (zero)."""
    if len(mastoids) != 2 or tuple(mastoids) == (None, None):
        raise ValueError("mastoids must name the left and right mastoid channels (at most one None)")
    refs = []
    for m in mastoids:
        if m is None:
            refs.append(0.0)
        elif m not in raw.ch_names or m in raw.info["bads"]:
            raise ValueError(f"Mastoid channel {m!r} is missing or bad")
        else:
            refs.append(raw.get_data(picks=[m])[0])
    return (refs[0] + refs[1]) / 2


class LinkedMastoidsReference(NeuralPreprocStep):
    """
    Re-references the EEG channels to the linked mastoids: each EEG-typed channel minus the mean of the two mastoids.
    mastoids names the left and right mastoid channels (any type, e.g. misc); None means that mastoid is the
    recording's reference (e.g. bentum2023: (None, "A2")). The mastoid channels themselves are left as they are.
    """

    def __init__(self, mastoids: tuple[str | None, str | None] = ("A1", "A2")):
        self.mastoids = tuple(mastoids)

    def run(self, raw: BaseRaw) -> BaseRaw:
        raw = raw.copy().load_data(verbose="ERROR")
        ref = _mastoid_reference(raw, self.mastoids)
        picks = mne.pick_types(raw.info, eeg=True, exclude=[])
        raw._data[picks] -= ref
        return raw

    def __repr__(self) -> str:
        return f"LinkedMastoidsReference(mastoids={self.mastoids})"


class CzLinkedMastoids(NeuralPreprocStep):
    """
    One channel: Cz minus the mean of the two mastoids.

    mastoids names the left and right mastoid channels (any type, e.g. misc); None means that mastoid is the
    recording's reference, so it is zero in the data (e.g. bentum2023: (None, "A2"), left-mastoid reference).
    A bad or missing Cz is interpolated from the good EEG channels; the mastoids must be present and good.
    """

    def __init__(self, mastoids: tuple[str | None, str | None] = ("A1", "A2"), alpha: float = 1e-5):
        if len(mastoids) != 2 or mastoids == (None, None):
            raise ValueError("mastoids must name the left and right mastoid channels (at most one None)")
        self.mastoids = tuple(mastoids)
        self.alpha = alpha

    def run(self, raw: BaseRaw) -> BaseRaw:
        raw = raw.copy().load_data(verbose="ERROR")
        ref = _mastoid_reference(raw, self.mastoids)
        if "Cz" in raw.ch_names and "Cz" not in raw.info["bads"]:
            cz = raw.get_data(picks=["Cz"])[0]
        else:
            good = raw.copy().pick("eeg", exclude="bads")
            target = pick_montage(mne.channels.make_standard_montage("standard_1020"), ["Cz"])
            matrix, _ = montage_interpolation_matrix(good.info, target, alpha=self.alpha)
            cz = (matrix @ good.get_data())[0]
        out = mne.io.RawArray((cz - ref)[None], mne.create_info(["Cz"], raw.info["sfreq"], "eeg"),
                              verbose="ERROR")
        out.set_meas_date(raw.info["meas_date"])
        out.set_annotations(raw.annotations)
        return out

    def __repr__(self) -> str:
        return f"CzLinkedMastoids(mastoids={self.mastoids})"


# ------------------------------------------------------------------------------------------------------------
# Specs
# ------------------------------------------------------------------------------------------------------------

def _default_n_layers(fs: int, band: str, segment_length: float) -> int:
    """3 for hf; for broadband, the most layers whose receptive field (kernel 3) stays within ~15% of a segment."""
    if band == "hf":
        return 3
    n = 1
    while n < 6 and 3 ** (n + 1) <= 0.15 * segment_length * fs:
        n += 1
    return n


@dataclass(frozen=True)
class ClassifierSpec:
    fs: int = 1024
    montage: str = "1020-26"
    band: str = "broadband"
    n_layers: int | None = None          # default: see _default_n_layers
    interp_alpha: float = 1e-5
    line_freq: float = 50.0
    segment_length: float = 5.0
    mismatch_offset: float = 6.0
    extra_model_kwargs: dict = field(default_factory=dict)
    reference: str = "average"           # "average" or "linked-mastoids"; Cz-mastoids is always linked mastoids
    stimulus: str = "envelope"           # "envelope" or "rectified"
    hp_cutoff: float | None = None       # hf band: high-pass cutoff in Hz (default min(fs/4, 80))

    def __post_init__(self):
        if self.montage not in MONTAGES:
            raise ValueError(f"Unknown montage {self.montage!r}; choose from {list(MONTAGES)}")
        if self.band not in BANDS:
            raise ValueError(f"Unknown band {self.band!r}; choose from {BANDS}")
        if self.montage == "Cz-mastoids":
            object.__setattr__(self, "reference", "linked-mastoids")
        if self.reference not in REFERENCES:
            raise ValueError(f"Unknown reference {self.reference!r}; choose from {REFERENCES}")
        if self.stimulus not in STIMULI:
            raise ValueError(f"Unknown stimulus {self.stimulus!r}; choose from {STIMULI}")
        if self.hp_cutoff is not None and self.band != "hf":
            raise ValueError("hp_cutoff only applies to the hf band")
        if self.n_layers is None:
            object.__setattr__(self, "n_layers", _default_n_layers(self.fs, self.band, self.segment_length))

    # --- description ---

    @property
    def name(self) -> str:
        montage = self.montage + ("-lm" if self.reference == "linked-mastoids" and self.montage != "Cz-mastoids" else "")
        band = f"hp{self.hp_cutoff:g}" if self.hp_cutoff is not None else self.band
        return f"fs{self.fs}_{montage}_{band}" + ("_rect" if self.stimulus == "rectified" else "")

    @property
    def ch_names(self) -> list[str]:
        return list(MONTAGES[self.montage])

    @property
    def needs_mastoids(self) -> bool:
        return self.reference == "linked-mastoids"

    @property
    def l_freq(self) -> float:
        if self.band == "broadband":
            return BROADBAND_L_FREQ
        return self.hp_cutoff if self.hp_cutoff is not None else min(0.25 * self.fs, 80.0)

    @property
    def dig_montage(self):
        return pick_montage(mne.channels.make_standard_montage("standard_1020"), self.ch_names)

    @property
    def model_kwargs(self) -> dict:
        return {"n_eeg_channels": len(self.ch_names), "n_stimfeat_channels": 1, "n_layers": self.n_layers,
                **self.extra_model_kwargs}

    @property
    def receptive_field_s(self) -> float:
        return (1 + 2 * sum(3 ** i for i in range(self.n_layers))) / self.fs

    # --- preprocessing ---

    def eeg_steps(self, mastoids: tuple[str | None, str | None] | None = None) -> list:
        """
        Preprocessing from a recording's Raw to the model's input channels. With linked mastoids (and for
        "Cz-mastoids"), `mastoids` names the recording's mastoid channels (see LinkedMastoidsReference); the 10-20
        montages are interpolated from its good EEG channels.
        """
        steps = []
        if self.needs_mastoids and mastoids is None:
            raise ValueError(f"{self.name} uses a linked-mastoid reference: give the recording's mastoid channels (mastoids=...)")
        if self.montage == "Cz-mastoids":
            steps.append(CzLinkedMastoids(mastoids, alpha=self.interp_alpha))
        elif self.reference == "linked-mastoids":
            steps.append(LinkedMastoidsReference(mastoids))
        steps += [
            MNERawMethod("filter", l_freq=self.l_freq, h_freq=None, picks="eeg", verbose="ERROR"),
            ResampleNeural(self.fs),
        ]
        notch = [f for f in np.arange(self.line_freq, self.fs / 2, self.line_freq) if f >= self.l_freq]
        if self.band == "hf" and notch:
            steps.append(MNERawMethod("notch_filter", freqs=notch, picks="eeg", verbose="ERROR"))
        if self.montage != "Cz-mastoids":
            steps.append(InterpolateToMontage(self.dig_montage, alpha=self.interp_alpha,
                                              average_reference=self.reference == "average"))
        return steps

    def stim_steps(self) -> list:
        first = HalfWaveRectify() if self.stimulus == "rectified" else HilbertEnvelope()
        steps = [first, ResampleStimulus(self.fs)]
        if self.band == "hf":
            steps.append(HighPassStimulus(self.l_freq))
        return steps

    def session_kwargs(self, mastoids: tuple[str | None, str | None] | None = None, **overrides) -> dict:
        """Keyword arguments for SessionDataset / load_sessions that prepare a recording for this classifier."""
        kwargs = dict(
            fs=self.fs,
            eeg_steps=self.eeg_steps(mastoids),
            stim_steps=self.stim_steps(),
            # linked mastoids needs the (often misc-typed) mastoid channels, so nothing is dropped before its first step
            picks=None if self.needs_mastoids else "eeg",
            segment_length=self.segment_length,
            mismatch_offset=self.mismatch_offset,
        )
        return {**kwargs, **overrides}

    # --- (de)serialisation ---

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(name=self.name, ch_names=self.ch_names, l_freq=self.l_freq, receptive_field_s=self.receptive_field_s)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ClassifierSpec":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


def save_classifier(path: str | Path, model: SimilarityDetector, spec: ClassifierSpec, **info) -> Path:
    """Save weights with the spec (sample rate, channels, reference, band, model kwargs) and any extra info."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
        "spec": spec.to_dict(),
        "model_kwargs": spec.model_kwargs,
        "fs": spec.fs,
        "ch_names": spec.ch_names,
        "reference": spec.reference,
        "band": spec.band,
        "l_freq": spec.l_freq,
        **info,
    }, path)
    return path


def load_classifier(path: str | Path, device: str = "cpu") -> tuple[SimilarityDetector, ClassifierSpec, dict]:
    """(model in eval mode, its ClassifierSpec, the full checkpoint dict)."""
    checkpoint = torch.load(path, weights_only=False, map_location="cpu")
    spec = ClassifierSpec.from_dict(checkpoint["spec"])
    model = SimilarityDetector(**checkpoint["model_kwargs"])
    model.load_state_dict(checkpoint["state_dict"])
    return model.to(device).eval(), spec, checkpoint


def choose_spec(
        specs: list[ClassifierSpec],
        fs: float,
        ch_names: list[str],
        band: str | None = None,
        fs_tolerance: float = 0.05,
        min_coverage: float = 0.9,
        ) -> ClassifierSpec:
    """
    The most appropriate classifier for a recording at `fs` with EEG channels `ch_names`:
    - sample rate: the highest model rate the recording supports (up to fs_tolerance above its own rate, so
      1000 Hz data can use a 1024 Hz model);
    - montage: the largest 10-20 montage whose channels the recording (mostly, min_coverage) has, so interpolation
      fills gaps rather than inventing whole regions; Cz-mastoids only if no 10-20 montage qualifies.
    """
    candidates = [s for s in specs if (band is None or s.band == band) and s.fs <= fs * (1 + fs_tolerance)]
    if not candidates:
        raise ValueError(f"No classifier at or below {fs:g} Hz" + (f" for band {band!r}" if band else ""))
    best_fs = max(s.fs for s in candidates)
    candidates = [s for s in candidates if s.fs == best_fs]

    def coverage(s):
        return np.mean([ch in ch_names for ch in s.ch_names])

    tenten = [s for s in candidates if s.montage != "Cz-mastoids" and coverage(s) >= min_coverage]
    if tenten:
        return max(tenten, key=lambda s: (len(s.ch_names), coverage(s)))
    fallback = [s for s in candidates if s.montage == "Cz-mastoids"]
    if fallback:
        return fallback[0]
    raise ValueError(f"No classifier montage covers these channels: {ch_names}")
