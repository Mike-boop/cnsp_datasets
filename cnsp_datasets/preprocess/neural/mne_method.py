from mne.io import BaseRaw

from cnsp_datasets.preprocess.base import NeuralPreprocStep


class MNERawMethod(NeuralPreprocStep):
    """
    Calls a named method on an MNE Raw object.

    Example:
        MNERawMethod("filter", l_freq=1.0, h_freq=40.0)
        MNERawMethod("set_eeg_reference", ref_channels="average")
    """

    def __init__(self, method: str, *args, load_data: bool = True, **kwargs):
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.load_data = load_data

    def run(self, raw: BaseRaw) -> BaseRaw:
        if self.load_data:
            raw.load_data()
        return getattr(raw, self.method)(*self.args, **self.kwargs)

    def __repr__(self) -> str:
        return f"MNERawMethod({self.method!r})"
