from abc import ABC, abstractmethod
from typing import Callable, Any

import numpy as np
from mne.io import BaseRaw


StimulusData = dict  # {"fs": int, "data": np.ndarray (channels, time)}


def get_stim_array(data: StimulusData) -> np.ndarray:
    """
    Return the signal array from a stimulus dict.

    "data" is the canonical key; "waveform" is accepted for files that were
    standardised before the key was unified.
    """
    for key in ("data", "waveform"):
        if key in data:
            return data[key]
    raise KeyError(f"Stimulus dict has no 'data' key (found keys: {sorted(data)})")


class PreprocStep(ABC):
    """
    Abstract base for a lazy preprocessing step.

    __call__(fn) wraps a zero-arg loader so that run() fires when data is
    actually accessed, not at pipeline construction time.

    Stimulus steps may set output_feature_name to rename the feature they
    produce (e.g. "audio" -> "envelope"); None keeps the current name.
    """

    output_feature_name: str | None = None

    def __call__(self, fn: Callable[[], Any]) -> Callable[[], Any]:
        def wrapped():
            return self.run(fn())
        return wrapped

    @abstractmethod
    def run(self, data: Any) -> Any:
        pass

    def __repr__(self) -> str:
        return self.__class__.__name__


class NeuralPreprocStep(PreprocStep, ABC):
    @abstractmethod
    def run(self, data: BaseRaw) -> BaseRaw:
        pass


class StimulusPreprocStep(PreprocStep, ABC):
    @abstractmethod
    def run(self, data: StimulusData) -> StimulusData:
        pass
