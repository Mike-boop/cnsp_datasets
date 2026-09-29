from mne.io import BaseRaw

from cnsp_datasets.preprocess.base import NeuralPreprocStep


class FillBads(NeuralPreprocStep):
    """
    Replaces data in channels marked bad in raw.info['bads'] with a fixed value.

    Example:
        FillBads(fill_value=0.0)
    """

    def __init__(self, fill_value: float = 0.0):
        self.fill_value = fill_value

    def run(self, raw: BaseRaw) -> BaseRaw:
        raw = raw.copy().load_data()
        bad_idxs = [raw.ch_names.index(ch) for ch in raw.info["bads"]]
        raw._data[bad_idxs, :] = self.fill_value
        return raw

    def __repr__(self) -> str:
        return f"FillBads(fill_value={self.fill_value})"
