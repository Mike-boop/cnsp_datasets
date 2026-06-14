from abc import abstractmethod
from math import gcd

import numpy as np
from scipy.signal import resample_poly as scipy_resample_poly

from cnsp_datasets.preprocess2.base.classes import PreprocStep


class Resample(PreprocStep):
    """
    Shared base for resampling steps.

    Computes up/down rational factors via GCD and applies scipy's resample_poly
    along the last axis. Subclasses implement run() to unpack the current fs
    and array, call _resample_array(), and return the appropriate output type.
    """

    def __init__(self, target_fs: int):
        self.target_fs = int(target_fs)

    def _resample_array(self, data: np.ndarray, current_fs: int) -> np.ndarray:
        current_fs = int(current_fs)
        if current_fs == self.target_fs:
            return data
        divisor = gcd(current_fs, self.target_fs)
        up = self.target_fs // divisor
        down = current_fs // divisor
        return scipy_resample_poly(data, up, down, axis=-1)

    @abstractmethod
    def run(self, data):
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(target_fs={self.target_fs})"
