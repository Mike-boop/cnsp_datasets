from functools import partial

from cnsp_datasets.datasets.piazza2025_base.adaptor import Piazza2025Adaptor

ADAPTOR = partial(Piazza2025Adaptor, group="l1l")
