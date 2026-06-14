from cnsp_datasets.preprocess.base import StimulusPreprocStep, StimulusData
from cnsp_datasets.preprocess.base.signal import Resample


class ResampleStimulus(Resample, StimulusPreprocStep):
    """
    Resamples stimulus data to a target sampling frequency.

    Example:
        ResampleStimulus(target_fs=16000)
    """

    def __init__(self, target_fs: int, output_feature_name: str | None = None):
        super().__init__(target_fs)
        self.output_feature_name = output_feature_name

    def run(self, data: StimulusData) -> StimulusData:
        resampled = self._resample_array(data["data"], data["fs"])
        return {"fs": self.target_fs, "data": resampled}
