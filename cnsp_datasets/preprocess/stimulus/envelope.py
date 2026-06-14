import numpy as np
from scipy.signal import hilbert

from cnsp_datasets.preprocess.base import StimulusPreprocStep, StimulusData


class HilbertEnvelope(StimulusPreprocStep):
    """
    Extracts the amplitude envelope of a stimulus via the Hilbert transform.

    output_feature_name defaults to "envelope", so applying this step to an
    "audio" stimulus will add a new StimulusRecord with feature_name="envelope".
    """

    def __init__(self, output_feature_name: str = "envelope"):
        self.output_feature_name = output_feature_name

    def run(self, data: StimulusData) -> StimulusData:
        envelope = np.abs(hilbert(data["data"], axis=-1))
        return {"fs": data["fs"], "data": envelope}
