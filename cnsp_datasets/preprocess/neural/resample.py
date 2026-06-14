from mne.io import BaseRaw

from cnsp_datasets.preprocess.base import NeuralPreprocStep
from cnsp_datasets.preprocess.base.signal import Resample
from cnsp_datasets.preprocess.base.mne_helpers import set_raw_sfreq


class ResampleNeural(Resample, NeuralPreprocStep):
    """
    Resamples an MNE Raw object to a target sampling frequency.

    Example:
        ResampleNeural(target_fs=128)
    """

    def run(self, raw: BaseRaw) -> BaseRaw:
        raw.resample(sfreq=self.target_fs, npad="auto", window="hann", n_jobs=1)
        return raw
