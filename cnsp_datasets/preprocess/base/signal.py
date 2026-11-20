from abc import abstractmethod
from fractions import Fraction

import numpy as np
from scipy.signal import resample_poly as scipy_resample_poly

from cnsp_datasets.preprocess.base.classes import PreprocStep


class Resample(PreprocStep):
    """
    Shared base for resampling steps.

    Computes exact up/down rational factors (also for non-integer rates such as TDT's 24414.0625 Hz) and
    applies scipy's resample_poly along the last axis. Subclasses implement run() to unpack the current fs
    and array, call _resample_array(), and return the appropriate output type.
    """

    def __init__(self, target_fs: int):
        self.target_fs = int(target_fs)

    def _resample_array(self, data: np.ndarray, current_fs: float) -> np.ndarray:
        if current_fs == self.target_fs:
            return data
        ratio = Fraction(self.target_fs) / Fraction(float(current_fs)).limit_denominator(10 ** 6)  # numpy ints too
        return scipy_resample_poly(data, ratio.numerator, ratio.denominator, axis=-1)

    @abstractmethod
    def run(self, data):
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(target_fs={self.target_fs})"
