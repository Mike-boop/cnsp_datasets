import numpy as np
from mne.io import BaseRaw
from scipy.signal import sosfilt

from cnsp_datasets.preprocess2.base import NeuralPreprocStep


class SOSFilt(NeuralPreprocStep):
    """
    Applies a scipy SOS IIR filter channel-wise to an MNE Raw object.

    Example:
        from scipy.signal import butter
        sos = butter(4, [1, 40], btype="bandpass", fs=128, output="sos")
        SOSFilt(sos)
    """

    def __init__(self, sos: np.ndarray):
        self.sos = sos

    def run(self, raw: BaseRaw) -> BaseRaw:
        raw.load_data()
        raw.apply_function(lambda data: sosfilt(self.sos, data))
        return raw
