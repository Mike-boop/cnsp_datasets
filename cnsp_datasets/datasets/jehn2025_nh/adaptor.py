from cnsp_datasets.datasets.jehn2025_base.adaptor import Jehn2025Adaptor


class Jehn2025NHAdaptor(Jehn2025Adaptor):
    """jehn2025_nh: the nh group's archive."""

    def __init__(self, download_dir: str, **options):
        super().__init__(download_dir, h5_fname="nh_dataset_1kHz.hdf5", **options)


ADAPTOR = Jehn2025NHAdaptor
