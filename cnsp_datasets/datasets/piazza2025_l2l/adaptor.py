from cnsp_datasets.datasets.piazza2025_base.adaptor import Piazza2025Adaptor


class Piazza2025L2LAdaptor(Piazza2025Adaptor):
    """Piazza et al. 2025, group l2l (see Piazza2025Adaptor)."""

    def __init__(self, download_dir: str):
        super().__init__(download_dir, group="l2l")


ADAPTOR = Piazza2025L2LAdaptor
