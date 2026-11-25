from cnsp_datasets.datasets.jehn2025_base.adaptor import Jehn2025Adaptor


class Jehn2025HIAdaptor(Jehn2025Adaptor):
    """jehn2025_hi: the hi group's archive."""

    def __init__(self, download_dir: str, **options):
        super().__init__(download_dir, h5_fname="hi_dataset_1kHz.hdf5", **options)


ADAPTOR = Jehn2025HIAdaptor
