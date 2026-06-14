from abc import ABC, abstractmethod
from typing import Callable, Any

import numpy as np
from mne.io import BaseRaw


StimulusData = dict  # {"fs": int, "data": np.ndarray (channels, time)}


class PreprocStep(ABC):
    """
    Abstract base for a lazy preprocessing step.

    __call__(fn) wraps a zero-arg loader so that run() fires when data is
    actually accessed, not at pipeline construction time.
    """

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
