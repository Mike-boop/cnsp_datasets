from functools import partial
from cnsp_datasets.datasets.jehn2025_base.adaptor import Jehn2025Adaptor as BaseAdaptor

ADAPTOR = partial(BaseAdaptor, h5_fname="nh_dataset_1kHz.hdf5")